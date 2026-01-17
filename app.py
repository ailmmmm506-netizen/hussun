import streamlit as st
import pandas as pd
import data_bot  # استيراد المحرك

# إعداد الصفحة
st.set_page_config(page_title="المستشار العقاري - دراسة الجدوى", layout="wide", page_icon="🏗️")

# --- التنسيق الجمالي (CSS) ---
st.markdown("""
<style>
    .header-style {font-size:24px; font-weight:bold; color:#2c3e50; margin-bottom:15px;}
    .sub-header {font-size:18px; font-weight:bold; color:#505c6e;}
    .metric-box {border:1px solid #e0e0e0; padding:15px; border-radius:10px; background-color:#f9f9f9; text-align:center;}
    .profit-win {color: green; font-weight: bold;}
    .profit-loss {color: red; font-weight: bold;}
</style>
""", unsafe_allow_html=True)

# --- 1. التأكد من الاتصال بالبيانات ---
if 'bot' not in st.session_state:
    with st.spinner("جاري جلب بيانات السوق الحالية..."):
        try:
            st.session_state.bot = data_bot.RealEstateBot()
        except Exception as e:
            st.error(f"خطأ في الاتصال: {e}")

# استدعاء البيانات
if hasattr(st.session_state, 'bot') and hasattr(st.session_state.bot, 'df'):
    df = st.session_state.bot.df
else:
    df = pd.DataFrame()

# --- القائمة الجانبية (للتحديث) ---
with st.sidebar:
    st.header("لوحة التحكم")
    if st.button("🔄 تحديث بيانات السوق", type="primary", use_container_width=True):
        st.cache_data.clear()
        for key in list(st.session_state.keys()): del st.session_state[key]
        st.rerun()
    
    st.markdown("---")
    if not df.empty:
        st.success(f"✅ متصل بقاعدة البيانات\n({len(df)} صفقة مرصودة)")
    else:
        st.warning("⚠️ لا توجد بيانات. اضغط تحديث.")

# --- العنوان ---
st.title("🏗️ نظام دراسة الجدوى العقارية الشامل")
st.markdown("حاسبة مطورة لحساب تكاليف شراء الأرض، التطوير، والبناء، ومقارنتها بأسعار السوق الحالية.")

if df.empty:
    st.info("الرجاء تحديث البيانات من القائمة الجانبية للبدء.")
    st.stop()

# ========================================================
# 1. مدخلات الدراسة (Inputs)
# ========================================================
with st.form("feasibility_form"):
    st.markdown("<div class='header-style'>1️⃣ بيانات الأرض والشراء</div>", unsafe_allow_html=True)
    
    # اختيار الحي (مفلتر)
    districts = sorted(df['الحي'].unique()) if 'الحي' in df.columns else []
    if not districts: st.error("لا توجد أحياء!"); st.stop()
    
    c1, c2, c3 = st.columns(3)
    with c1:
        selected_dist = st.selectbox("📍 الحي المستهدف", districts)
    with c2:
        land_area = st.number_input("📐 مساحة الأرض (م²)", value=375, step=25)
    with c3:
        offer_price = st.number_input("💰 سعر المتر المعروض (ريال)", value=3500, step=50)

    st.markdown("---")
    st.markdown("<div class='header-style'>2️⃣ تكاليف التطوير والبناء</div>", unsafe_allow_html=True)
    
    c4, c5, c6 = st.columns(3)
    with c4:
        # نسبة البناء (عادة الفيلا تكون 2.2 الى 2.5 من مساحة الارض شامل الاسوار والملحقات)
        build_ratio = st.slider("نسبة مسطحات البناء (%)", 1.5, 3.5, 2.3, help="إجمالي الأمتار المبنية مقارنة بمساحة الأرض (مثلاً 2.3 تعني فيلا دورين وملحق)")
    with c5:
        build_cost_sqm = st.number_input("🔨 تكلفة بناء المتر 'تسليم مفتاح' (ريال)", value=1700, step=50, help="تشمل العظم والتشطيب")
    with c6:
        other_fees_pct = st.number_input("مشال وتصاريم وإشراف (%)", value=2.5, step=0.5, help="نسبة من تكلفة البناء (مكتب هندسي، إشراف، حفر...)")

    st.markdown("---")
    submitted = st.form_submit_button("📊 بدء التحليل وحساب الجدوى", type="primary", use_container_width=True)

