import streamlit as st
import pandas as pd
import numpy as np
import data_bot  # المحرك

# إعداد الصفحة
st.set_page_config(page_title="المستشار العقاري", layout="wide", page_icon="🏢")

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
    /* تحسين القائمة الجانبية */
    [data-testid="stSidebar"] {
        background-color: #f8f9fa;
        border-left: 1px solid #ddd;
    }
    .profit-positive { color: #27ae60; font-weight: bold; font-size: 24px; }
    .profit-negative { color: #c0392b; font-weight: bold; font-size: 24px; }
</style>
""", unsafe_allow_html=True)

# --- دوال مساعدة ---
def get_clean_stats(df_input, col='سعر_المتر'):
    if df_input.empty: return 0, 0, 0
    clean = df_input[df_input[col] > 100].copy()
    if clean.empty: return 0, 0, 0
    low, high = clean[col].quantile(0.10), clean[col].quantile(0.90)
    final = clean[(clean[col] >= low) & (clean[col] <= high)]
    if final.empty: return 0, 0, 0
    return final[col].median(), final[col].min(), final[col].max()

# --- الاتصال بالبيانات ---
if 'bot' not in st.session_state:
    with st.spinner("جاري الاتصال..."):
        try: st.session_state.bot = data_bot.RealEstateBot()
        except: st.error("خطأ في الاتصال")

df = st.session_state.bot.df if hasattr(st.session_state.bot, 'df') else pd.DataFrame()

# ========================================================
# 🟢 القائمة الجانبية (لوحة القيادة والمدخلات)
# ========================================================
with st.sidebar:
    st.image("https://cdn-icons-png.flaticon.com/512/2642/2642226.png", width=50)
    st.title("إعدادات المشروع")
    
    if st.button("🔄 تحديث البيانات", use_container_width=True):
        st.cache_data.clear()
        for key in list(st.session_state.keys()): del st.session_state[key]
        st.rerun()
    
    st.divider()

    if df.empty:
        st.warning("بانتظار البيانات...")
        st.stop()

    # 1. تحديد الموقع
    st.subheader("1️⃣ الموقع والأرض")
    districts_list = sorted(df['الحي'].unique()) if 'الحي' in df.columns else []
    
    # ميزة الرابط الذكي
    location_input = st.text_input("🔗 رابط أو اسم الحي", placeholder="بحث ذكي...")
    default_ix = 0
    if location_input:
        for i, d in enumerate(districts_list):
            if d in location_input: 
                default_ix = i; st.toast(f"✅ تم تحديد: {d}"); break
    
    selected_dist = st.selectbox("📍 الحي", districts_list, index=default_ix)
    
    c_s1, c_s2 = st.columns(2)
    with c_s1: land_area = st.number_input("المساحة (م²)", value=375)
    with c_s2: offer_price = st.number_input("شراء المتر", value=3500)

    st.divider()

    # 2. التكاليف والبيع (تم التحديث هنا كما طلبت)
    st.subheader("2️⃣ التكاليف والبيع")
    build_cost_sqm = st.number_input("تكلفة البناء/م", value=1750, step=50)
    
    # الخانة الجديدة المطلوبة
    expected_sell_sqm = st.number_input("💰 سعر البيع المتوقع للمتر", value=6500, step=100, help="سعر بيع المتر (شامل الأرض والبناء) المتوقع للوحدة الجاهزة")
    
    build_ratio = st.slider("نسبة البناء (%)", 1.0, 3.5, 2.3)
    fees_pct = st.number_input("رسوم إدارية (%)", value=8.0)

    st.divider()

    # تقرير المصادر
    with st.expander("📂 مصدر البيانات"):
        if 'Source_File' in df.columns:
            stats = df['Source_File'].value_counts().reset_index()
            stats.columns = ['الملف', 'العدد']
            st.dataframe(stats, hide_index=True)

# ========================================================
# 🏭 المعالجة والحسابات
# ========================================================
# 1. فلترة البيانات
lands_raw = df[(df['الحي'] == selected_dist) & (df['نوع_العقار'].str.contains('أرض', na=False))]
builds_raw = df[(df['الحي'] == selected_dist) & (df['نوع_العقار'].str.contains('مبني', na=False))]
clean_land, _, _ = get_clean_stats(lands_raw)
clean_build, _, _ = get_clean_stats(builds_raw)

# 2. حساب التكاليف
land_base = land_area * offer_price
land_fees = land_base * 0.075 # 5% ضريبة + 2.5% سعي
build_area = land_area * build_ratio
exec_cost = build_area * build_cost_sqm
admin_fees = exec_cost * (fees_pct / 100)
total_project_cost = land_base + land_fees + exec_cost + admin_fees

# 3. حساب الأرباح (بناءً على مدخلاتك اليدوية)
manual_revenue = land_area * expected_sell_sqm  # إيرادك المتوقع بناء على السعر الذي أدخلته
manual_profit = manual_revenue - total_project_cost
manual_roi = (manual_profit / total_project_cost) * 100

# ========================================================
# 📑 الشاشة الرئيسية (Tabs)
# ========================================================
st.title(f"تحليل مشروع: حي {selected_dist}")

tab1, tab2, tab3, tab4 = st.tabs([
    "1️⃣ السوق والموقع", 
    "2️⃣ التكاليف والربحية", 
    "3️⃣ تحليل المخاطر", 
    "4️⃣ ملخص المستثمر"
])

# --------------------------------------------------------
# الشريحة 1: السوق
# --------------------------------------------------------
with tab1:
    col_map, col_data = st.columns([1, 2])
    with col_map:
        st.markdown("##### 🗺️ الموقع")
        map_url = f"https://www.google.com/maps/search/?api=1&query={selected_dist}+الرياض"
        st.markdown(f"[![Maps](https://upload.wikimedia.org/wikipedia/commons/thumb/a/aa/Google_Maps_icon_%282020%29.svg/80px-Google_Maps_icon_%282020%29.svg.png)]({map_url})")
        st.caption("اضغط لفتح الخريطة")
        
    with col_data:
        st.markdown("##### 📊 أسعار السوق (مقارنة بأسعارك)")
        m1, m2 = st.columns(2)
        with m1:
            st.markdown("#### 🟫 الأراضي")
            if clean_land > 0:
                diff = ((offer_price - clean_land)/clean_land)*100
                st.metric("متوسط السوق", f"{clean_land:,.0f}", delta=f"{diff:+.1f}% فرق سعرك", delta_color="inverse")
            else: st.info("لا تتوفر بيانات")
            
        with m2:
            st.markdown("#### 🏠 المباني (بيع)")
            if clean_build > 0:
                diff_sell = ((expected_sell_sqm - clean_build)/clean_build)*100
                st.metric("متوسط السوق", f"{clean_build:,.0f}", delta=f"{diff_sell:+.1f}% فرق سعرك")
            else: st.info("لا تتوفر بيانات")

# --------------------------------------------------------
# الشريحة 2: التكاليف والربحية (تم التعديل هنا)
# --------------------------------------------------------
with tab2:
    col_cost, col_profit = st.columns([1.5, 1])
    
    with col_cost:
        st.markdown("#### 🧾 تفاصيل التكاليف")
        cost_df = pd.DataFrame([
            {"البند": "قيمة الأرض", "التكلفة": land_base, "%": f"{(land_base/total_project_cost)*100:.1f}%"},
            {"البند": "رسوم (ضريبة+سعي)", "التكلفة": land_fees, "%": f"{(land_fees/total_project_cost)*100:.1f}%"},
            {"البند": "تكاليف البناء", "التكلفة": exec_cost, "%": f"{(exec_cost/total_project_cost)*100:.1f}%"},
            {"البند": "إشراف وإدارة", "التكلفة": admin_fees, "%": f"{(admin_fees/total_project_cost)*100:.1f}%"},
            {"البند": "🔴 الإجمالي", "التكلفة": total_project_cost, "%": "100%"}
        ])
        st.dataframe(cost_df.style.format({"التكلفة": "{:,.0f}"}), use_container_width=True)

    with col_profit:
        st.markdown("#### 💰 تحليل الربحية (حسب مدخلاتك)")
        st.markdown(f"""
        <div style="background-color:#f9f9f9; padding:20px; border-radius:10px; border:1px solid #eee;">
            <div style="margin-bottom:10px;">
                <span style="color:#7f8c8d;">سعر البيع المتوقع:</span><br>
                <span style="font-size:20px; font-weight:bold;">{manual_revenue:,.0f} ريال</span>
            </div>
            <div style="margin-bottom:10px;">
                <span style="color:#7f8c8d;">صافي الربح:</span><br>
                <span class="{'profit-positive' if manual_profit > 0 else 'profit-negative'}">{manual_profit:,.0f} ريال</span>
            </div>
            <div>
                <span style="color:#7f8c8d;">العائد على الاستثمار (ROI):</span><br>
                <span class="{'profit-positive' if manual_profit > 0 else 'profit-negative'}">{manual_roi:.1f}%</span>
            </div>
        </div>
        """, unsafe_allow_html=True)
        
        # تقييم سريع
        if manual_roi > 20: st.success("🌟 عائد ممتاز!")
        elif manual_roi > 10: st.info("✅ عائد جيد")
        else: st.warning("⚠️ عائد منخفض")

# --------------------------------------------------------
# الشريحة 3: المخاطر
# --------------------------------------------------------
with tab3:
    st.markdown("#### 📉 تحليل الحساسية")
    c1, c2 = st.columns(2)
    with c1: duration = st.number_input("المدة (شهر)", value=14)
    with c2: fin_rate = st.number_input("فائدة التمويل (%)", value=0.0)
    
    fin_cost = total_project_cost * (fin_rate/100) * (duration/12)
    grand_total_risk = total_project_cost + fin_cost
    
    # استخدام السعر اليدوي كنقطة ارتكاز
    base_sell = manual_revenue
    
    p_changes = [-0.1, -0.05, 0, 0.05, 0.1]
    c_changes = [-0.1, -0.05, 0, 0.05, 0.1]
    
    matrix = []
    for p in p_changes:
        row = []
        sell = base_sell * (1 + p)
        for c in c_changes:
            cost_new = (exec_cost+admin_fees) * (1 + c) + land_base + land_fees + fin_cost
            roi = ((sell - cost_new)/cost_new)*100
            row.append(roi)
        matrix.append(row)
        
    df_risk = pd.DataFrame(matrix, index=[f"بيع {x:+.0%}" for x in p_changes], columns=[f"بناء {x:+.0%}" for x in c_changes])
    st.dataframe(df_risk.style.background_gradient(cmap="RdYlGn", vmin=0, vmax=30).format("{:.1f}%"), use_container_width=True)

# --------------------------------------------------------
# الشريحة 4: الملخص
# --------------------------------------------------------
with tab4:
    net_profit_final = manual_revenue - grand_total_risk
    roi_final = (net_profit_final / grand_total_risk) * 100
    
    color = "#27ae60" if roi_final > 15 else "#f39c12" if roi_final > 0 else "#c0392b"
    
    st.markdown(f"""
    <div class="investor-card" style="border-top-color: {color};">
        <h2 style="color:{color};">ملخص المشروع الاستثماري</h2>
        <p>حي {selected_dist} | المساحة {land_area}م²</p>
        <hr>
        <div style="display: flex; justify-content: space-around; margin-top: 20px;">
            <div><div class="stat-label">رأس المال</div><div class="big-stat">{grand_total_risk:,.0f}</div></div>
            <div><div class="stat-label">الإيراد (بناءً على سعرك)</div><div class="big-stat">{manual_revenue:,.0f}</div></div>
        </div>
        <div style="display: flex; justify-content: space-around; margin-top: 20px;">
            <div><div class="stat-label">الربح الصافي</div><div class="big-stat" style="color:{color};">{net_profit_final:,.0f}</div></div>
            <div><div class="stat-label">ROI</div><div class="big-stat" style="color:{color};">{roi_final:.1f}%</div></div>
        </div>
    </div>
    """, unsafe_allow_html=True)
