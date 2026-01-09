# dashboard.py
import streamlit as st
import pandas as pd
from data_bot import RealEstateBot

# إعداد الصفحة لتكون عريضة (Wide Mode) لراحة العين مع الجداول
st.set_page_config(page_title="غرفة مراقبة البيانات", layout="wide", page_icon="📊")

bot = RealEstateBot()

# --- الهيدر ---
col_h1, col_h2 = st.columns([3, 1])
col_h1.title("📊 غرفة تحليل بيانات السوق")
col_h1.caption("لوحة تحكم للمراقبة والمقارنة - (Admin View)")

# --- شريط البحث العلوي ---
with st.container():
    c1, c2, c3 = st.columns([2, 2, 1])
    city = c1.text_input("المدينة", "الرياض", label_visibility="collapsed", placeholder="المدينة")
    district = c2.text_input("الحي", "حي الملقا", label_visibility="collapsed", placeholder="الحي")
    btn_run = c3.button("🔍 سحب البيانات", type="primary", use_container_width=True)

st.markdown("---")

if btn_run:
    with st.spinner("جاري الاتصال بالروبوت وجلب الجداول..."):
        data = bot.fetch_data(district)
    
    if data['status'] == 'success':
        # 1. المؤشرات السريعة (KPIs)
        k1, k2, k3 = st.columns(3)
        k1.metric("توقيت السحب", data['timestamp'])
        k2.metric("متوسط التنفيذ (الأساس)", f"{data['summary']['exec_avg']:,.0f} ريال")
        k3.metric("سقف الشقة (Ticket)", f"{data['summary']['ticket_cap']:,.0f} ريال")
        
        st.markdown("### 📋 جدول تحليل الأسعار")
        
        # 2. إنشاء الجدول الذكي
        df = pd.DataFrame(data['records'])
        
        # تنسيق الجدول (تلوين الأسعار)
        # هذا الكود يجعل الخلفية متدرجة حسب السعر (الأغلى أحمر، الأرخص أخضر)
        st.dataframe(
            df.style.background_gradient(subset=['السعر'], cmap="RdYlGn_r") # _r لعكس الألوان
              .format({"السعر": "{:,.0f} ريال"}),
            use_container_width=True,
            height=300, # ارتفاع الجدول
            hide_index=True
        )
        
        # 3. روابط المصادر (أزرار سريعة)
        st.markdown("### 🔗 التحقق من المصادر")
        links = bot.generate_links(city, district)
        lc1, lc2, lc3, lc4 = st.columns(4)
        lc1.link_button("مؤشر الهيئة", links['rega'])
        lc2.link_button("منصة إيرث", links['earth'])
        lc3.link_button("عقار ساس", links['sas'])
        
        # 4. التصدير
        st.download_button(
            "📥 تحميل الجدول (Excel/CSV)",
            data=df.to_csv(index=False).encode('utf-8'),
            file_name=f"market_data_{district}.csv",
            mime="text/csv"
        )

    else:
        st.error(f"❌ لم يتم العثور على بيانات لحي: {district}")

else:
    st.info("اضغط زر 'سحب البيانات' لعرض الجدول.")
    
