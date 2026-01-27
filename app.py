import streamlit as st
import pandas as pd
import data_bot  # المحرك الذكي

# إعداد الصفحة
st.set_page_config(page_title="المطور العقاري الذكي", layout="wide", page_icon="🏢")

# --- التنسيق الجمالي ---
st.markdown("""
<style>
    /* تنسيق الكروت */
    .market-card { background-color: #e8f4f8; padding: 20px; border-radius: 10px; border-top: 5px solid #3498db; margin-top: 20px; }
    .cost-card { background-color: #f8f9fa; padding: 20px; border-radius: 10px; border-left: 5px solid #2ecc71; margin-bottom: 10px; }
    [data-testid="stSidebar"] { background-color: #f8f9fa; border-left: 1px solid #ddd; }
    .stDataFrame { border: 1px solid #eee; border-radius: 5px; }
</style>
""", unsafe_allow_html=True)

# --- دالة الإحصاء المتقدمة (لاستبعاد القيم الشاذة) ---
def get_clean_stats(df_input, col='سعر_المتر'):
    if df_input.empty: return 0, "لا توجد بيانات"
    # تنظيف أولي
    clean = df_input[(df_input[col] > 100) & (df_input[col] < 150000)].copy()
    if len(clean) < 3: return 0, "بيانات غير كافية"
    
    # خوارزمية IQR لاستبعاد الشواذ
    Q1 = clean[col].quantile(0.25)
    Q3 = clean[col].quantile(0.75)
    IQR = Q3 - Q1
    lower_bound = Q1 - 1.5 * IQR
    upper_bound = Q3 + 1.5 * IQR
    
    final_df = clean[(clean[col] >= lower_bound) & (clean[col] <= upper_bound)]
    
    if final_df.empty: return clean[col].median(), "تشتت عالي (تم استخدام الكل)"
    
    return final_df[col].median(), f"تم تحليل {len(final_df)} عقار (بعد التنظيف)"

# --- الاتصال بالكاش ---
@st.cache_resource(show_spinner="جاري جلب البيانات...", ttl=3600)
def load_bot():
    try: return data_bot.RealEstateBot()
    except: return None

if 'bot' not in st.session_state: st.session_state.bot = load_bot()
df = st.session_state.bot.df if hasattr(st.session_state.bot, 'df') else pd.DataFrame()

# ========================================================
# 🟢 القائمة الجانبية
# ========================================================
with st.sidebar:
    st.image("https://cdn-icons-png.flaticon.com/512/2642/2642226.png", width=70)
    st.title("القائمة الرئيسية")
    
    app_mode = st.radio(
        "اختر القسم:", 
        ["📊 لوحة البيانات (Dashboard)", "🏗️ حاسبة التكاليف (Calculator)"],
        index=0
    )
    st.divider()

# ========================================================
# 📊 القسم الأول: الداشبورد
# ========================================================
if app_mode == "📊 لوحة البيانات (Dashboard)":
    # ... (نفس كود الداشبورد السابق بدون تغيير) ...
    with st.sidebar:
        st.subheader("🔍 فلتر البيانات")
        if st.button("🔄 تحديث البيانات", use_container_width=True):
            st.cache_data.clear()
            st.cache_resource.clear()
            st.rerun()

        if df.empty:
            st.warning("جاري سحب البيانات...")
            st.stop()

        districts = sorted(df['الحي'].unique()) if 'الحي' in df.columns else []
        selected_dist = st.selectbox("تصفية حسب الحي:", ["الكل"] + districts)
        
        if selected_dist != "الكل": filtered_df = df[df['الحي'] == selected_dist]
        else: filtered_df = df
            
        st.divider()
        c_sold = len(filtered_df[filtered_df['Data_Category'] == 'صفقات (Sold)'])
        c_ask = len(filtered_df[filtered_df['Data_Category'] == 'عروض (Ask)'])
        st.write(f"🟢 صفقات: {c_sold}")
        st.write(f"🔵 عروض: {c_ask}")

    st.title(f"سجل البيانات العقارية: {selected_dist}")
    
    if 'Source_File' in df.columns:
        with st.expander("📂 تفاصيل الملفات والمصادر", expanded=False):
            file_stats = filtered_df['Source_File'].value_counts().reset_index()
            file_stats.columns = ['اسم الملف', 'عدد العقارات']
            st.dataframe(file_stats, use_container_width=True)

    if filtered_df.empty:
        st.info("لا توجد بيانات مطابقة.")
    else:
        tab_deals, tab_offers = st.tabs(["💰 سجل الصفقات", "🏷️ العروض"])
        cols_show = ['Source_File', 'اسم_المطور', 'الحي', 'السعر', 'المساحة', 'سعر_المتر', 'نوع_العقار', 'الحالة', 'عدد_الغرف']
        cols_map = {'Source_File': 'الملف', 'اسم_المطور': 'المطور', 'سعر_المتر': 'المتر', 'نوع_العقار': 'النوع'}
        valid_cols = [c for c in cols_show if c in filtered_df.columns]

        with tab_deals:
            d_data = filtered_df[filtered_df['Data_Category'] == 'صفقات (Sold)']
            if not d_data.empty: st.dataframe(d_data[valid_cols].rename(columns=cols_map).sort_values('المتر'), use_container_width=True)
            else: st.warning("لا توجد صفقات.")

        with tab_offers:
            o_data = filtered_df[filtered_df['Data_Category'] == 'عروض (Ask)']
            if not o_data.empty: st.dataframe(o_data[valid_cols].rename(columns=cols_map).sort_values('المتر'), use_container_width=True)
            else: st.warning("لا توجد عروض.")

