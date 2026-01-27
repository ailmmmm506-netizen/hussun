import streamlit as st
import pandas as pd
import data_bot  # المحرك الذكي

# إعداد الصفحة
st.set_page_config(page_title="المطور العقاري الذكي", layout="wide", page_icon="🏢")

# --- التنسيق الجمالي ---
st.markdown("""
<style>
    /* تنسيق الكروت */
    .market-card { 
        background-color: #ffffff; 
        padding: 15px; 
        border-radius: 10px; 
        border-top: 5px solid #3498db; 
        margin-bottom: 15px; 
        box-shadow: 0 2px 5px rgba(0,0,0,0.05);
        text-align: center;
    }
    .market-card h3 { font-size: 16px; color: #7f8c8d; margin-bottom: 5px; }
    .market-card h2 { font-size: 24px; font-weight: bold; color: #2c3e50; margin: 0; }
    .market-card small { font-size: 12px; color: #95a5a6; }
    
    .cost-card { background-color: #f8f9fa; padding: 20px; border-radius: 10px; border-left: 5px solid #2ecc71; margin-bottom: 10px; }
    [data-testid="stSidebar"] { background-color: #f8f9fa; border-left: 1px solid #ddd; }
    .stDataFrame { border: 1px solid #eee; border-radius: 5px; }
</style>
""", unsafe_allow_html=True)

# --- دالة الإحصاء المحدثة ---
def get_clean_stats(df_input, col='سعر_المتر'):
    if df_input.empty: return 0, "لا توجد بيانات", df_input
    
    # تنظيف القيم الشاذة (استبعاد الأصفار والأسعار الخيالية)
    clean = df_input[(df_input[col] > 100) & (df_input[col] < 250000)].copy()
    
    if clean.empty: return 0, "القيم خارج النطاق", clean
    
    # إذا البيانات قليلة، خذ المتوسط مباشرة
    if len(clean) < 5:
        return clean[col].median(), f"عدد ({len(clean)})", clean
    
    # IQR لاستبعاد القيم المتطرفة
    Q1 = clean[col].quantile(0.25)
    Q3 = clean[col].quantile(0.75)
    IQR = Q3 - Q1
    lower_bound = Q1 - 1.5 * IQR
    upper_bound = Q3 + 1.5 * IQR
    
    final_df = clean[(clean[col] >= lower_bound) & (clean[col] <= upper_bound)]
    
    if final_df.empty: 
        return clean[col].median(), f"عدد ({len(clean)})", clean
    
    return final_df[col].median(), f"عدد ({len(final_df)})", final_df

