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

# قائمة بأسماء أحياء الرياض الشائعة للمطابقة (يمكنك زيادتها)
KNOWN_DISTRICTS = [
    'الملقا', 'العارض', 'النرجس', 'الياسمين', 'القيروان', 'حطين', 'العقيق', 'النخيل', 
    'الصحافة', 'الربيع', 'الندى', 'الفلاح', 'الوادي', 'الغدير', 'النسيم', 'الجنادرية', 
    'الرمال', 'البيان', 'المونسية', 'قرطبة', 'اشبيليا', 'اليرموك', 'غرناطة', 'النهضة', 
    'الخليج', 'الروضة', 'القدس', 'الحمراء', 'الملك فيصل', 'الاندلس', 'الريان', 'النسيم',
    'السلي', 'الفيحاء', 'الجزيرة', 'النور', 'العزيزية', 'الخالدية', 'الدار البيضاء', 
    'المنصورة', 'نمار', 'طويق', 'ديراب', 'الحزم', 'الشفاء', 'بدر', 'المروة', 'عكاظ', 
    'أحد', 'الشعلة', 'نمار', 'ظهرة لبن', 'ظهرة نمار', 'السويدي', 'شبرا', 'الدرعية', 
    'الخزامى', 'عرقة', 'مهدية', 'لبن', 'الشميسي', 'عليشة', 'الناصرية', 'الفاخرية',
    'الملز', 'الضباط', 'الزهراء', 'الصفا', 'الجرادية', 'عتيقة', 'منفوحة', 'غبيراء',
    'العليا', 'السليمانية', 'الملك فهد', 'المحمدية', 'الرحمانية', 'الرائد', 'جامعة الملك سعود'
]

