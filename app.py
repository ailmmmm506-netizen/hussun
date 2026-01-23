import streamlit as st
import pandas as pd
import numpy as np
import data_bot  # المحرك

# إعداد الصفحة
st.set_page_config(page_title="المستشار العقاري المتقدم", layout="wide", page_icon="🏢")

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
    
    # 1. تنظيف أولي (استبعاد الأصفار والقيم المستحيلة)
    clean = df_input[(df_input[col] > 100) & (df_input[col] < 100000)].copy()
    if len(clean) < 3: return 0, 0, 0, 0, "بيانات غير كافية"

    # 2. تطبيق IQR (المدى الربيعي) لعزل الشواذ بدقة
    Q1 = clean[col].quantile(0.25)
    Q3 = clean[col].quantile(0.75)
    IQR = Q3 - Q1
    
    # تحديد الحدود المقبولة إحصائياً
    lower_bound = Q1 - 1.5 * IQR
    upper_bound = Q3 + 1.5 * IQR
    
    final_df = clean[(clean[col] >= lower_bound) & (clean[col] <= upper_bound)]
    
    if final_df.empty: return 0, 0, 0, 0, "تشتت عالي جداً"
    
    # 3. حساب جودة البيانات
    count = len(final_df)
    confidence = "✅ دقة عالية" if count > 15 else "⚠️ دقة متوسطة" if count > 5 else "❌ دقة منخفضة (صفقات قليلة)"
    
    return final_df[col].median(), final_df[col].min(), final_df[col].max(), count, confidence

# --- الاتصال بالبيانات ---
if 'bot' not in st.session_state:
    with st.spinner("جاري تحليل البيانات..."):
        try: st.session_state.bot = data_bot.RealEstateBot()
        except: st.error("خطأ في الاتصال")

df = st.session_state.bot.df if hasattr(st.session_state.bot, 'df') else pd.DataFrame()

# ========================================================
# 🟢 القائمة الجانبية (فلاتر دقيقة)
# ========================================================
with st.sidebar:
    st.image("https://cdn-icons-png.flaticon.com/512/2642/2642226.png", width=50)
    st.title("إعدادات التحليل")
    
    if st.button("🔄 تحديث البيانات", use_container_width=True):
        st.cache_data.clear()
        for key in list(st.session_state.keys()): del st.session_state[key]
        st.rerun()
    st.divider()

    if df.empty:
        st.warning("بانتظار البيانات...")
        st.stop()

    # 1. الموقع
    st.subheader("1️⃣ الموقع")
    districts_list = sorted(df['الحي'].unique()) if 'الحي' in df.columns else []
    
    location_input = st.text_input("🔗 بحث ذكي (رابط/اسم)", placeholder="لصق رابط جوجل...")
    default_ix = 0
    if location_input:
        for i, d in enumerate(districts_list):
            if d in location_input: default_ix = i; st.toast(f"📍 {d}"); break
    
    selected_dist = st.selectbox("اختر الحي", districts_list, index=default_ix)
    
    # 2. نوع العقار (التصفية الجوهرية) - ميزة جديدة
    st.subheader("2️⃣ تصنيف الأرض")
    land_type_filter = st.radio("نوع الأرض للمقارنة:", ["سكني (عام)", "تجاري / استثماري"], index=0, help="يساعد في فصل الأسعار لكي لا يختلط السكني بالتجاري")
    
    # منطق الفلترة بناءً على الكلمات المفتاحية في البيانات
    keyword_filter = ""
    if land_type_filter == "تجاري / استثماري":
        keyword_filter = "تجاري" # يبحث عن أي شيء فيه "تجاري"
    
    # 3. الأرقام
    c_s1, c_s2 = st.columns(2)
    with c_s1: land_area = st.number_input("المساحة (م²)", value=375)
    with c_s2: offer_price = st.number_input("سعر المتر المعروض", value=3500)

    st.divider()
    st.subheader("3️⃣ التكاليف")
    build_cost_sqm = st.number_input("تكلفة البناء/م", value=1750)
    expected_sell_sqm = st.number_input("سعر البيع المتوقع/م", value=6500)
    build_ratio = st.slider("نسبة البناء", 1.0, 3.5, 2.3)
    fees_pct = st.number_input("رسوم إدارية (%)", value=8.0)

