import streamlit as st
import pandas as pd
from google.oauth2 import service_account
from googleapiclient.discovery import build
import io
import os
import numpy as np

# ==========================================
# 1. إعدادات الاتصال والتعريفات (Backend)
# ==========================================
FOLDER_ID = "1kgzKj9sn8pQVjr78XcN7_iF5KLmflwME"
SCOPES = ['https://www.googleapis.com/auth/drive.readonly']

# القاموس الشامل (Universal Mapping)
COLUMN_MAPPING = {
    # السعر
    'قيمة الصفقات': 'السعر', 'السعر': 'السعر', 'مبلغ الصفقة': 'السعر', 'Price': 'السعر', 
    'سعر الوحدة': 'السعر', 'Total Price': 'السعر',
    # المساحة
    'المساحة M2': 'المساحة', 'المساحة': 'المساحة', 'المساحة بالأمتار': 'المساحة', 
    'Area': 'المساحة', 'Size': 'المساحة', 'مساحة الوحدة': 'المساحة',
    # الموقع
    'الحي': 'الحي', 'اسم الحي': 'الحي', 'District Name': 'الحي', 'الموقع': 'الحي',
    'المدينة': 'المدينة', 'City': 'المدينة', 'المنطقة': 'المدينة',
    # النوع
    'نوع العقار': 'نوع_العقار_الخام', 'تصنيف العقار': 'نوع_العقار_الخام', 
    'الوحدة': 'نوع_العقار_الخام', 'النوع': 'نوع_العقار_الخام', 'Property Type': 'نوع_العقار_الخام',
    # إضافي
    'عدد الصكوك': 'عدد_الصكوك', 'المطور': 'اسم_المطور'
}

