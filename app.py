import streamlit as st
import pandas as pd
import data_bot  # المحرك الذكي

# إعداد الصفحة
st.set_page_config(page_title="المستشار العقاري الشامل", layout="wide", page_icon="🏢")

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
    .big-stat { font-size: 24px; font-weight: bold; color: #2c3e50; }
    .stat-label { font-size: 14px; color: #7f8c8d; margin-bottom: 5px; }
    [data-testid="stSidebar"] { background-color: #f8f9fa; border-left: 1px solid #ddd; }
    .price-target { color: #8e44ad; font-weight: bold; font-size: 26px; }
</style>
""", unsafe_allow_html=True)

# --- دوال مساعدة ---
def get_advanced_stats(df_input, col='سعر_المتر'):
    if df_input.empty: return 0, 0, 0, 0, "لا توجد بيانات"
    clean = df_input[(df_input[col] > 100) & (df_input[col] < 150000)].copy()
    if len(clean) < 3: return 0, 0, 0, 0, "بيانات غير كافية"
    Q1 = clean[col].quantile(0.25); Q3 = clean[col].quantile(0.75); IQR = Q3 - Q1
    lower_bound = Q1 - 1.5 * IQR; upper_bound = Q3 + 1.5 * IQR
    final_df = clean[(clean[col] >= lower_bound) & (clean[col] <= upper_bound)]
    if final_df.empty: return 0, 0, 0, 0, "تشتت عالي"
    count = len(final_df)
    confidence = "✅ عالية" if count > 10 else "⚠️ متوسطة" if count > 5 else "❌ منخفضة"
    return final_df[col].median(), final_df[col].min(), final_df[col].max(), count, confidence

# --- الاتصال بالمحرك ---
if 'bot' not in st.session_state:
    with st.spinner("جاري الاتصال بالنظام..."):
        try: st.session_state.bot = data_bot.RealEstateBot()
        except: st.error("خطأ في الاتصال")

df = st.session_state.bot.df if hasattr(st.session_state.bot, 'df') else pd.DataFrame()

# ========================================================
# 🟢 القائمة الجانبية (التنقل + الإعدادات العامة)
# ========================================================
with st.sidebar:
    st.image("https://cdn-icons-png.flaticon.com/512/2642/2642226.png", width=60)
    
    # --- التنقل بين التطبيق والداشبورد ---
    app_mode = st.radio("اختر النظام:", ["📱 دراسة الجدوى (App)", "📊 سجل البيانات (Dashboard)"])
    
    st.divider()
    
    if st.button("🔄 تحديث البيانات", use_container_width=True):
        st.cache_data.clear()
        for key in list(st.session_state.keys()): del st.session_state[key]
        st.rerun()

    if df.empty:
        st.warning("بانتظار البيانات...")
        st.stop()

    # --- فلتر الحي (مشترك) ---
    st.subheader("📍 الموقع")
    districts = sorted(df['الحي'].unique()) if 'الحي' in df.columns else []
    
    # البحث الذكي
    location_input = st.text_input("بحث سريع (رابط/اسم)", placeholder="لصق رابط جوجل...")
    default_ix = 0
    if location_input:
        for i, d in enumerate(districts):
            if d in location_input: default_ix = i; st.toast(f"تم تحديد: {d}"); break
            
    selected_dist = st.selectbox("اختر الحي", districts, index=default_ix)

# ========================================================
# 📱 الصفحة 1: تطبيق دراسة الجدوى
# ========================================================
if app_mode == "📱 دراسة الجدوى (App)":
    
    # مدخلات خاصة بالتطبيق فقط
    with st.sidebar:
        st.divider()
        st.subheader("⚙️ إعدادات المشروع")
        
        # خيار مصدر المقارنة
        compare_source = st.selectbox("قارن مشروعي بـ:", ["عروض السوق (Ask)", "صفقات منفذة (Sold)"], index=0)
        selected_cat = "عروض (Ask)" if "عروض" in compare_source else "صفقات (Sold)"
        
        c1, c2 = st.columns(2)
        with c1: land_area = st.number_input("مساحة الأرض", value=375)
        with c2: offer_price = st.number_input("سعر شراء الأرض", value=3500)
        
        build_cost_sqm = st.number_input("تكلفة البناء/م", value=1750)
        target_margin = st.slider("هامش الربح المستهدف %", 10, 50, 25)
        build_ratio = st.slider("نسبة البناء (FAR)", 1.0, 3.5, 2.3)
        fees_pct = st.number_input("رسوم إدارية %", value=8.0)

    # --- معالجة التطبيق ---
    st.title(f"دراسة جدوى: {selected_dist}")
    st.caption(f"يتم التحليل بناءً على: **{selected_cat}**")

    # فلترة البيانات للمقارنة
    comp_df = df[(df['الحي'] == selected_dist) & (df['Data_Category'] == selected_cat)]
    
    # فصل المباني للمقارنة
    if selected_cat == "عروض (Ask)":
        comp_builds = comp_df[comp_df['نوع_العقار'].isin(['فيلا', 'مبني (فيلا)'])]
    else:
        comp_builds = comp_df[comp_df['نوع_العقار'] == 'مبني']

    clean_build, min_build, max_build, build_count, build_conf = get_advanced_stats(comp_builds)

    # 🛠️ [تصحيح] تعريف المتغيرات بشكل صريح هنا قبل استخدامها
    land_base = land_area * offer_price
    # تعريف المتغيرات المفقودة
    exec_cost = land_area * build_ratio * build_cost_sqm
    admin_fees = exec_cost * (fees_pct / 100)
    
    # حساب الإجمالي
    total_cost = (land_base * 1.075) + exec_cost + admin_fees
    
    # حسابات الربح
    target_profit = total_cost * (target_margin / 100)
    req_revenue = total_cost + target_profit
    req_sell_sqm = req_revenue / land_area

    # العرض
    tab1, tab2, tab3, tab4 = st.tabs(["🎯 الاستراتيجية", "💰 التكاليف", "📉 المخاطر", "💎 المستثمر"])

    with tab1:
        c_kpi, c_msg = st.columns([1, 2])
        with c_kpi:
            st.markdown(f"""
            <div style="background:#f0f2f6; padding:15px; border-radius:10px; text-align:center;">
                <div style="color:#7f8c8d;">سعر البيع المستهدف للمتر</div>
                <div class="price-target">{req_sell_sqm:,.0f} ريال</div>
                <small>لتحقيق ربح {target_margin}%</small>
            </div>
            """, unsafe_allow_html=True)
        
        with c_msg:
            st.info(f"مؤشر دقة السوق: **{build_conf}** ({build_count} عقار مشابه)")
            if clean_build > 0:
                diff = ((req_sell_sqm - clean_build)/clean_build)*100
                if req_sell_sqm > max_build:
                    st.error(f"⚠️ سعرك ({req_sell_sqm:,.0f}) أعلى من أغلى عقار في الحي ({max_build:,.0f})! المشروع خطر.")
                elif req_sell_sqm > clean_build:
                    st.warning(f"⚖️ سعرك أعلى من المتوسط بـ {diff:.1f}%. تحتاج جودة تنفيذ عالية.")
                else:
                    st.success(f"✅ سعرك منافس جداً (أقل من السوق بـ {abs(diff):.1f}%).")
            else:
                st.warning("لا توجد بيانات مقارنة كافية.")

    with tab2:
        st.markdown("#### هيكل التكاليف التقديري")
        # استخدام المتغيرات المعرفة حديثاً (exec_cost, admin_fees)
        cost_df = pd.DataFrame([
            {"البند": "قيمة الأرض (مع الضريبة)", "التكلفة": land_base * 1.05},
            {"البند": "سعي الأرض (2.5%)", "التكلفة": land_base * 0.025},
            {"البند": "تكلفة البناء (تنفيذ)", "التكلفة": exec_cost},
            {"البند": "رسوم إدارية وإشراف", "التكلفة": admin_fees},
            {"البند": "🔴 إجمالي رأس المال", "التكلفة": total_cost}
        ])
        st.dataframe(cost_df.style.format({"التكلفة": "{:,.0f}"}), use_container_width=True)

    with tab3:
        st.markdown("#### نقطة التعادل وتحليل الحساسية")
        breakeven = total_cost / land_area
        st.metric("نقطة التعادل (لا ربح ولا خسارة)", f"{breakeven:,.0f} ريال/م")
        
        st.write("نسبة الربح المتوقعة عند تغيير سعر البيع:")
        changes = [-0.1, -0.05, 0, 0.05, 0.1]
        res = {}
        for c in changes:
            sell = req_revenue * (1 + c)
            roi = ((sell - total_cost)/total_cost)*100
            res[f"{c:+.0%}"] = f"{roi:.1f}%"
        st.dataframe(pd.DataFrame([res]), use_container_width=True)

    with tab4:
        st.markdown(f"""
        <div class="investor-card">
            <h3 style="color:#1f77b4;">ملخص الفرصة - حي {selected_dist}</h3>
            <div style="display:flex; justify-content:space-around; margin-top:15px;">
                <div><div class="stat-label">رأس المال</div><div class="big-stat">{total_cost:,.0f}</div></div>
                <div><div class="stat-label">الإيراد المتوقع</div><div class="big-stat">{req_revenue:,.0f}</div></div>
                <div><div class="stat-label">صافي الربح</div><div class="big-stat" style="color:#27ae60;">{target_profit:,.0f}</div></div>
            </div>
        </div>
        """, unsafe_allow_html=True)


# ========================================================
# 📊 الصفحة 2: الداشبورد (سجل البيانات)
# ========================================================
elif app_mode == "📊 سجل البيانات (Dashboard)":
    
    st.title(f"سجل البيانات: {selected_dist}")
    
    # 1. إحصائيات الملفات
    if 'Source_File' in df.columns:
        with st.expander("📂 تفاصيل المصادر (الملفات المسحوبة)", expanded=False):
            file_stats = df['Source_File'].value_counts().reset_index()
            file_stats.columns = ['اسم الملف', 'عدد العقارات']
            st.dataframe(file_stats, use_container_width=True)

    # 2. الجدول الرئيسي
    dash_df = df[df['الحي'] == selected_dist].copy()
    
    if dash_df.empty:
        st.warning(f"لا توجد بيانات مسجلة لحي {selected_dist}.")
    else:
        t_deals, t_offers = st.tabs(["💰 الصفقات (Sold)", "🏷️ العروض (Offers)"])
        
        cols_show = ['Source_File', 'اسم_المطور', 'السعر', 'المساحة', 'سعر_المتر', 'نوع_العقار', 'الحالة', 'عدد_الغرف']
        # التأكد من وجود الأعمدة قبل العرض
        existing_cols = [c for c in cols_show if c in dash_df.columns]
        
        with t_deals:
            d_data = dash_df[dash_df['Data_Category'] == 'صفقات (Sold)']
            if not d_data.empty:
                st.dataframe(d_data[existing_cols].sort_values('سعر_المتر'), use_container_width=True)
            else: st.info("لا توجد صفقات.")

        with t_offers:
            o_data = dash_df[dash_df['Data_Category'] == 'عروض (Ask)']
            if not o_data.empty:
                st.dataframe(o_data[existing_cols].sort_values('سعر_المتر'), use_container_width=True)
            else: st.info("لا توجد عروض.")