# ========================================================
# 🏭 المعالجة الذكية
# ========================================================
# 1. فلترة الحي
district_df = df[df['الحي'] == selected_dist]

# 2. فلترة النوع (سكني vs تجاري) داخل الأراضي
# إذا اختار تجاري، نبحث عن الكلمة. إذا سكني، نستبعد التجاري قدر الإمكان
lands_raw = district_df[district_df['نوع_العقار'].str.contains('أرض', na=False)]

if land_type_filter == "تجاري / استثماري":
    # نحاول نصيد الصفقات التجارية (غالباً سعرها عالي أو مسماها تجاري)
    # ملاحظة: هذا يعتمد على توفر كلمة تجاري في البيانات، أو يمكننا استخدام السعر كفلتر
    lands_filtered = lands_raw[lands_raw['نوع_العقار_الخام'].str.contains('تجاري', na=False) | (lands_raw['سعر_المتر'] > lands_raw['سعر_المتر'].median() * 1.5)]
    if lands_filtered.empty: lands_filtered = lands_raw # رجوع للعام إذا لم نجد تصنيف دقيق
else:
    # سكني: نحاول استبعاد التجاري الصريح
    lands_filtered = lands_raw[~lands_raw['نوع_العقار_الخام'].str.contains('تجاري', na=False)]

# بيانات المباني (للمقارنة)
builds_raw = district_df[district_df['نوع_العقار'].str.contains('مبني', na=False)]

# 3. التحليل الإحصائي المتقدم
clean_land, min_land, max_land, land_count, land_conf = get_advanced_stats(lands_filtered)
clean_build, min_build, max_build, build_count, build_conf = get_advanced_stats(builds_raw)

# 4. الحسابات المالية
land_base = land_area * offer_price
land_fees = land_base * 0.075 
build_area = land_area * build_ratio
exec_cost = build_area * build_cost_sqm
admin_fees = exec_cost * (fees_pct / 100)
total_project_cost = land_base + land_fees + exec_cost + admin_fees

manual_revenue = land_area * expected_sell_sqm
manual_profit = manual_revenue - total_project_cost
manual_roi = (manual_profit / total_project_cost) * 100

# ========================================================
# 📑 الشاشة الرئيسية
# ========================================================
st.title(f"تحليل العقار: {selected_dist} ({land_type_filter})")

tab1, tab2, tab3, tab4 = st.tabs(["1️⃣ جودة السوق", "2️⃣ التكاليف والربح", "3️⃣ المخاطر", "4️⃣ الملخص"])

# --- الشريحة 1: جودة السوق (جديدة) ---
with tab1:
    col_kpi, col_chart = st.columns([1, 1.5])
    
    with col_kpi:
        st.markdown("#### 🧐 مصداقية السعر")
        
        # عرض مؤشر الثقة
        st.info(f"مؤشر دقة بيانات الأراضي: **{land_conf}**\n\n(تم الاعتماد على {land_count} صفقة بعد استبعاد الشواذ)")

        if clean_land > 0:
            diff = ((offer_price - clean_land)/clean_land)*100
            
            st.metric("متوسط السوق (الواقعي)", f"{clean_land:,.0f} ريال", delta=f"{diff:+.1f}% عن سعرك", delta_color="inverse")
            st.caption(f"النطاق السعري المقبول في الحي: من {min_land:,.0f} إلى {max_land:,.0f}")
            
            if offer_price > max_land:
                st.error("⚠️ انتبه: السعر المعروض أعلى من أغلى صفقة تم رصدها في الحي!")
            elif offer_price < min_land:
                st.success("🔥 فرصة: السعر المعروض أقل من أدنى سعر مرصود!")
        else:
            st.warning("البيانات غير كافية لإعطاء متوسط سعري موثوق.")

    with col_chart:
        if clean_land > 0 and not lands_filtered.empty:
            st.markdown("#### 📊 توزيع الصفقات في الحي")
            # رسم بياني يوضح أين يقع سعرك مقارنة بالسوق
            chart_data = lands_filtered[(lands_filtered['سعر_المتر'] > 0) & (lands_filtered['سعر_المتر'] < clean_land*3)]
            
            # نستخدم Altair أو Vega Lite بسيط عبر st.scatter_chart
            st.scatter_chart(chart_data, x='المساحة', y='سعر_المتر', color='Source_Type', size='سعر_المتر')
            st.caption("النقاط تمثل الصفقات الفعلية. قارن موقع نقطتك (سعرك ومساحتك) مع التكتل الموجود.")

