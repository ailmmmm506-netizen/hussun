import streamlit as st
import pandas as pd
from google.oauth2 import service_account
from googleapiclient.discovery import build
import io
import csv
import os

# ==========================================
# 1. كود الروبوت (المحرك)
# ==========================================
FOLDER_ID = "1kgzKj9sn8pQVjr78XcN7_iF5KLmflwME"
SCOPES = ['https://www.googleapis.com/auth/drive.readonly']

COLUMN_MAPPING = {
    'السعر': 'السعر', 'مبلغ الصفقة': 'السعر', 'Price': 'السعر', 'قيمة الصفقات': 'السعر', 'سعر الوحدة': 'السعر',
    'المساحة': 'المساحة', 'المساحة بالأمتار': 'المساحة', 'Area': 'المساحة', 'مساحة الوحدة': 'المساحة',
    'الحي': 'الحي', 'اسم الحي': 'الحي', 'District Name': 'الحي', 'الموقع': 'الحي',
    'نوع العقار': 'نوع_العقار_الخام', 'تصنيف العقار': 'نوع_العقار_الخام', 'الوحدة': 'نوع_العقار_الخام', 'النوع': 'نوع_العقار_الخام',
    'المدينة': 'المدينة', 
    'المطور': 'اسم_المطور', 'اسم المشروع': 'اسم_المشروع'
}

class RealEstateBot:
    def __init__(self):
        self.log_messages = []
        self.creds = self.get_creds()
        self.service = build('drive', 'v3', credentials=self.creds)
        self.df = self.load_data_from_drive()

    def log(self, msg):
        print(msg)
        self.log_messages.append(msg)

    def get_creds(self):
        # البحث عن الأسرار في Streamlit (للنشر)
        if 'gcp_service_account' in st.secrets:
            return service_account.Credentials.from_service_account_info(st.secrets['gcp_service_account'], scopes=SCOPES)
        # البحث عن الملف محلياً (للتطوير)
        elif os.path.exists('credentials.json'):
            return service_account.Credentials.from_service_account_file('credentials.json', scopes=SCOPES)
        else:
            raise FileNotFoundError("⚠️ لم يتم العثور على مفاتيح الدخول (Secrets أو credentials.json)")

    def load_data_from_drive(self):
        all_data = []
        self.log("📂 جاري البحث عن الملفات...")
        
        try:
            results = self.service.files().list(
                q=f"'{FOLDER_ID}' in parents and trashed=false",
                fields="files(id, name)").execute()
            files = results.get('files', [])

            for file in files:
                if not file['name'].lower().endswith('.csv'):
                    continue
                
                try:
                    request = self.service.files().get_media(fileId=file['id'])
                    content_bytes = request.execute()
                    
                    try: content_str = content_bytes.decode('utf-8-sig')
                    except: content_str = content_bytes.decode('utf-16')

                    is_dev = any(x in file['name'].lower() for x in ['dev', 'مطور', 'brochure', 'projects'])
                    
                    if is_dev:
                        df_temp = pd.read_csv(io.StringIO(content_str), sep=None, engine='python')
                        df_temp['Source_Type'] = 'سوق_حالي (مطورين)'
                    elif 'MOJ' in file['name'].upper():
                        f = io.StringIO(content_str)
                        reader = csv.reader(f, delimiter=';')
                        header_row = None; data_rows = []
                        for row in reader:
                            clean_row = [str(cell).strip() for cell in row]
                            if 'السعر' in clean_row and 'الحي' in clean_row: header_row = clean_row; continue
                            if header_row and len(clean_row) >= len(header_row): data_rows.append(clean_row[:len(header_row)])
                        if header_row: df_temp = pd.DataFrame(data_rows, columns=header_row)
                        else: continue
                        df_temp['Source_Type'] = 'صفقات_منفذة (العدل)'
                    else:
                        df_temp = pd.read_csv(io.StringIO(content_str), sep=None, engine='python')
                        df_temp['Source_Type'] = 'مؤشرات_عامة'

                    df_temp.columns = df_temp.columns.str.strip()
                    df_temp.rename(columns=COLUMN_MAPPING, inplace=True)
                    df_temp = df_temp.loc[:, ~df_temp.columns.duplicated()]

                    if 'المدينة' in df_temp.columns:
                        df_temp['المدينة'] = df_temp['المدينة'].astype(str).str.strip()
                        df_temp = df_temp[df_temp['المدينة'] == 'الرياض']

                    for col in ['السعر', 'المساحة']:
                        if col in df_temp.columns:
                            df_temp[col] = df_temp[col].astype(str).str.replace(',', '').str.replace(r'[^\d.]', '', regex=True)
                            df_temp[col] = pd.to_numeric(df_temp[col], errors='coerce')

                    df_temp.dropna(subset=['السعر', 'المساحة'], inplace=True)
                    df_temp['سعر_المتر'] = df_temp['السعر'] / df_temp['المساحة']
                    # حفظ اسم الملف للعرض في الإحصائيات
                    df_temp['Source_File'] = file['name'] 
                    
                    if 'نوع_العقار_الخام' not in df_temp.columns: df_temp['نوع_العقار_الخام'] = "غير محدد"
                    
                    cols = ['الحي', 'السعر', 'المساحة', 'سعر_المتر', 'نوع_العقار_الخام', 'Source_File', 'Source_Type', 'اسم_المطور']
                    all_data.append(df_temp[[c for c in cols if c in df_temp.columns]])

                except Exception as e:
                    self.log(f"خطأ في ملف {file['name']}: {e}")

            if all_data:
                total_df = pd.concat(all_data, ignore_index=True)
                medians = total_df.groupby('الحي')['سعر_المتر'].median().to_dict()

                def classify(row):
                    raw = str(row.get('نوع_العقار_الخام', '')).strip().lower()
                    if row.get('Source_Type') == 'سوق_حالي (مطورين)':
                        if 'شقة' in raw: return 'مبني (شقة - مطور)'
                        if 'فيلا' in raw: return 'مبني (فيلا - مطور)'
                        if 'أرض' in raw: return 'أرض (مطور)'
                    if 'تجاري' in raw: return "أرض (تجاري)"
                    area, ppm, dist = row['المساحة'], row['سعر_المتر'], row['الحي']
                    if area < 200: return "مبني (شقة)"
                    avg = medians.get(dist, 0)
                    if avg > 0 and ppm > (avg * 1.5) and area < 900: return "مبني (فيلا/بيت)"
                    return "أرض"

                total_df['نوع_العقار'] = total_df.apply(classify, axis=1)
                return total_df
            return pd.DataFrame()
        except Exception as e:
            self.log(f"خطأ عام: {e}")
            return pd.DataFrame()

