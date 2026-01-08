# data_bot.py
import urllib.parse
import random
import time

class RealEstateBot:
    def __init__(self):
        self.sources = {
            "execution": ["البورصة العقارية", "إيرث", "عقار ساس"],
            "listing": ["تطبيق عقار", "واصلت", "ديل"]
        }

    def generate_search_links(self, city, district):
        """
        توليد روابط مباشرة لغرفة العمليات
        """
        query = f"{city} {district}"
        encoded_query = urllib.parse.quote(query)
        
        return {
            "rega": f"https://rei.rega.gov.sa/?topDistrictOrder=transactions",
            "earth": f"https://earthapp.com.sa/transaction",
            "sas": f"https://aqarsas.sa/search?q={encoded_query}",
            "aqar": f"https://sa.aqar.fm/أراضي-للبيع/{city}/{district}",
            "google_comp": f"https://www.google.com/search?q=سعر+متر+شقق+تمليك+{encoded_query}"
        }

    def fetch_market_data(self, city, district):
        """
        هذه الدالة هي التي ستتطور مستقبلاً لتسحب البيانات آلياً.
        حالياً سنستخدم محاكاة ذكية جداً (Smart Simulation) مبنية على بيانات تاريخية
        لكي يعمل البرنامج معك وكأنه سحب البيانات، إلى أن نربط APIs حقيقية.
        """
        
        # محاكاة تأخير الشبكة (كأنه يبحث فعلياً)
        time.sleep(1.5)
        
        # هنا سنضع "منطق" تقديري ذكي (مؤقتاً) بدلاً من الكشط المحظور
        # في المستقبل: هنا تضع كود Selenium أو Beautiful Soup
        
        # قاعدة بيانات افتراضية للأحياء المعروفة (للاختبار)
        district_db = {
            "الملقا": {"exec": 6500, "offer_a": 9500, "offer_b": 7800},
            "العارض": {"exec": 3800, "offer_a": 5500, "offer_b": 4200},
            "النرجس": {"exec": 4200, "offer_a": 6000, "offer_b": 4800},
            "الرمال": {"exec": 2100, "offer_a": 3200, "offer_b": 2500},
            "طويق": {"exec": 1800, "offer_a": 2600, "offer_b": 2100},
        }
        
        # البحث في القاعدة
        found_key = None
        for key in district_db:
            if key in district:
                found_key = key
                break
        
        if found_key:
            base = district_db[found_key]
            # نضيف تغيير بسيط عشوائي ليكون واقعياً في كل مرة
            variation = random.uniform(0.95, 1.05)
            
            return {
                "status": "success",
                "source": "قاعدة بيانات الروبوت (محاكاة)",
                "data": {
                    "execution_price": int(base['exec'] * variation),
                    "competitor_a": int(base['offer_a'] * variation),
                    "competitor_b": int(base['offer_b'] * variation),
                    "competitor_c": int(base['offer_b'] * 0.85 * variation), # الفئة C دائماً أقل
                    "max_ticket": int(1300000 * variation) # سقف الحي
                }
            }
        else:
            # إذا الحي جديد وغير مسجل، نرجع أصفار ليدخلها المستخدم يدوياً
            return {
                "status": "failed",
                "source": "غير موجود",
                "data": {
                    "execution_price": 0, "competitor_a": 0, "competitor_b": 0, "competitor_c": 0, "max_ticket": 0
                }
            }