# ==========================================
# 2. قاموس توحيد الأعمدة
# ==========================================
COLUMN_MAPPING = {
    'السعر': 'السعر', 'قيمة الصفقات': 'السعر', 'Price': 'السعر', 'القيمة': 'السعر',
    'المساحة': 'المساحة', 'المساحة M2': 'المساحة', 'Area': 'المساحة', 'مساحة': 'المساحة',
    'المدينة': 'المدينة', 'City': 'المدينة',
    'الحي': 'الحي', 'اسم الحي': 'الحي', 'District': 'الحي', 'Location': 'الحي',
    'اسم المشروع': 'اسم_المشروع_الخام', 'المشروع': 'اسم_المشروع_الخام', 'Project Name': 'اسم_المشروع_الخام',
    'المخطط': 'اسم_المشروع_الخام',
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
                    request = self.service.files().get_media(fileId=file['id'])
                    content_bytes = request.execute()
                    try: content_str = content_bytes.decode('utf-8-sig')
                    except: content_str = content_bytes.decode('utf-16')
                    
                    lines = content_str.splitlines()
                    header_idx = 0; sep = ','
                    for i, line in enumerate(lines[:50]):
                        if ('السعر' in line or 'Price' in line) and ('المساحة' in line or 'Area' in line):
                            header_idx = i
                            sep = ';' if ';' in line else '\t' if '\t' in line else ','
                            break
                    
                    df_temp = pd.read_csv(io.StringIO(content_str), sep=sep, header=header_idx, engine='python')

                    fname = file['name'].lower()
                    data_cat = "عروض (Ask)" if ("عروض" in fname or "offer" in fname) else "صفقات (Sold)"
                    source_type = 'عدل' if ('MOJ' in file['name'].upper()) else ('مطورين' if any(x in fname for x in ['dev', 'مطور']) else 'عام')

                    df_temp.columns = df_temp.columns.str.strip()
                    df_temp.rename(columns=COLUMN_MAPPING, inplace=True)
                    df_temp = df_temp.loc[:, ~df_temp.columns.duplicated()]

                    # =========================================================
                    # 🕵️‍♂️ منطق البحث المتسلسل (Sequential Logic)
                    # =========================================================
                    if 'الحي' not in df_temp.columns: df_temp['الحي'] = None
                    if 'اسم_المشروع_الخام' not in df_temp.columns: df_temp['اسم_المشروع_الخام'] = ''

                    def resolve_district(row):
                        current_val = str(row['الحي']).strip()
                        project_val = str(row.get('اسم_المشروع_الخام', '')).strip()
                        
                        # قائمة الشك (كلمات عامة أو غير دقيقة)
                        suspicious_words = ['جميع', 'All', 'مشروع', 'Project', 'عام', 'راكز', 'Rakez', 'nan', 'None', '', 'مخطط']
                        
                        is_suspicious = any(w in current_val for w in suspicious_words) or len(current_val) < 3
                        
                        # 1. إذا القيمة الأصلية سليمة، اعتمدها فوراً
                        if not is_suspicious:
                            return current_val
                        
                        # 2. إذا القيمة مشبوهة، ابحث في "اسم المشروع" عن نمط (حي X)
                        match_prefix = re.search(r'(?:حي|مخطط)\s+([\w\u0600-\u06FF]+)', project_val)
                        if match_prefix:
                            return match_prefix.group(1).strip()
                        
                        # 3. البحث في "اسم المشروع" عن أي حي معروف (من القائمة)
                        for district in KNOWN_DISTRICTS:
                            if district in project_val:
                                return district

                        # 4. البحث في "الحي" المشبوه نفسه عن أي حي معروف (قد يكون "مشروع راكز النرجس")
                        for district in KNOWN_DISTRICTS:
                            if district in current_val:
                                return district
                                
                        # 5. إذا فشل كل شيء، حاول الاستخراج من اسم الملف
                        for district in KNOWN_DISTRICTS:
                            if district in fname:
                                return district
                                
                        # 6. الملاذ الأخير: نظف اسم الملف من الكلمات الزائدة واستخدمه
                        clean_fname = file['name'].replace('.csv', '').replace('.CSV', '')
                        for w in ['عروض', 'صفقات', 'Offers', 'Sold', 'الرياض', 'Riyadh', 'حي', 'District', '_', '-', 'مخطط']:
                            clean_fname = clean_fname.replace(w, ' ')
                        
                        return clean_fname.strip()

                    # تطبيق الدالة على كل صف
                    df_temp['الحي'] = df_temp.apply(resolve_district, axis=1)
                    # =========================================================

                    # المعالجة الرقمية
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
                medians = {}
                if 'الحي' in total_df.columns:
                    land_only = total_df[total_df['نوع_العقار_الخام'].astype(str).str.contains('أرض', na=False)]
                    if not land_only.empty:
                        medians = land_only.groupby('الحي')['سعر_المتر'].median().to_dict()

                def classify_property(row):
                    raw = str(row.get('نوع_العقار_الخام', '')).strip().lower()
                    category = row.get('Data_Category', '')
                    
                    if 'عروض' in category or 'Ask' in category:
                        if 'أرض' in raw or 'land' in raw: return "أرض"
                        if 'دور' in raw: return "دور"
                        if 'شقة' in raw: return "شقة"
                        if any(x in raw for x in ['فيلا', 'فله', 'villa', 'بيت', 'تاون']): return "فيلا"
                        if 'عمارة' in raw: return "عمارة"
                        area = row.get('المساحة', 0)
                        if not raw or raw == 'nan' or raw == 'none':
                            if area > 0 and area < 250: return "شقة"
                            if area > 250: return "فيلا"
                        return raw
                    else:
                        if 'أرض' in raw or 'land' in raw: return "أرض"
                        if any(x in raw for x in ['فيلا', 'بيت', 'شقة', 'عمارة', 'دور']): return "مبني"
                        area = row.get('المساحة', 0)
                        ppm = row.get('سعر_المتر', 0)
                        dist = row.get('الحي', '')
                        avg_land = medians.get(dist, 0)
                        if avg_land > 0 and ppm > (avg_land * 1.5): return "مبني"
                        return "أرض"

                total_df['نوع_العقار'] = total_df.apply(classify_property, axis=1)
                return total_df
            
            return pd.DataFrame()
        except: return pd.DataFrame()
