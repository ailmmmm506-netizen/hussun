import streamlit as st
import pandas as pd
import data_bot  # المحرك الذكي

# إعداد الصفحة
st.set_page_config(page_title="المطور العقاري الذكي", layout="wide", page_icon="🏗️")

# --- التنسيق الجمالي (CSS) ---
st.markdown("""
<style>
    /* كروت السوق */
    .market-card { 
        background-color: #ffffff; 
        padding: 15px; 
        border-radius: 12px; 
        border-top: 5px solid #3498db; 
        box-shadow: 0 4px 6px rgba(0,0,0,0.05); 
        text-align: center; 
        transition: transform 0.2s;
    }
    .market-card:hover { transform: translateY(-5px); }
    .market-card h3 { font-size: 16px; color: #7f8c8d; margin-bottom: 5px; font-weight: bold; }
    .market-card h2 { font-size: 26px; font-weight: bold; color: #2c3e50; margin: 0; }
    .market-card small { font-size: 13px; color: #95a5a6; display: block; margin-top: 5px; }

    /* كروت التكلفة */
    .cost-card { background-color: #f8f9fa; padding: 20px; border-radius: 10px; border-left: 5px solid #2ecc71; margin-bottom: 15px; }
    
    /* عام */
    [data-testid="stSidebar"] { background-color: #f8f9fa; border-left: 1px solid #ddd; }
    .stProgress > div > div > div > div { background-color: #2ecc71; }
</style>
""", unsafe_allow_html=True)

# --- دالة إحصائية (للتنظيف والحساب) ---
def get_clean_stats(df_input):
    if df_input.empty: return 0, 0
    
    # تحويل لعمود رقمي والتخلص من القيم غير المنطقية
    df_input = df_input.copy()
    # تأمين إضافي: التأكد من أن العمود رقمي
    df_input['سعر_المتر'] = pd.to_numeric(df_input['سعر_المتر'], errors='coerce')
    
    # استبعاد الأصفار والقيم الشاذة (أقل من 500 ريال أو أعلى من 100 ألف للمتر)
    clean = df_input[(df_input['سعر_المتر'] > 500) & (df_input['سعر_المتر'] < 100000)]
    
    if clean.empty: return 0, 0
    
    # نستخدم الوسيط (Median) لأنه أدق في العقار من المتوسط الحسابي
    return clean['سعر_المتر'].median(), len(clean)

# --- تحميل البيانات (مرة واحدة) ---
@st.cache_resource(show_spinner="جاري تحليل بيانات السوق العقاري...", ttl=3600)
def load_data():
    return data_bot.RealEstateBot()

if 'bot' not in st.session_state: st.session_state.bot = load_data()
df = st.session_state.bot.df if hasattr(st.session_state.bot, 'df') else pd.DataFrame()

# ==========================================
# 🟢 القائمة الجانبية (Sidebar)
# ==========================================
with st.sidebar:
    st.title("القائمة الرئيسية")
    app_mode = st.radio("التطبيق:", ["📊 لوحة البيانات (Dashboard)", "🏗️ حاسبة التكاليف (Calculator)"])
    st.divider()
    if st.button("🔄 تحديث البيانات", use_container_width=True):
        st.cache_data.clear()
        st.cache_resource.clear()
        st.rerun()

# ==========================================
# 📊 القسم 1: لوحة البيانات (Dashboard)
# ==========================================
if app_mode == "📊 لوحة البيانات (Dashboard)":
    if df.empty:
        st.error("لا توجد بيانات متاحة. تأكد من اتصال الإنترنت وملفات الدرايف.")
        st.stop()

    districts = sorted(df['الحي'].astype(str).unique())
    selected_dist = st.sidebar.selectbox("تصفية حسب الحي:", ["الكل"] + districts)
    
    view_df = df if selected_dist == "الكل" else df[df['الحي'] == selected_dist]
    
    st.title(f"سجل البيانات: {selected_dist}")
    
    # إحصائية سريعة
    if 'Source_File' in df.columns:
        with st.expander("📂 مصادر البيانات (الملفات)", expanded=False):
            stats = view_df['Source_File'].value_counts().reset_index()
            stats.columns = ['اسم الملف', 'عدد العقارات']
            st.dataframe(stats, use_container_width=True)

    tab1, tab2 = st.tabs(["💰 الصفقات (Sold)", "🏷️ العروض (Ask)"])
    
    # أعمدة العرض
    cols = ['Source_File', 'الحي', 'السعر', 'المساحة', 'سعر_المتر', 'نوع_العقار']
    final_cols = [c for c in cols if c in view_df.columns]
    
    with tab1:
        # فلترة الصفقات
        sold_data = view_df[view_df['Data_Category'].str.contains('Sold', na=False)]
        st.dataframe(sold_data[final_cols], use_container_width=True)
        
    with tab2:
        # فلترة العروض
        ask_data = view_df[view_df['Data_Category'].str.contains('Ask', na=False)]
        st.dataframe(ask_data[final_cols], use_container_width=True)

