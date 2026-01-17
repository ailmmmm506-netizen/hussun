import streamlit as st
import pandas as pd
import data_bot  # نستورد المحرك السليم

# إعداد الصفحة
st.set_page_config(page_title="دراسة الجدوى العقارية", layout="centered", page_icon="💰")

# --- 1. التأكد من تحميل البيانات (نفس كود الداشبورد بالضبط) ---
if 'bot' not in st.session_state:
    with st.spinner("جاري الاتصال بقاعدة البيانات..."):
        try:
            # هنا نجبر التطبيق على تشغيل البوت إذا لم يكن موجوداً
            st.session_state.bot = data_bot.RealEstateBot()
        except Exception as e:
            st.error(f"فشل الاتصال: {e}")

# سحب الداتا من البوت
if hasattr(st.session_state, 'bot') and hasattr(st.session_state.bot, 'df'):
    df = st.session_state.bot.df
else:
    df = pd.DataFrame()

# --- 2. القائمة الجانبية (للتأكد أن كل شيء تمام) ---
with st.sidebar:
    st.header("⚙️ حالة النظام")
    
    # زر التحديث (مهم جداً لإنعاش الذاكرة)
    if st.button("🔄 تحديث البيانات", type="primary"):
        st.cache_data.clear()
        # مسح الذاكرة لإجبار إعادة التحميل
        for key in list(st.session_state.keys()):
            del st.session_state[key]
        st.rerun()

    st.divider()
    
    # مؤشر الحالة
    if not df.empty:
        st.success(f"✅ متصل: {len(df)} صفقة")
        st.info("البيانات جاهزة للتحليل")
    else:
        st.error("❌ غير متصل / لا توجد بيانات")
        st.warning("حاول الضغط على زر التحديث بالأعلى 👆")

# --- 3. تطبيق دراسة الجدوى ---
st.title("💰 حاسبة الجدوى العقارية")

if df.empty:
    st.warning("⚠️ النظام بانتظار البيانات... الرجاء الضغط على 'تحديث البيانات' في القائمة الجانبية.")
else:
    # --- واجهة الإدخال ---
    st.markdown("### 📝 تفاصيل الفرصة")
    
    # التأكد من وجود أحياء قبل عرض القائمة
    districts = sorted(df['الحي'].unique()) if 'الحي' in df.columns else []
    
    if not districts:
        st.error("البيانات موجودة لكن لا يوجد عمود 'الحي'. تأكد من ملفات الإكسل.")
        st.stop()

    c1, c2 = st.columns(2)
    with c1:
        selected_dist = st.selectbox("اختر الحي:", districts)
        land_area = st.number_input("مساحة الأرض (م²):", value=400, step=10)
    with c2:
        offer_price = st.number_input("سعر المتر المعروض (ريال):", value=3500, step=50)
        build_cost = st.number_input("تكلفة البناء للمتر (ريال):", value=1800, step=50)

    # --- المحرك الحسابي ---
    # فلترة البيانات للحي المختار
    lands_data = df[(df['الحي'] == selected_dist) & (df['نوع_العقار'].str.contains('أرض', na=False))]
    build_data = df[(df['الحي'] == selected_dist) & (df['نوع_العقار'].str.contains('مبني', na=False))]
    
    # حساب المتوسطات
    market_land_price = lands_data['سعر_المتر'].median() if not lands_data.empty else 0
    market_villa_price = build_data['سعر_المتر'].median() if not build_data.empty else 0

    st.markdown("---")
    
    # --- عرض النتائج ---
    res1, res2 = st.columns(2)
    
    # 1. تحليل سعر الأرض
    with res1:
        st.subheader("📊 تحليل سعر الأرض")
        if market_land_price > 0:
            diff_pct = ((offer_price - market_land_price) / market_land_price) * 100
            
            st.metric("متوسط سعر السوق (للأراضي)", f"{market_land_price:,.0f} ريال")
            
            if diff_pct < -5:
                st.success(f"✅ فرصة ممتازة! (أقل من السوق بـ {abs(diff_pct):.1f}%)")
            elif diff_pct > 5:
                st.error(f"❌ سعر مرتفع (أعلى من السوق بـ {diff_pct:.1f}%)")
            else:
                st.warning("⚖️ سعر عادل (موافق للسوق)")
        else:
            st.info(f"لا تتوفر صفقات أراضي كافية في حي {selected_dist} للمقارنة.")

    # 2. تحليل التطوير (الجدوى)
    with res2:
        st.subheader("🏗️ جدوى التطوير (فيلا)")
        if market_villa_price > 0:
            # التكاليف
            land_cost = land_area * offer_price
            construction_cost = land_area * 2.2 * build_cost # افتراض مسطحات 2.2
            total_cost = land_cost + construction_cost
            
            # الإيراد المتوقع (مساحة الأرض * سعر متر الفيلا القائم شامل الأرض والبناء)
            expected_revenue = land_area * market_villa_price
            
            profit = expected_revenue - total_cost
            roi = (profit / total_cost) * 100
            
            st.write(f"التكلفة التقديرية: **{total_cost:,.0f}** ريال")
            st.write(f"البيع المتوقع: **{expected_revenue:,.0f}** ريال")
            
            if profit > 0:
                st.markdown(f":green[**ربح صافي متوقع: {profit:,.0f} ريال ({roi:.1f}%)**]")
            else:
                st.markdown(f":red[**خسارة محتملة: {profit:,.0f} ريال**]")
        else:
            st.info(f"لا تتوفر صفقات فلل كافية في حي {selected_dist} لحساب سعر البيع المتوقع.")