class RealEstateBot:
    def __init__(self):
        self.files_found_count = 0
        self.creds = self.get_creds()
        self.service = build('drive', 'v3', credentials=self.creds)
        self.df = self.load_data_from_drive()

    def get_creds(self):
        if 'gcp_service_account' in st.secrets:
            return service_account.Credentials.from_service_account_info(st.secrets['gcp_service_account'], scopes=SCOPES)
        elif os.path.exists('credentials.json'):
            return service_account.Credentials.from_service_account_file('credentials.json', scopes=SCOPES)
        else:
            return None

    def load_data_from_drive(self):
        all_data = []
        if not self.creds: return pd.DataFrame()

        try:
            results = self.service.files().list(
                q=f"'{FOLDER_ID}' in parents and trashed=false",
                fields="files(id, name)").execute()
            files = results.get('files', [])
            self.files_found_count = len(files)

            for file in files:
                if not file['name'].lower().endswith('.csv'): continue
                
                try:
                    request = self.service.files().get_media(fileId=file['id'])
                    content_bytes = request.execute()
                    try: content_str = content_bytes.decode('utf-8-sig')
                    except: content_str = content_bytes.decode('utf-16')

                    # صائد العناوين (Header Hunter)
                    lines = content_str.splitlines()
                    header_idx = 0; sep = ','
                    found_header = False
                    for i, line in enumerate(lines[:30]):
                        if any(x in line for x in ['المساحة M2', 'قيمة الصفقات', 'المساحة', 'Price']):
                            header_idx = i; found_header = True
                            if ';' in line: sep = ';'
                            elif '\t' in line: sep = '\t'
                            break
                    
                    if found_header:
                        df_temp = pd.read_csv(io.StringIO(content_str), sep=sep, header=header_idx, engine='python')
                    else:
                        df_temp = pd.read_csv(io.StringIO(content_str), sep=None, engine='python')

                    # تحديد المصدر
                    is_dev = any(x in file['name'].lower() for x in ['dev', 'مطور', 'brochure'])
                    source_type = 'مطورين' if is_dev else 'عام'
                    if 'MOJ' in file['name'].upper() or 'عدد الصكوك' in df_temp.columns: source_type = 'عدل'

                    # التنظيف والتوحيد
                    df_temp.columns = df_temp.columns.str.strip()
                    df_temp.rename(columns=COLUMN_MAPPING, inplace=True)
                    df_temp = df_temp.loc[:, ~df_temp.columns.duplicated()]

                    if 'السعر' in df_temp.columns and 'المساحة' in df_temp.columns:
                        for col in ['السعر', 'المساحة']:
                            df_temp[col] = df_temp[col].astype(str).str.replace(',', '').str.replace(r'[^\d.]', '', regex=True)
                            df_temp[col] = pd.to_numeric(df_temp[col], errors='coerce')
                        
                        df_temp.dropna(subset=['السعر', 'المساحة'], inplace=True)
                        df_temp = df_temp[df_temp['المساحة'] > 0]
                        
                        df_temp['سعر_المتر'] = df_temp['السعر'] / df_temp['المساحة']
                        df_temp['Source_File'] = file['name']
                        df_temp['Source_Type'] = source_type
                        
                        if 'الحي' in df_temp.columns: df_temp['الحي'] = df_temp['الحي'].astype(str).str.strip()
                        
                        for needed in ['نوع_العقار_الخام', 'اسم_المطور', 'عدد_الصكوك']:
                            if needed not in df_temp.columns: df_temp[needed] = "غير محدد"

                        cols = ['الحي', 'السعر', 'المساحة', 'سعر_المتر', 'نوع_العقار_الخام', 'Source_File', 'Source_Type', 'اسم_المطور', 'عدد_الصكوك']
                        all_data.append(df_temp[[c for c in cols if c in df_temp.columns]])

                except Exception as e:
                    print(f"Error reading {file['name']}: {e}")

            if all_data:
                total_df = pd.concat(all_data, ignore_index=True)
                medians = {}
                if 'الحي' in total_df.columns:
                    medians = total_df.groupby('الحي')['سعر_المتر'].median().to_dict()

                def classify(row):
                    raw = str(row.get('نوع_العقار_الخام', '')).strip().lower()
                    stype = row.get('Source_Type', '')
                    if stype == 'مطورين':
                        if 'شقة' in raw: return 'مبني (شقة - مطور)'
                        return 'مبني (فيلا - مطور)' if 'فيلا' in raw else 'أرض (مطور)'
                    if 'أرض' in raw: return "أرض"
                    if 'شقة' in raw: return "مبني (شقة)"
                    if 'فيلا' in raw or 'بيت' in raw: return "مبني (فيلا)"
                    
                    # التخمين الذكي
                    area, ppm, dist = row.get('المساحة',0), row.get('سعر_المتر',0), row.get('الحي','')
                    if area < 250: return "مبني (شقة)"
                    avg = medians.get(dist, 0)
                    if avg > 0 and ppm > (avg * 1.5) and area < 900: return "مبني (فيلا/بيت)"
                    return "أرض"

                total_df['نوع_العقار'] = total_df.apply(classify, axis=1)
                return total_df
            return pd.DataFrame()
        except: return pd.DataFrame()

# ==========================================
# 2. واجهة التطبيق (Frontend)
# ==========================================
st.set_page_config(page_title="المستشار العقاري الذكي", layout="wide", page_icon="🏗️")

# --- التنسيق الجمالي (CSS) ---
st.markdown("""
<style>
    .metric-card {background-color: #f0f2f6; border-radius: 10px; padding: 15px; text-align: center; border: 1px solid #e0e0e0;}
    .big-font {font-size: 18px !important; font-weight: bold; color: #31333F;}
    .success-text {color: #008000; font-weight: bold;}
    .danger-text {color: #FF0000; font-weight: bold;}
</style>
""", unsafe_allow_html=True)

# --- التهيئة ---
if 'bot' not in st.session_state:
    with st.spinner("جاري تهيئة النظام وسحب البيانات..."):
        st.session_state.bot = RealEstateBot()

