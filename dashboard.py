import streamlit as st
import pandas as pd
from google.oauth2 import service_account
from googleapiclient.discovery import build
import io
import os

# ==========================================
# 1. الإعدادات
# ==========================================
FOLDER_ID = "1kgzKj9sn8pQVjr78XcN7_iF5KLmflwME"
SCOPES = ['https://www.googleapis.com/auth/drive.readonly']

# القاموس الشامل
COLUMN_MAPPING = {
    # السعر
    'قيمة الصفقات': 'السعر', 'السعر': 'السعر', 'مبلغ الصفقة': 'السعر', 'Price': 'السعر', 
    'سعر الوحدة': 'السعر', 'Total Price': 'السعر',
    
    # المساحة
    'المساحة M2': 'المساحة', 'المساحة': 'المساحة', 'المساحة بالأمتار': 'المساحة', 
    'Area': 'المساحة', 'Size': 'المساحة', 'مساحة الوحدة': 'المساحة',
    
    # الحي والمدينة
    'الحي': 'الحي', 'اسم الحي': 'الحي', 'District Name': 'الحي', 'الموقع': 'الحي',
    'المدينة': 'المدينة', 'City': 'المدينة', 'المنطقة': 'المدينة', # دمجنا المنطقة مع المدينة
    
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
                    # تحميل المحتوى
                    request = self.service.files().get_media(fileId=file['id'])
                    content_bytes = request.execute()
                    try: content_str = content_bytes.decode('utf-8-sig')
                    except: content_str = content_bytes.decode('utf-16')

                    # ---------------------------------------------------------
                    # 🕵️‍♂️ الخوارزمية الذكية: صائد العناوين (Header Hunter)
                    # ---------------------------------------------------------
                    lines = content_str.splitlines()
                    header_row_index = 0
                    sep = ',' # الفاصل الافتراضي
                    found_header = False

                    # نبحث في أول 20 سطر عن الكلمات المميزة للملف
                    for i, line in enumerate(lines[:30]):
                        if 'المساحة M2' in line or 'قيمة الصفقات' in line or 'المساحة' in line:
                            header_row_index = i
                            found_header = True
                            # محاولة اكتشاف الفاصل (فاصلة أو فاصلة منقوطة)
                            if ';' in line: sep = ';'
                            elif '\t' in line: sep = '\t'
                            else: sep = ','
                            break
                    
                    # القراءة بناءً على ما وجدناه
                    if found_header:
                        # نقرأ الملف بدءاً من سطر العناوين الصحيح
                        df_temp = pd.read_csv(io.StringIO(content_str), sep=sep, header=header_row_index, engine='python')
                    else:
                        # محاولة تقليدية
                        df_temp = pd.read_csv(io.StringIO(content_str), sep=None, engine='python')

                    # تحديد نوع المصدر
                    is_dev = any(x in file['name'].lower() for x in ['dev', 'مطور', 'brochure', 'projects'])
                    source_type = 'مطورين' if is_dev else 'عام'
                    if 'MOJ' in file['name'].upper() or 'عدد الصكوك' in df_temp.columns: source_type = 'عدل'

                    # ---------------------------------------------------------
                    # المعالجة والتوحيد
                    # ---------------------------------------------------------
                    df_temp.columns = df_temp.columns.str.strip() # تنظيف أسماء الأعمدة
                    df_temp.rename(columns=COLUMN_MAPPING, inplace=True)
                    df_temp = df_temp.loc[:, ~df_temp.columns.duplicated()]

                    # التأكد من نجاح العملية (وجود السعر والمساحة)
                    if 'السعر' in df_temp.columns and 'المساحة' in df_temp.columns:
                        
                        # تنظيف الأرقام (إزالة الفواصل والنصوص)
                        for col in ['السعر', 'المساحة']:
                            df_temp[col] = df_temp[col].astype(str).str.replace(',', '').str.replace(r'[^\d.]', '', regex=True)
                            df_temp[col] = pd.to_numeric(df_temp[col], errors='coerce')
                        
                        # حذف الصفوف الفارغة أو الصفرية
                        df_temp.dropna(subset=['السعر', 'المساحة'], inplace=True)
                        df_temp = df_temp[df_temp['المساحة'] > 0]
                        
                        # إضافة البيانات الوصفية
                        df_temp['سعر_المتر'] = df_temp['السعر'] / df_temp['المساحة']
                        df_temp['Source_File'] = file['name']
                        df_temp['Source_Type'] = source_type
                        
                        # معالجة الحي (تأكد أنها نص)
                        if 'الحي' in df_temp.columns:
                            df_temp['الحي'] = df_temp['الحي'].astype(str)

                        # إضافة الأعمدة الناقصة لتوحيد الجدول
                        for needed_col in ['نوع_العقار_الخام', 'اسم_المطور', 'عدد_الصكوك']:
                            if needed_col not in df_temp.columns:
                                df_temp[needed_col] = "غير محدد"

                        # اختيار الأعمدة النهائية
                        cols = ['الحي', 'السعر', 'المساحة', 'سعر_المتر', 'نوع_العقار_الخام', 'Source_File', 'Source_Type', 'اسم_المطور', 'عدد_الصكوك']
                        final_cols = [c for c in cols if c in df_temp.columns]
                        
                        all_data.append(df_temp[final_cols])
                        # print(f"✅ تم سحب {len(df_temp)} صف من {file['name']}")
                    else:
                        pass # print(f"❌ فشل: لم نجد أعمدة السعر والمساحة في {file['name']}")

                except Exception as e:
                    print(f"Error in {file['name']}: {e}")

            if all_data:
                total_df = pd.concat(all_data, ignore_index=True)
                
                # حساب متوسط الحي للتصنيف
                medians = {}
                if 'الحي' in total_df.columns:
                    medians = total_df.groupby('الحي')['سعر_المتر'].median().to_dict()

                # دالة التصنيف الموحد
                def classify(row):
                    raw = str(row.get('نوع_العقار_الخام', '')).strip().lower()
                    stype = row.get('Source_Type', '')
                    
                    # 1. تصنيف المطورين
                    if stype == 'مطورين':
                        if 'شقة' in raw: return 'مبني (شقة - مطور)'
                        if 'فيلا' in raw: return 'مبني (فيلا - مطور)'
                        return 'أرض (مطور)'
                    
                    # 2. تصنيف صريح
                    if 'أرض' in raw: return "أرض"
                    if 'شقة' in raw: return "مبني (شقة)"
                    if 'فيلا' in raw: return "مبني (فيلا)"
                    if 'بيت' in raw: return "مبني (بيت)"
                    if 'معرض' in raw or 'تجاري' in raw: return "أرض (تجاري)"

                    # 3. تصنيف تخميني (للبيانات الناقصة)
                    area, ppm = row.get('المساحة', 0), row.get('سعر_المتر', 0)
                    dist = row.get('الحي', '')
                    
                    if area < 250: return "مبني (شقة)" # مساحة صغيرة غالباً شقة
                    
                    # مقارنة بمتوسط الحي
                    avg = medians.get(dist, 0)
                    if avg > 0 and ppm > (avg * 1.5) and area < 900: 
                        return "مبني (فيلا/بيت)" # سعر متر غالي ومساحة متوسطة
                    
                    return "أرض" # الافتراضي

                total_df['نوع_العقار'] = total_df.apply(classify, axis=1)
                return total_df
            
            return pd.DataFrame()

        except Exception as e:
            st.error(f"خطأ الاتصال بقاعدة البيانات: {e}")
            return pd.DataFrame()

# ==========================================
# 2. واجهة المستخدم
# ==========================================
st.set_page_config(page_title="المحلل العقاري الذكي", layout="wide", page_icon="🏢")

with st.sidebar:
    st.header("⚙️ لوحة التحكم")
    if st.button("🔄 تحديث البيانات", use_container_width=True, type="primary"):
        st.cache_data.clear()
        st.rerun()
    
    if 'bot' in st.session_state and hasattr(st.session_state.bot, 'df'):
        bot = st.session_state.bot
        st.divider()
        if not bot.df.empty:
            st.markdown(f"**📂 الملفات النشطة:** {bot.df['Source_File'].nunique()}")
            # جدول الإحصائيات
            stats = bot.df.groupby('Source_File').size().reset_index(name='عدد الصفقات')
            st.dataframe(stats, hide_index=True, use_container_width=True)
            st.caption(f"الإجمالي: {len(bot.df):,} صفقة")
        else:
            st.error("⚠️ لم يتم العثور على بيانات.")

st.title("🧐 مدقق البيانات العقارية")

if 'bot' not in st.session_state:
    with st.spinner("جاري قراءة الملفات وتحليلها..."):
        try:
            st.session_state.bot = RealEstateBot()
        except Exception as e:
            st.error(f"حدث خطأ: {e}")

if 'bot' in st.session_state and hasattr(st.session_state.bot, 'df'):
    df = st.session_state.bot.df
    
    if df.empty:
        st.warning("⚠️ لا توجد بيانات. تأكد من صحة الملفات في جوجل درايف.")
    else:
        # الفلاتر
        st.markdown("### 🧹 فلترة البحث")
        col1, col2 = st.columns(2)
        with col1: min_p = st.number_input("أقل سعر للمتر:", 100, step=100)
        with col2: max_p = st.number_input("أعلى سعر للمتر:", 50000, value=50000, step=1000)

        # تطبيق الفلتر
        clean_df = df[(df['سعر_المتر'] >= min_p) & (df['سعر_المتر'] <= max_p)].copy()
        
        st.divider()
        st.markdown("### 🔍 نتائج التحليل")
        
        c_search, c_btn = st.columns([4, 1])
        search_q = c_search.text_input("ابحث عن حي:", "الملقا")
        run_search = c_btn.button("بحث 📊", type="primary", use_container_width=True)
        
        if run_search or search_q:
            # فلترة الحي
            res = clean_df[clean_df['الحي'].str.contains(search_q, na=False)]
            
            if res.empty:
                st.info(f"لا توجد صفقات لحي '{search_q}' ضمن النطاق السعري المحدد.")
            else:
                # تقسيم النتائج
                lands = res[res['نوع_العقار'].str.contains('أرض')]
                buildings = res[res['نوع_العقار'].str.contains('مبني')]
                
                # بطاقات الأرقام
                k1, k2, k3, k4 = st.columns(4)
                k1.metric("عدد الأراضي", f"{len(lands):,}")
                k2.metric("متوسط متر الأرض", f"{lands['سعر_المتر'].median():,.0f}")
                k3.metric("عدد المباني", f"{len(buildings):,}")
                k4.metric("متوسط متر المبنى", f"{buildings['سعر_المتر'].median():,.0f}")
                
                st.markdown("#### 📋 تفاصيل الصفقات")
                # ترتيب الأعمدة للعرض
                display_cols = ['الحي', 'نوع_العقار', 'المساحة', 'السعر', 'سعر_المتر', 'عدد_الصكوك', 'Source_File']
                final_display = [c for c in display_cols if c in res.columns]
                
                st.dataframe(
                    res[final_display].sort_values('سعر_المتر').style.format({
                        'السعر': '{:,.0f}', 
                        'سعر_المتر': '{:,.0f}',
                        'المساحة': '{:,.2f}'
                    }),
                    use_container_width=True
                )