# ==========================================
# 2. واجهة المستخدم (Dashboard UI)
# ==========================================
st.set_page_config(page_title="المحلل العقاري الذكي", layout="wide", page_icon="🏢")

# ---------------- القائمة الجانبية (مع إحصائيات الملفات) ----------------
with st.sidebar:
    st.header("⚙️ التحكم")
    if st.button("🔄 تحديث البيانات", use_container_width=True, type="primary"):
        st.cache_data.clear()
        st.rerun()
    
    # هنا الإضافة الجديدة: إظهار مصادر البيانات
    if 'bot' in st.session_state and hasattr(st.session_state.bot, 'df'):
        df_stats = st.session_state.bot.df
        if not df_stats.empty:
            st.divider()
            st.markdown("### 📁 مصادر البيانات")
            st.markdown("عدد الصفقات في كل ملف:")
            
            # حساب عدد الصفقات لكل ملف
            file_counts = df_stats['Source_File'].value_counts().reset_index()
            file_counts.columns = ['اسم الملف', 'عدد الصفقات']
            
            # عرضها كجدول صغير
            st.dataframe(file_counts, hide_index=True, use_container_width=True)

# ---------------- الشاشة الرئيسية ----------------
st.title("🧐 مدقق البيانات العقارية (النسخة الموحدة)")

# تشغيل الروبوت
if 'bot' not in st.session_state:
    with st.spinner("جاري الاتصال بقاعدة البيانات..."):
        try:
            st.session_state.bot = RealEstateBot()
        except Exception as e:
            st.error(f"حدث خطأ: {e}")

if 'bot' in st.session_state and hasattr(st.session_state.bot, 'df'):
    df = st.session_state.bot.df
    
    if df.empty:
        st.warning("⚠️ لا توجد بيانات. تأكد من صحة المفاتيح والملفات.")
    else:
        # الفلترة
        st.markdown("### 🧹 فلترة البيانات")
        c1, c2 = st.columns(2)
        with c1: min_p = st.number_input("أقل سعر متر:", value=500, step=100)
        with c2: max_p = st.number_input("أعلى سعر متر:", value=25000, step=1000)

        clean_df = df[(df['سعر_المتر'] >= min_p) & (df['سعر_المتر'] <= max_p)].copy()
        
        st.divider()
        st.markdown("### 🔍 البحث والتحليل")
        
        sc1, sc2 = st.columns([3, 1])
        search = sc1.text_input("اسم الحي:", "الملقا")
        
        if sc2.button("عرض 📊", use_container_width=True, type="primary") or search:
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
                
                # عرض المصدر (اسم الملف) في الجدول الرئيسي أيضاً
                st.dataframe(res[['الحي', 'نوع_العقار', 'المساحة', 'السعر', 'سعر_المتر', 'Source_File']].style.format({'السعر':'{:,.0f}', 'سعر_المتر':'{:,.0f}'}), use_container_width=True)