# --- القائمة الجانبية ---
with st.sidebar:
    st.image("https://cdn-icons-png.flaticon.com/512/609/609803.png", width=80)
    st.title("لوحة التحكم")
    
    if st.button("🔄 تحديث البيانات", type="primary", use_container_width=True):
        st.cache_data.clear()
        st.rerun()

    if hasattr(st.session_state.bot, 'df') and not st.session_state.bot.df.empty:
        st.success(f"تم تحميل {len(st.session_state.bot.df)} صفقة")
        st.markdown("---")
        st.markdown("### 📁 المصادر")
        stats = st.session_state.bot.df['Source_File'].value_counts().reset_index()
        stats.columns = ['الملف', 'العدد']
        st.dataframe(stats, hide_index=True, use_container_width=True)

# --- المحتوى الرئيسي ---
st.title("🏗️ نظام دعم القرار العقاري")

tab1, tab2 = st.tabs(["📊 تحليل السوق (Market Analysis)", "💰 دراسة الجدوى (Feasibility Study)"])

df = st.session_state.bot.df if hasattr(st.session_state.bot, 'df') else pd.DataFrame()

# ==================== تبويب 1: تحليل السوق ====================
with tab1:
    if df.empty:
        st.warning("⚠️ لا توجد بيانات. تأكد من صحة الملفات.")
    else:
        # فلاتر علوية
        col_f1, col_f2, col_f3 = st.columns(3)
        with col_f1:
            districts = sorted(df['الحي'].unique().tolist())
            selected_district = st.selectbox("اختر الحي:", ["الكل"] + districts)
        with col_f2:
            prop_type = st.selectbox("نوع العقار:", ["الكل", "أرض", "مبني"])
        with col_f3:
            price_range = st.slider("نطاق سعر المتر:", 0, 30000, (500, 15000))

        # تطبيق الفلترة
        filtered_df = df.copy()
        if selected_district != "الكل": filtered_df = filtered_df[filtered_df['الحي'] == selected_district]
        if prop_type != "الكل": filtered_df = filtered_df[filtered_df['نوع_العقار'].str.contains(prop_type)]
        filtered_df = filtered_df[(filtered_df['سعر_المتر'] >= price_range[0]) & (filtered_df['سعر_المتر'] <= price_range[1])]

        st.markdown("---")
        
        # المؤشرات الرئيسية
        m1, m2, m3, m4 = st.columns(4)
        m1.metric("عدد الصفقات", f"{len(filtered_df):,}")
        m2.metric("متوسط سعر المتر", f"{filtered_df['سعر_المتر'].median():,.0f} ريال")
        m3.metric("أعلى سعر متر", f"{filtered_df['سعر_المتر'].max():,.0f} ريال")
        m4.metric("أقل سعر متر", f"{filtered_df['سعر_المتر'].min():,.0f} ريال")

        # الجدول
        st.dataframe(
            filtered_df[['الحي', 'نوع_العقار', 'المساحة', 'السعر', 'سعر_المتر', 'Source_File']].sort_values('سعر_المتر'),
            use_container_width=True
        )

