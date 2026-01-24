import streamlit as st
import pandas as pd
from google.oauth2 import service_account
from googleapiclient.discovery import build
import io
import os

# ==========================================
# 1. إعدادات الاتصال
# ==========================================
FOLDER_ID = "1kgzKj9sn8pQVjr78XcN7_iF5KLmflwME"
SCOPES = ['https://www.googleapis.com/auth/drive.readonly']

# ==========================================
# 2. قاموس توحيد الأعمدة (حسب طلبك)
# ==========================================
COLUMN_MAPPING = {
    # السعر
    'السعر': 'السعر', 'قيمة الصفقات': 'السعر', 'مبلغ الصفقة': 'السعر', 'Price': 'السعر',
    
    # المساحة
    'المساحة': 'المساحة', 'المساحة M2': 'المساحة', 'Area': 'المساحة', 'المساحة (م2)': 'المساحة',
    
    # الموقع
    'المدينة': 'المدينة', 'City': 'المدينة',
    'الحي': 'الحي', 'اسم الحي': 'الحي', 'District': 'الحي',
    
    # التفاصيل (الجديدة)
    'نوع العقار': 'نوع_العقار_الخام', 'تصنيف العقار': 'نوع_العقار_الخام', 'النوع': 'نوع_العقار_الخام',
    'الحالة': 'الحالة', 'Status': 'الحالة',
    'عدد الغرف': 'عدد_الغرف', 'غرف': 'عدد_الغرف', 'Rooms': 'عدد_الغرف',
    
    # إضافات
    'عدد الصكوك': 'عدد_الصكوك', 'المطور': 'اسم_المطور'
}

