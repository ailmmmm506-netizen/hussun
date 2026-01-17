import streamlit as st
import pandas as pd
import data_bot  # استيراد المحرك

st.set_page_config(page_title="تحليل السوق العقاري", layout="wide", page_icon="📊")

# تشغيل المحرك
if 'bot' not in st.session_state:
    with st.spinner("جاري سحب البيانات..."):
        st.session_state.bot = data_bot.RealEstateBot()

df = st.session_state.bot.df if hasattr(st.session_state.bot, 'df') else pd.DataFrame()

# القائمة الجانبية
with st.sidebar:
    st.title("التحكم")
    if st.button("تحديث البيانات 🔄"):
        st.cache_data.clear()
        st.rerun()
    if not df.empty:
        st.success(f"إجمالي الصفقات: {len(df)}")

st.title("📊 لوحة بيانات السوق العقاري")

if df.empty:
    st.warning("لا توجد بيانات. تأكد من الملفات.")
else:
    # الفلاتر
    col1, col2, col3 = st.columns(3)
    with col1:
        city_list = sorted(df['الحي'].unique())
        selected_dist = st.selectbox("الحي:", ["الكل"] + city_list)
    with col2:
        types = ["الكل"] + sorted(df['نوع_العقار'].unique())
        selected_type = st.selectbox("النوع:", types)
    with col3:
        price_range = st.slider("سعر المتر:", int(df['سعر_المتر'].min()), int(df['سعر_المتر'].max()), (500, 20000))

    # التطبيق
    filtered = df.copy()
    if selected_dist != "الكل": filtered = filtered[filtered['الحي'] == selected_dist]
    if selected_type != "الكل": filtered = filtered[filtered['نوع_العقار'] == selected_type]
    filtered = filtered[(filtered['سعر_المتر'] >= price_range[0]) & (filtered['سعر_المتر'] <= price_range[1])]

    # النتائج
    st.metric("عدد النتائج", len(filtered))
    st.dataframe(filtered[['الحي', 'نوع_العقار', 'المساحة', 'السعر', 'سعر_المتر', 'Source_File', 'Source_Type']], use_container_width=True)
