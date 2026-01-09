# data_bot.py
import random
import time
from datetime import datetime
import urllib.parse
import pandas as pd

class RealEstateBot:
    def generate_links(self, city, district):
        q = urllib.parse.quote(f"{city} {district}")
        return {
            "rega": "https://rei.rega.gov.sa/?topDistrictOrder=transactions",
            "earth": "https://earthapp.com.sa/transaction",
            "sas": f"https://aqarsas.sa/search?q={q}"
        }

    def fetch_data(self, district):
        # محاكاة سحب البيانات
        time.sleep(0.5)
        # قاعدة بيانات افتراضية
        db = {
            "الملقا": {"exec": 6500, "comp": [9500, 7800, 6200], "ticket": 1300000},
            "العارض": {"exec": 3800, "comp": [5500, 4200, 3900], "ticket": 950000},
            "النرجس": {"exec": 4200, "comp": [6000, 4800, 4500], "ticket": 1100000},
        }
        
        found = None
        for k in db:
            if k in district: found = db[k]
        
        ts = datetime.now().strftime("%H:%M:%S")
        
        if found:
            var = random.uniform(0.99, 1.01)
            return {
                "status": "success",
                "timestamp": ts,
                "summary": {
                    "exec_avg": int(found['exec'] * var),
                    "ticket_cap": int(found['ticket'] * var)
                },
                "records": [
                    {"النوع": "تنفيذ (صفقات)", "الفئة": "السوق", "السعر": int(found['exec']*var), "المصدر": "وزارة العدل", "الحالة": "مؤكد"},
                    {"النوع": "عرض بيع", "الفئة": "A (فاخر)", "السعر": int(found['comp'][0]*var), "المصدر": "تطبيق عقار", "الحالة": "تقديري"},
                    {"النوع": "عرض بيع", "الفئة": "B (متوسط)", "السعر": int(found['comp'][1]*var), "المصدر": "تطبيق عقار", "الحالة": "تقديري"},
                    {"النوع": "عرض بيع", "الفئة": "C (اقتصادي)", "السعر": int(found['comp'][2]*var), "المصدر": "مكاتب", "الحالة": "تقديري"},
                ]
            }
        else:
            return {"status": "failed", "timestamp": ts}
