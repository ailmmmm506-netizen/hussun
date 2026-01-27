import streamlit as st
import pandas as pd
import data_bot  # المحرك الذكي

# إعداد الصفحة
st.set_page_config(page_title="المطور العقاري الذكي", layout="wide", page_icon="🏢")

# --- التنسيق الجمالي ---
st.markdown("""
<style>
    /* تنسيق الكروت */
    .cost-card { background-color: #f8f9fa; padding: 20px; border-radius: 10px; border-left: 5px solid #2ecc71; margin-bottom: 10px; }
    .wafi-card { background-color: #fff3cd; padding: 20px; border-radius: 10px; border-left: 5px solid #ffc107; margin-bottom: 10px; }
    .stat-box { background-color: #ffffff; padding: 15px; border-radius: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.05); text-align: center; }
    
    /* تحسين السايدبار */
    [data-testid="stSidebar"] { background-color: #f8f9fa; border-left: 1px solid #ddd; }
    
    /* تنسيق الجداول */
    .stDataFrame { border: 1px solid #eee; border-radius: 5px; }
</style>
""", unsafe_allow_html=True)

# --- دالة الاتصال مع الكاش ---
@st.cache_resource(show_spinner="جاري جلب البيانات...", ttl=3600)
def load_bot():
    try: return data_bot.RealEstateBot()
    except: return None

if 'bot' not in st.session_state: st.session_state.bot = load_bot()
df = st.session_state.bot.df if hasattr(st.session_state.bot, 'df') else pd.DataFrame()

# ========================================================
# 🟢 القائمة الجانبية (نظام التنقل الرئيسي)
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
# 📊 القسم الأول: لوحة البيانات (Dashboard)
# ========================================================
if app_mode == "📊 لوحة البيانات (Dashboard)":
    
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
        st.markdown(f"**📌 ملخص {selected_dist}:**")
        st.write(f"🟢 صفقات: {c_sold}")
        st.write(f"🔵 عروض: {c_ask}")

    st.title(f"سجل البيانات العقارية: {selected_dist}")
    
    if 'Source_File' in df.columns:
        with st.expander("📂 تفاصيل الملفات والمصادر", expanded=False):
            file_stats = filtered_df['Source_File'].value_counts().reset_index()
            file_stats.columns = ['اسم الملف', 'عدد العقارات']
            st.dataframe(file_stats, use_container_width=True, column_config={"عدد العقارات": st.column_config.ProgressColumn(format="%d", max_value=int(file_stats['عدد العقارات'].max()))})

    if filtered_df.empty:
        st.info("لا توجد بيانات مطابقة.")
    else:
        tab_deals, tab_offers = st.tabs(["💰 سجل الصفقات (Sold)", "🏷️ عروض السوق (Offers)"])
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
# 🏗️ القسم الثاني: حاسبة التكاليف (Calculator)
# ========================================================
elif app_mode == "🏗️ حاسبة التكاليف (Calculator)":
    
    st.title("🏗️ حاسبة تكاليف التطوير المتقدمة")
    
    # --- سايدبار الحاسبة ---
    with st.sidebar:
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
        marketing_pct = st.number_input("نسبة التسويق والعمولات (%)", value=2.5, help="تحسب كنسبة من إجمالي تكلفة المشروع كميزانية تقديرية")
        is_offplan = st.checkbox("بيع على الخارطة (Off-plan)?", value=False)
        
        wafi_fees = 0
        if is_offplan:
            wafi_fees = st.number_input("رسوم وافي وأمين الحساب", value=50000)
            
    # --- العمليات الحسابية ---
    
    # 1. الأرض
    base_land_cost = land_area * land_price
    land_adds = base_land_cost * ((tax_pct + comm_pct) / 100)
    total_land_cost = base_land_cost + land_adds

    # 2. البناء
    total_construction_cost = bua * turnkey_price
    total_bone_cost = bua * bone_price
    
    # 3. الرسوم والخدمات
    malath_insurance = total_bone_cost * 0.01
    services_total = num_units * services_cost_per_unit
    
    # 4. الطوارئ (2%)
    sub_total_hard = total_land_cost + total_construction_cost + services_total + permits_cost + design_fees + wafi_fees
    contingency_val = sub_total_hard * 0.02 
    
    # 5. التسويق (الجديد) 📣
    # نحسبها كنسبة من (التكاليف المباشرة + الطوارئ) لتكوين ميزانية
    marketing_budget = (sub_total_hard + contingency_val) * (marketing_pct / 100)
    
    # 6. الإجمالي النهائي
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

    col_table, col_chart = st.columns([1.5, 1])
    
    with col_table:
        st.subheader("📑 تفاصيل الفاتورة")
        
        breakdown = [
            {"البند": "قيمة الأرض (مع الضريبة والسعي)", "التكلفة": total_land_cost},
            {"البند": "تكلفة البناء (تسليم مفتاح)", "التكلفة": total_construction_cost},
            {"البند": "تأمين ملاذ (1% من العظم)", "التكلفة": malath_insurance},
            {"البند": f"خدمات ({num_units} عدادات)", "التكلفة": services_total},
            {"البند": "رخص + تصميم وإشراف", "التكلفة": permits_cost + design_fees},
            {"البند": f"تسويق وعمولات بيع ({marketing_pct}%)", "التكلفة": marketing_budget}, # البند الجديد
            {"البند": "احتياطي طوارئ (2%)", "التكلفة": contingency_val},
        ]
        if is_offplan:
            breakdown.append({"البند": "رسوم وافي وأمين حساب", "التكلفة": wafi_fees})
            
        df_cost = pd.DataFrame(breakdown)
        df_cost['الوزن'] = (df_cost['التكلفة'] / grand_total_cost)
        
        st.dataframe(
            df_cost,
            use_container_width=True,
            column_config={
                "التكلفة": st.column_config.NumberColumn(format="%d ريال"),
                "الوزن": st.column_config.ProgressColumn(format="%.1f%%", min_value=0, max_value=1)
            }
        )
        
    with col_chart:
        st.subheader("🍰 توزيع التكاليف")
        chart_data = df_cost.set_index("البند")
        st.bar_chart(chart_data['التكلفة'])

    st.divider()
    st.info(f"💡 تم رصد ميزانية تسويقية قدرها **{marketing_budget:,.0f} ريال**. هذا المبلغ يغطي عادةً عمولات الوسطاء والحملات الإعلانية عند بدء البيع.")
    
