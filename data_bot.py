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
# 2. قاموس توحيد الأعمدة (شامل جداً)
# ==========================================
COLUMN_MAPPING = {
    # السعر
    'السعر': 'السعر', 'قيمة الصفقات': 'السعر', 'مبلغ الصفقة': 'السعر', 'Price': 'السعر', 'القيمة': 'السعر',
    
    # المساحة
    'المساحة': 'المساحة', 'المساحة M2': 'المساحة', 'Area': 'المساحة', 'المساحة (م2)': 'المساحة', 'مساحة': 'المساحة',
    
    # الموقع (هنا الذكاء: نربط كل مسميات الموقع بعمود الحي)
    'المدينة': 'المدينة', 'City': 'المدينة',
    'الحي': 'الحي', 'اسم الحي': 'الحي', 'District': 'الحي', 
    'الموقع': 'الحي', 'Location': 'الحي', # نعتبر الموقع هو الحي
    'المخطط': 'الحي', # نعتبر المخطط هو الحي
    'اسم المشروع': 'الحي', 'المشروع': 'الحي', # نعتبر المشروع هو الحي
    
    # التفاصيل
    'نوع العقار': 'نوع_العقار_الخام', 'تصنيف العقار': 'نوع_العقار_الخام', 'النوع': 'نوع_العقار_الخام', 'Usage': 'نوع_العقار_الخام',
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
                    # 1. قراءة الملف
                    request = self.service.files().get_media(fileId=file['id'])
                    content_bytes = request.execute()
                    try: content_str = content_bytes.decode('utf-8-sig')
                    except: content_str = content_bytes.decode('utf-16')
                    
                    # 2. تحديد بداية الجدول (الهيدر)
                    lines = content_str.splitlines()
                    header_idx = 0; sep = ','
                    for i, line in enumerate(lines[:50]):
                        # نبحث عن السطر الذي يحتوي على السعر والمساحة
                        if ('السعر' in line or 'Price' in line or 'القيمة' in line) and ('المساحة' in line or 'Area' in line):
                            header_idx = i
                            sep = ';' if ';' in line else '\t' if '\t' in line else ','
                            break
                    
                    df_temp = pd.read_csv(io.StringIO(content_str), sep=sep, header=header_idx, engine='python')

                    # 3. تحديد نوع البيانات من اسم الملف
                    fname = file['name'].lower()
                    data_cat = "عروض (Ask)" if ("عروض" in fname or "offer" in fname) else "صفقات (Sold)"
                    
                    # تحديد المصدر
                    source_type = 'عام'
                    if 'MOJ' in file['name'].upper() or 'عدد الصكوك' in df_temp.columns: source_type = 'عدل'
                    elif any(x in fname for x in ['dev', 'مطور']): source_type = 'مطورين'

                    # 4. توحيد أسماء الأعمدة (Mapping)
                    # ملاحظة: إذا كان الملف يحتوي على "الحي" و "المخطط"، سيأخذ أول واحد يطابق القاموس
                    df_temp.columns = df_temp.columns.str.strip()
                    df_temp.rename(columns=COLUMN_MAPPING, inplace=True)
                    
                    # حذف الأعمدة المكررة الناتجة عن الـ Mapping (مثلاً لو وجد الحي والموقع، سيبقي واحداً)
                    df_temp = df_temp.loc[:, ~df_temp.columns.duplicated()]

                    # 5. تنظيف وتجهيز اسم الحي (من البيانات نفسها)
                    if 'الحي' in df_temp.columns:
                        # دالة لتنظيف النص داخل الخلية
                        def clean_district_name(text):
                            if pd.isna(text): return None
                            text = str(text).strip()
                            # حذف كلمات زائدة لاستخراج الاسم الصافي
                            text = re.sub(r'حي\s+|مخطط\s+|مشروع\s+|Project\s+|District\s+', '', text)
                            return text.strip()

                        df_temp['الحي'] = df_temp['الحي'].apply(clean_district_name)
                    else:
                        # إذا لم يوجد عمود حي، ننشئه فارغاً
                        df_temp['الحي'] = None

                    # 6. التعبئة الاحتياطية (فقط للخانات الفارغة تماماً)
                    # نستخرج اسم الحي من اسم الملف كخيار أخير فقط
                    potential_dist_file = file['name'].replace('.csv', '').replace('.CSV', '')
                    noise = ['عروض', 'صفقات', 'Offers', 'Sold', 'Offer', 'الرياض', 'Riyadh', 'حي', 'District', '_', '-']
                    for w in noise: potential_dist_file = potential_dist_file.replace(w, ' ')
                    potential_dist_file = potential_dist_file.strip()
                    
                    # نملأ الـ NaN فقط باسم الملف
                    df_temp['الحي'] = df_temp['الحي'].fillna(potential_dist_file)

                    # 7. المعالجة الرقمية
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
                        
                        # إكمال الأعمدة الناقصة
                        for c in ['نوع_العقار_الخام', 'الحالة', 'عدد_الغرف', 'المدينة', 'اسم_المطور', 'عدد_الصكوك']: 
                            if c not in df_temp.columns: df_temp[c] = None 
                        
                        cols = ['المدينة', 'الحي', 'السعر', 'المساحة', 'سعر_المتر', 
                                'نوع_العقار_الخام', 'الحالة', 'عدد_الغرف',
                                'Source_File', 'Source_Type', 'Data_Category']
                        
                        final_cols = [c for c in cols if c in df_temp.columns]
                        all_data.append(df_temp[final_cols])

                except Exception as e:
                    print(f"Error processing {file['name']}: {e}")

            if all_data:
                total_df = pd.concat(all_data, ignore_index=True)
                medians = {}
                if 'الحي' in total_df.columns:
                    medians = total_df.groupby('الحي')['سعر_المتر'].median().to_dict()

                # 8. تصنيف نوع العقار (تطوير المنطق)
                def classify(row):
                    raw = str(row.get('نوع_العقار_الخام', '')).strip().lower()
                    
                    # الأولوية لما هو مكتوب في "نوع العقار"
                    if 'أرض' in raw or 'land' in raw: return "أرض"
                    if 'فيلا' in raw or 'بيت' in raw or 'villa' in raw: return "مبني (فيلا)"
                    if 'شقة' in raw or 'apartment' in raw: return "مبني (شقة)"
                    if 'عمارة' in raw or 'building' in raw: return "مبني (عمارة)"
                    
                    # الاستنتاج الذكي في حال غياب النوع
                    area = row.get('المساحة', 0)
                    ppm = row.get('سعر_المتر', 0)
                    dist = row.get('الحي', '')
                    
                    if area < 250: return "مبني (شقة)"
                    
                    avg = medians.get(dist, 0)
                    # إذا السعر أغلى من متوسط الحي بـ 50% والمساحة أقل من 900 -> غالباً فيلا
                    if avg > 0 and ppm > (avg * 1.5) and area < 900: return "مبني (فيلا)"
                    
                    return "أرض"

                total_df['نوع_العقار'] = total_df.apply(classify, axis=1)
                return total_df
            
            return pd.DataFrame()
        except: return pd.DataFrame()
