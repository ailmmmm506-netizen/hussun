import streamlit as st
import pandas as pd
from google.oauth2 import service_account
from googleapiclient.discovery import build
import io
import csv
import os

# إعدادات الاتصال
FOLDER_ID = "1kgzKj9sn8pQVjr78XcN7_iF5KLmflwME"
SCOPES = ['https://www.googleapis.com/auth/drive.readonly']

# قاموس الترجمة وتوحيد الأسماء
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
        # 1. البحث عن الملف محلياً (للاستخدام في Codespace)
        if os.path.exists('credentials.json'):
            return service_account.Credentials.from_service_account_file('credentials.json', scopes=SCOPES)
        
        # 2. البحث في أسرار Streamlit (للاستخدام بعد النشر)
        elif 'gcp_service_account' in st.secrets:
            return service_account.Credentials.from_service_account_info(st.secrets['gcp_service_account'], scopes=SCOPES)
        
        else:
            raise FileNotFoundError("لم يتم العثور على ملف credentials.json ولا على الأسرار في Streamlit Cloud")

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
                
                self.log(f"🔹 معالجة الملف: {file['name']}")
                
                try:
                    request = self.service.files().get_media(fileId=file['id'])
                    content_bytes = request.execute()
                    
                    try:
                        content_str = content_bytes.decode('utf-8-sig')
                    except:
                        content_str = content_bytes.decode('utf-16')

                    # تحديد نوع الملف
                    is_developer_file = any(x in file['name'].lower() for x in ['dev', 'مطور', 'brochure', 'projects'])
                    
                    if is_developer_file:
                        self.log("   🌟 بيانات مطورين")
                        df_temp = pd.read_csv(io.StringIO(content_str), sep=None, engine='python')
                        df_temp['Source_Type'] = 'سوق_حالي (مطورين)'
                    
                    elif 'MOJ' in file['name'].upper():
                        self.log("   ⚖️ بيانات عدل")
                        f = io.StringIO(content_str)
                        reader = csv.reader(f, delimiter=';')
                        header_row = None; data_rows = []
                        for row in reader:
                            clean_row = [str(cell).strip() for cell in row]
                            if 'السعر' in clean_row and 'الحي' in clean_row:
                                header_row = clean_row; continue
                            if header_row and len(clean_row) >= len(header_row):
                                data_rows.append(clean_row[:len(header_row)])
                        
                        if header_row: 
                            df_temp = pd.DataFrame(data_rows, columns=header_row)
                        else: 
                            self.log("❌ فشل MOJ"); continue
                        df_temp['Source_Type'] = 'صفقات_منفذة (العدل)'

                    else:
                        self.log("   ℹ️ مؤشرات عامة")
                        df_temp = pd.read_csv(io.StringIO(content_str), sep=None, engine='python')
                        df_temp['Source_Type'] = 'مؤشرات_عامة'

                    # التنظيف والتوحيد
                    df_temp.columns = df_temp.columns.str.strip()
                    df_temp.rename(columns=COLUMN_MAPPING, inplace=True)
                    df_temp = df_temp.loc[:, ~df_temp.columns.duplicated()]

                    # فلترة الرياض
                    if 'المدينة' in df_temp.columns:
                        df_temp['المدينة'] = df_temp['المدينة'].astype(str).str.strip()
                        df_temp = df_temp[df_temp['المدينة'] == 'الرياض']
                    
                    # تنظيف الأرقام
                    for col in ['السعر', 'المساحة']:
                        if col in df_temp.columns:
                            df_temp[col] = df_temp[col].astype(str).str.replace(',', '').str.replace(r'[^\d.]', '', regex=True)
                            df_temp[col] = pd.to_numeric(df_temp[col], errors='coerce')

                    df_temp.dropna(subset=['السعر', 'المساحة'], inplace=True)
                    df_temp['سعر_المتر'] = df_temp['السعر'] / df_temp['المساحة']
                    df_temp['Source_File'] = file['name']
                    
                    if 'نوع_العقار_الخام' not in df_temp.columns:
                        df_temp['نوع_العقار_الخام'] = "غير محدد"

                    # اختيار الأعمدة النهائية
                    cols = ['الحي', 'السعر', 'المساحة', 'سعر_المتر', 'نوع_العقار_الخام', 'Source_File', 'Source_Type', 'اسم_المطور']
                    final_cols = [c for c in cols if c in df_temp.columns]
                    
                    all_data.append(df_temp[final_cols])
                    self.log(f"   ✅ تم: {len(df_temp)} صف")

                except Exception as e:
                    self.log(f"⛔ خطأ في الملف: {e}")

            if all_data:
                total_df = pd.concat(all_data, ignore_index=True)
                
                # التحليل الذكي للنوع
                district_medians = total_df.groupby('الحي')['سعر_المتر'].median().to_dict()

                def classify(row):
                    raw = str(row.get('نوع_العقار_الخام', '')).strip().lower()
                    if row.get('Source_Type') == 'سوق_حالي (مطورين)':
                        if 'شقة' in raw: return 'مبني (شقة - مطور)'
                        if 'فيلا' in raw: return 'مبني (فيلا - مطور)'
                        if 'أرض' in raw: return 'أرض (مطور)'
                    
                    if 'تجاري' in raw: return "أرض (تجاري)"
                    if 'زراعي' in raw: return "أرض (زراعي)"
                    
                    area, ppm, dist = row['المساحة'], row['سعر_المتر'], row['الحي']
                    if area < 200: return "مبني (شقة)"
                    
                    avg = district_medians.get(dist, 0)
                    if avg > 0 and ppm > (avg * 1.5) and area < 900: return "مبني (فيلا/بيت)"
                    return "أرض"

                total_df['نوع_العقار'] = total_df.apply(classify, axis=1)
                return total_df
            else:
                return pd.DataFrame()
