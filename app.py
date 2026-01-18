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
</style>
""", unsafe_allow_html=True)

# --- دالة التنظيف الذكي (Smart Cleaning) ---
def get_clean_stats(df_input, col='سعر_المتر'):
    if df_input.empty: return 0, 0, 0
    
    clean_df = df_input[df_input[col] > 100].copy()
    if clean_df.empty: return 0, 0, 0

    low_limit = clean_df[col].quantile(0.10)
    high_limit = clean_df[col].quantile(0.90)
    
    final_df = clean_df[(clean_df[col] >= low_limit) & (clean_df[col] <= high_limit)]
    
    if final_df.empty: return 0, 0, 0
    
    return final_df[col].median(), final_df[col].min(), final_df[col].max()

# --- التأكد من الاتصال ---
if 'bot' not in st.session_state:
    with st.spinner("جاري تهيئة خوارزميات التدقيق..."):
        try:
            st.session_state.bot = data_bot.RealEstateBot()
        except: st.error("خطأ في الاتصال")

df = st.session_state.bot.df if hasattr(st.session_state.bot, 'df') else pd.DataFrame()

# ========================================================
# 🟢 القائمة الجانبية (تم التعديل هنا)
# ========================================================
with st.sidebar:
    st.header("⚙️ لوحة التحكم")
    
    # 1. زر التحديث
    if st.button("🔄 تحديث وتحليل البيانات", type="primary", use_container_width=True):
        st.cache_data.clear()
        for key in list(st.session_state.keys()): del st.session_state[key]
        st.rerun()
    
    st.divider()

    # 2. عرض حالة البيانات
    if not df.empty:
        st.success(f"✅ الحالة: متصل ({len(df):,} صفقة)")
        
        # 🆕 الميزة الجديدة: خانة مصادر البيانات القابلة للفتح
        with st.expander("📂 مصدر البيانات (الملفات)", expanded=False):
            if 'Source_File' in df.columns:
                # حساب عدد الصفقات لكل ملف
                file_stats = df['Source_File'].value_counts().reset_index()
                file_stats.columns = ['اسم الملف', 'العدد']
                st.dataframe(file_stats, hide_index=True, use_container_width=True)
            else:
                st.info("لا توجد تفاصيل للمصادر.")
    else:
        st.error("❌ لا توجد بيانات")

# --- الواجهة الرئيسية ---
st.title("🏗️ دراسة الجدوى العقارية (المدققة)")
st.caption("نظام ذكي لتقييم الفرص الاستثمارية بناءً على بيانات السوق الحقيقية.")

if df.empty:
    st.warning("⚠️ النظام بانتظار البيانات... اضغط 'تحديث وتحليل البيانات' في القائمة الجانبية.")
    st.stop()

# ========================================================
# 1. المدخلات (Inputs)
# ========================================================
with st.container():
    st.markdown("<div class='header-style'>1️⃣ محددات الدراسة</div>", unsafe_allow_html=True)
    
    districts = sorted(df['الحي'].unique()) if 'الحي' in df.columns else []
    
    c1, c2, c3 = st.columns(3)
    with c1:
        selected_dist = st.selectbox("📍 اختر الحي", districts)
    with c2:
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

# --- تطبيق التنظيف الذكي ---
clean_land_price, min_land, max_land = get_clean_stats(lands_raw)
clean_build_price, min_build, max_build = get_clean_stats(builds_raw)

st.markdown("---")

# ========================================================
# 3. عرض مؤشرات السوق (Market Benchmarks)
# ========================================================
st.markdown("<div class='header-style'>2️⃣ مؤشرات السوق (الصافية)</div>", unsafe_allow_html=True)

m1, m2 = st.columns(2)

with m1:
    st.info(f"📊 مؤشر الأراضي في {selected_dist}")
    if clean_land_price > 0:
        c1_sub, c2_sub, c3_sub = st.columns(3)
        c1_sub.metric("متوسط سعر المتر", f"{clean_land_price:,.0f} ريال")
        c2_sub.metric("أقل سعر", f"{min_land:,.0f} ريال")
        c3_sub.metric("أعلى سعر", f"{max_land:,.0f} ريال")
    else:
        st.warning("لا توجد صفقات أراضي كافية.")

with m2:
    st.success(f"🏠 مؤشر المباني في {selected_dist}")
    if clean_build_price > 0:
        c1_sub, c2_sub, c3_sub = st.columns(3)
        c1_sub.metric("متوسط سعر المتر (شامل)", f"{clean_build_price:,.0f} ريال")
        c2_sub.metric("أقل سعر", f"{min_build:,.0f} ريال")
        c3_sub.metric("أعلى سعر", f"{max_build:,.0f} ريال")
    else:
        st.warning("لا توجد صفقات مباني كافية.")

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

# ب. الإيرادات المتوقعة
expected_revenue_conservative = land_area * clean_build_price 
expected_revenue_optimistic = land_area * max_build 

# ج. الربح
profit = expected_revenue_conservative - grand_total
roi = (profit / grand_total) * 100

# العرض
row1_1, row1_2 = st.columns([1, 2])

with row1_1:
    st.markdown("#### 💸 التكاليف")
    costs_df = pd.DataFrame({
        "البند": ["قيمة الأرض", "رسوم وضرائب", "تكلفة البناء", "الإجمالي"],
        "المبلغ": [base_land_cost, added_fees, total_construction_cost, grand_total]
    })
    st.dataframe(costs_df.style.format({"المبلغ": "{:,.0f}"}), use_container_width=True)

with row1_2:
    st.markdown("#### 📈 الربحية المتوقعة")
    
    if clean_build_price > 0:
        k1, k2, k3 = st.columns(3)
        k1.metric("التكلفة الكلية", f"{grand_total:,.0f}")
        k2.metric("البيع المتوقع", f"{expected_revenue_conservative:,.0f}")
        k3.metric("صافي الربح", f"{profit:,.0f}", delta=f"{roi:.1f}%")
        
        # التوصية
        if roi > 25:
            st.success("🌟 **فرصة ممتازة:** العائد المتوقع مرتفع جداً.")
        elif roi > 15:
            st.success("✅ **فرصة جيدة:** العائد ضمن النطاق المقبول.")
        elif roi > 0:
            st.warning("⚠️ **هامش منخفض:** العائد قليل، يحتاج مراجعة التكاليف.")
        else:
            st.error("⛔ **غير مجدية:** المشروع يحقق خسارة بالأسعار الحالية.")
            
        st.progress(min(max(roi/100, 0.0), 1.0))
    else:
        st.info("تعذر حساب الربحية لغياب بيانات المباني.")

# تقييم سعر المتر المعروض
st.markdown("---")
if clean_land_price > 0:
    diff_pct = ((offer_price - clean_land_price) / clean_land_price) * 100
    st.write(f"**تقييم سعر العرض ({offer_price}):**")
    if diff_pct < -5:
        st.caption(f"✅ أرخص من السوق بـ {abs(diff_pct):.1f}%")
    elif diff_pct > 5:
        st.caption(f"❌ أغلى من السوق بـ {diff_pct:.1f}%")
    else:
        st.caption("⚖️ سعر عادل.")
