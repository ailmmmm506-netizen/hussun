import streamlit as st
import pandas as pd
import numpy as np
import data_bot  # المحرك

# إعداد الصفحة
st.set_page_config(page_title="المستشار العقاري - المدقق", layout="wide", page_icon="✔️")

# --- التنسيق الجمالي ---
st.markdown("""
<style>
    .investor-card {
        background-color: #ffffff;
        border-top: 5px solid #1f77b4;
        border-radius: 10px;
        padding: 25px;
        box-shadow: 0 4px 6px rgba(0,0,0,0.1);
        text-align: center;
        margin-bottom: 20px;
    }
    .big-stat { font-size: 28px; font-weight: bold; color: #2c3e50; }
    .stat-label { font-size: 14px; color: #7f8c8d; margin-bottom: 5px; }
    [data-testid="stSidebar"] { background-color: #f8f9fa; border-left: 1px solid #ddd; }
    .metric-good { color: #27ae60; }
    .metric-bad { color: #c0392b; }
</style>
""", unsafe_allow_html=True)

# --- 🧠 دالة التنظيف الإحصائي المتقدم (IQR Method) ---
def get_advanced_stats(df_input, col='سعر_المتر'):
    if df_input.empty: return 0, 0, 0, 0, "لا توجد بيانات"
    
    # 1. تنظيف أولي (استبعاد الأصفار)
    clean = df_input[(df_input[col] > 100) & (df_input[col] < 150000)].copy()
    if len(clean) < 3: return 0, 0, 0, 0, "بيانات غير كافية"

    # 2. تطبيق IQR (عزل الشواذ)
    Q1 = clean[col].quantile(0.25)
    Q3 = clean[col].quantile(0.75)
    IQR = Q3 - Q1
    
    lower_bound = Q1 - 1.5 * IQR
    upper_bound = Q3 + 1.5 * IQR
    
    final_df = clean[(clean[col] >= lower_bound) & (clean[col] <= upper_bound)]
    
    if final_df.empty: return 0, 0, 0, 0, "تشتت عالي"
    
    count = len(final_df)
    confidence = "✅ عالية" if count > 10 else "⚠️ متوسطة" if count > 5 else "❌ منخفضة"
    
    return final_df[col].median(), final_df[col].min(), final_df[col].max(), count, confidence

# --- الاتصال بالبيانات ---
if 'bot' not in st.session_state:
    with st.spinner("جاري الاتصال..."):
        try: st.session_state.bot = data_bot.RealEstateBot()
        except: st.error("خطأ في الاتصال")

df = st.session_state.bot.df if hasattr(st.session_state.bot, 'df') else pd.DataFrame()

# ========================================================
# 🟢 القائمة الجانبية
# ========================================================
with st.sidebar:
    st.title("🔎 إعدادات التحليل")
    
    if st.button("🔄 تحديث البيانات", use_container_width=True):
        st.cache_data.clear()
        for key in list(st.session_state.keys()): del st.session_state[key]
        st.rerun()
    st.divider()

    if df.empty:
        st.warning("بانتظار البيانات...")
        st.stop()

    # 1. الموقع
    districts_list = sorted(df['الحي'].unique()) if 'الحي' in df.columns else []
    
    location_input = st.text_input("🔗 بحث ذكي (رابط/اسم)", placeholder="رابط جوجل أو اسم الحي")
    default_ix = 0
    if location_input:
        for i, d in enumerate(districts_list):
            if d in location_input: default_ix = i; st.toast(f"📍 {d}"); break
    
    selected_dist = st.selectbox("اختر الحي", districts_list, index=default_ix)
    
    # 2. فلتر ذكي (مهم جداً لفصل البيانات)
    st.subheader("🛠️ فلترة نوع الأرض")
    land_filter_mode = st.radio("نوع الأرض:", ["سكني (أراضي فقط)", "تجاري / استثماري"], 
                               help="اختر 'سكني' لاستبعاد الأراضي التجارية باهظة الثمن")
    
    # 3. الأرقام
    c_s1, c_s2 = st.columns(2)
    with c_s1: land_area = st.number_input("المساحة (م²)", value=375)
    with c_s2: offer_price = st.number_input("سعر المتر المعروض", value=3500)

    st.divider()
    st.subheader("💰 التكاليف والبيع")
    build_cost_sqm = st.number_input("تكلفة البناء/م", value=1750)
    expected_sell_sqm = st.number_input("سعر بيع المتوقع/م", value=6500)
    build_ratio = st.slider("نسبة البناء", 1.0, 3.5, 2.3)
    fees_pct = st.number_input("رسوم إدارية (%)", value=8.0)

