import streamlit as st
import pandas as pd
import data_bot  # يعتمد على المحرك الذكي في التصنيف

# ---------------------------------------------------------
# 1. إعدادات الصفحة والتصميم
# ---------------------------------------------------------
st.set_page_config(page_title="المطور العقاري الذكي", layout="wide", page_icon="🏗️")

st.markdown("""
<style>
    /* تنسيق كروت السوق */
    .market-card { 
        background-color: #ffffff; 
        padding: 20px; 
        border-radius: 15px; 
        border-top: 6px solid #3498db; 
        box-shadow: 0 4px 10px rgba(0,0,0,0.05); 
        text-align: center; 
        height: 100%;
        transition: transform 0.2s;
    }
    .market-card:hover { transform: translateY(-5px); }
    .market-card h2 { font-size: 28px; font-weight: bold; color: #2c3e50; margin: 10px 0; }
    .market-card h3 { font-size: 16px; color: #7f8c8d; font-weight: bold; }
    .market-card .stat-label { font-size: 13px; color: #95a5a6; margin-top: 5px; }
    
    /* تنسيق السايدبار */
    [data-testid="stSidebar"] { background-color: #f8f9fa; border-left: 1px solid #ddd; }
    
    /* أشرطة التقدم */
    .stProgress > div > div > div > div { background-color: #2ecc71; }
</style>
""", unsafe_allow_html=True)

# ---------------------------------------------------------
# 2. دوال مساعدة
# ---------------------------------------------------------
@st.cache_resource(show_spinner="جاري جلب وتحليل البيانات...", ttl=3600)
def load_data():
    return data_bot.RealEstateBot()

def get_clean_median(df_subset):
    """حساب الوسيط الحسابي مع استبعاد القيم الشاذة"""
    if df_subset.empty: return 0, 0
    # تنظيف سريع
    vals = pd.to_numeric(df_subset['سعر_المتر'], errors='coerce')
    vals = vals[(vals > 500) & (vals < 150000)] # استبعاد الأصفار والقيم الخيالية
    if vals.empty: return 0, 0
    return vals.median(), len(vals)

# ---------------------------------------------------------
# 3. تحميل البيانات
# ---------------------------------------------------------
if 'bot' not in st.session_state: st.session_state.bot = load_data()
df = st.session_state.bot.df if hasattr(st.session_state.bot, 'df') else pd.DataFrame()

# ---------------------------------------------------------
# 4. القائمة الجانبية (Sidebar)
# ---------------------------------------------------------
with st.sidebar:
    st.image("https://cdn-icons-png.flaticon.com/512/2642/2642226.png", width=80)
    st.title("القائمة الرئيسية")
    
    app_mode = st.radio("اختر النظام:", 
                        ["📊 لوحة البيانات (Dashboard)", 
                         "🏗️ حاسبة التكاليف ودراسة السوق"])
    
    st.divider()
    if st.button("🗑️ تحديث البيانات ومسح الكاش", type="primary", use_container_width=True):
        st.cache_data.clear()
        st.cache_resource.clear()
        for key in list(st.session_state.keys()): del st.session_state[key]
        st.rerun()

# =========================================================
# 📊 التطبيق 1: لوحة البيانات (Dashboard)
# =========================================================
if app_mode == "📊 لوحة البيانات (Dashboard)":
    if df.empty:
        st.warning("جاري سحب البيانات... يرجى الانتظار")
        st.stop()

    # فلاتر
    districts = sorted(df['الحي'].astype(str).unique())
    selected_dist = st.sidebar.selectbox("تصفية حسب الحي:", ["الكل"] + districts)
    
    view_df = df if selected_dist == "الكل" else df[df['الحي'] == selected_dist]
    
    st.title(f"سجل البيانات العقارية: {selected_dist}")
    
    # إحصائيات سريعة
    c1, c2 = st.columns(2)
    with c1: st.metric("عدد الصفقات (Sold)", len(view_df[view_df['Data_Category'].str.contains('Sold', na=False)]))
    with c2: st.metric("عدد العروض (Ask)", len(view_df[view_df['Data_Category'].str.contains('Ask', na=False)]))
    
    st.divider()

    tab1, tab2 = st.tabs(["💰 سجل الصفقات", "🏷️ عروض السوق"])
    
    # الأعمدة للعرض
    cols = ['Source_File', 'الحي', 'السعر', 'المساحة', 'سعر_المتر', 'نوع_العقار']
    
    with tab1:
        st.dataframe(view_df[view_df['Data_Category'].str.contains('Sold', na=False)][cols], use_container_width=True)
        
    with tab2:
        st.dataframe(view_df[view_df['Data_Category'].str.contains('Ask', na=False)][cols], use_container_width=True)