# ==================== تبويب 2: دراسة الجدوى (الجديد) ====================
with tab2:
    st.markdown("### 🧠 حاسبة الفرص الاستثمارية")
    st.info("أدخل بيانات الأرض التي تريد شراءها، وسنقارنها بمتوسطات السوق الفعلية من ملفاتك.")

    if df.empty:
        st.error("يجب تحميل البيانات أولاً لإجراء الدراسة.")
    else:
        # 1. مدخلات الدراسة
        with st.container():
            c1, c2, c3 = st.columns(3)
            with c1:
                target_district = st.selectbox("📍 الحي المستهدف", sorted(df['الحي'].unique()))
            with c2:
                land_area = st.number_input("📐 مساحة الأرض (م2)", value=300, step=10)
            with c3:
                asking_price_per_meter = st.number_input("💰 سعر المتر المعروض (ريال)", value=3500, step=100)

            c4, c5 = st.columns(2)
            with c4:
                build_cost_meter = st.number_input("🔨 تكلفة بناء المتر (تقديري)", value=1800, step=50)
            with c5:
                built_up_area_ratio = st.slider("نسبة مساحة البناء (المسطحات)", 1.0, 3.5, 2.2, help="كم متر مربع مباني لكل متر أرض؟ (مثلاً 2.2 للفلل)")

        st.markdown("---")

        # 2. جلب بيانات المقارنة من قاعدة البيانات
        # بيانات الأراضي في نفس الحي
        district_lands = df[(df['الحي'] == target_district) & (df['نوع_العقار'].str.contains('أرض'))]
        # بيانات المباني في نفس الحي
        district_buildings = df[(df['الحي'] == target_district) & (df['نوع_العقار'].str.contains('مبني'))]

        avg_land_market = district_lands['سعر_المتر'].median() if not district_lands.empty else 0
        avg_build_market = district_buildings['سعر_المتر'].median() if not district_buildings.empty else 0

        # 3. التحليل والنتائج
        col_res1, col_res2 = st.columns([1, 1])

        with col_res1:
            st.markdown("#### 📊 تقييم سعر الأرض")
            if avg_land_market > 0:
                diff = ((asking_price_per_meter - avg_land_market) / avg_land_market) * 100
                st.write(f"متوسط سعر المتر (أراضي) في {target_district}: **{avg_land_market:,.0f} ريال**")
                
                if diff < -5:
                    st.success(f"✅ فرصة! السعر المعروض أقل من السوق بـ {abs(diff):.1f}%")
                elif diff > 5:
                    st.error(f"❌ انتبه! السعر المعروض أعلى من السوق بـ {diff:.1f}%")
                else:
                    st.warning(f"⚖️ السعر عادل (قريب جداً من متوسط السوق)")
                
                # مقياس بصري
                st.progress(min(max(0.5 + (diff/100), 0.0), 1.0))
            else:
                st.warning("لا توجد بيانات كافية عن الأراضي في هذا الحي للمقارنة.")

        with col_res2:
            st.markdown("#### 🏗️ الجدوى الاقتصادية (المطور)")
            
            # الحسابات
            land_cost_total = land_area * asking_price_per_meter
            total_built_area = land_area * built_up_area_ratio
            construction_cost_total = total_built_area * build_cost_meter
            total_project_cost = land_cost_total + construction_cost_total
            
            # توقع البيع (بناءً على متوسط بيع المباني في الحي)
            if avg_build_market > 0:
                # نحسب سعر بيع الوحدة بناء على سعر متر المبنى في السوق * مساحة الأرض (تقريبياً كوحدة)
                # أو الأفضل: سعر متر المبنى * مساحة الأرض (لأن صفقات الفلل تباع كأرض ومبنى)
                # سنستخدم متوسط سعر متر المبنى (الذي يشمل الأرض والبناء) من السوق
                expected_revenue = land_area * avg_build_market 
                
                profit = expected_revenue - total_project_cost
                roi = (profit / total_project_cost) * 100

                st.write(f"التكلفة الإجمالية (أرض + بناء): **{total_project_cost:,.0f} ريال**")
                st.write(f"سعر البيع المتوقع (حسب السوق): **{expected_revenue:,.0f} ريال**")
                
                st.markdown("---")
                if profit > 0:
                    st.markdown(f"<h3 style='color:green'>الربح المتوقع: {profit:,.0f} ريال (+{roi:.1f}%)</h3>", unsafe_allow_html=True)
                else:
                    st.markdown(f"<h3 style='color:red'>الخسارة المتوقعة: {profit:,.0f} ريال ({roi:.1f}%)</h3>", unsafe_allow_html=True)
                    st.caption("سبب الخسارة المحتمل: إما تكلفة الأرض عالية جداً، أو تكلفة البناء المدخلة مرتفعة مقارنة بأسعار بيع الجاهز في السوق.")
            else:
                st.warning("لا توجد بيانات صفقات مباني (فلل/شقق) في هذا الحي لحساب سعر البيع المتوقع.")
