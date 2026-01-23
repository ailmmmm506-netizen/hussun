import streamlit as st
import pandas as pd
import numpy as np
import data_bot  # المحرك

# إعداد الصفحة
st.set_page_config(page_title="المستشار العقاري - استراتيجية البيع", layout="wide", page_icon="🎯")

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
    .price-target { color: #8e44ad; font-weight: bold; font-size: 26px; }
    .market-comp { font-size: 16px; color: #555; }
</style>
""", unsafe_allow_html=True)

# --- دالة الإحصاء ---
def get_advanced_stats(df_input, col='سعر_المتر'):
    if df_input.empty: return 0, 0, 0, 0, "لا توجد بيانات"
    # تنظيف أولي
    clean = df_input[(df_input[col] > 100) & (df_input[col] < 150000)].copy()
    if len(clean) < 3: return 0, 0, 0, 0, "بيانات غير كافية"
    # IQR
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
    st.image("https://cdn-icons-png.flaticon.com/512/2642/2642226.png", width=50)
    st.title("بيانات التطوير")
    
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
    location_input = st.text_input("🔗 بحث ذكي", placeholder="رابط/اسم الحي")
    default_ix = 0
    if location_input:
        for i, d in enumerate(districts_list):
            if d in location_input: default_ix = i; st.toast(f"📍 {d}"); break
    
    selected_dist = st.selectbox("📍 الحي", districts_list, index=default_ix)
    
    # 2. التكاليف
    st.subheader("🛠️ التكاليف")
    c_s1, c_s2 = st.columns(2)
    with c_s1: land_area = st.number_input("المساحة (م²)", value=375)
    with c_s2: offer_price = st.number_input("سعر الأرض/م", value=3500)
    
    build_cost_sqm = st.number_input("تكلفة البناء/م", value=1750)
    build_ratio = st.slider("نسبة البناء (%)", 1.0, 3.5, 2.3)
    fees_pct = st.number_input("رسوم إدارية (%)", value=8.0)

    st.divider()
    
    # 3. الهدف (الجديد)
    st.subheader("🎯 هدفك الربحي")
    target_margin = st.slider("هامش الربح المطلوب (%)", 10, 50, 25, help="نسبة الربح الصافي التي تستهدفها من المشروع")

# ========================================================
# 🏭 المعالجة
# ========================================================
district_df = df[df['الحي'] == selected_dist].copy()

# فصل البيانات (للمباني فقط كما طلبت)
builds_raw = district_df[district_df['نوع_العقار'].str.contains('مبني|فيلا|شقة|بيت', regex=True, na=False)]
clean_build, min_build, max_build, build_count, build_conf = get_advanced_stats(builds_raw)

# حساب التكاليف
land_base = land_area * offer_price
total_project_cost = (land_base * 1.075) + (land_area * build_ratio * build_cost_sqm) + ((land_area * build_ratio * build_cost_sqm) * (fees_pct/100))

# الحساب العكسي (Reverse Calculation)
# الربح المستهدف
target_profit_amount = total_project_cost * (target_margin / 100)
# إجمالي المبيعات المطلوبة
required_revenue = total_project_cost + target_profit_amount
# سعر بيع المتر المطلوب (للوصول للهدف)
required_sell_sqm = required_revenue / land_area 

# ========================================================
# 📑 الشاشة الرئيسية
# ========================================================
st.title(f"استراتيجية تسعير المباني: {selected_dist}")

tab1, tab2, tab3, tab4 = st.tabs(["1️⃣ تحليل سعر السوق", "2️⃣ استراتيجية التسعير", "3️⃣ الملاءة المالية", "4️⃣ فحص البيانات"])

# --- الشريحة 1: تحليل سعر السوق (التركيز على المباني) ---
with tab1:
    st.markdown("### 🏠 ماذا يقول السوق عن أسعار المباني؟")
    
    col_kpi, col_chart = st.columns([1, 2])
    
    with col_kpi:
        st.info(f"دقة البيانات: **{build_conf}** ({build_count} صفقة مباني)")
        if clean_build > 0:
            st.metric("متوسط سعر السوق (شامل)", f"{clean_build:,.0f} ريال/م", help="سعر المتر المسطح للفيلا الجاهزة شامل الأرض")
            st.write("---")
            st.write(f"🟢 **أقل سعر بيع:** {min_build:,.0f} ريال")
            st.write(f"🔴 **أعلى سعر بيع:** {max_build:,.0f} ريال")
        else:
            st.warning("لا توجد بيانات مباني كافية في هذا الحي.")

    with col_chart:
        if not builds_raw.empty:
            st.markdown("#### 📊 توزيع أسعار المباني في الحي")
            # رسم بياني للصفقات
            chart_data = builds_raw[(builds_raw['سعر_المتر'] > 1000) & (builds_raw['سعر_المتر'] < 20000)]
            st.scatter_chart(chart_data, x='المساحة', y='سعر_المتر', color='Source_Type', size='سعر_المتر')
            st.caption("كل نقطة تمثل صفقة بيع فيلا/مبنى في الحي.")

# --- الشريحة 2: استراتيجية التسعير (القلب النابض) ---
with tab2:
    st.markdown(f"### 🎯 لكي تحقق ربح {target_margin}%، هذا هو سعرك:")
    
    c1, c2 = st.columns(2)
    with c1:
        st.markdown(f"""
        <div style="background-color:#f0f2f6; padding:20px; border-radius:10px; text-align:center;">
            <div style="color:#7f8c8d; font-size:18px;">سعر البيع المطلوب للمتر</div>
            <div class="price-target">{required_sell_sqm:,.0f} ريال</div>
            <div style="color:#27ae60; font-weight:bold; margin-top:10px;">
                قيمة الفيلا كاملة: {required_revenue:,.0f} ريال
            </div>
        </div>
        """, unsafe_allow_html=True)
    
    with c2:
        # مقارنة مع السوق
        if clean_build > 0:
            diff = required_sell_sqm - clean_build
            diff_pct = (diff / clean_build) * 100
            
            if required_sell_sqm > max_build:
                st.error(f"⛔ **خطر جداً:** سعرك المستهدف ({required_sell_sqm:,.0f}) أعلى من أغلى فيلا بيعت في الحي ({max_build:,.0f})!")
                st.markdown("💡 **نصيحة:** قلل تكاليف الأرض أو البناء، أو اقبل بهامش ربح أقل.")
            elif required_sell_sqm > clean_build:
                st.warning(f"⚠️ **مرتفع:** سعرك أعلى من متوسط السوق بـ {diff_pct:.1f}%. تحتاج لتشطيب فاخر لتبرير السعر.")
            else:
                st.success(f"✅ **ممتاز:** سعرك المستهدف منافس جداً (أقل من السوق بـ {abs(diff_pct):.1f}%).")
        else:
            st.info("لا يمكن التقييم لعدم وجود بيانات سوقية.")

    st.markdown("---")
    
    # تحليل نقطة التعادل
    breakeven = total_project_cost / land_area
    st.markdown(f"**🛡️ نقطة التعادل (رأس المال فقط):** {breakeven:,.0f} ريال للمتر (أي بيع فوق هذا الرقم هو ربح).")

# --- الشريحة 3: الملاءة المالية ---
with tab3:
    st.markdown("#### 🧾 هيكل التكاليف")
    cost_df = pd.DataFrame([
        {"البند": "قيمة الأرض (مع الضريبة والسعي)", "التكلفة": land_base * 1.075},
        {"البند": "تكلفة البناء والتطوير", "التكلفة": (exec_cost + admin_fees)},
        {"البند": "إجمالي رأس المال", "التكلفة": total_project_cost},
        {"البند": "الربح المستهدف", "التكلفة": target_profit_amount}
    ])
    st.dataframe(cost_df.style.format({"التكلفة": "{:,.0f}"}), use_container_width=True)
    
    st.progress(target_margin / 100)
    st.caption(f"هامش الربح المستهدف: {target_margin}%")

# --- الشريحة 4: فحص البيانات ---
with tab4:
    st.header("🔍 صفقات المباني المستخدمة")
    st.markdown("تأكد أن هذه الصفقات تمثل فلل مشابهة لمشروعك:")
    if not builds_raw.empty:
        st.dataframe(builds_raw[['الحي', 'المساحة', 'السعر', 'سعر_المتر', 'نوع_العقار']].sort_values('سعر_المتر'), use_container_width=True)
    else:
        st.warning("لا توجد صفقات مباني.")