# =========================================================
# 🏗️ التطبيق 2: حاسبة التكاليف + ماسح السوق
# =========================================================
elif app_mode == "🏗️ حاسبة التكاليف ودراسة السوق":
    
    st.title("🏗️ دراسة الجدوى الشاملة")
    
    # --- أ) المدخلات (في السايدبار) ---
    with st.sidebar:
        st.header("1️⃣ الموقع")
        # قائمة الأحياء من البيانات المتوفرة
        calc_dist = st.selectbox("حي المشروع:", sorted(df['الحي'].astype(str).unique()) if not df.empty else [])
        
        st.header("2️⃣ الأرض")
        land_area = st.number_input("المساحة (م²)", value=375, step=25)
        land_price = st.number_input("سعر المتر (ريال)", value=3500, step=50)
        tax_pct = st.number_input("الضريبة (%)", value=5.0)
        saei_pct = st.number_input("السعي (%)", value=2.5)
        
        st.header("3️⃣ البناء")
        build_ratio = st.slider("معامل البناء (FAR)", 1.0, 3.5, 2.3)
        turnkey_price = st.number_input("سعر المتر (مفتاح)", value=1800)
        bone_price = st.number_input("سعر المتر (عظم) - للتأمين", value=700)
        
        st.header("4️⃣ مصاريف أخرى")
        units = st.number_input("عدد الوحدات", 4)
        services = st.number_input("تكلفة الخدمات/وحدة", 15000)
        permits = st.number_input("رخص وتصاميم (إجمالي)", 50000)
        marketing_pct = st.number_input("تسويق وعمولات (%)", 2.5)
        is_offplan = st.checkbox("بيع على الخارطة (وافي)؟", False)
        wafi_fees = st.number_input("رسوم وافي", 50000) if is_offplan else 0

    # --- ب) محرك الحسابات ---
    bua = land_area * build_ratio # مسطح البناء
    
    # تكاليف الأرض
    base_land = land_area * land_price
    land_total = base_land * (1 + (tax_pct + saei_pct)/100)
    
    # تكاليف البناء
    build_total = bua * turnkey_price
    malath = (bua * bone_price) * 0.01 # 1% من العظم
    
    # تكاليف أخرى
    services_total = units * services
    sub_total = land_total + build_total + malath + services_total + permits + wafi_fees
    
    # طوارئ وتسويق
    contingency = sub_total * 0.02 # 2% احتياطي
    marketing = (sub_total + contingency) * (marketing_pct / 100)
    
    # الإجمالي
    grand_total = sub_total + contingency + marketing
    cost_sqm = grand_total / bua # تكلفة المتر البيعي (على المسطح)

    # --- ج) عرض النتائج ---
    # 1. المؤشرات الرئيسية
    c1, c2, c3 = st.columns(3)
    with c1: st.metric("إجمالي التكلفة الاستثمارية", f"{grand_total:,.0f} ريال")
    with c2: st.metric("تكلفة المتر (شامل الأرض والبناء)", f"{cost_sqm:,.0f} ريال/م")
    with c3: st.metric("إجمالي مسطح البناء", f"{bua:,.0f} م²")
    
    st.divider()
    
    # 2. تفاصيل التكاليف (جدول ورسم)
    col_table, col_chart = st.columns([1, 1])
    with col_table:
        st.subheader("📑 تفاصيل الفاتورة")
        breakdown = [
            {"البند": "الأرض (مع ضريبة وسعي)", "التكلفة": land_total},
            {"البند": "البناء والتشطيب", "التكلفة": build_total},
            {"البند": "تأمين ملاذ (1% عظم)", "التكلفة": malath},
            {"البند": "خدمات (كهرباء/مياه)", "التكلفة": services_total},
            {"البند": "رخص وتصاميم", "التكلفة": permits},
            {"البند": "تسويق وعمولات", "التكلفة": marketing},
            {"البند": "احتياطي طوارئ (2%)", "التكلفة": contingency},
        ]
        if is_offplan: breakdown.append({"البند": "رسوم وافي", "التكلفة": wafi_fees})
        
        df_cost = pd.DataFrame(breakdown)
        df_cost['النسبة'] = df_cost['التكلفة'] / grand_total
        st.dataframe(df_cost, use_container_width=True, column_config={"التكلفة": st.column_config.NumberColumn(format="%d ريال"), "النسبة": st.column_config.ProgressColumn(format="%.1f%%")})

    with col_chart:
        st.subheader("توزيع الميزانية")
        st.bar_chart(df_cost.set_index("البند")['التكلفة'])

    # =========================================================
    # 🧠 د) ماسح السوق (Market Scanner)
    # =========================================================
    st.markdown("---")
    st.header(f"📊 مؤشرات السوق في حي {calc_dist}")
    
    # 1. فلترة البيانات (الحي + عروض فقط)
    # نعتمد على 'Data_Category' لتحديد العروض
    market_df = df[(df['الحي'] == calc_dist) & (df['Data_Category'].str.contains('Ask', na=False))]
    
    if market_df.empty:
        st.warning(f"لا توجد عروض بيع مسجلة حالياً لحي {calc_dist} للمقارنة.")
    else:
        # 2. التقسيم حسب "نوع_العقار" الذي صنفه Data Bot
        villas = market_df[market_df['نوع_العقار'] == 'فيلا']
        apts   = market_df[market_df['نوع_العقار'] == 'شقة']
        floors = market_df[market_df['نوع_العقار'] == 'دور']
        
        # المتوسط العام (بدون الأراضي)
        general = market_df[market_df['نوع_العقار'] != 'أرض']

        # 3. حساب المتوسطات
        p_villa, n_villa = get_clean_median(villas)
        p_apt, n_apt     = get_clean_median(apts)
        p_floor, n_floor = get_clean_median(floors)
        p_gen, n_gen     = get_clean_median(general)

        # 4. عرض الكروت
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            st.markdown(f"""
            <div class="market-card">
                <h3>🏠 الفلل</h3>
                <h2>{p_villa:,.0f}</h2>
                <div class="stat-label">عدد العروض: {n_villa}</div>
            </div>
            """, unsafe_allow_html=True)
            if n_villa > 0:
                with st.expander("تفاصيل الفلل"): st.dataframe(villas[['السعر', 'المساحة', 'سعر_المتر']], use_container_width=True)

        with col2:
            st.markdown(f"""
            <div class="market-card">
                <h3>🏢 الشقق</h3>
                <h2>{p_apt:,.0f}</h2>
                <div class="stat-label">عدد العروض: {n_apt}</div>
            </div>
            """, unsafe_allow_html=True)
            if n_apt > 0:
                with st.expander("تفاصيل الشقق"): st.dataframe(apts[['السعر', 'المساحة', 'سعر_المتر']], use_container_width=True)

        with col3:
            st.markdown(f"""
            <div class="market-card">
                <h3>🏘️ الأدوار</h3>
                <h2>{p_floor:,.0f}</h2>
                <div class="stat-label">عدد العروض: {n_floor}</div>
            </div>
            """, unsafe_allow_html=True)
            if n_floor > 0:
                with st.expander("تفاصيل الأدوار"): st.dataframe(floors[['السعر', 'المساحة', 'سعر_المتر']], use_container_width=True)

        with col4:
            st.markdown(f"""
            <div class="market-card" style="border-top-color: #f1c40f;">
                <h3>📈 العام</h3>
                <h2>{p_gen:,.0f}</h2>
                <div class="stat-label">إجمالي العروض: {n_gen}</div>
            </div>
            """, unsafe_allow_html=True)

        # 5. دراسة الجدوى (المقارنة)
        st.divider()
        st.subheader("💡 جدوى المشروع (مقارنة بالسوق)")
        
        def show_feasibility(label, market_price):
            if market_price > 0:
                margin = ((market_price - cost_sqm) / cost_sqm) * 100
                st.write(f"**الربح المتوقع في {label}:**")
                st.progress(min(max((margin+50)/100, 0.0), 1.0))
                
                color = "green" if margin > 20 else "orange" if margin > 0 else "red"
                icon = "🚀" if margin > 20 else "⚠️" if margin > 0 else "⛔"
                
                st.caption(f"{icon} الهامش: **{margin:.1f}%** (سعر السوق: {market_price:,.0f} - تكلفتك: {cost_sqm:,.0f})")
            else:
                st.info(f"لا توجد بيانات {label} للمقارنة")

        k1, k2 = st.columns(2)
        with k1:
            show_feasibility("الشقق 🏢", p_apt)
            show_feasibility("الأدوار 🏘️", p_floor)
        with k2:
            show_feasibility("الفلل 🏠", p_villa)
            show_feasibility("المتوسط العام 📈", p_gen)
