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
    'السعر': 'السعر', 'قيمة الصفقات': 'السعر', 'Price': 'السعر', 'القيمة': 'السعر',
    'المساحة': 'المساحة', 'المساحة M2': 'المساحة', 'Area': 'المساحة', 'مساحة': 'المساحة',
    'المدينة': 'المدينة', 'City': 'المدينة',
    'الحي': 'الحي', 'اسم الحي': 'الحي', 'District': 'الحي', 'Location': 'الحي',
    'اسم المشروع': 'اسم_المشروع_الخام', 'المشروع': 'اسم_المشروع_الخام', 'Project Name': 'اسم_المشروع_الخام', 'المخطط': 'اسم_المشروع_الخام',
    'نوع العقار': 'نوع_العقار_الخام', 'تصنيف العقار': 'نوع_العقار_الخام', 'النوع': 'نوع_العقار_الخام',
    'الحالة': 'الحالة', 'Status': 'الحالة',
    'عدد الغرف': 'عدد_الغرف', 'غرف': 'عدد_الغرف',
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
                    # قراءة الملف
                    request = self.service.files().get_media(fileId=file['id'])
                    content_bytes = request.execute()
                    try: content_str = content_bytes.decode('utf-8-sig')
                    except: content_str = content_bytes.decode('utf-16')
                    
                    # تحديد الهيدر
                    lines = content_str.splitlines()
                    header_idx = 0; sep = ','
                    for i, line in enumerate(lines[:50]):
                        if ('السعر' in line or 'Price' in line) and ('المساحة' in line or 'Area' in line):
                            header_idx = i
                            sep = ';' if ';' in line else '\t' if '\t' in line else ','
                            break
                    
                    df_temp = pd.read_csv(io.StringIO(content_str), sep=sep, header=header_idx, engine='python')

                    # تحديد نوع البيانات (عروض أم صفقات) من اسم الملف
                    fname = file['name'].lower()
                    data_cat = "عروض (Ask)" if ("عروض" in fname or "offer" in fname) else "صفقات (Sold)"
                    source_type = 'عدل' if ('MOJ' in file['name'].upper()) else ('مطورين' if any(x in fname for x in ['dev', 'مطور']) else 'عام')

                    # توحيد الأعمدة
                    df_temp.columns = df_temp.columns.str.strip()
                    df_temp.rename(columns=COLUMN_MAPPING, inplace=True)
                    df_temp = df_temp.loc[:, ~df_temp.columns.duplicated()]

                    # ============================================
                    # معالجة الأحياء (المنطق السابق)
                    # ============================================
                    if 'الحي' not in df_temp.columns: df_temp['الحي'] = None
                    if 'اسم_المشروع_الخام' not in df_temp.columns: df_temp['اسم_المشروع_الخام'] = ''

                    def resolve_district(row):
                        val = str(row['الحي']).strip()
                        proj = str(row.get('اسم_المشروع_الخام', '')).strip()
                        suspicious = ['جميع', 'All', 'مشروع', 'Project', 'عام', 'راكز', 'nan', 'None', '', 'مخطط']
                        if not any(w in val for w in suspicious) and len(val) > 2: return val
                        match = re.search(r'(?:حي|مخطط)\s+([\w\u0600-\u06FF]+)', proj)
                        if match: return match.group(1).strip()
                        clean_fname = file['name'].replace('.csv', '').replace('عروض', '').replace('صفقات', '').replace('الرياض', '').replace('_', ' ')
                        return clean_fname.strip()

                    df_temp['الحي'] = df_temp.apply(resolve_district, axis=1)

                    # ============================================
                    # المعالجة الرقمية
                    # ============================================
                    if 'السعر' in df_temp.columns and 'المساحة' in df_temp.columns:
                        for col in ['السعر', 'المساحة']:
                            df_temp[col] = df_temp[col].astype(str).str.replace(',', '').str.replace(r'[^\d.]', '', regex=True)
                            df_temp[col] = pd.to_numeric(df_temp[col], errors='coerce')
                        
                        df_temp.dropna(subset=['السعر', 'المساحة'], inplace=True)
                        df_temp = df_temp[df_temp['المساحة'] > 0]
                        df_temp['سعر_المتر'] = df_temp['السعر'] / df_temp['المساحة']
                        df_temp['Source_File'] = file['name']
                        df_temp['Data_Category'] = data_cat
                        if 'اسم_المطور' not in df_temp.columns: df_temp['اسم_المطور'] = None
                        if 'نوع_العقار_الخام' not in df_temp.columns: df_temp['نوع_العقار_الخام'] = ''

                        # ============================================
                        # 🔥 التصنيف الصارم (Core Logic)
                        # ============================================
                        def strict_classify(row):
                            raw_type = str(row.get('نوع_العقار_الخام', '')).strip().lower()
                            cat = row['Data_Category']
                            
                            # 1. إذا كانت صفقات (Sold) -> أرض أو مبني فقط
                            if 'صفقات' in cat or 'Sold' in cat:
                                if 'أرض' in raw_type or 'land' in raw_type: return "أرض"
                                return "مبني" # الافتراضي للصفقات هو مبني إذا لم تكن أرض صريحة
                            
                            # 2. إذا كانت عروض (Ask) -> شقة، فيلا، دور، أرض
                            else:
                                # تصنيف الشقق
                                if any(x in raw_type for x in ['شقة', 'شقه', 'apartment', 'flat', 'تمليك', 'استوديو']):
                                    return "شقة"
                                
                                # تصنيف الفلل (يشمل البنتهاوس والتاون هاوس)
                                if any(x in raw_type for x in ['فيلا', 'فله', 'villa', 'تاون', 'town', 'دبلكس', 'duplex', 'بنتهاوس', 'penthouse', 'بيت']):
                                    return "فيلا"
                                
                                # تصنيف الأدوار
                                if any(x in raw_type for x in ['دور', 'طابق', 'floor']):
                                    return "دور"
                                
                                # تصنيف الأراضي
                                if any(x in raw_type for x in ['أرض', 'land', 'قطعة']):
                                    return "أرض"
                                
                                # --- معالجة الحالات المبهمة في العروض ---
                                # إذا لم يكتب النوع، نخمن بناءً على المساحة
                                area = row.get('المساحة', 0)
                                if area < 250: return "شقة"       # مساحة صغيرة = شقة
                                if area > 250 and area < 400: return "دور" # مساحة متوسطة = دور (تقريبي)
                                if area >= 400: return "فيلا"     # مساحة كبيرة = فيلا
                                
                                return "فيلا" # الملاذ الأخير للعروض المبهمة الكبيرة

                        df_temp['نوع_العقار'] = df_temp.apply(strict_classify, axis=1)
                        
                        # تصفية الأعمدة النهائية
                        final_cols = ['Source_File', 'Data_Category', 'الحي', 'السعر', 'المساحة', 'سعر_المتر', 'نوع_العقار', 'اسم_المطور', 'نوع_العقار_الخام']
                        final_cols = [c for c in final_cols if c in df_temp.columns]
                        all_data.append(df_temp[final_cols])

                except Exception as e:
                    print(f"Error in {file['name']}: {e}")

            if all_data:
                return pd.concat(all_data, ignore_index=True)
            return pd.DataFrame()
