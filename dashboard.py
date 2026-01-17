import streamlit as st
import pandas as pd
from google.oauth2 import service_account
from googleapiclient.discovery import build
import io
import csv
import os

# ==========================================
# 1. الإعدادات
# ==========================================
FOLDER_ID = "1kgzKj9sn8pQVjr78XcN7_iF5KLmflwME"
SCOPES = ['https://www.googleapis.com/auth/drive.readonly']

# القاموس المحدث بناءً على الأسماء التي أرسلتها
COLUMN_MAPPING = {
    # السعر
    'قيمة الصفقات': 'السعر', 'السعر': 'السعر', 'مبلغ الصفقة': 'السعر', 'Price': 'السعر', 
    'سعر الوحدة': 'السعر', 'Total Price': 'السعر',
    
    # المساحة (تم إضافة المساحة M2)
    'المساحة M2': 'المساحة', 'المساحة': 'المساحة', 'المساحة بالأمتار': 'المساحة', 
    'Area': 'المساحة', 'مساحة الوحدة': 'المساحة', 'Size': 'المساحة', 
    
    # الحي والمدينة
    'الحي': 'الحي', 'اسم الحي': 'الحي', 'District Name': 'الحي', 'الموقع': 'الحي',
    'المدينة': 'المدينة', 'City': 'المدينة', 'المنطقة': 'المنطقة',
    
    # النوع (تمت إضافة تصنيف العقار ونوع العقار)
    'نوع العقار': 'نوع_العقار_الخام', 'تصنيف العقار': 'نوع_العقار_الخام', 
    'الوحدة': 'نوع_العقار_الخام', 'النوع': 'نوع_العقار_الخام', 'Property Type': 'نوع_العقار_الخام',
    
    # إضافي
    'عدد الصكوك': 'عدد_الصكوك', 'المطور': 'اسم_المطور', 'اسم المشروع': 'اسم_المشروع'
}

class RealEstateBot:
    def __init__(self):
        self.log_messages = []
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

                    is_dev = any(x in file['name'].lower() for x in ['dev', 'مطور', 'brochure', 'projects'])
                    source_type = 'مطورين' if is_dev else 'عام'
                    
                    # محاولة قراءة ذكية (سواء كانت فواصل عادية أو منقوطة)
                    try:
                        # نجرب الفاصلة المنقوطة أولاً (لأن ملفات العدل غالباً تستخدمها)
                        df_temp = pd.read_csv(io.StringIO(content_str), sep=';', engine='python')
                        if len(df_temp.columns) <= 1: # إذا فشل الفصل، نجرب الفاصلة العادية
                            df_temp = pd.read_csv(io.StringIO(content_str), sep=',', engine='python')
                    except:
                        # محاولة أخيرة بفاصل تلقائي
                        df_temp = pd.read_csv(io.StringIO(content_str), sep=None, engine='python')

                    if 'MOJ' in file['name'].upper():
                         source_type = 'عدل'

                    # ---------------------------------------------
                    # المعالجة والتوحيد
                    # ---------------------------------------------
                    df_temp.columns = df_temp.columns.str.strip() # تنظيف أسماء الأعمدة من المسافات
                    df_temp.rename(columns=COLUMN_MAPPING, inplace=True)
                    df_temp = df_temp.loc[:, ~df_temp.columns.duplicated()]

                    # التأكد من وجود الأعمدة الأساسية بعد التوحيد
                    if 'السعر' in df_temp.columns and 'المساحة' in df_temp.columns:
                        
                        # فلترة الرياض (إذا وجد عمود المدينة)
                        if 'المدينة' in df_temp.columns:
                            df_temp['المدينة'] = df_temp['المدينة'].astype(str).str.strip()
                            df_temp = df_temp[df_temp['المدينة'] == 'الرياض']

                        # تنظيف الأرقام
                        for col in ['السعر', 'المساحة']:
                            df_temp[col] = df_temp[col].astype(str).str.replace(',', '').str.replace(r'[^\d.]', '', regex=True)
                            df_temp[col] = pd.to_numeric(df_temp[col], errors='coerce')
                        
                        df_temp.dropna(subset=['السعر', 'المساحة'], inplace=True)
                        
                        if not df_temp.empty:
                            df_temp['سعر_المتر'] = df_temp['السعر'] / df_temp['المساحة']
                            df_temp['Source_File'] = file['name']
                            df_temp['Source_Type'] = source_type
                            if 'نوع_العقار_الخام' not in df_temp.columns: df_temp['نوع_العقار_الخام'] = "غير محدد"

                            # تحديد الأعمدة المطلوبة للسحب
                            cols = ['الحي', 'السعر', 'المساحة', 'سعر_المتر', 'نوع_العقار_الخام', 'Source_File', 'Source_Type', 'اسم_المطور', 'عدد_الصكوك']
                            found_cols = [c for c in cols if c in df_temp.columns]
                            all_data.append(df_temp[found_cols])

                except Exception as e:
                    print(f"خطأ في ملف {file['name']}: {e}")

            if all_data:
                total_df = pd.concat(all_data, ignore_index=True)
                medians = total_df.groupby('الحي')['سعر_المتر'].median().to_dict()

                # تصنيف ذكي
                def classify(row):
                    raw = str(row.get('نوع_العقار_الخام', '')).strip().lower()
                    if row.get('Source_Type') == 'سوق_حالي (مطورين)':
                        if 'شقة' in raw: return 'مبني (شقة - مطور)'
                        if 'فيلا' in raw: return 'مبني (فيلا - مطور)'
                        return 'أرض (مطور)'
                    
                    if 'أرض' in raw: return "أرض"
                    if 'تجاري' in raw: return "أرض (تجاري)"
                    
                    # تخمين
                    area, ppm, dist = row['المساحة'], row['سعر_المتر'], row['الحي']
                    if area < 200: return "مبني (شقة)"
                    avg = medians.get(dist, 0)
                    if avg > 0 and ppm > (avg * 1.5) and area < 900: return "مبني (فيلا/بيت)"
                    return "أرض" # الافتراضي

                total_df['نوع_العقار'] = total_df.apply(classify, axis=1)
                return total_df
            return pd.DataFrame()

        except Exception as e:
            st.error(f"خطأ الاتصال: {e}")
            return pd.DataFrame()

