import streamlit as st
import pandas as pd
import data_bot  # استيراد نفس المحرك

st.set_page_config(page_title="دراسة الجدوى", layout="centered", page_icon="💰")

if 'bot' not in st.session_state:
    with st.spinner("جاري تجهيز البيانات للدراسة..."):
        st.session_state.bot = data_bot.RealEstateBot()

df = st.session_state.bot.df if hasattr(st.session_state.bot, 'df') else pd.DataFrame()

st.title("💰 حاسبة الجدوى العقارية")

if df.empty:
    st.error("البيانات غير متوفرة. لا يمكن إجراء المقارنة.")
else:
    # المدخلات
    st.markdown("### بيانات الفرصة المعروضة")
    col1, col2 = st.columns(2)
    with col1:
        dist = st.selectbox("الحي:", sorted(df['الحي'].unique()))
        area = st.number_input("مساحة الأرض (م):", value=400)
    with col2:
        price_pm = st.number_input("سعر المتر المعروض:", value=3500)
        build_cost = st.number_input("تكلفة البناء للمتر:", value=1800)

    # التحليل
    lands = df[(df['الحي'] == dist) & (df['نوع_العقار'].str.contains('أرض'))]
    buildings = df[(df['الحي'] == dist) & (df['نوع_العقار'].str.contains('مبني'))]
    
    avg_land = lands['سعر_المتر'].median() if not lands.empty else 0
    avg_build = buildings['سعر_المتر'].median() if not buildings.empty else 0

    st.markdown("---")
    st.subheader("النتائج")
    
    # 1. تقييم الأرض
    if avg_land > 0:
        diff = ((price_pm - avg_land) / avg_land) * 100
        st.write(f"متوسط الحي للأراضي: **{avg_land:,.0f}** ريال")
        if diff < -5: st.success(f"✅ لقطة! أقل من السوق بـ {abs(diff):.1f}%")
        elif diff > 5: st.error(f"❌ غالية! أعلى من السوق بـ {diff:.1f}%")
        else: st.warning("⚖️ سعر عادل (سعر سوق)")
    else:
        st.warning("لا توجد بيانات أراضي للمقارنة.")

    # 2. تقييم التطوير
    if avg_build > 0:
        total_cost = (area * price_pm) + (area * 2.2 * build_cost) # افتراض مسطحات 2.2
        expected_sell = area * avg_build # تقريبي
        profit = expected_sell - total_cost
        
        st.write(f"تكلفة المشروع التقديرية: **{total_cost:,.0f}** ريال")
        st.write(f"سعر البيع المتوقع (للفيلا): **{expected_sell:,.0f}** ريال")
        
        if profit > 0: st.markdown(f"<h3 style='color:green'>ربح متوقع: {profit:,.0f} ريال</h3>", unsafe_allow_html=True)
        else: st.markdown(f"<h3 style='color:red'>خسارة محتملة: {profit:,.0f} ريال</h3>", unsafe_allow_html=True)
    else:
        st.info("لا توجد بيانات مباني في هذا الحي لحساب الجدوى.")