# ========================================================
# 🏗️ القسم الثاني: حاسبة التكاليف + تحليل السوق
# ========================================================
elif app_mode == "🏗️ حاسبة التكاليف (Calculator)":
    
    st.title("🏗️ حاسبة التكاليف المربوطة بالسوق")
    
    # --- سايدبار الحاسبة ---
    with st.sidebar:
        # 0. تحديد الحي (مهم جداً للربط بالسوق)
        st.markdown("### 📍 موقع المشروع")
        districts_list = sorted(df['الحي'].unique()) if 'الحي' in df.columns else []
        calc_dist = st.selectbox("اختر الحي للتحليل:", districts_list)
        
        st.divider()

        st.subheader("1️⃣ الأرض")
        land_area = st.number_input("مساحة الأرض (م²)", value=375, step=25)
        land_price = st.number_input("سعر المتر (ريال)", value=3500, step=50)
        tax_pct = st.number_input("ضريبة التصرفات (%)", value=5.0)
        comm_pct = st.number_input("سعي الشراء (%)", value=2.5)

        st.divider()

        st.subheader("2️⃣ البناء")
        build_ratio = st.slider("معامل البناء (FAR)", 1.0, 3.5, 2.3)
        bua = land_area * build_ratio
        st.caption(f"مسطح البناء المتوقع: **{bua:,.0f} م²**")
        turnkey_price = st.number_input("سعر البناء (تسليم مفتاح)/م", value=1800)
        bone_price = st.number_input("سعر العظم (للتأمين)/م", value=700)
        
        st.divider()

        st.subheader("3️⃣ الخدمات والرخص")
        num_units = st.number_input("عدد الوحدات", value=4)
        services_cost_per_unit = st.number_input("تكلفة الخدمات/وحدة", value=15000)
        permits_cost = st.number_input("إجمالي الرخص والتصاريح", value=25000)
        design_fees = st.number_input("تصميم وإشراف هندسي", value=40000)

        st.divider()

        st.subheader("4️⃣ التسويق والاستراتيجية")
        marketing_pct = st.number_input("نسبة التسويق والعمولات (%)", value=2.5)
        is_offplan = st.checkbox("بيع على الخارطة (Off-plan)?", value=False)
        
        wafi_fees = 0
        if is_offplan:
            wafi_fees = st.number_input("رسوم وافي وأمين الحساب", value=50000)
            
    # --- الحسابات ---
    base_land_cost = land_area * land_price
    land_adds = base_land_cost * ((tax_pct + comm_pct) / 100)
    total_land_cost = base_land_cost + land_adds

    total_construction_cost = bua * turnkey_price
    total_bone_cost = bua * bone_price
    malath_insurance = total_bone_cost * 0.01
    services_total = num_units * services_cost_per_unit
    
    sub_total_hard = total_land_cost + total_construction_cost + services_total + permits_cost + design_fees + wafi_fees
    contingency_val = sub_total_hard * 0.02 
    marketing_budget = (sub_total_hard + contingency_val) * (marketing_pct / 100)
    grand_total_cost = sub_total_hard + contingency_val + marketing_budget
    cost_per_built_meter = grand_total_cost / bua

    # --- عرض النتائج ---
    if is_offplan: st.warning("⚠️ وضع التحليل: **بيع على الخارطة**")
    else: st.success("✅ وضع التحليل: **تطوير تقليدي**")

    c1, c2, c3 = st.columns(3)
    with c1: st.metric("إجمالي التكلفة", f"{grand_total_cost:,.0f} ريال")
    with c2: st.metric("تكلفة المتر (على المسطح)", f"{cost_per_built_meter:,.0f} ريال")
    with c3: st.metric("مسطح البناء", f"{bua:,.0f} م²")

    st.divider()

    # الجدول والرسم
    col_table, col_chart = st.columns([1.5, 1])
    with col_table:
        st.subheader("📑 تفاصيل الفاتورة")
        breakdown = [
            {"البند": "قيمة الأرض (مع الضريبة والسعي)", "التكلفة": total_land_cost},
            {"البند": "تكلفة البناء (تسليم مفتاح)", "التكلفة": total_construction_cost},
            {"البند": "تأمين ملاذ (1% من العظم)", "التكلفة": malath_insurance},
            {"البند": f"خدمات ({num_units} عدادات)", "التكلفة": services_total},
            {"البند": "رخص + تصميم وإشراف", "التكلفة": permits_cost + design_fees},
            {"البند": f"تسويق وعمولات بيع ({marketing_pct}%)", "التكلفة": marketing_budget},
            {"البند": "احتياطي طوارئ (2%)", "التكلفة": contingency_val},
        ]
        if is_offplan: breakdown.append({"البند": "رسوم وافي وأمين حساب", "التكلفة": wafi_fees})
        df_cost = pd.DataFrame(breakdown)
        df_cost['الوزن'] = (df_cost['التكلفة'] / grand_total_cost)
        st.dataframe(df_cost, use_container_width=True, column_config={"التكلفة": st.column_config.NumberColumn(format="%d ريال"), "الوزن": st.column_config.ProgressColumn(format="%.1f%%", min_value=0, max_value=1)})
        
    with col_chart:
        st.subheader("🍰 توزيع التكاليف")
        chart_data = df_cost.set_index("البند")
        st.bar_chart(chart_data['التكلفة'])

    # ==========================================================
    # 🧠 تحليل السوق الذكي (The New Market Insight Section)
    # ==========================================================
    
    st.markdown("---")
    st.header(f"📊 مؤشرات السوق الحقيقية: {calc_dist}")
    
    # فلترة بيانات الحي المحدد
    market_df = df[df['الحي'] == calc_dist]
    
    if market_df.empty:
        st.warning(f"عذراً، لا توجد بيانات مسجلة في النظام لحي {calc_dist} للمقارنة.")
    else:
        # 1. تحليل الأراضي (من الصفقات فقط)
        sold_lands = market_df[
            (market_df['Data_Category'] == 'صفقات (Sold)') & 
            (market_df['نوع_العقار'].str.contains('أرض', na=False))
        ]
        avg_land_market, land_msg = get_clean_stats(sold_lands)

        # 2. تحليل الشقق (من العروض فقط)
        ask_apts = market_df[
            (market_df['Data_Category'] == 'عروض (Ask)') & 
            (market_df['نوع_العقار'].str.contains('شقة', na=False))
        ]
        avg_apt_market, apt_msg = get_clean_stats(ask_apts)

        # عرض الكروت
        col_m1, col_m2 = st.columns(2)
        
        with col_m1:
            st.markdown(f"""
            <div class="market-card">
                <h3>🏷️ متوسط سعر متر الأرض (صفقات)</h3>
                <h2 style="color:#2c3e50;">{avg_land_market:,.0f} ريال</h2>
                <small>{land_msg}</small>
            </div>
            """, unsafe_allow_html=True)
            
            # مقارنة مدخلاتك بالسوق
            if avg_land_market > 0:
                diff_land = ((land_price - avg_land_market) / avg_land_market) * 100
                if diff_land > 10:
                    st.error(f"⚠️ انتبه: سعرك المدخل ({land_price}) أعلى من متوسط الصفقات بـ {diff_land:.1f}%")
                elif diff_land < -10:
                    st.success(f"🔥 لقطة: سعرك أقل من متوسط الصفقات بـ {abs(diff_land):.1f}%")
                else:
                    st.info("✅ سعرك منطقي وموافق لمتوسط السوق.")

        with col_m2:
            st.markdown(f"""
            <div class="market-card" style="border-top-color: #9b59b6;">
                <h3>🏢 متوسط عرض الشقق (عروض)</h3>
                <h2 style="color:#8e44ad;">{avg_apt_market:,.0f} ريال</h2>
                <small>{apt_msg}</small>
            </div>
            """, unsafe_allow_html=True)
            
            # مقارنة تكلفتك بسعر السوق للشقق
            if avg_apt_market > 0:
                # نحسب تكلفة المتر الصافية للمشروع (شامل الأرض والبناء)
                proj_cost_sqm = cost_per_built_meter
                potential_profit_margin = ((avg_apt_market - proj_cost_sqm) / proj_cost_sqm) * 100
                
                st.write(f"تكلفة مشروعك للمتر: **{proj_cost_sqm:,.0f} ريال**")
                if potential_profit_margin > 20:
                    st.success(f"🚀 فرصة ممتازة: هامش الربح المتوقع (مقارنة بالسوق) يصل إلى {potential_profit_margin:.1f}%")
                elif potential_profit_margin > 0:
                    st.warning(f"⚠️ ربح محدود: الهامش المتوقع {potential_profit_margin:.1f}% (المنافسة قوية)")
                else:
                    st.error(f"⛔ خطر: تكلفتك أعلى من سعر بيع السوق الحالي!")
