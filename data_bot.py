# data_bot.py
import urllib.parse
import random
import time
from datetime import datetime

class RealEstateBot:
    def __init__(self):
        # قاعدة بيانات محاكاة (يمكنك لاحقاً استبدالها بكود Scraping حقيقي)
        self.db = {
            "الملقا": {"exec": 6500, "comp": [9500, 7800, 6200], "ticket": 1300000},
            "العارض": {"exec": 3800, "comp": [5500, 4200, 3900], "ticket": 950000},
            "النرجس": {"exec": 4200, "comp": [6000, 4800, 4500], "ticket": 1100000},
        }

    def generate_links(self, city, district):
        query = urllib.parse.quote(f"{city} {district}")
        return {
            "rega": "https://rei.rega.gov.sa/?topDistrictOrder=transactions",
            "earth": "https://earthapp.com.sa/transaction",
            "sas": f"https://aqarsas.sa/search?q={query}"
        }

    def fetch_data(self, city, district):
        # محاكاة الوقت المستغرق للسحب
        time.sleep(1.0)
        
        # البحث
        found = None
        for k in self.db:
            if k in district: found = self.db[k]
        
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        if found:
            var = random.uniform(0.98, 1.02) # تغيير بسيط للواقعية
            return {
                "status": "success",
                "meta": {"time": timestamp, "source": "Internal DB", "district": district},
                "market": {
                    "execution_price": int(found['exec'] * var),
                    "max_ticket": int(found['ticket'] * var)
                },
                "competitors": [
                    {"tier": "A (فاخر)", "price": int(found['comp'][0]*var), "notes": "مواصفات سمارت"},
                    {"tier": "B (متوسط)", "price": int(found['comp'][1]*var), "notes": "تشطيب مودرن"},
                    {"tier": "C (اقتصادي)", "price": int(found['comp'][2]*var), "notes": "تجاري"}
                ]
            }
        else:
            return {"status": "failed", "meta": {"time": timestamp}, "msg": "الحي غير مسجل"}