# --- دالة الفلترة الذكية (هنا الحل للمشكلة) ---
def smart_filter(df, keywords):
    # تحويل العمود لنص وتنظيفه
    mask = df['نوع_العقار'].astype(str).str.contains('|'.join(keywords), case=False, na=False)
    return df[mask]

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
# 🏗️ القسم الثاني: حاسبة التكاليف + تحليل السوق الشامل
# ========================================================
elif app_mode == "🏗️ حاسبة التكاليف (Calculator)":
    
    st.title("🏗️ حاسبة التكاليف المربوطة بالسوق")
    
    # --- سايدبار الحاسبة ---
    with st.sidebar:
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

        st.subheader("3️⃣ الخدمات والتسويق")
        num_units = st.number_input("عدد الوحدات", value=4)
        services_cost_per_unit = st.number_input("تكلفة الخدمات/وحدة", value=15000)
        permits_cost = st.number_input("إجمالي الرخص", value=25000)
        design_fees = st.number_input("تصميم وإشراف", value=40000)
        marketing_pct = st.number_input("نسبة التسويق (%)", value=2.5)
        
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

    # --- عرض النتائج العلوية ---
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
            {"البند": "قيمة الأرض", "التكلفة": total_land_cost},
            {"البند": "تكلفة البناء", "التكلفة": total_construction_cost},
            {"البند": "تأمين ملاذ", "التكلفة": malath_insurance},
            {"البند": "خدمات", "التكلفة": services_total},
            {"البند": "رخص وإشراف", "التكلفة": permits_cost + design_fees},
            {"البند": "تسويق", "التكلفة": marketing_budget},
            {"البند": "طوارئ", "التكلفة": contingency_val},
        ]
        if is_offplan: breakdown.append({"البند": "رسوم وافي", "التكلفة": wafi_fees})
        df_cost = pd.DataFrame(breakdown)
        df_cost['الوزن'] = (df_cost['التكلفة'] / grand_total_cost)
        st.dataframe(df_cost, use_container_width=True, column_config={"التكلفة": st.column_config.NumberColumn(format="%d"), "الوزن": st.column_config.ProgressColumn(format="%.1f%%")})
        
    with col_chart:
        st.bar_chart(df_cost.set_index("البند")['التكلفة'])

    # ==========================================================
    # 🧠 تحليل السوق الشامل (Scanner)
    # ==========================================================
    
    st.markdown("---")
    st.header(f"📊 مسح أسعار العروض في حي {calc_dist}")
    
    market_df = df[df['الحي'] == calc_dist]
    
    if market_df.empty:
        st.warning(f"لا توجد بيانات مسجلة لحي {calc_dist}.")
    else:
        # 1. فلترة العروض فقط
        offers_df = market_df[market_df['Data_Category'] == 'عروض (Ask)']
        
        if offers_df.empty:
            st.warning("لا توجد عروض بيع مسجلة في هذا الحي.")
        else:
            # 2. الفلترة الذكية (هنا التعديل المهم)
            
            # أ) الفلل (تشمل: فيلا، فلة، تاون، دبلكس، Villa, House)
            villa_keywords = ['فيلا', 'فلة', 'تاون', 'دبلكس', 'Villa', 'Town', 'Duplex', 'بيت']
            villa_offers = smart_filter(offers_df, villa_keywords)
            avg_villa, msg_villa, df_villa = get_clean_stats(villa_offers)
            
            # ب) الشقق (تشمل: شقة، شقه، تمليك، Apartment, Flat)
            apt_keywords = ['شقة', 'شقه', 'تمليك', 'Apartment', 'Flat', 'ستوديو']
            # إضافة شرط الحجم: أحياناً لا يكتبون شقة ولكن المساحة صغيرة (<250)
            apt_mask = (offers_df['نوع_العقار'].astype(str).str.contains('|'.join(apt_keywords), case=False, na=False)) | \
                       ((offers_df['المساحة'] < 250) & (offers_df['نوع_العقار'].astype(str).str.contains('مبني', na=False)))
            apt_offers = offers_df[apt_mask]
            avg_apt, msg_apt, df_apt = get_clean_stats(apt_offers)
            
            # ج) الأدوار (تشمل: دور، طابق، Floor)
            floor_keywords = ['دور', 'طابق', 'Floor']
            floor_offers = smart_filter(offers_df, floor_keywords)
            avg_floor, msg_floor, df_floor = get_clean_stats(floor_offers)
            
            # د) المتوسط العام
            avg_all, msg_all, df_all = get_clean_stats(offers_df)

            # 3. عرض النتائج
            col_res1, col_res2, col_res3, col_res4 = st.columns(4)
            
            with col_res1:
                st.markdown(f"""
                <div class="market-card">
                    <h3>🏠 متوسط الفلل</h3>
                    <h2>{avg_villa:,.0f}</h2>
                    <small>{msg_villa}</small>
                </div>
                """, unsafe_allow_html=True)
                with st.expander("👁️ تفاصيل"):
                    if not df_villa.empty: st.dataframe(df_villa[['السعر', 'المساحة', 'سعر_المتر', 'نوع_العقار']], use_container_width=True)
            
            with col_res2:
                st.markdown(f"""
                <div class="market-card">
                    <h3>🏢 متوسط الشقق</h3>
                    <h2>{avg_apt:,.0f}</h2>
                    <small>{msg_apt}</small>
                </div>
                """, unsafe_allow_html=True)
                with st.expander("👁️ تفاصيل"):
                    if not df_apt.empty: st.dataframe(df_apt[['السعر', 'المساحة', 'سعر_المتر', 'نوع_العقار']], use_container_width=True)
                
            with col_res3:
                st.markdown(f"""
                <div class="market-card">
                    <h3>🏘️ متوسط الأدوار</h3>
                    <h2>{avg_floor:,.0f}</h2>
                    <small>{msg_floor}</small>
                </div>
                """, unsafe_allow_html=True)

            with col_res4:
                st.markdown(f"""
                <div class="market-card" style="border-top-color: #f1c40f;">
                    <h3>📈 المتوسط العام</h3>
                    <h2>{avg_all:,.0f}</h2>
                    <small>{msg_all}</small>
                </div>
                """, unsafe_allow_html=True)
            
            # 4. مقارنة تكلفتك
            st.divider()
            st.subheader("💡 تحليل الجدوى (مقارنة بالسوق)")
            proj_cost = cost_per_built_meter
            
            def show_comparison(label, market_price):
                if market_price > 0:
                    diff = ((market_price - proj_cost) / proj_cost) * 100
                    icon = "🚀" if diff > 20 else "⚠️" if diff > 0 else "⛔"
                    st.write(f"**مقارنة مع {label}:**")
                    st.progress(min(max((diff + 50)/100, 0.0), 1.0))
                    st.caption(f"{icon} الهامش المتوقع: **{diff:.1f}%** (سعر السوق: {market_price:,.0f})")

            c_comp1, c_comp2 = st.columns(2)
            with c_comp1:
                show_comparison("الشقق", avg_apt)
                show_comparison("الأدوار", avg_floor)
            with c_comp2:
                show_comparison("الفلل", avg_villa)
                show_comparison("المتوسط العام", avg_all)