# ========================================================
# 🏭 المعالجة الذكية (الفصل الصارم)
# ========================================================
district_df = df[df['الحي'] == selected_dist].copy()

# 1. فصل الأراضي (Lands)
# الشرط: يجب أن يحتوي النوع على "أرض" ولا يحتوي على "فيلا" أو "شقة" أو "بيت" أو "مبني"
# هذا يمنع الفلل المسجلة كأراضي من الدخول هنا
lands_raw = district_df[
    (district_df['نوع_العقار'].str.contains('أرض', na=False)) & 
    (~district_df['نوع_العقار'].str.contains('مبني|فيلا|شقة|بيت', regex=True, na=False))
]

# فلترة إضافية للسكني/التجاري
if land_filter_mode == "سكني (أراضي فقط)":
    # استبعاد التجاري الصريح + استبعاد الأسعار الفلكية (أعلى من 15000 للمتر غالباً تجاري)
    lands_filtered = lands_raw[
        (~lands_raw['نوع_العقار_الخام'].str.contains('تجاري', na=False)) &
        (lands_raw['سعر_المتر'] < 15000) 
    ]
else:
    # التجاري: نبحث عن كلمة تجاري أو أسعار عالية
    lands_filtered = lands_raw[
        (lands_raw['نوع_العقار_الخام'].str.contains('تجاري', na=False)) |
        (lands_raw['سعر_المتر'] >= 5000)
    ]
    if lands_filtered.empty: lands_filtered = lands_raw # احتياط

# 2. فصل المباني (Buildings)
builds_raw = district_df[district_df['نوع_العقار'].str.contains('مبني|فيلا|شقة|بيت', regex=True, na=False)]

# التحليل الإحصائي
clean_land, min_land, max_land, land_count, land_conf = get_advanced_stats(lands_filtered)
clean_build, min_build, max_build, build_count, build_conf = get_advanced_stats(builds_raw)

# الحسابات المالية
land_base = land_area * offer_price
total_project_cost = (land_base * 1.075) + (land_area * build_ratio * build_cost_sqm) + ((land_area * build_ratio * build_cost_sqm) * (fees_pct/100))
manual_profit = (land_area * expected_sell_sqm) - total_project_cost
manual_roi = (manual_profit / total_project_cost) * 100

# ========================================================
# 📑 الشاشة الرئيسية
# ========================================================
st.title(f"تحليل العقار: {selected_dist}")

tab1, tab2, tab3, tab4, tab5 = st.tabs(["1️⃣ جودة السوق", "2️⃣ التكاليف والربح", "3️⃣ المخاطر", "4️⃣ الملخص", "🔍 فحص الجودة (تأكد بنفسك)"])

# --- الشريحة 1: جودة السوق ---
with tab1:
    col_kpi, col_chart = st.columns([1, 1.5])
    with col_kpi:
        st.info(f"مؤشر دقة بيانات الأراضي: **{land_conf}** ({land_count} صفقة)")
        if clean_land > 0:
            diff = ((offer_price - clean_land)/clean_land)*100
            st.metric("متوسط سعر الأرض (الواقعي)", f"{clean_land:,.0f} ريال", delta=f"{diff:+.1f}% عن سعرك", delta_color="inverse")
            st.caption(f"نطاق السوق: {min_land:,.0f} - {max_land:,.0f}")
        else: st.warning("بيانات غير كافية")
        
        st.divider()
        st.success(f"مؤشر دقة بيانات المباني: **{build_conf}** ({build_count} صفقة)")
        if clean_build > 0:
            st.metric("متوسط بيع المتر (مبني)", f"{clean_build:,.0f} ريال")
        else: st.warning("لا توجد مباني للمقارنة")

    with col_chart:
        if not lands_filtered.empty:
            st.markdown("#### 📍 موقع سعرك من السوق")
            # دمج سعرك مع البيانات للرسم
            chart_data = lands_filtered[['سعر_المتر', 'المساحة']].copy()
            chart_data['النوع'] = 'صفقات السوق'
            
            user_point = pd.DataFrame({'سعر_المتر': [offer_price], 'المساحة': [land_area], 'النوع': ['🔴 سعرك المعروض']})
            combined = pd.concat([chart_data, user_point])
            
            st.scatter_chart(combined, x='المساحة', y='سعر_المتر', color='النوع', size='سعر_المتر')
            st.caption("النقطة الحمراء هي أرضك. النقاط الزرقاء هي صفقات السوق.")

