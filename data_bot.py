import streamlit as st
import pandas as pd
from google.oauth2 import service_account
from googleapiclient.discovery import build
import io
import os
import re

# ==========================================
# 1. إعدادات الاتصال وقائمة الأحياء
# ==========================================
FOLDER_ID = "1kgzKj9sn8pQVjr78XcN7_iF5KLmflwME"
SCOPES = ['https://www.googleapis.com/auth/drive.readonly']

# قائمة بأسماء أحياء الرياض الشائعة للمساعدة في البحث داخل اسم المشروع
KNOWN_DISTRICTS = [
    'الملقا', 'العارض', 'النرجس', 'الياسمين', 'القيروان', 'حطين', 'العقيق', 'النخيل', 
    'الصحافة', 'الربيع', 'الندى', 'الفلاح', 'الوادي', 'الغدير', 'النسيم', 'الجنادرية', 
    'الرمال', 'البيان', 'المونسية', 'قرطبة', 'اشبيليا', 'اليرموك', 'غرناطة', 'النهضة', 
    'الخليج', 'الروضة', 'القدس', 'الحمراء', 'الملك فيصل', 'الاندلس', 'الريان', 
    'السلي', 'الفيحاء', 'الجزيرة', 'النور', 'العزيزية', 'الخالدية', 'الدار البيضاء', 
    'المنصورة', 'نمار', 'طويق', 'ديراب', 'الحزم', 'الشفاء', 'بدر', 'المروة', 'عكاظ', 
    'أحد', 'الشعلة', 'ظهرة لبن', 'ظهرة نمار', 'السويدي', 'شبرا', 'الدرعية', 
    'الخزامى', 'عرقة', 'مهدية', 'لبن', 'الشميسي', 'عليشة', 'الناصرية', 'الفاخرية',
    'الملز', 'الضباط', 'الزهراء', 'الصفا', 'الجرادية', 'عتيقة', 'منفوحة', 'غبيراء',
    'العليا', 'السليمانية', 'الملك فهد', 'المحمدية', 'الرحمانية', 'الرائد', 'التعاون'
]

# قاموس توحيد الأعمدة
COLUMN_MAPPING = {
    'السعر': 'السعر', 'Price': 'السعر', 'القيمة': 'السعر',
    'المساحة': 'المساحة', 'Area': 'المساحة', 'مساحة': 'المساحة',
    'المدينة': 'المدينة',
    'الحي': 'الحي', 'District': 'الحي',
    'اسم المشروع': 'اسم_المشروع_الخام', 'المشروع': 'اسم_المشروع_الخام',
    'نوع العقار': 'نوع_العقار_الخام', 'النوع': 'نوع_العقار_الخام',
    'المطور': 'اسم_المطور'
}

