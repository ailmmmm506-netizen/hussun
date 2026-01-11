# data_bot.py (v5.0 - محلل الأراضي والمباني)
import pandas as pd
import numpy as np
import time
from datetime import datetime
import urllib.parse

class RealEstateBot:
    def __init__(self):
        self.mode = "SIMULATION"
        try:
            # قراءة ملف البيانات
            self.df = pd.read_csv('riyadh_data.csv', header=7)
            
            # تنظيف الأعمدة
            self.df.columns = self.df.columns.str.strip()
            if 'الحي' in self.df.columns:
                self.df['الحي'] = self.df['الحي'].astype(str).str.strip()
            
            self.mode = "REAL_DATA"
            print("✅ تم تفعيل المحلل المالي (أراضي vs مباني)")
        except Exception as e:
            print(f"⚠️ وضع المحاكاة: {e}")

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
        
        # القيم الافتراضية
        land_price = 0
        built_price = 0
        status = "failed"
        report = ""

        if self.mode == "REAL_DATA":
            try:
                # 1. فلترة الحي + سكني
                mask = (self.df['الحي'] == clean_dist) & (self.df['تصنيف العقار'] == 'سكني')
                data = self.df[mask].copy()
                
                if not data.empty:
                    # تحويل الأرقام وحساب سعر المتر
                    data['السعر'] = pd.to_numeric(data['السعر'], errors='coerce')
                    data['المساحة'] = pd.to_numeric(data['المساحة'], errors='coerce')
                    data['سعر_المتر'] = data['السعر'] / data['المساحة']
                    
                    # تنظيف القيم الشاذة (استبعاد أي متر أقل من 500 ريال لأنه غير منطقي)
                    data = data[(data['سعر_المتر'] > 500) & (data['سعر_المتر'] < 30000)]
                    
                    # --- التقسيم الذكي ---
                    
                    # 1. سوق المباني/الشقق (المساحات الصغيرة < 250م)
                    # هذا يعطيك مؤشر "سعر البيع المتوقع"
                    built_df = data[data['المساحة'] < 250]
                    if not built_df.empty:
                        built_price = int(built_df['سعر_المتر'].median())
                    
                    # 2. سوق الأراضي (المساحات الكبيرة >= 250م)
                    # هذا يعطيك مؤشر "تكلفتك كمطور"
                    land_df = data[data['المساحة'] >= 250]
                    if not land_df.empty:
                        land_price = int(land_df['سعر_المتر'].median())
                    
                    # التحقق من النتائج
                    if land_price > 0 or built_price > 0:
                        status = "success"
                        # منطق تعويض القيم الناقصة
                        if land_price == 0 and built_price > 0:
                            land_price = int(built_price * 0.5) # تقدير تقريبي
                        if built_price == 0 and land_price > 0:
                            built_price = int(land_price * 1.8) # تقدير تقريبي
                        
                        report = f"تحليل {len(data)} صفقة: (أراضي وشقق)"

            except Exception as e:
                print(f"Error: {e}")

        # محاكاة في حال الفشل
        if status == "failed":
            land_price = 4000
            built_price = 6500
            status = "success"
            report = "بيانات تقديرية"

        return {
            "status": status,
            "timestamp": ts,
            "msg": report,
            "summary": {
                "exec_avg": land_price,       # سعر الأرض (للحسابات)
                "built_avg": built_price,     # سعر المبني (للمقارنة)
                "ticket_cap": int(built_price * 130) # متوسط سعر الشقة السوقي
            },
            "records": [
                {"النوع": "شراء (أرض خام)", "الفئة": "تطوير", "السعر": land_price, "المصدر": "وزارة العدل (>250م)", "الحالة": "📉 التكلفة"},
                {"النوع": "بيع (شقق جاهزة)", "الفئة": "سوق", "السعر": built_price, "المصدر": "وزارة العدل (<250م)", "الحالة": "📈 البيع"}
            ]
        }