# --- الشريحة 2: التكاليف والربح ---
with tab2:
    c1, c2 = st.columns(2)
    with c1:
        st.markdown("#### 🧾 التكاليف")
        st.dataframe(pd.DataFrame([
            {"البند": "قيمة الأرض", "القيمة": land_base},
            {"البند": "التكلفة الكلية (تقديرية)", "القيمة": total_project_cost}
        ]).style.format({"القيمة": "{:,.0f}"}), use_container_width=True)
    with c2:
        st.markdown("#### 💰 الربحية")
        st.metric("الربح المتوقع", f"{manual_profit:,.0f} ريال", delta=f"{manual_roi:.1f}% ROI")

# --- الشريحة 3: المخاطر ---
with tab3:
    st.markdown("#### 📉 حساسية الربح لتغير سعر البيع")
    p_changes = [-0.1, -0.05, 0, 0.05, 0.1]
    matrix = []
    base_sell = land_area * expected_sell_sqm
    for p in p_changes:
        sell = base_sell * (1 + p)
        roi = ((sell - total_project_cost)/total_project_cost)*100
        matrix.append(roi)
    st.dataframe(pd.DataFrame([matrix], columns=[f"{x:+.0%}" for x in p_changes], index=["نسبة الربح"]).style.background_gradient(cmap="RdYlGn", vmin=0, vmax=30).format("{:.1f}%"))

# --- الشريحة 4: الملخص ---
with tab4:
    color = "#27ae60" if manual_roi > 15 else "#c0392b"
    st.markdown(f"""<div class="investor-card" style="border-top-color: {color};">
        <h2 style="color:{color};">ROI: {manual_roi:.1f}%</h2>
        <p>ربح متوقع: {manual_profit:,.0f} ريال</p>
    </div>""", unsafe_allow_html=True)

# --- الشريحة 5: فحص الجودة (الشفافية) ---
with tab5:
    st.header("🔍 فحص البيانات الخام (للتأكد)")
    st.markdown("هنا نعرض لك البيانات التي استخدمها الكود **بالضبط** لحساب المتوسطات، لتتأكد من عدم خلط الأراضي بالمباني.")
    
    col_l, col_b = st.columns(2)
    
    with col_l:
        st.subheader(f"🟫 قائمة الأراضي ({len(lands_filtered)})")
        st.caption("تم استبعاد أي عقار يحتوي اسمه على 'فيلا' أو 'بيت' أو سعره شاذ.")
        if not lands_filtered.empty:
            st.dataframe(lands_filtered[['الحي', 'المساحة', 'السعر', 'سعر_المتر', 'نوع_العقار', 'نوع_العقار_الخام']].sort_values('سعر_المتر'), use_container_width=True)
        else:
            st.warning("لم يتم العثور على أراضي مطابقة للفلاتر.")
            
    with col_b:
        st.subheader(f"🏠 قائمة المباني ({len(builds_raw)})")
        st.caption("تشمل الفلل والبيوت والشقق.")
        if not builds_raw.empty:
            st.dataframe(builds_raw[['الحي', 'المساحة', 'السعر', 'سعر_المتر', 'نوع_العقار']].sort_values('سعر_المتر'), use_container_width=True)
        else:
            st.warning("لم يتم العثور على مباني.")