class RealEstateBot:
    def __init__(self):
        self.creds = self.get_creds()
        self.service = build('drive', 'v3', credentials=self.creds)
        self.df = self.load_data_from_drive()

    def get_creds(self):
        if 'gcp_service_account' in st.secrets:
            return service_account.Credentials.from_service_account_info(st.secrets['gcp_service_account'], scopes=SCOPES)
        elif os.path.exists('credentials.json'):
            return service_account.Credentials.from_service_account_file('credentials.json', scopes=SCOPES)
        return None

    def load_data_from_drive(self):
        all_data = []
        if not self.creds: return pd.DataFrame()
        
        try:
            results = self.service.files().list(q=f"'{FOLDER_ID}' in parents and trashed=false", fields="files(id, name)").execute()
            files = results.get('files', [])
            
            for file in files:
                if not file['name'].lower().endswith('.csv'): continue
                try:
                    # تحميل محتوى الملف
                    request = self.service.files().get_media(fileId=file['id'])
                    content_bytes = request.execute()
                    try: content_str = content_bytes.decode('utf-8-sig')
                    except: content_str = content_bytes.decode('utf-16')
                    
                    # -----------------------------------------------
                    # 1. صائد العناوين الذكي (Header Hunter)
                    # -----------------------------------------------
                    lines = content_str.splitlines()
                    header_idx = 0; sep = ','
                    # نبحث عن السطر الذي يحتوي على أهم عمودين (السعر والمساحة)
                    for i, line in enumerate(lines[:50]):
                        if ('السعر' in line or 'Price' in line) and ('المساحة' in line or 'Area' in line):
                            header_idx = i
                            sep = ';' if ';' in line else '\t' if '\t' in line else ','
                            break
                    
                    df_temp = pd.read_csv(io.StringIO(content_str), sep=sep, header=header_idx, engine='python')

                    # -----------------------------------------------
                    # 2. تصنيف الملف (عروض vs صفقات)
                    # -----------------------------------------------
                    fname = file['name'].lower()
                    if "عروض" in fname or "offer" in fname:
                        data_cat = "عروض (Ask)"
                    else:
                        data_cat = "صفقات (Sold)"

                    # -----------------------------------------------
                    # 3. تحديد المصدر (مطور / وزارة عدل / عام)
                    # -----------------------------------------------
                    is_dev = any(x in fname for x in ['dev', 'مطور'])
                    source_type = 'مطورين' if is_dev else 'عام'
                    if 'MOJ' in file['name'].upper() or 'عدد الصكوك' in df_temp.columns: source_type = 'عدل'

                    # -----------------------------------------------
                    # 4. المعالجة والتوحيد
                    # -----------------------------------------------
                    df_temp.columns = df_temp.columns.str.strip()
                    df_temp.rename(columns=COLUMN_MAPPING, inplace=True)
                    df_temp = df_temp.loc[:, ~df_temp.columns.duplicated()]

                    # التأكد من وجود الأعمدة الأساسية
                    if 'السعر' in df_temp.columns and 'المساحة' in df_temp.columns:
                        
                        # تنظيف الأرقام (إزالة الفواصل والنصوص)
                        for col in ['السعر', 'المساحة', 'عدد_الغرف']:
                            if col in df_temp.columns:
                                df_temp[col] = df_temp[col].astype(str).str.replace(',', '').str.replace(r'[^\d.]', '', regex=True)
                                df_temp[col] = pd.to_numeric(df_temp[col], errors='coerce')
                        
                        # حذف الصفوف الفارغة أو الصفرية
                        df_temp.dropna(subset=['السعر', 'المساحة'], inplace=True)
                        df_temp = df_temp[df_temp['المساحة'] > 0]
                        
                        # الحسابات الإضافية
                        df_temp['سعر_المتر'] = df_temp['السعر'] / df_temp['المساحة']
                        df_temp['Source_File'] = file['name']
                        df_temp['Source_Type'] = source_type
                        df_temp['Data_Category'] = data_cat
                        
                        # تنظيف النصوص
                        if 'الحي' in df_temp.columns: df_temp['الحي'] = df_temp['الحي'].astype(str).str.strip()
                        
                        # تعبئة الأعمدة الناقصة لتوحيد الجدول
                        required_cols = ['نوع_العقار_الخام', 'الحالة', 'عدد_الغرف', 'المدينة', 'اسم_المطور', 'عدد_الصكوك']
                        for c in required_cols: 
                            if c not in df_temp.columns: df_temp[c] = None 
                        
                        # اختيار الأعمدة النهائية للسحب
                        cols = ['المدينة', 'الحي', 'السعر', 'المساحة', 'سعر_المتر', 
                                'نوع_العقار_الخام', 'الحالة', 'عدد_الغرف',
                                'Source_File', 'Source_Type', 'Data_Category']
                        
                        final_cols = [c for c in cols if c in df_temp.columns]
                        all_data.append(df_temp[final_cols])

                except Exception as e:
                    print(f"Skipping {file['name']}: {e}")

            if all_data:
                total_df = pd.concat(all_data, ignore_index=True)
                medians = {}
                if 'الحي' in total_df.columns:
                    medians = total_df.groupby('الحي')['سعر_المتر'].median().to_dict()

                # -----------------------------------------------
                # 5. خوارزمية التصنيف الذكي (أرض vs مبنى)
                # -----------------------------------------------
                def classify(row):
                    raw = str(row.get('نوع_العقار_الخام', '')).strip().lower()
                    
                    # 1. تصنيف صريح من الاسم
                    if 'أرض' in raw: return "أرض"
                    if 'فيلا' in raw or 'بيت' in raw: return "مبني (فيلا)"
                    if 'شقة' in raw: return "مبني (شقة)"
                    if 'عمارة' in raw: return "مبني (عمارة)"
                    
                    # 2. استنتاج ذكي (إذا النوع غير محدد)
                    area = row.get('المساحة', 0)
                    ppm = row.get('سعر_المتر', 0)
                    dist = row.get('الحي', '')
                    
                    if area < 250: return "مبني (شقة)" # مساحة صغيرة غالباً شقة
                    
                    # إذا السعر أعلى من متوسط الحي بمرة ونصف والمساحة معقولة -> غالباً مبنى مسجل كأرض
                    avg = medians.get(dist, 0)
                    if avg > 0 and ppm > (avg * 1.5) and area < 900: return "مبني (فيلا)"
                    
                    return "أرض" # الافتراضي

                total_df['نوع_العقار'] = total_df.apply(classify, axis=1)
                return total_df
            
            return pd.DataFrame()
        except: return pd.DataFrame()
