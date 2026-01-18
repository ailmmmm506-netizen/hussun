import streamlit as st
import pandas as pd
import numpy as np
import data_bot  # استيراد المحرك

# إعداد الصفحة
st.set_page_config(page_title="المستشار العقاري - دراسة الجدوى الدقيقة", layout="wide", page_icon="⚖️")

# --- التنسيق الجمالي ---
st.markdown("""
<style>
    .header-style {font-size:22px; font-weight:bold; color:#1f77b4; margin-bottom:10px;}
    .metric-container {background-color:#f8f9fa; padding:15px; border-radius:8px; border:1px solid #ddd; text-align:center;}
    .big-num {font-size:24px; font-weight:bold; color:#2c3e50;}
    .label-text {font-size:14px; color:#7f8c8d;}
</style>
""", unsafe_allow_html=True)

# --- دالة التنظيف الذكي (Smart Cleaning) ---
def get_clean_stats(df_input, col='سعر_المتر'):
    """
    تقوم هذه الدالة بحذف القيم الشاذة (أعلى 10% وأقل 10%) 
    لإعطاء متوسط سعري دقيق يعكس واقع السوق.
    """
    if df_input.empty: return 0, 0, 0
    
    # 1. استبعاد القيم الصفرية أو السالبة
    clean_df = df_input[df_input[col] > 100].copy() # نفترض أن المتر لا يقل عن 100 ريال
    
    if clean_df.empty: return 0, 0, 0

    # 2. حساب الحدود (Quantiles) لاستبعاد الشواذ
    low_limit = clean_df[col].quantile(0.10) # استبعاد أرخص 10% (غالباً صفقات عائلية)
    high_limit = clean_df[col].quantile(0.90) # استبعاد أغلى 10% (غالباً أخطاء إدخال)
    
    # 3. الفلترة النهائية
    final_df = clean_df[(clean_df[col] >= low_limit) & (clean_df[col] <= high_limit)]
    
    if final_df.empty: return 0, 0, 0
    
    # إرجاع: المتوسط (Median)، أقل سعر حقيقي، أعلى سعر حقيقي
    return final_df[col].median(), final_df[col].min(), final_df[col].max()

# --- التأكد من الاتصال ---
if 'bot' not in st.session_state:
    with st.spinner("جاري تهيئة خوارزميات التدقيق..."):
        try:
            st.session_state.bot = data_bot.RealEstateBot()
        except: st.error("خطأ في الاتصال")

df = st.session_state.bot.df if hasattr(st.session_state.bot, 'df') else pd.DataFrame()

# --- القائمة الجانبية ---
with st.sidebar:
    st.header("⚙️ التحكم")
    if st.button("🔄 تحديث وتحليل البيانات", type="primary", use_container_width=True):
        st.cache_data.clear()
        for key in list(st.session_state.keys()): del st.session_state[key]
        st.rerun()
    
    st.divider()
    if not df.empty:
        st.success(f"✅ قاعدة البيانات: {len(df)} صفقة")
    else:
        st.error("❌ لا توجد بيانات")

# --- الواجهة الرئيسية ---
st.title("🏗️ دراسة الجدوى العقارية (المدققة)")
st.caption("يتم استخدام خوارزمية لاستبعاد الصفقات الشاذة (المنخفضة جداً أو المرتفعة جداً) لضمان دقة التقييم.")

if df.empty:
    st.warning("الرجاء تحديث البيانات من القائمة الجانبية.")
    st.stop()

# ========================================================
# 1. المدخلات (Inputs)
# ========================================================
with st.container():
    st.markdown("<div class='header-style'>1️⃣ محددات الدراسة</div>", unsafe_allow_html=True)
    
    districts = sorted(df['الحي'].unique()) if 'الحي' in df.columns else []
    
    col1, col2, col3 = st.columns(3)
    with col1:
        selected_dist = st.selectbox("📍 اختر الحي", districts)
    with col2:
        land_area = st.number_input("📐 مساحة الأرض (م²)", value=375)
    with c3:
        offer_price = st.number_input("💰 سعر المتر المعروض (ريال)", value=3500)

    col4, col5, col6 = st.columns(3)
    with col4:
        build_cost = st.number_input("🔨 تكلفة البناء للمتر (ريال)", value=1700, help="تكلفة العظم والتشطيب")
    with col5:
        build_ratio = st.slider("نسبة المسطحات (%)", 1.5, 3.5, 2.3)
    with col6:
        fees_pct = st.number_input("رسوم إضافية (%)", value=7.5, help="تشمل 5% ضريبة تصرفات + 2.5% سعي")

# ========================================================
# 2. المعالجة والتحليل (Processing)
# ========================================================

# فصل البيانات
lands_raw = df[(df['الحي'] == selected_dist) & (df['نوع_العقار'].str.contains('أرض', na=False))]
builds_raw = df[(df['الحي'] == selected_dist) & (df['نوع_العقار'].str.contains('مبني', na=False))]

# --- تطبيق التنظيف الذكي للحصول على أرقام دقيقة ---
clean_land_price, min_land, max_land = get_clean_stats(lands_raw)
clean_build_price, min_build, max_build = get_clean_stats(builds_raw)