# --- الشريحة 2: التكاليف والربح ---
with tab2:
    c1, c2 = st.columns([1.5, 1])
    with c1:
        st.markdown("#### 🧾 تفاصيل التكاليف")
        cost_df = pd.DataFrame([
            {"البند": "قيمة الأرض", "التكلفة": land_base},
            {"البند": "رسوم (ضريبة+سعي)", "التكلفة": land_fees},
            {"البند": "تكاليف البناء", "التكلفة": exec_cost},
            {"البند": "إشراف وإدارة", "التكلفة": admin_fees},
            {"البند": "🔴 الإجمالي", "التكلفة": total_project_cost}
        ])
        st.dataframe(cost_df.style.format({"التكلفة": "{:,.0f}"}), use_container_width=True)
        
    with c2:
        st.markdown("#### 💰 نتيجتك (بناءً على سعرك)")
        st.metric("صافي الربح المتوقع", f"{manual_profit:,.0f} ريال")
        st.metric("العائد (ROI)", f"{manual_roi:.1f}%")
        
        if manual_roi < 10:
            st.warning("العائد أقل من 10%، يعتبر مخاطرة.")

# --- الشريحة 3: المخاطر ---
with tab3:
    st.markdown("#### 📉 ماذا لو تغير السوق؟")
    p_changes = [-0.15, -0.10, -0.05, 0, 0.05, 0.10]
    
    matrix = []
    for p in p_changes:
        sell = manual_revenue * (1 + p) # تغيير في سعر البيع المتوقع
        profit = sell - total_project_cost
        roi = (profit/total_project_cost)*100
        matrix.append(roi)
    
    df_sens = pd.DataFrame([matrix], columns=[f"{x:+.0%}" for x in p_changes], index=["نسبة الربح"])
    st.dataframe(df_sens.style.background_gradient(cmap="RdYlGn", vmin=-10, vmax=30).format("{:.1f}%"), use_container_width=True)
    st.caption("الجدول يوضح نسبة الربح إذا تغير سعر البيع المتوقع صعوداً أو نزولاً.")

# --- الشريحة 4: الملخص ---
with tab4:
    color = "#27ae60" if manual_roi > 15 else "#f39c12" if manual_roi > 0 else "#c0392b"
    st.markdown(f"""
    <div class="investor-card" style="border-top-color: {color};">
        <h2 style="color:{color};">تقرير الجدوى النهائي</h2>
        <p>حي {selected_dist} | نوع التحليل: {land_type_filter}</p>
        <hr>
        <div style="display: flex; justify-content: space-around; margin-top: 20px;">
            <div><div class="stat-label">التكلفة الكلية</div><div class="big-stat">{total_project_cost:,.0f}</div></div>
            <div><div class="stat-label">الربح المتوقع</div><div class="big-stat" style="color:{color};">{manual_profit:,.0f}</div></div>
            <div><div class="stat-label">ROI</div><div class="big-stat" style="color:{color};">{manual_roi:.1f}%</div></div>
        </div>
        <br>
        <div style="background:#f9f9f9; padding:10px; font-size:14px;">
            مؤشر دقة البيانات المستخدمة في المقارنة: <b>{land_conf}</b>
        </div>
    </div>
    """, unsafe_allow_html=True)
