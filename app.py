import streamlit as st
import pandas as pd
import numpy as np
import data_bot  # استيراد المحرك

# إعداد الصفحة
st.set_page_config(page_title="المستشار العقاري - دراسة الجدوى الاحترافية", layout="wide", page_icon="🏦")

# --- التنسيق الجمالي ---
st.markdown("""
<style>
    .header-style {font-size:22px; font-weight:bold; color:#1f77b4; margin-bottom:10px; border-bottom: 2px solid #eee; padding-bottom: 5px;}
    .metric-container {background-color:#f8f9fa; padding:15px; border-radius:8px; border:1px solid #ddd; text-align:center;}
    .dataframe {direction: rtl;}
</style>
""", unsafe_allow_html=True)

# --- دوال مساعدة ---
def get_clean_stats(df_input, col='سعر_المتر'):
    if df_input.empty: return 0, 0, 0
    clean_df = df_input[df_input[col] > 100].copy()
    if clean_df.empty: return 0, 0, 0
    low_limit = clean_df[col].quantile(0.10)
    high_limit = clean_df[col].quantile(0.90)
    final_df = clean_df[(clean_df[col] >= low_limit) & (clean_df[col] <= high_limit)]
    if final_df.empty: return 0, 0, 0
    return final_df[col].median(), final_df[col].min(), final_df[col].max()

# --- الاتصال ---
if 'bot' not in st.session_state:
    with st.spinner("جاري الاتصال..."):
        try: st.session_state.bot = data_bot.RealEstateBot()
        except: st.error("خطأ في الاتصال")

df = st.session_state.bot.df if hasattr(st.session_state.bot, 'df') else pd.DataFrame()

# ========================================================
# 🟢 القائمة الجانبية
# ========================================================
with st.sidebar:
    st.header("⚙️ التحكم")
    if st.button("🔄 تحديث البيانات", type="primary", use_container_width=True):
        st.cache_data.clear()
        for key in list(st.session_state.keys()): del st.session_state[key]
        st.rerun()
    
    st.divider()
    if not df.empty:
        st.success(f"✅ متصل: {len(df):,} صفقة")
        with st.expander("📂 تفاصيل الملفات"):
            if 'Source_File' in df.columns:
                stats = df['Source_File'].value_counts().reset_index()
                stats.columns = ['الملف', 'العدد']
                st.dataframe(stats, hide_index=True)
    else:
        st.error("❌ لا توجد بيانات")

# ========================================================
# 📟 الواجهة الرئيسية
# ========================================================
st.title("🏦 دراسة الجدوى العقارية (الاحترافية)")
st.caption("نظام تحليل مخاطر وعوائد التطوير العقاري.")

if df.empty:
    st.warning("⚠️ بانتظار البيانات... الرجاء التحديث من القائمة الجانبية.")
    st.stop()

# --------------------------------------------------------
# 1. المدخلات الأساسية
# --------------------------------------------------------
with st.container():
    st.markdown("<div class='header-style'>1️⃣ محددات الأرض والبناء</div>", unsafe_allow_html=True)
    districts = sorted(df['الحي'].unique()) if 'الحي' in df.columns else []
    
    c1, c2, c3 = st.columns(3)
    with c1: selected_dist = st.selectbox("📍 الحي", districts)
    with c2: land_area = st.number_input("📐 مساحة الأرض (م²)", value=375)
    with c3: offer_price = st.number_input("💰 سعر المتر (ريال)", value=3500)

    c4, c5, c6 = st.columns(3)
    with c4: build_cost = st.number_input("🔨 تكلفة البناء/م (ريال)", value=1700)
    with c5: build_ratio = st.slider("نسبة المسطحات (%)", 1.5, 3.5, 2.3)
    with c6: fees_pct = st.number_input("رسوم حكومية وسعي (%)", value=7.5)

# --------------------------------------------------------
# 2. المدخلات المالية والزمنية (الميزة الجديدة)
# --------------------------------------------------------
with st.expander("⏳ التكاليف التمويلية والزمنية (إعدادات متقدمة)", expanded=True):
    fc1, fc2 = st.columns(2)
    with fc1:
        project_duration = st.number_input("مدة المشروع (أشهر)", value=14, step=1, help="من شراء الأرض حتى البيع")
    with fc2:
        finance_rate = st.number_input("تكلفة التمويل السنوية (%)", value=0.0, step=0.5, help="نسبة البنك أو تكلفة الفرصة البديلة لرأس المال")

# --------------------------------------------------------
# 3. المعالجة
# --------------------------------------------------------
lands_raw = df[(df['الحي'] == selected_dist) & (df['نوع_العقار'].str.contains('أرض', na=False))]
builds_raw = df[(df['الحي'] == selected_dist) & (df['نوع_العقار'].str.contains('مبني', na=False))]

clean_land_price, min_land, max_land = get_clean_stats(lands_raw)
clean_build_price, min_build, max_build = get_clean_stats(builds_raw)