st.markdown("---")

# ========================================================
# 3. عرض مؤشرات السوق الدقيقة (Market Benchmarks)
# ========================================================
st.markdown("<div class='header-style'>2️⃣ مؤشرات السوق (بعد التنظيف واستبعاد الشواذ)</div>", unsafe_allow_html=True)

m1, m2 = st.columns(2)

with m1:
    st.info(f"📊 مؤشر الأراضي في {selected_dist}")
    if clean_land_price > 0:
        c1, c2, c3 = st.columns(3)
        c1.metric("متوسط سعر المتر (الدقيق)", f"{clean_land_price:,.0f} ريال")
        c2.metric("أقل سعر سوقي", f"{min_land:,.0f} ريال")
        c3.metric("أعلى سعر سوقي", f"{max_land:,.0f} ريال")
    else:
        st.warning("لا توجد صفقات أراضي كافية للتحليل الدقيق.")

with m2:
    st.success(f"🏠 مؤشر المباني (الفلل/الشقق) في {selected_dist}")
    if clean_build_price > 0:
        c1, c2, c3 = st.columns(3)
        c1.metric("متوسط بيع المتر (شامل)", f"{clean_build_price:,.0f} ريال")
        c2.metric("أقل سعر بيع", f"{min_build:,.0f} ريال")
        c3.metric("أعلى سعر بيع", f"{max_build:,.0f} ريال")
    else:
        st.warning("لا توجد صفقات مباني كافية للتحليل الدقيق.")

st.markdown("---")

# ========================================================
# 4. تقرير الجدوى (Feasibility Report)
# ========================================================
st.markdown("<div class='header-style'>3️⃣ تقرير الجدوى الاقتصادية</div>", unsafe_allow_html=True)

# أ. التكاليف
base_land_cost = land_area * offer_price
added_fees = base_land_cost * (fees_pct / 100)
total_land_cost = base_land_cost + added_fees

total_build_area = land_area * build_ratio
total_construction_cost = total_build_area * build_cost

grand_total = total_land_cost + total_construction_cost

# ب. الإيرادات المتوقعة (بناءً على متوسط السوق للمباني)
expected_revenue_conservative = land_area * clean_build_price # السيناريو الواقعي
expected_revenue_optimistic = land_area * max_build # السيناريو المتفائل

# ج. الربح
profit = expected_revenue_conservative - grand_total
roi = (profit / grand_total) * 100

# العرض
row1_1, row1_2 = st.columns([1, 2])

with row1_1:
    st.markdown("#### 💸 ملخص التكاليف")
    costs_df = pd.DataFrame({
        "البند": ["قيمة الأرض", "رسوم وضرائب", "تكلفة البناء", "الإجمالي"],
        "المبلغ": [base_land_cost, added_fees, total_construction_cost, grand_total]
    })
    st.dataframe(costs_df.style.format({"المبلغ": "{:,.0f}"}), use_container_width=True)

with row1_2:
    st.markdown("#### 📈 تحليل الربحية (السيناريو الواقعي)")
    
    if clean_build_price > 0:
        k1, k2, k3 = st.columns(3)
        k1.metric("التكلفة الكلية", f"{grand_total:,.0f} ريال")
        k2.metric("البيع المتوقع", f"{expected_revenue_conservative:,.0f} ريال")
        k3.metric("صافي الربح", f"{profit:,.0f} ريال", delta=f"{roi:.1f}% عائد")
        
        # التوصية الذكية
        if roi > 25:
            st.success("🌟 **توصية:** فرصة ذهبية! العائد المتوقع ممتاز جداً (أعلى من 25%).")
        elif roi > 15:
            st.success("✅ **توصية:** مشروع جيد. العائد ضمن النطاق الصحي للتطوير (15-25%).")
        elif roi > 0:
            st.warning("⚠️ **توصية:** العائد منخفض. راجع تكاليف البناء أو فاوض في سعر الأرض.")
        else:
            st.error("⛔ **توصية:** المشروع خاسر بناءً على معطيات السوق الحالية.")
            
        # شريط التقدم للربح
        st.write("هامش الربح المتوقع:")
        st.progress(min(max(roi/100, 0.0), 1.0))
        
    else:
        st.info("لا يمكن حساب الربحية لعدم وجود بيانات بيع مباني في هذا الحي.")

# تقييم سعر المتر المعروض
st.markdown("---")
if clean_land_price > 0:
    diff_pct = ((offer_price - clean_land_price) / clean_land_price) * 100
    st.write(f"**تقييم سعر العرض ({offer_price}):**")
    if diff_pct < -5:
        st.caption(f"✅ السعر المعروض **أرخص** من متوسط السوق الدقيق بـ {abs(diff_pct):.1f}%")
    elif diff_pct > 5:
        st.caption(f"❌ السعر المعروض **أغلى** من متوسط السوق الدقيق بـ {diff_pct:.1f}%")
    else:
        st.caption("⚖️ السعر المعروض **عادل** ومطابق للسوق.")
