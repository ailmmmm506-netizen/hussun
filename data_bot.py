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

# قائمة مرجعية للأحياء (للمساعدة في المطابقة)
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
    'العليا', 'السليمانية', 'الملك فهد', 'المحمدية', 'الرحمانية', 'الرائد', 'التعاون',
    'الواحة', 'صلاح الدين', 'المرسلات', 'المصيف', 'المروج', 'الملك عبدالله', 'الملك سلمان',
    'القادسية', 'المعيزيلة', 'الشرق', 'طيبة', 'العماجية', 'هيت', 'بنبان', 'الوسام', 'لبن'
]

COLUMN_MAPPING = {
    'السعر': 'السعر', 'Price': 'السعر', 'القيمة': 'السعر',
    'المساحة': 'المساحة', 'Area': 'المساحة', 'مساحة': 'المساحة',
    'المدينة': 'المدينة',
    'الحي': 'الحي', 'District': 'الحي',
    'اسم المشروع': 'اسم_المشروع_الخام', 'المشروع': 'اسم_المشروع_الخام',
    'نوع العقار': 'نوع_العقار_الخام', 'النوع': 'نوع_العقار_الخام', 'Type': 'نوع_العقار_الخام', 'تصنيف العقار': 'نوع_العقار_الخام',
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
                fname = file['name'].lower()
                
                # 🛑 شرط 1: استبعاد صفقات راكز فقط (حسب طلبك)
                # إذا الملف يحتوي على "راكز" وليس "عروض" -> تجاوز الملف
                if 'راكز' in fname and 'عروض' not in fname and 'offer' not in fname:
                    continue

                if not fname.endswith('.csv'): continue

                try:
                    content = self.service.files().get_media(fileId=file['id']).execute().decode('utf-8-sig')
                    sep = ';' if ';' in content.splitlines()[0] else ','
                    df_temp = pd.read_csv(io.StringIO(content), sep=sep, engine='python')
                    
                    df_temp.columns = df_temp.columns.str.strip()
                    df_temp.rename(columns=COLUMN_MAPPING, inplace=True)
                    
                    data_cat = "عروض (Ask)" if "عروض" in fname or "offer" in fname else "صفقات (Sold)"
                    
                    for col in ['السعر', 'المساحة']:
                        if col in df_temp.columns:
                            df_temp[col] = pd.to_numeric(df_temp[col].astype(str).str.replace(r'[^\d.]', '', regex=True), errors='coerce')
                    
                    df_temp.dropna(subset=['السعر', 'المساحة'], inplace=True)
                    df_temp = df_temp[df_temp['المساحة'] > 10]
                    df_temp['سعر_المتر'] = df_temp['السعر'] / df_temp['المساحة']
                    df_temp['Source_File'] = file['name']
                    df_temp['Data_Category'] = data_cat
                    
                    if 'الحي' not in df_temp.columns: df_temp['الحي'] = None
                    if 'اسم_المشروع_الخام' not in df_temp.columns: df_temp['اسم_المشروع_الخام'] = ''

                    # =================================================
                    # 1. استخراج الحي (المنطق المصحح للصفقات)
                    # =================================================
                    def resolve_district(row):
                        current_val = str(row['الحي']).strip()
                        project_val = str(row.get('اسم_المشروع_الخام', '')).strip()
                        file_name_val = file['name']
                        
                        # تنظيف اسم الملف لاستخدامه كحي (نحذف كلمة صفقات وعروض)
                        # هذا يضمن أن 'صفقات_الملقا' تتحول إلى 'الملقا'
                        clean_name = re.sub(r'(صفقات|عروض|sold|ask|offers|deals|الرياض|riyadh|\.csv)', '', file_name_val, flags=re.IGNORECASE).strip()
                        clean_name = clean_name.replace('_', ' ').replace('-', ' ').strip()

                        # متى نعتبر خانة الحي "فاسدة"؟
                        bad_indicators = ['جميع', 'All', 'مشروع', 'Project', 'عام', 'راكز', 'Rakez', 'nan', 'None', 'مخطط', 'عروض', 'صفقات']
                        is_bad = any(w in current_val for w in bad_indicators) or len(current_val) < 3
                        
                        candidate = current_val
                        
                        if is_bad:
                            # أ) محاولة من اسم المشروع
                            found = False
                            for known in KNOWN_DISTRICTS:
                                if known in project_val:
                                    candidate = known; found = True; break
                            
                            if not found:
                                # ب) محاولة من اسم الملف (بحث عن حي معروف)
                                for known in KNOWN_DISTRICTS:
                                    if known in file_name_val:
                                        candidate = known; found = True; break
                                
                                # ج) الحل الأخير: استخدام اسم الملف "المنظف" (مهم جداً لملفات الصفقات)
                                if not found and len(clean_name) > 2:
                                    candidate = clean_name

                        # ⛔ الفلتر النهائي: نمنع فقط الكلمات السيئة الصريحة
                        # لن نمنع كلمة 'الملقا' حتى لو جاءت من ملف صفقات
                        blocklist = ['راكز', 'Rakez', 'عروض', 'Offers', 'صفقات', 'Sold', 'Ask', 'مخطط', 'nan']
                        if any(w == str(candidate).strip() for w in blocklist): 
                            return None 
                        
                        return candidate

                    df_temp['الحي'] = df_temp.apply(resolve_district, axis=1)
                    df_temp.dropna(subset=['الحي'], inplace=True)

                    # =================================================
                    # 2. تصنيف العقار
                    # =================================================
                    def final_classify(row):
                        raw = str(row.get('نوع_العقار_الخام', '')).strip().lower()
                        area = row.get('المساحة', 0)
                        
                        if 'صفقات' in data_cat or 'Sold' in data_cat:
                            if any(w in raw for w in ['أرض', 'land', 'راس', 'قطعة']): return "أرض"
                            return "مبني"
                        else:
                            if any(w in raw for w in ['أرض', 'land', 'راس', 'قطعة']): return "أرض"
                            if any(w in raw for w in ['فيلا', 'فله', 'فلل', 'villa', 'تاون', 'town', 'بنتهاوس', 'penthouse', 'دبلكس']): return "فيلا"
                            if any(w in raw for w in ['شقة', 'شقه', 'شقق', 'apartment', 'flat', 'تمليك', 'استوديو']): return "شقة"
                            if any(w in raw for w in ['دور', 'طابق', 'floor', 'ادوار', 'أدوار']): return "دور"
                            
                            # التصنيف بالمساحة
                            if area < 200: return "شقة"        
                            if 200 <= area < 360: return "دور" 
                            return "فيلا"                      

                    df_temp['نوع_العقار'] = df_temp.apply(final_classify, axis=1)
                    
                    # نحتفظ بالعمود الخام للفحص (Debug)
                    cols = ['Source_File', 'Data_Category', 'الحي', 'السعر', 'المساحة', 'سعر_المتر', 'نوع_العقار', 'نوع_العقار_الخام']
                    existing_cols = [c for c in cols if c in df_temp.columns]
                    all_data.append(df_temp[existing_cols])

                except Exception: continue
        except Exception: pass
        
        if all_data: return pd.concat(all_data, ignore_index=True)
        return pd.DataFrame()