# --------------------------------------------------------
# 4. الحسابات المالية المفصلة
# --------------------------------------------------------
# التكاليف المباشرة
land_base = land_area * offer_price
land_fees = land_base * (fees_pct / 100)
total_land = land_base + land_fees

build_area = land_area * build_ratio
total_construction = build_area * build_cost

direct_cost = total_land + total_construction

# التكاليف التمويلية (Financing Costs)
# الفائدة تحسب تقريباً على كامل المبلغ أو متوسط الصرف، سنحسبها على إجمالي التكلفة المباشرة للتبسيط والتحوط
finance_cost = direct_cost * (finance_rate / 100) * (project_duration / 12)

grand_total = direct_cost + finance_cost

# الإيرادات
expected_revenue = land_area * clean_build_price

# الربح
net_profit = expected_revenue - grand_total
roi = (net_profit / grand_total) * 100

st.markdown("---")

# --------------------------------------------------------
# 5. التقرير المالي
# --------------------------------------------------------
st.markdown("<div class='header-style'>2️⃣ النتائج المالية</div>", unsafe_allow_html=True)

col_res1, col_res2 = st.columns([1.5, 2])

with col_res1:
    st.markdown("#### 💸 هيكل التكاليف")
    cost_data = {
        "البند": ["الأرض والرسوم", "البناء والتطوير", "تكاليف التمويل/الزمن", "🔴 الإجمالي"],
        "القيمة": [total_land, total_construction, finance_cost, grand_total]
    }
    df_cost = pd.DataFrame(cost_data)
    st.dataframe(df_cost.style.format({"القيمة": "{:,.0f}"}), use_container_width=True)

with col_res2:
    st.markdown("#### 📈 مؤشرات الربحية")
    if clean_build_price > 0:
        k1, k2, k3 = st.columns(3)
        k1.metric("التكلفة الكلية", f"{grand_total:,.0f}")
        k2.metric("الإيراد المتوقع", f"{expected_revenue:,.0f}")
        k3.metric("صافي الربح", f"{net_profit:,.0f}", delta=f"{roi:.1f}%")
        
        if roi > 20: st.success("🌟 مشروع ممتاز (العائد > 20%)")
        elif roi > 10: st.info("✅ مشروع جيد (العائد > 10%)")
        else: st.error("⚠️ مشروع عالي المخاطر (العائد < 10%)")
    else:
        st.warning("لا توجد بيانات بيع فلل في الحي لحساب الربح.")

# --------------------------------------------------------
# 6. تحليل الحساسية (Sensitivity Analysis) - الميزة القوية
# --------------------------------------------------------
st.markdown("---")
st.markdown("<div class='header-style'>3️⃣ تحليل الحساسية (سيناريوهات ماذا لو؟)</div>", unsafe_allow_html=True)
st.caption("هذا الجدول يوضح كيف يتأثر عائد الاستثمار (ROI) إذا تغيرت تكلفة البناء أو سعر البيع.")

if clean_build_price > 0:
    # إنشاء نطاقات للتغير (-10% إلى +10%)
    cost_changes = [-0.10, -0.05, 0, 0.05, 0.10]
    price_changes = [-0.10, -0.05, 0, 0.05, 0.10]
    
    # مصفوفة النتائج
    results = []
    for p_change in price_changes:
        row = []
        new_sell_price = expected_revenue * (1 + p_change)
        for c_change in cost_changes:
            # نغير فقط تكلفة البناء (الأرض ثابتة لأنك اشتريتها خلاص)
            new_build_cost = total_construction * (1 + c_change)
            new_total_cost = total_land + new_build_cost + finance_cost # إعادة حساب التكلفة
            
            profit_scenario = new_sell_price - new_total_cost
            roi_scenario = (profit_scenario / new_total_cost) * 100
            row.append(roi_scenario)
        results.append(row)
    
    # تحويل لجدول
    df_sens = pd.DataFrame(results, 
                           index=[f"بيع {p:+.0%}" for p in price_changes],
                           columns=[f"بناء {c:+.0%}" for c in cost_changes])
    
    # عرض الجدول مع تلوين (Heatmap)
    st.dataframe(df_sens.style.background_gradient(cmap="RdYlGn", vmin=0, vmax=30).format("{:.1f}%"), use_container_width=True)
    st.caption("👈 الأعمدة: تغير تكلفة البناء | الصفوف: تغير سعر البيع في السوق")

else:
    st.info("يتطلب تحليل الحساسية وجود بيانات بيع للمباني.")

# --------------------------------------------------------
# 7. تقييم سعر الأرض
# --------------------------------------------------------
st.markdown("---")
if clean_land_price > 0:
    diff_pct = ((offer_price - clean_land_price) / clean_land_price) * 100
    st.write(f"**⚖️ حكمنا على سعر الأرض:**")
    if diff_pct < -5: st.success(f"لقطة! أرخص من السوق بـ {abs(diff_pct):.1f}%")
    elif diff_pct > 5: st.error(f"غالية! أغلى من السوق بـ {diff_pct:.1f}%")
    else: st.warning("سعر عادل (مطابق للسوق)")
