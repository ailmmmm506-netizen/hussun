# dashboard.py
import streamlit as st
import pandas as pd
from data_bot import RealEstateBot

st.set_page_config(page_title="غرفة المراقبة", layout="wide", page_icon="🕵️‍♂️")
bot = RealEstateBot()

st.title("🕵️‍♂️ غرفة مراقبة الروبوت (Dashboard)")
st.caption("هذه الصفحة مستقلة عن الموقع الرئيسي")

c1, c2 = st.columns([3, 1])
dist = c1.text_input("الحي", "حي الملقا")
if c2.button("تشغيل الروبوت 🔍", type="primary"):
    res = bot.fetch_data(dist)
    if res['status'] == 'success':
        st.success(f"تم السحب الساعة: {res['timestamp']}")
        
        # عرض الجدول الملون
        df = pd.DataFrame(res['records'])
        st.dataframe(
            df.style.background_gradient(subset=['السعر'], cmap="Greens"),
            use_container_width=True,
            hide_index=True
        )
        
        st.metric("سعر التنفيذ المعتمد", f"{res['summary']['exec_avg']:,.0f}")
    else:
        st.error("لا توجد بيانات لهذا الحي")