class RealEstateBot:
    def __init__(self):
        self.creds = self.get_creds()
        self.service = build('drive', 'v3', credentials=self.creds)
        self.df = self.load_data_from_drive()

    def get_creds(self):
        if 'gcp_service_account' in st.secrets:
            return service_account.Credentials.from_service_account_info(st.secrets['gcp_service_account'], scopes=SCOPES)
        return None

    def load_data_from_drive(self):
        all_data = []
        if not self.creds: return pd.DataFrame()
        
        try:
            results = self.service.files().list(q=f"'{FOLDER_ID}' in parents and trashed=false", fields="files(id, name)").execute()
            
            for file in results.get('files', []):
                if not file['name'].lower().endswith('.csv'): continue
                try:
                    # قراءة الملف
                    content = self.service.files().get_media(fileId=file['id']).execute().decode('utf-8-sig')
                    
                    # تحديد الفواصل
                    sep = ';' if ';' in content.splitlines()[0] else ','
                    df_temp = pd.read_csv(io.StringIO(content), sep=sep, engine='python')
                    
                    # تنظيف وتوحيد الأعمدة
                    df_temp.columns = df_temp.columns.str.strip()
                    df_temp.rename(columns=COLUMN_MAPPING, inplace=True)
                    
                    # تصنيف الملف (عروض/صفقات)
                    fname = file['name'].lower()
                    data_cat = "عروض (Ask)" if "عروض" in fname or "offer" in fname else "صفقات (Sold)"
                    
                    # معالجة الأرقام
                    for col in ['السعر', 'المساحة']:
                        if col in df_temp.columns:
                            df_temp[col] = pd.to_numeric(df_temp[col].astype(str).str.replace(r'[^\d.]', '', regex=True), errors='coerce')
                    
                    df_temp.dropna(subset=['السعر', 'المساحة'], inplace=True)
                    df_temp = df_temp[df_temp['المساحة'] > 10]
                    df_temp['سعر_المتر'] = df_temp['السعر'] / df_temp['المساحة']
                    df_temp['Source_File'] = file['name']
                    df_temp['Data_Category'] = data_cat
                    
                    # تجهيز الأعمدة الناقصة
                    if 'الحي' not in df_temp.columns: df_temp['الحي'] = None
                    if 'اسم_المشروع_الخام' not in df_temp.columns: df_temp['اسم_المشروع_الخام'] = ''

                    # =================================================
                    # 🕵️‍♂️ الميزة 1: استخراج الحي الذكي (Logic Fix)
                    # =================================================
                    def resolve_district(row):
                        current_val = str(row['الحي']).strip()
                        project_val = str(row.get('اسم_المشروع_الخام', '')).strip()
                        
                        # قائمة الكلمات التي تجعلنا نشك في صحة خانة الحي
                        suspicious_words = ['جميع', 'All', 'مشروع', 'Project', 'عام', 'راكز', 'nan', 'None', '', 'مخطط']
                        is_suspicious = any(w in current_val for w in suspicious_words) or len(current_val) < 3
                        
                        # 1. إذا كان اسم الحي سليماً، نعتمد عليه
                        if not is_suspicious:
                            return current_val
                        
                        # 2. إذا كان مشبوهاً، نبحث في "اسم المشروع" عن (حي X) أو (مخطط X)
                        match_prefix = re.search(r'(?:حي|مخطط)\s+([\w\u0600-\u06FF]+)', project_val)
                        if match_prefix:
                            return match_prefix.group(1).strip()
                        
                        # 3. إذا لم نجد كلمة "حي"، نبحث عن أسماء أحياء معروفة داخل اسم المشروع
                        for district in KNOWN_DISTRICTS:
                            if district in project_val:
                                return district
                                
                        # 4. الملاذ الأخير: اسم الملف
                        clean_fname = file['name'].replace('.csv', '').replace('عروض', '').replace('صفقات', '').replace('الرياض', '').replace('_', ' ')
                        return clean_fname.strip()

                    df_temp['الحي'] = df_temp.apply(resolve_district, axis=1)

                    # =================================================
                    # 🏭 الميزة 2: تصنيف العقار الذكي (بناءً على القواعد والمساحة)
                    # =================================================
                    def final_classify(row):
                        raw = str(row.get('نوع_العقار_الخام', '')).strip().lower()
                        area = row.get('المساحة', 0)
                        
                        # أ) الصفقات: أرض أو مبني
                        if 'صفقات' in data_cat or 'Sold' in data_cat:
                            if 'أرض' in raw or 'land' in raw: return "أرض"
                            return "مبني"
                        
                        # ب) العروض: شقة، دور، فيلا، أرض
                        else:
                            if 'أرض' in raw or 'land' in raw: return "أرض"
                            
                            # الكلمات المفتاحية الصريحة
                            if any(w in raw for w in ['شقة', 'شقه', 'apartment', 'flat', 'تمليك', 'استوديو']): return "شقة"
                            if any(w in raw for w in ['دور', 'طابق', 'floor']): return "دور"
                            if any(w in raw for w in ['فيلا', 'فله', 'villa', 'تاون', 'دبلكس', 'بنتهاوس']): return "فيلا"
                            
                            # التصنيف بالمساحة (للحالات المبهمة)
                            if area < 200: return "شقة"        
                            if 200 <= area < 350: return "دور" 
                            return "فيلا"                      

                    df_temp['نوع_العقار'] = df_temp.apply(final_classify, axis=1)
                    
                    # حفظ البيانات
                    cols = ['Source_File', 'Data_Category', 'الحي', 'السعر', 'المساحة', 'سعر_المتر', 'نوع_العقار', 'اسم_المطور']
                    cols = [c for c in cols if c in df_temp.columns]
                    all_data.append(df_temp[cols])

                except Exception: continue

        except Exception: pass
        
        if all_data: return pd.concat(all_data, ignore_index=True)
        return pd.DataFrame()
