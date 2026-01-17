import streamlit as st
import pandas as pd
from google.oauth2 import service_account
from googleapiclient.discovery import build
import io
import os

FOLDER_ID = "1kgzKj9sn8pQVjr78XcN7_iF5KLmflwME"
SCOPES = ['https://www.googleapis.com/auth/drive.readonly']

COLUMN_MAPPING = {
    'قيمة الصفقات': 'السعر', 'السعر': 'السعر', 'مبلغ الصفقة': 'السعر', 'Price': 'السعر',
    'المساحة M2': 'المساحة', 'المساحة': 'المساحة', 'المساحة بالأمتار': 'المساحة', 'Area': 'المساحة',
    'الحي': 'الحي', 'اسم الحي': 'الحي', 'District Name': 'الحي', 'الموقع': 'الحي',
    'المدينة': 'المدينة', 'City': 'المدينة', 'المنطقة': 'المدينة',
    'نوع العقار': 'نوع_العقار_الخام', 'تصنيف العقار': 'نوع_العقار_الخام', 'الوحدة': 'نوع_العقار_الخام',
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
                        if any(x in line for x in ['المساحة', 'السعر', 'Price', 'Area']):
                            header_idx = i; sep = ';' if ';' in line else '\t' if '\t' in line else ','; break
                    
                    df_temp = pd.read_csv(io.StringIO(content_str), sep=sep, header=header_idx, engine='python')
                    
                    is_dev = any(x in file['name'].lower() for x in ['dev', 'مطور'])
                    source_type = 'مطورين' if is_dev else 'عام'
                    if 'MOJ' in file['name'].upper() or 'عدد الصكوك' in df_temp.columns: source_type = 'عدل'

                    df_temp.columns = df_temp.columns.str.strip()
                    df_temp.rename(columns=COLUMN_MAPPING, inplace=True)
                    df_temp = df_temp.loc[:, ~df_temp.columns.duplicated()]

                    if 'السعر' in df_temp.columns and 'المساحة' in df_temp.columns:
                        for col in ['السعر', 'المساحة']:
                            df_temp[col] = df_temp[col].astype(str).str.replace(',', '').str.replace(r'[^\d.]', '', regex=True)
                            df_temp[col] = pd.to_numeric(df_temp[col], errors='coerce')
                        
                        df_temp.dropna(subset=['السعر', 'المساحة'], inplace=True)
                        df_temp = df_temp[df_temp['المساحة'] > 0]
                        df_temp['سعر_المتر'] = df_temp['السعر'] / df_temp['المساحة']
                        df_temp['Source_File'] = file['name']
                        df_temp['Source_Type'] = source_type
                        if 'الحي' in df_temp.columns: df_temp['الحي'] = df_temp['الحي'].astype(str).str.strip()
                        for c in ['نوع_العقار_الخام', 'اسم_المطور', 'عدد_الصكوك']: 
                            if c not in df_temp.columns: df_temp[c] = "غير محدد"
                        
                        cols = ['الحي', 'السعر', 'المساحة', 'سعر_المتر', 'نوع_العقار_الخام', 'Source_File', 'Source_Type', 'اسم_المطور', 'عدد_الصكوك']
                        all_data.append(df_temp[[c for c in cols if c in df_temp.columns]])
                except: pass

            if all_data:
                total_df = pd.concat(all_data, ignore_index=True)
                medians = {} if 'الحي' not in total_df.columns else total_df.groupby('الحي')['سعر_المتر'].median().to_dict()
                def classify(row):
                    raw = str(row.get('نوع_العقار_الخام', '')).strip().lower()
                    if row.get('Source_Type') == 'مطورين': return 'مبني (شقة - مطور)' if 'شقة' in raw else 'مبني (فيلا - مطور)' if 'فيلا' in raw else 'أرض (مطور)'
                    if 'أرض' in raw: return "أرض"
                    if 'شقة' in raw: return "مبني (شقة)"
                    area, ppm, dist = row.get('المساحة',0), row.get('سعر_المتر',0), row.get('الحي','')
                    if area < 250: return "مبني (شقة)"
                    if medians.get(dist, 0) > 0 and ppm > (medians.get(dist)*1.5) and area < 900: return "مبني (فيلا/بيت)"
                    return "أرض"
                total_df['نوع_العقار'] = total_df.apply(classify, axis=1)
                return total_df
            return pd.DataFrame()
        except: return pd.DataFrame()
