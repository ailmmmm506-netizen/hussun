# dashboard.py
import streamlit as st
import pandas as pd
from data_bot import RealEstateBot

# إعداد الصفحة
st.set_page_config(page_title="غرفة المراقبة", layout="wide", page_icon="🕵️‍♂️")

# استدعاء الروبوت (سيتصل بـ Google Drive تلقائياً)
bot = RealEstateBot()

st.title("🕵️‍♂️ غرفة مراقبة الروبوت (Dashboard)")
st.caption("هذه الصفحة مستقلة لفحص الأسعار القادمة من Google Drive")

# تقسيم الشاشة
c1, c2 = st.columns([3, 1])
dist = c1.text_input("اكتب اسم الحي:", "حي الملقا")

# زر التشغيل
if c2.button("تشغيل الروبوت 🔍", type="primary"):
    # جلب البيانات
    res = bot.fetch_data(dist)
    
    if res['status'] == 'success':
        st.success(f"✅ تم سحب البيانات بنجاح | التوقيت: {res['timestamp']}")
        
        # عرض مصدر البيانات (للتأكد)
        if 'msg' in res:
             st.info(f"📂 المصدر: {res['msg']}")

        # تجهيز الجدول للعرض
        df = pd.DataFrame(res['records'])
        
        # عرض الجدول الملون (الأخضر للأسعار)
        st.dataframe(
            df.style.background_gradient(subset=['السعر'], cmap="Greens"),
            use_container_width=True,
            hide_index=True
        )
        
        # عرض الأرقام الكبيرة
        k1, k2 = st.columns(2)
        k1.metric("سعر متر الأرض (تطوير)", f"{res['summary']['exec_avg']:,.0f}")
        k2.metric("سعر متر الشقة (بيع)", f"{res['summary']['built_avg']:,.0f}")
        
    else:
        st.error("⚠️ لا توجد بيانات لهذا الحي في ملفاتك، أو الاسم غير مطابق.")