# ========================================================
# 2. الحسابات والنتائج (Results)
# ========================================================
if submitted:
    # --- أ. تجهيز بيانات المقارنة من السوق ---
    # صفقات الأراضي في نفس الحي
    lands_data = df[(df['الحي'] == selected_dist) & (df['نوع_العقار'].str.contains('أرض', na=False))]
    # صفقات الفلل في نفس الحي
    villas_data = df[(df['الحي'] == selected_dist) & (df['نوع_العقار'].str.contains('مبني', na=False))]
    
    avg_land_market = lands_data['سعر_المتر'].median() if not lands_data.empty else 0
    # سعر بيع الفيلا في السوق (نحسبه كسعر متر شامل الأرض والبناء)
    avg_villa_market_sqm = villas_data['سعر_المتر'].median() if not villas_data.empty else 0
    max_villa_market_sqm = villas_data['سعر_المتر'].max() if not villas_data.empty else 0

    # --- ب. الحسابات المالية الدقيقة ---
    # 1. تكاليف الأرض
    land_base_price = land_area * offer_price
    tax_rett = land_base_price * 0.05  # ضريبة تصرفات 5%
    broker_fee = land_base_price * 0.025 # سعي 2.5%
    total_land_cost = land_base_price + tax_rett + broker_fee
    
    # 2. تكاليف البناء
    total_build_area = land_area * build_ratio # إجمالي المسطحات
    construction_cost = total_build_area * build_cost_sqm
    design_supervision_cost = construction_cost * (other_fees_pct / 100)
    total_build_cost = construction_cost + design_supervision_cost
    
    # 3. إجمالي المشروع
    grand_total_cost = total_land_cost + total_build_cost
    cost_per_unit_sqm = grand_total_cost / land_area # تكلفتك للمتر (شامل أرض وبناء)

    # --- ج. عرض النتائج ---
    
    # 1. تحليل سعر الأرض
    st.markdown(f"### 🔎 1. تحليل سعر الأرض في حي ({selected_dist})")
    k1, k2, k3 = st.columns(3)
    k1.metric("السعر المعروض", f"{offer_price:,.0f} ريال")
    k2.metric("متوسط السوق (أراضي)", f"{avg_land_market:,.0f} ريال", delta=f"{offer_price - avg_land_market:,.0f} الفارق", delta_color="inverse")
    
    if avg_land_market > 0:
        diff_pct = ((offer_price - avg_land_market) / avg_land_market) * 100
        if diff_pct < -2:
            st.success(f"✅ السعر ممتاز! أقل من متوسط السوق بـ {abs(diff_pct):.1f}%")
        elif diff_pct > 2:
            st.error(f"❌ السعر مرتفع! أعلى من متوسط السوق بـ {diff_pct:.1f}%")
        else:
            st.warning("⚖️ السعر عادل (مطابق للسوق)")
    else:
        st.info("لا توجد بيانات أراضي كافية للمقارنة الدقيقة.")

    st.markdown("---")

    # 2. التفاصيل المالية (الجدول)
    st.markdown("### 💸 2. تفاصيل التكاليف التقديرية")
    
    cost_data = {
        "البند": [
            "قيمة الأرض الأساسية", 
            "ضريبة التصرفات العقارية (5%)", 
            "سعي المكتب (2.5%)", 
            "--- إجمالي تكلفة الأرض ---",
            f"تكلفة البناء ({total_build_area:,.0f} م² مسطحات)",
            f"تصميم وإشراف وخدمات ({other_fees_pct}%)",
            "--- إجمالي تكلفة البناء ---",
            "✨ إجمالي تكلفة المشروع"
        ],
        "المبلغ (ريال)": [
            land_base_price, 
            tax_rett, 
            broker_fee, 
            total_land_cost,
            construction_cost,
            design_supervision_cost,
            total_build_cost,
            grand_total_cost
        ]
    }
    st.dataframe(pd.DataFrame(cost_data).style.format({"المبلغ (ريال)": "{:,.0f}"}), use_container_width=True)

    st.markdown("---")

    # 3. مؤشرات الربحية (الزبدة)
    st.markdown("### 📈 3. جدوى المشروع (الربح المتوقع)")

    if avg_villa_market_sqm > 0:
        # السيناريو المتحفظ (البيع بمتوسط السوق)
        revenue_conservative = land_area * avg_villa_market_sqm
        profit_conservative = revenue_conservative - grand_total_cost
        roi_conservative = (profit_conservative / grand_total_cost) * 100
        
        # السيناريو المتفائل (البيع بأعلى سعر في الحي)
        revenue_optimistic = land_area * max_villa_market_sqm
        profit_optimistic = revenue_optimistic - grand_total_cost
        roi_optimistic = (profit_optimistic / grand_total_cost) * 100

        col_a, col_b = st.columns(2)
        
        with col_a:
            st.markdown("#### 😐 السيناريو المتحفظ (متوسط السوق)")
            st.write(f"سعر البيع المتوقع: **{revenue_conservative:,.0f}** ريال")
            if profit_conservative > 0:
                st.markdown(f"<span class='profit-win'>صافي الربح: {profit_conservative:,.0f} ريال ({roi_conservative:.1f}%)</span>", unsafe_allow_html=True)
            else:
                st.markdown(f"<span class='profit-loss'>خسارة محتملة: {profit_conservative:,.0f} ريال</span>", unsafe_allow_html=True)

        with col_b:
            st.markdown("#### 🤩 السيناريو المتفائل (أعلى سعر)")
            st.write(f"سعر البيع المتوقع: **{revenue_optimistic:,.0f}** ريال")
            if profit_optimistic > 0:
                st.markdown(f"<span class='profit-win'>صافي الربح: {profit_optimistic:,.0f} ريال ({roi_optimistic:.1f}%)</span>", unsafe_allow_html=True)
            else:
                st.markdown(f"<span class='profit-loss'>خسارة محتملة: {profit_optimistic:,.0f} ريال</span>", unsafe_allow_html=True)
                
    else:
        st.warning(f"⚠️ لا توجد صفقات فلل مباعة في حي ({selected_dist}) مؤخراً، لذا يصعب تقدير سعر البيع بدقة. يفضل البحث عن أحياء مجاورة للمقارنة.")