# ==========================================
# 🏗️ القسم 2: حاسبة التكاليف + مسح السوق
# ==========================================
elif app_mode == "🏗️ حاسبة التكاليف (Calculator)":
    
    st.title("🏗️ حاسبة التكاليف ومسح السوق")
    
    # --- أ) المدخلات (Sidebar) ---
    with st.sidebar:
        st.header("1️⃣ إعدادات الموقع")
        districts_list = sorted(df['الحي'].astype(str).unique()) if not df.empty else []
        calc_dist = st.selectbox("اختر الحي للتحليل:", districts_list)
        
        st.divider()
        st.header("2️⃣ الأرض")
        land_area = st.number_input("مساحة الأرض (م²)", 375, step=25)
        land_price = st.number_input("سعر المتر (ريال)", 3500, step=50)
        tax_pct = st.number_input("الضريبة (%)", 5.0)
        saei_pct = st.number_input("السعي (%)", 2.5)
        
        st.divider()
        st.header("3️⃣ البناء والتطوير")
        build_ratio = st.slider("معامل البناء (FAR)", 1.0, 3.5, 2.3)
        bua = land_area * build_ratio # مسطح البناء
        st.caption(f"مسطح البناء المتوقع: **{bua:,.0f} م²**")
        
        turnkey_price = st.number_input("سعر البناء (مفتاح)/م", 1800)
        bone_price = st.number_input("سعر العظم (للتأمين)/م", 700)
        
        st.divider()
        st.header("4️⃣ مصاريف أخرى")
        units_count = st.number_input("عدد الوحدات", 4)
        service_cost = st.number_input("تكلفة الخدمات/وحدة", 15000)
        permits_cost = st.number_input("رخص وتصاميم (إجمالي)", 60000)
        marketing_pct = st.number_input("تسويق وعمولات (%)", 2.5)
        is_offplan = st.checkbox("بيع على الخارطة؟", False)
        
        wafi_fees = 0
        if is_offplan:
            wafi_fees = st.number_input("رسوم وافي وأمين حساب", 50000)

    # --- ب) الحسابات الرياضية ---
    
    # 1. الأرض
    base_land = land_area * land_price
    land_extras = base_land * ((tax_pct + saei_pct) / 100)
    total_land = base_land + land_extras
    
    # 2. البناء
    total_construction = bua * turnkey_price
    total_bone = bua * bone_price
    
    # 3. الرسوم
    malath = total_bone * 0.01  # 1% من العظم
    services_total = units_count * service_cost
    
    # 4. المجموع الأولي (لحساب الطوارئ والتسويق)
    sub_total = total_land + total_construction + malath + services_total + permits_cost + wafi_fees
    
    # 5. النسب
    contingency = sub_total * 0.02 # 2% طوارئ
    marketing = (sub_total + contingency) * (marketing_pct / 100)
    
    # 6. الإجمالي النهائي
    grand_total = sub_total + contingency + marketing
    cost_per_sqm = grand_total / bua # تكلفة المتر (على المسطح)

    # --- ج) عرض النتائج ---
    
    # المؤشرات العلوية
    c1, c2, c3 = st.columns(3)
    with c1: st.metric("إجمالي التكلفة", f"{grand_total:,.0f} ريال")
    with c2: st.metric("تكلفة المتر (شامل)", f"{cost_per_sqm:,.0f} ريال/م")
    with c3: st.metric("مسطح البناء", f"{bua:,.0f} م²")
    
    st.divider()
    
    # الجدول والرسم
    col_t, col_c = st.columns([1.5, 1])
    with col_t:
        st.subheader("📑 تفاصيل التكاليف")
        breakdown = [
            {"البند": "الأرض (شامل الضريبة والسعي)", "التكلفة": total_land},
            {"البند": "البناء (تسليم مفتاح)", "التكلفة": total_construction},
            {"البند": "تأمين ملاذ (1% عظم)", "التكلفة": malath},
            {"البند": "خدمات (كهرباء/مياه)", "التكلفة": services_total},
            {"البند": "رخص وتصاميم", "التكلفة": permits_cost},
            {"البند": "تسويق وعمولات", "التكلفة": marketing},
            {"البند": "احتياطي طوارئ (2%)", "التكلفة": contingency},
        ]
        if is_offplan: breakdown.append({"البند": "رسوم وافي", "التكلفة": wafi_fees})
        
        df_cost = pd.DataFrame(breakdown)
        df_cost['النسبة'] = df_cost['التكلفة'] / grand_total
        st.dataframe(
            df_cost, 
            use_container_width=True, 
            column_config={
                "التكلفة": st.column_config.NumberColumn(format="%d ريال"),
                "النسبة": st.column_config.ProgressColumn(format="%.1f%%")
            }
        )

    with col_c:
        st.subheader("توزيع الميزانية")
        st.bar_chart(df_cost.set_index("البند")['التكلفة'])

    # ==========================================
    # 🧠 مسح السوق (Market Scanner)
    # ==========================================
    st.divider()
    st.header(f"📊 مسح أسعار العروض في حي {calc_dist}")
    
    # فلترة الحي + العروض فقط
    market_df = df[(df['الحي'] == calc_dist) & (df['Data_Category'].str.contains('Ask', na=False))]
    
    if market_df.empty:
        st.warning(f"لا توجد عروض بيع مسجلة حالياً لحي {calc_dist}")
    else:
        # الفلترة المباشرة بناءً على التصنيف الجاهز من data_bot
        # هذا يضمن دقة 100% لأن التصنيف تم بمعاييرك (راس، تاون، مساحات...)
        villas = market_df[market_df['نوع_العقار'] == 'فيلا']
        apts   = market_df[market_df['نوع_العقار'] == 'شقة']
        floors = market_df[market_df['نوع_العقار'] == 'دور']
        # المتوسط العام لكل المباني (نستثني الأراضي من متوسط البناء)
        all_built = market_df[market_df['نوع_العقار'] != 'أرض']
        
        # حساب المتوسطات
        p_villa, n_villa = get_clean_stats(villas)
        p_apt, n_apt     = get_clean_stats(apts)
        p_floor, n_floor = get_clean_stats(floors)
        p_all, n_all     = get_clean_stats(all_built)
        
        # عرض الكروت
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            st.markdown(f"""
            <div class="market-card">
                <h3>🏠 متوسط الفلل</h3>
                <h2>{p_villa:,.0f}</h2>
                <small>عدد العروض: {n_villa}</small>
            </div>
            """, unsafe_allow_html=True)
            
        with col2:
            st.markdown(f"""
            <div class="market-card">
                <h3>🏢 متوسط الشقق</h3>
                <h2>{p_apt:,.0f}</h2>
                <small>عدد العروض: {n_apt}</small>
            </div>
            """, unsafe_allow_html=True)
            
        with col3:
            st.markdown(f"""
            <div class="market-card">
                <h3>🏘️ متوسط الأدوار</h3>
                <h2>{p_floor:,.0f}</h2>
                <small>عدد العروض: {n_floor}</small>
            </div>
            """, unsafe_allow_html=True)
            
        with col4:
            st.markdown(f"""
            <div class="market-card" style="border-top-color: #f1c40f;">
                <h3>📈 المتوسط العام</h3>
                <h2>{p_all:,.0f}</h2>
                <small>عدد العروض: {n_all}</small>
            </div>
            """, unsafe_allow_html=True)
            
        # --- تحليل الجدوى (المقارنة) ---
        st.divider()
        st.subheader("💡 تحليل الجدوى (مقارنة تكلفتك بالسوق)")
        
        # دالة لرسم المقارنة
        def draw_comparison(label, market_avg):
            if market_avg > 0:
                profit_margin = ((market_avg - cost_per_sqm) / cost_per_sqm) * 100
                color_icon = "🚀" if profit_margin > 20 else "⚠️" if profit_margin > 0 else "⛔"
                
                st.write(f"**مقارنة مع {label}:**")
                # شريط التقدم (نحوله لقيمة بين 0 و 1 للعرض)
                progress_val = min(max((profit_margin + 50) / 100, 0.0), 1.0)
                st.progress(progress_val)
                st.caption(f"{color_icon} الهامش المتوقع: **{profit_margin:.1f}%** (سعر السوق: {market_avg:,.0f} - تكلفتك: {cost_per_sqm:,.0f})")
            else:
                st.info(f"لا توجد بيانات كافية لـ {label} للمقارنة.")

        c_comp1, c_comp2 = st.columns(2)
        with c_comp1:
            draw_comparison("الشقق", p_apt)
            draw_comparison("الأدوار", p_floor)
        with c_comp2:
            draw_comparison("الفلل", p_villa)
            draw_comparison("المتوسط العام", p_all)
