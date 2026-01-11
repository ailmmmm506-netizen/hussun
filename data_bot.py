import pandas as pd
import numpy as np
import time
from datetime import datetime
from google.oauth2 import service_account
from googleapiclient.discovery import build
import io
from googleapiclient.http import MediaIoBaseDownload

class RealEstateBot:
    def __init__(self):
        self.mode = "SIMULATION"
        
        # 👇👇 (تأكد أن كود المجلد حقك موجود هنا) 👇👇
        FOLDER_ID = "1kgzKj9sn8pQVjr78XcN7_iF5KLmflwME" 
        # ------------------------------------------------
        
        try:
            print("🔄 جاري الاتصال بمجلد Google Drive...")
            
            SCOPES = ['https://www.googleapis.com/auth/drive']
            creds = service_account.Credentials.from_service_account_file('credentials.json', scopes=SCOPES)
            service = build('drive', 'v3', credentials=creds)
            
            results = service.files().list(
                q=f"'{FOLDER_ID}' in parents and mimeType='text/csv' and trashed=false",
                fields="files(id, name)").execute()
            items = results.get('files', [])

            if not items:
                print("⚠️ المجلد فارغ!")
                self.df = pd.DataFrame()
            else:
                all_dfs = []
                for item in items:
                    print(f"📥 قراءة الملف: {item['name']}...")
                    request = service.files().get_media(fileId=item['id'])
                    fh = io.BytesIO()
                    downloader = MediaIoBaseDownload(fh, request)
                    done = False
                    while done is False:
                        status, done = downloader.next_chunk()
                    
                    fh.seek(0)
                    df_temp = pd.read_csv(fh, header=7)
                    
                    # 🆕 حركة ذكية: تسجيل اسم الملف في عمود جديد
                    df_temp['Source_File'] = item['name']
                    
                    all_dfs.append(df_temp)

                self.df = pd.concat(all_dfs, ignore_index=True)
                
                # تنظيف البيانات
                self.df.columns = self.df.columns.str.strip()
                if 'الحي' in self.df.columns:
                    self.df['الحي'] = self.df['الحي'].astype(str).str.strip()
                
                self.mode = "REAL_DATA"
                print(f"✅ تم! الروبوت جاهز ومعه {len(self.df)} صفقة من {len(items)} ملفات.")

        except Exception as e:
            print(f"⚠️ خطأ: {e}")
            self.df = pd.DataFrame()

    def generate_links(self, city, district):
        clean_dist = district.replace("حي", "").strip()
        return {
            "srem": f"https://srem.moj.gov.sa/transactions-info?region_id=1&city_id=4&district_name={clean_dist}",
            "aqar": f"https://sa.aqar.fm/شقق-للبيع/{city}/{clean_dist}"
        }

    def fetch_data(self, district):
        time.sleep(0.5)
        clean_dist = district.replace("حي", "").strip()
        ts = datetime.now().strftime("%Y-%m-%d")
        
        land_price = 0; built_price = 0; status = "failed"; source_note = ""

        if self.mode == "REAL_DATA" and not self.df.empty:
            try:
                mask = (self.df['الحي'] == clean_dist) & (self.df['تصنيف العقار'] == 'سكني')
                data = self.df[mask].copy()
                
                if not data.empty:
                    # 🆕 استخراج اسم الملف الذي جاءت منه البيانات
                    # (يأخذ أول ملف وجد فيه البيانات)
                    file_name = data['Source_File'].iloc[0]
                    source_note = f"ملف: {file_name}"

                    data['السعر'] = pd.to_numeric(data['السعر'], errors='coerce')
                    data['المساحة'] = pd.to_numeric(data['المساحة'], errors='coerce')
                    data['سعر_المتر'] = data['السعر'] / data['المساحة']
                    data = data[(data['سعر_المتر'] > 500) & (data['سعر_المتر'] < 35000)]
                    
                    lands = data[data['المساحة'] >= 250]
                    if not lands.empty: land_price = int(lands['سعر_المتر'].median())
                    
                    apts = data[data['المساحة'] < 250]
                    if not apts.empty: built_price = int(apts['سعر_المتر'].median())

                    if land_price > 0 or built_price > 0:
                        status = "success"
                        # منطق التعويض
                        if land_price == 0 and built_price > 0: land_price = int(built_price * 0.45)
                        if built_price == 0 and land_price > 0: built_price = int(land_price * 1.8)
            except: pass

        if status == "failed":
            land_price = 4000; built_price = 6500; source_note = "بيانات تقديرية (محاكاة)"; status = "success"

        return {
            "status": status, "timestamp": ts, "msg": source_note,
            "summary": {"exec_avg": land_price, "built_avg": built_price, "ticket_cap": int(built_price * 130)},
            "records": [
                {"البيان": "سعر متر الأرض", "السعر": land_price, "المصدر": source_note},
                {"البيان": "سعر متر الشقة", "السعر": built_price, "المصدر": source_note}
            ]
        }
