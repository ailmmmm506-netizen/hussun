import streamlit as st
import pandas as pd
from google.oauth2 import service_account
from googleapiclient.discovery import build
import io
import os
import re

# ==========================================
# 1. إعدادات الاتصال
# ==========================================
FOLDER_ID = "1kgzKj9sn8pQVjr78XcN7_iF5KLmflwME"
SCOPES = ['https://www.googleapis.com/auth/drive.readonly']

# ==========================================
# 2. قاموس توحيد الأعمدة
# ==========================================
COLUMN_MAPPING = {
    # السعر
    'السعر': 'السعر', 'قيمة الصفقات': 'السعر', 'Price': 'السعر', 'القيمة': 'السعر',
    # المساحة
    'المساحة': 'المساحة', 'المساحة M2': 'المساحة', 'Area': 'المساحة', 'مساحة': 'المساحة',
    # الموقع
    'المدينة': 'المدينة', 'City': 'المدينة',
    'الحي': 'الحي', 'اسم الحي': 'الحي', 'District': 'الحي', 'Location': 'الحي',
    # أعمدة الاستنتاج
    'اسم المشروع': 'اسم_المشروع_الخام', 'المشروع': 'اسم_المشروع_الخام', 'Project Name': 'اسم_المشروع_الخام',
    'المخطط': 'اسم_المشروع_الخام',
    # التفاصيل
    'نوع العقار': 'نوع_العقار_الخام', 'تصنيف العقار': 'نوع_العقار_الخام', 'النوع': 'نوع_العقار_الخام',
    'الحالة': 'الحالة', 'Status': 'الحالة',
    'عدد الغرف': 'عدد_الغرف', 'غرف': 'عدد_الغرف',
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
                    # 1. قراءة الملف
                    request = self.service.files().get_media(fileId=file['id'])
                    content_bytes = request.execute()
                    try: content_str = content_bytes.decode('utf-8-sig')
                    except: content_str = content_bytes.decode('utf-16')
                    
                    # 2. تحديد الهيدر
                    lines = content_str.splitlines()
                    header_idx = 0; sep = ','
                    for i, line in enumerate(lines[:50]):
                        if ('السعر' in line or 'Price' in line) and ('المساحة' in line or 'Area' in line):
                            header_idx = i
                            sep = ';' if ';' in line else '\t' if '\t' in line else ','
                            break
                    
                    df_temp = pd.read_csv(io.StringIO(content_str), sep=sep, header=header_idx, engine='python')

                    # 3. تصنيف الملف (عروض vs صفقات)
                    fname = file['name'].lower()
                    data_cat = "عروض (Ask)" if ("عروض" in fname or "offer" in fname) else "صفقات (Sold)"
                    source_type = 'عدل' if ('MOJ' in file['name'].upper()) else ('مطورين' if any(x in fname for x in ['dev', 'مطور']) else 'عام')

                    # 4. توحيد الأعمدة
                    df_temp.columns = df_temp.columns.str.strip()
                    df_temp.rename(columns=COLUMN_MAPPING, inplace=True)
                    df_temp = df_temp.loc[:, ~df_temp.columns.duplicated()]

                    # =========================================================
                    # 🕵️‍♂️ استخراج الحي المفقود (كما اتفقنا سابقاً)
                    # =========================================================
                    if 'الحي' not in df_temp.columns: df_temp['الحي'] = None
                    if 'اسم_المشروع_الخام' not in df_temp.columns: df_temp['اسم_المشروع_الخام'] = ''

                    bad_mask = df_temp['الحي'].isna() | df_temp['الحي'].astype(str).str.contains(r'جميع|All|مشروع|عام', case=False, na=False) | (df_temp['الحي'].astype(str).str.len() < 3)

                    # تكتيك 1: استخراج "حي كذا" من اسم المشروع
                    def extract_with_prefix(text):
                        if pd.isna(text): return None
                        match = re.search(r'(?:حي|مخطط)\s+([\w\u0600-\u06FF]+)', str(text))
                        return match.group(1).strip() if match else None

                    df_temp.loc[bad_mask, 'الحي'] = df_temp.loc[bad_mask, 'اسم_المشروع_الخام'].apply(extract_with_prefix)
                    
                    # تكتيك 2: اسم الملف كخيار أخير
                    potential_dist_file = file['name'].replace('.csv', '').replace('.CSV', '')
                    for w in ['عروض', 'صفقات', 'Offers', 'Sold', 'الرياض', 'Riyadh', 'حي', 'District', '_', '-']:
                        potential_dist_file = potential_dist_file.replace(w, ' ')
                    
                    df_temp['الحي'] = df_temp['الحي'].fillna(potential_dist_file.strip())
                    # =========================================================

                    # 5. المعالجة الرقمية
                    if 'السعر' in df_temp.columns and 'المساحة' in df_temp.columns:
                        for col in ['السعر', 'المساحة', 'عدد_الغرف']:
                            if col in df_temp.columns:
                                df_temp[col] = df_temp[col].astype(str).str.replace(',', '').str.replace(r'[^\d.]', '', regex=True)
                                df_temp[col] = pd.to_numeric(df_temp[col], errors='coerce')
                        
                        df_temp.dropna(subset=['السعر', 'المساحة'], inplace=True)
                        df_temp = df_temp[df_temp['المساحة'] > 0]
                        
                        df_temp['سعر_المتر'] = df_temp['السعر'] / df_temp['المساحة']
                        df_temp['Source_File'] = file['name']
                        df_temp['Source_Type'] = source_type
                        df_temp['Data_Category'] = data_cat
                        
                        # إكمال النواقص
                        for c in ['نوع_العقار_الخام', 'الحالة', 'عدد_الغرف', 'المدينة', 'اسم_المطور', 'عدد_الصكوك', 'اسم_المشروع_الخام']: 
                            if c not in df_temp.columns: df_temp[c] = None 
                        
                        cols = ['المدينة', 'الحي', 'السعر', 'المساحة', 'سعر_المتر', 
                                'نوع_العقار_الخام', 'الحالة', 'عدد_الغرف',
                                'Source_File', 'Source_Type', 'Data_Category', 'اسم_المشروع_الخام']
                        
                        final_cols = [c for c in cols if c in df_temp.columns]
                        all_data.append(df_temp[final_cols])

                except Exception as e:
                    print(f"Skipping {file['name']}: {e}")

            if all_data:
                total_df = pd.concat(all_data, ignore_index=True)
                
                # حساب متوسط الحي (للاستنتاج في الصفقات فقط)
                medians = {}
                if 'الحي' in total_df.columns:
                    # نحسب المتوسط فقط للصفقات المصنفة كأرض مبدئياً ليكون معياراً
                    land_only = total_df[total_df['نوع_العقار_الخام'].astype(str).str.contains('أرض', na=False)]
                    medians = land_only.groupby('الحي')['سعر_المتر'].median().to_dict()

                # =========================================================
                # 🧠 خوارزمية التصنيف المزدوجة (Dual Classification Logic)
                # =========================================================
                def classify_property(row):
                    raw = str(row.get('نوع_العقار_الخام', '')).strip().lower()
                    category = row.get('Data_Category', '')
                    
                    # -----------------------------------
                    # السيناريو 1: العروض (Offers)
                    # -----------------------------------
                    # القاعدة: خذ البيانات من الملف كما هي، وحدد النوع بدقة (دور، شقة، فيلا)
                    if 'عروض' in category or 'Ask' in category:
                        if 'أرض' in raw or 'land' in raw: return "أرض"
                        if 'دور' in raw or 'floor' in raw: return "دور"
                        if 'شقة' in raw or 'apartment' in raw: return "شقة"
                        if any(x in raw for x in ['فيلا', 'فله', 'villa', 'بيت', 'تاون']): return "فيلا"
                        if 'عمارة' in raw or 'building' in raw: return "عمارة"
                        
                        # إذا كان النوع فارغاً في ملف العروض، حاول الاستنتاج من المساحة كحل أخير
                        area = row.get('المساحة', 0)
                        if not raw or raw == 'nan' or raw == 'none':
                            if area > 0 and area < 250: return "شقة" # افتراضي للمساحات الصغيرة
                            if area > 250: return "فيلا" # افتراضي للمساحات الكبيرة
                        
                        return raw # إذا لم يتطابق، أرجع النص الأصلي كما هو

                    # -----------------------------------
                    # السيناريو 2: الصفقات (Deals)
                    # -----------------------------------
                    # القاعدة: حدد هل هو مبني أم لا (Binary Classification)
                    else:
                        # التصنيف الصريح
                        if 'أرض' in raw or 'land' in raw: return "أرض"
                        if any(x in raw for x in ['فيلا', 'بيت', 'شقة', 'عمارة', 'دور', 'سكني تجاري']): return "مبني"

                        # الاستنتاج الذكي (Heuristic) للصفقات المبهمة
                        area = row.get('المساحة', 0)
                        ppm = row.get('سعر_المتر', 0)
                        dist = row.get('الحي', '')
                        
                        avg_land_price = medians.get(dist, 0)
                        
                        # إذا السعر أغلى من متوسط أراضي الحي بـ 50% -> غالباً مبني
                        if avg_land_price > 0 and ppm > (avg_land_price * 1.5):
                            return "مبني"
                        
                        return "أرض" # الافتراضي في الصفقات هو الأرض

                total_df['نوع_العقار'] = total_df.apply(classify_property, axis=1)
                return total_df
            
            return pd.DataFrame()
        except: return pd.DataFrame()
