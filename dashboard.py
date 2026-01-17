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

# قائمة التوحيد (سنقوم بتحديثها بناء على ما سنكتشفه)
COLUMN_MAPPING = {
    'السعر': 'السعر', 'مبلغ الصفقة': 'السعر', 'Price': 'السعر', 'قيمة الصفقات': 'السعر', 'سعر الوحدة': 'السعر', 'Total Price': 'السعر',
    'المساحة': 'المساحة', 'المساحة بالأمتار': 'المساحة', 'Area': 'المساحة', 'مساحة الوحدة': 'المساحة', 'Size': 'المساحة',
    'الحي': 'الحي', 'اسم الحي': 'الحي', 'District Name': 'الحي', 'الموقع': 'الحي', 'District': 'الحي',
    'نوع العقار': 'نوع_العقار_الخام', 'تصنيف العقار': 'نوع_العقار_الخام', 'الوحدة': 'نوع_العقار_الخام', 'النوع': 'نوع_العقار_الخام', 'Property Type': 'نوع_العقار_الخام',
    'المدينة': 'المدينة', 'City': 'المدينة',
    'المطور': 'اسم_المطور', 'اسم المشروع': 'اسم_المشروع'
}

class RealEstateBot:
    def __init__(self):
        self.log_messages = []
        self.files_found_count = 0
        self.debug_info = []  # لتخزين معلومات التشخيص
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
                    # تحميل الملف
                    request = self.service.files().get_media(fileId=file['id'])
                    content_bytes = request.execute()
                    try: content_str = content_bytes.decode('utf-8-sig')
                    except: content_str = content_bytes.decode('utf-16')

                    # قراءة مبدئية
                    is_dev = any(x in file['name'].lower() for x in ['dev', 'مطور', 'brochure', 'projects'])
                    
                    if 'MOJ' in file['name'].upper():
                        f = io.StringIO(content_str)
                        reader = csv.reader(f, delimiter=';')
                        header_row = None; data_rows = []
                        for row in reader:
                            clean_row = [str(cell).strip() for cell in row]
                            if 'السعر' in clean_row and 'الحي' in clean_row: header_row = clean_row; continue
                            if header_row and len(clean_row) >= len(header_row): data_rows.append(clean_row[:len(header_row)])
                        df_temp = pd.DataFrame(data_rows, columns=header_row) if header_row else pd.DataFrame()
                        source_type = 'عدل'
                    else:
                        df_temp = pd.read_csv(io.StringIO(content_str), sep=None, engine='python')
                        source_type = 'مطورين' if is_dev else 'عام'

                    # ---------------------------------------------
                    # 🕵️‍♂️ منطقة التشخيص (حفظ أسماء الأعمدة الأصلية)
                    # ---------------------------------------------
                    raw_cols = list(df_temp.columns)
                    
                    # التنظيف والتوحيد
                    df_temp.columns = df_temp.columns.str.strip()
                    df_temp.rename(columns=COLUMN_MAPPING, inplace=True)
                    df_temp = df_temp.loc[:, ~df_temp.columns.duplicated()]

                    # حفظ سبب الاستبعاد إن وجد
                    status = "✅ تم السحب"
                    rows_before = len(df_temp)
                    
                    # الفحص 1: هل توجد أعمدة السعر والمساحة؟
                    if 'السعر' not in df_temp.columns or 'المساحة' not in df_temp.columns:
                        status = "❌ فشل: أعمدة السعر/المساحة مفقودة"
                        df_temp = pd.DataFrame() # تصفير
                    
                    # الفحص 2: فلترة المدينة (إذا وجدت)
                    elif 'المدينة' in df_temp.columns:
                         df_temp['المدينة'] = df_temp['المدينة'].astype(str).str.strip()
                         # df_temp = df_temp[df_temp['المدينة'] == 'الرياض'] # أوقفنا الفلترة مؤقتاً للتجربة

                    # التنظيف النهائي
                    if not df_temp.empty:
                        for col in ['السعر', 'المساحة']:
                            df_temp[col] = df_temp[col].astype(str).str.replace(',', '').str.replace(r'[^\d.]', '', regex=True)
                            df_temp[col] = pd.to_numeric(df_temp[col], errors='coerce')
                        
                        df_temp.dropna(subset=['السعر', 'المساحة'], inplace=True)
                        df_temp['سعر_المتر'] = df_temp['السعر'] / df_temp['المساحة']
                        df_temp['Source_File'] = file['name']
                        df_temp['Source_Type'] = source_type
                        
                        cols = ['الحي', 'السعر', 'المساحة', 'سعر_المتر', 'نوع_العقار_الخام', 'Source_File', 'Source_Type', 'اسم_المطور']
                        found = [c for c in cols if c in df_temp.columns]
                        all_data.append(df_temp[found])

                    # تسجيل المعلومات للمستخدم
                    self.debug_info.append({
                        "الملف": file['name'],
                        "الحالة": status,
                        "عدد_الصفوف_قبل": rows_before,
                        "عدد_الصفوف_بعد": len(df_temp),
                        "الأعمدة_الأصلية": str(raw_cols) # هنا السر
                    })

                except Exception as e:
                     self.debug_info.append({"الملف": file['name'], "الحالة": f"خطأ برمجي: {str(e)}", "الأعمدة_الأصلية": "-"})

            if all_data:
                total_df = pd.concat(all_data, ignore_index=True)
                # (تصنيف العقار - مبسط)
                if 'نوع_العقار_الخام' not in total_df.columns: total_df['نوع_العقار_الخام'] = 'غير محدد'
                total_df['نوع_العقار'] = total_df['نوع_العقار_الخام'].apply(lambda x: 'أرض' if 'أرض' in str(x) else 'مبني')
                return total_df
            return pd.DataFrame()

        except Exception as e:
            st.error(f"خطأ الاتصال: {e}")
            return pd.DataFrame()

# ==========================================
# 2. الواجهة
# ==========================================
st.set_page_config(page_title="مراقب البيانات", layout="wide")

with st.sidebar:
    st.title("⚙️ تشخيص الملفات")
    if st.button("🔄 تحديث وفحص", use_container_width=True, type="primary"):
        st.cache_data.clear()
        st.rerun()

    # عرض تقرير التشخيص
    if 'bot' in st.session_state:
        st.write("---")
        st.markdown("### 🕵️‍♂️ تقرير قراءة الملفات")
        for info in st.session_state.bot.debug_info:
            with st.expander(f"📄 {info['الملف']}"):
                st.write(f"**الحالة:** {info['الحالة']}")
                st.write(f"**الصفوف:** {info['عدد_الصفوف_بعد']} (من أصل {info['عدد_الصفوف_قبل']})")
                st.code(info['الأعمدة_الأصلية'], language="text")

# التطبيق الرئيسي
st.title("🧐 مدقق البيانات العقارية (وضع التشخيص)")

if 'bot' not in st.session_state:
    with st.spinner("جاري فحص الملفات..."):
        st.session_state.bot = RealEstateBot()

if 'bot' in st.session_state and hasattr(st.session_state.bot, 'df'):
    df = st.session_state.bot.df
    
    col1, col2 = st.columns([3,1])
    search = col1.text_input("بحث عن حي:", "الملقا")
    
    if not df.empty:
        # عرض البيانات
        res = df[df['الحي'].astype(str).str.contains(search, na=False)] if search else df
        st.dataframe(res[['الحي', 'السعر', 'المساحة', 'Source_File']], use_container_width=True)
    else:
        st.warning("⚠️ لم يتم استخراج بيانات صالحة. راجع القائمة الجانبية لمعرفة السبب.")