# ==========================================
# 2. الواجهة
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
        st.markdown(f"**📂 الملفات المكتشفة:** {bot.files_found_count}")
        
        if not bot.df.empty:
            st.markdown("### 📊 حالة السحب")
            file_stats = bot.df['Source_File'].value_counts().reset_index()
            file_stats.columns = ['اسم الملف', 'عدد الصفقات']
            st.dataframe(file_stats, hide_index=True, use_container_width=True)
            st.caption(f"إجمالي الصفقات: {len(bot.df):,}")
        else:
            st.error("⚠️ لم يتم سحب أي بيانات. تأكد من تطابق أسماء الأعمدة.")

st.title("🧐 مدقق البيانات العقارية")

if 'bot' not in st.session_state:
    with st.spinner("جاري قراءة وتحليل الملفات..."):
        try:
            st.session_state.bot = RealEstateBot()
        except Exception as e:
            st.error(f"حدث خطأ: {e}")

if 'bot' in st.session_state and hasattr(st.session_state.bot, 'df'):
    df = st.session_state.bot.df
    
    if df.empty:
        st.warning("⚠️ لا توجد بيانات للعرض.")
    else:
        # الفلترة
        st.markdown("### 🧹 فلترة الأسعار")
        c1, c2 = st.columns(2)
        with c1: min_p = st.number_input("أقل سعر للمتر:", value=100, step=100)
        with c2: max_p = st.number_input("أعلى سعر للمتر:", value=50000, step=1000)

        clean_df = df[(df['سعر_المتر'] >= min_p) & (df['سعر_المتر'] <= max_p)].copy()
        
        st.divider()
        st.markdown("### 🔍 تحليل الأحياء")
        
        sc1, sc2 = st.columns([3, 1])
        search = sc1.text_input("اسم الحي:", "الملقا")
        
        if sc2.button("تحليل 📊", use_container_width=True, type="primary") or search:
            res = clean_df[clean_df['الحي'].astype(str).str.contains(search, na=False)]
            
            if res.empty:
                st.info(f"لا توجد نتائج لحي '{search}'")
            else:
                l_df = res[res['نوع_العقار'].str.contains('أرض', na=False)]
                b_df = res[res['نوع_العقار'].str.contains('مبني', na=False)]
                
                m1, m2, m3, m4 = st.columns(4)
                m1.metric("أراضي", f"{len(l_df):,}")
                m2.metric("متوسط أرض", f"{l_df['سعر_المتر'].median():,.0f}")
                m3.metric("مباني", f"{len(b_df):,}")
                m4.metric("متوسط مبنى", f"{b_df['سعر_المتر'].median():,.0f}")
                
                st.markdown("#### تفاصيل الصفقات:")
                
                # تجهيز الأعمدة للعرض (بما فيها عدد الصكوك الجديد)
                view_cols = ['الحي', 'نوع_العقار', 'المساحة', 'السعر', 'سعر_المتر', 'Source_File']
                if 'عدد_الصكوك' in res.columns: view_cols.insert(2, 'عدد_الصكوك')
                
                st.dataframe(
                    res[view_cols].style.format({'السعر':'{:,.0f}', 'سعر_المتر':'{:,.0f}'}), 
                    use_container_width=True
                )
                
