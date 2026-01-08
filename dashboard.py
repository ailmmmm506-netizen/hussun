# dashboard.py
# تشغيل هذا الملف: streamlit run dashboard.py
import streamlit as st
import pandas as pd
from data_bot import RealEstateBot

st.set_page_config(page_title="غرفة التحكم بالبيانات", layout="wide", page_icon="🕵️‍♂️")

# استدعاء المحرك
bot = RealEstateBot()

st.title("🕵️‍♂️ غرفة مراقبة الروبوت (Admin Data View)")
st.markdown("---")

# 1. إعدادات البحث
c1, c2, c3 = st.columns([2, 2, 1])
city = c1.text_input("المدينة", "الرياض")
district = c2.text_input("الحي المستهدف", "حي الملقا")
btn = c3.button("تشغيل الروبوت 🤖", type="primary")

if btn:
    with st.spinner("جاري الاتصال بالمصادر وسحب البيانات..."):
        data = bot.fetch_data(city, district)
    
    if data['status'] == 'success':
        # 2. عرض الميتاداتا (التوقيت والحالة)
        st.success(f"تم السحب بنجاح @ {data['meta']['time']}")
        
        # 3. عرض الأرقام الرئيسية
        col1, col2 = st.columns(2)
        col1.metric("سعر التنفيذ (العدل)", f"{data['market']['execution_price']:,.0f}", "ريال/م")
        col2.metric("سقف الشقة (Ticket)", f"{data['market']['max_ticket']:,.0f}", "ريال")
        
        # 4. جدول المنافسين (التفاصيل الدقيقة)
        st.subheader("📋 جدول المنافسين المرصود")
        df = pd.DataFrame(data['competitors'])
        st.dataframe(df.style.format({"price": "{:,.0f}"}), use_container_width=True)
        
        # 5. الروابط التي زارها الروبوت
        st.subheader("🔗 المصادر التي تم فحصها")
        links = bot.generate_links(city, district)
        for name, link in links.items():
            st.markdown(f"- **{name}**: [{link}]({link})")
            
        # 6. الكود الخام (JSON) للتأكد
        with st.expander("💾 عرض البيانات الخام (JSON Structure)"):
            st.json(data)
            
    else:
        st.error("فشل الروبوت في العثور على بيانات لهذا الحي.")

else:
    st.info("اضغط 'تشغيل الروبوت' لرؤية البيانات الحية.")
