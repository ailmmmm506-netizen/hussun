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
    
    # 1. زر التحديث
    if st.button("🔄 تحديث البيانات", use_container_width=True):
        st.cache_data.clear()
        for key in list(st.session_state.keys()): del st.session_state[key]
        st.rerun()
    
    st.divider()

    if df.empty:
        st.warning("بانتظار البيانات...")
        st.stop()

    # 2. تحديد الموقع (الذكاء في الرابط)
    st.subheader("1️⃣ الموقع والأرض")
    
    districts_list = sorted(df['الحي'].unique()) if 'الحي' in df.columns else []
    
    # ميزة الرابط الذكي
    location_input = st.text_input("🔗 رابط أو اسم الحي (بحث ذكي)", placeholder="الصق رابط جوجل ماب هنا...")
    
    default_ix = 0
    if location_input:
        # البحث عن اسم الحي داخل النص المدخل
        for i, d in enumerate(districts_list):
            if d in location_input: 
                default_ix = i
                st.toast(f"✅ تم اكتشاف الحي: {d}", icon="📍")
                break
    
    selected_dist = st.selectbox("📍 اختر الحي", districts_list, index=default_ix)
    
    c_s1, c_s2 = st.columns(2)
    with c_s1: land_area = st.number_input("المساحة (م²)", value=375)
    with c_s2: offer_price = st.number_input("سعر المتر", value=3500)

    st.divider()

    # 3. تكاليف التطوير
    st.subheader("2️⃣ تكاليف البناء")
    build_cost_sqm = st.number_input("تلفة البناء/م (تسليم مفتاح)", value=1750, step=50)
    build_ratio = st.slider("نسبة البناء (%)", 1.0, 3.5, 2.3)
    fees_pct = st.number_input("رسوم إشراف وإدارة (%)", value=8.0)

    st.divider()

    # 4. تقرير سحب البيانات (في الأسفل كما طلبت)
    with st.expander("📂 تقرير سحب البيانات (السجل)"):
        if 'Source_File' in df.columns:
            stats = df['Source_File'].value_counts().reset_index()
            stats.columns = ['اسم الملف', 'العدد']
            st.dataframe(stats, hide_index=True, use_container_width=True)
            st.caption(f"الإجمالي: {len(df)} صفقة")
        else:
            st.info("لا توجد تفاصيل.")

# ========================================================
# 🏭 المعالجة (في الخلفية)
# ========================================================
# فلترة البيانات
lands_raw = df[(df['الحي'] == selected_dist) & (df['نوع_العقار'].str.contains('أرض', na=False))]
builds_raw = df[(df['الحي'] == selected_dist) & (df['نوع_العقار'].str.contains('مبني', na=False))]
clean_land, _, _ = get_clean_stats(lands_raw)
clean_build, _, _ = get_clean_stats(builds_raw)

# حساب التكاليف
land_base = land_area * offer_price
land_fees = land_base * 0.075 # 5% ضريبة + 2.5% سعي
build_area = land_area * build_ratio
exec_cost = build_area * build_cost_sqm
admin_fees = exec_cost * (fees_pct / 100)
total_project_cost = land_base + land_fees + exec_cost + admin_fees

# ========================================================
# 📑 الشاشة الرئيسية (Tabs)
# ========================================================
st.title(f"تحليل مشروع: حي {selected_dist}")

tab1, tab2, tab3, tab4 = st.tabs([
    "1️⃣ السوق والموقع", 
    "2️⃣ جدول التكاليف", 
    "3️⃣ تحليل المخاطر", 
    "4️⃣ ملخص المستثمر"
])

# --------------------------------------------------------
# الشريحة 1
# --------------------------------------------------------
with tab1:
    col_map, col_data = st.columns([1, 2])
    
    with col_map:
        st.markdown("##### 🗺️ الموقع التقريبي")
        map_url = f"https://www.google.com/maps/search/?api=1&query={selected_dist}+الرياض"
        st.markdown(f"""
            <a href="{map_url}" target="_blank">
                <div style="background-color:#f0f2f6; padding:20px; border-radius:10px; text-align:center; cursor:pointer;">
                    <img src="https://upload.wikimedia.org/wikipedia/commons/thumb/a/aa/Google_Maps_icon_%282020%29.svg/100px-Google_Maps_icon_%282020%29.svg.png" width="50"><br><br>
                    <b>اضغط هنا لفتح {selected_dist} في خرائط جوجل</b>
                </div>
            </a>
        """, unsafe_allow_html=True)
        
    with col_data:
        st.markdown("##### 📊 ترمومتر الأسعار (بيانات مدققة)")
        m1, m2 = st.columns(2)
        with m1:
            st.markdown("#### 🟫 الأراضي")
            if clean_land > 0:
                st.metric("متوسط السوق", f"{clean_land:,.0f} ريال", delta=f"{clean_land - offer_price:,.0f} الفارق")
                diff = ((offer_price - clean_land)/clean_land)*100
                if diff < -5: st.success(f"✅ فرصة! أرخص من السوق بـ {abs(diff):.1f}%")
                elif diff > 5: st.error(f"❌ غالية! أغلى من السوق بـ {diff:.1f}%")
                else: st.warning("⚖️ سعر عادل")
            else: st.info("بيانات غير كافية")
            
        with m2:
            st.markdown("#### 🏠 المباني (بيع)")
            if clean_build > 0:
                st.metric("متوسط سعر المتر (شامل)", f"{clean_build:,.0f} ريال")
                st.caption("يستخدم هذا الرقم لتقدير المبيعات")
            else: st.info("بيانات غير كافية")

# --------------------------------------------------------
# الشريحة 2
# --------------------------------------------------------
with tab2:
    st.markdown("#### 🧾 القوائم المالية التقديرية")
    
    cost_df = pd.DataFrame([
        {"البند": "قيمة الأرض", "التكلفة": land_base, "التفاصيل": f"{land_area}م² × {offer_price}"},
        {"البند": "ضريبة وسعي (7.5%)", "التكلفة": land_fees, "التفاصيل": "رسوم حكومية + وساطة"},
        {"البند": "تكاليف البناء", "التكلفة": exec_cost, "التفاصيل": f"مسطحات {build_area:.0f}م²"},
        {"البند": "إشراف وإدارة", "التكلفة": admin_fees, "التفاصيل": f"{fees_pct}% من البناء"},
        {"البند": "✨ الإجمالي", "التكلفة": total_project_cost, "التفاصيل": "رأس المال العامل"}
    ])
    
    st.dataframe(cost_df.style.format({"التكلفة": "{:,.0f}"}), use_container_width=True)
    
    # رسم بياني بسيط للتكاليف
    st.markdown("##### توزيع التكاليف")
    chart_data = pd.DataFrame({
        'التكلفة': [land_base+land_fees, exec_cost+admin_fees],
        'النوع': ['الأرض والرسوم', 'البناء والتطوير']
    }).set_index('النوع')
    st.bar_chart(chart_data, horizontal=True)

# --------------------------------------------------------
# الشريحة 3
# --------------------------------------------------------
with tab3:
    st.markdown("#### 📉 تحليل المخاطر والتمويل")
    
    r1, r2 = st.columns(2)
    with r1: duration = st.number_input("مدة المشروع (شهر)", value=14)
    with r2: fin_rate = st.number_input("نسبة الفائدة/التمويل (%)", value=0.0)
    
    fin_cost = total_project_cost * (fin_rate/100) * (duration/12)
    grand_total_risk = total_project_cost + fin_cost
    
    st.info(f"💰 تكلفة التمويل/الفرصة البديلة: **{fin_cost:,.0f} ريال** (تضاف للتكلفة الإجمالية)")
    
    if clean_build > 0:
        expected_revenue = land_area * clean_build
        
        st.markdown("##### 🎲 مصفوفة الحساسية (العائد ROI)")
        st.caption("كيف يتأثر الربح بتغير تكلفة البناء (أعمدة) وسعر البيع (صفوف)")
        
        p_changes = [-0.1, -0.05, 0, 0.05, 0.1]
        c_changes = [-0.1, -0.05, 0, 0.05, 0.1]
        
        matrix = []
        for p in p_changes:
            row = []
            sell = expected_revenue * (1 + p)
            for c in c_changes:
                build_c_new = (exec_cost + admin_fees) * (1 + c)
                total_c_new = land_base + land_fees + build_c_new + fin_cost
                profit = sell - total_c_new
                roi = (profit/total_c_new)*100
                row.append(roi)
            matrix.append(row)
            
        df_risk = pd.DataFrame(matrix, index=[f"بيع {x:+.0%}" for x in p_changes], columns=[f"بناء {x:+.0%}" for x in c_changes])
        st.dataframe(df_risk.style.background_gradient(cmap="RdYlGn", vmin=0, vmax=30).format("{:.1f}%"), use_container_width=True)
    else:
        st.warning("يجب توفر بيانات مباني لحساب المخاطر.")

# --------------------------------------------------------
# الشريحة 4
# --------------------------------------------------------
with tab4:
    if clean_build > 0:
        # النتائج النهائية
        expected_revenue = land_area * clean_build
        net_profit = expected_revenue - grand_total_risk
        roi_final = (net_profit / grand_total_risk) * 100
        
        color = "#27ae60" if roi_final > 15 else "#f39c12" if roi_final > 0 else "#c0392b"
        rec_text = "فرصة استثمارية مميزة" if roi_final > 15 else "فرصة مقبولة" if roi_final > 0 else "غير مجدية حالياً"
        
        st.markdown(f"""
        <div class="investor-card" style="border-top-color: {color};">
            <h2 style="color:{color};">{rec_text}</h2>
            <p>دراسة جدوى لتطوير فيلا في حي <b>{selected_dist}</b></p>
            <hr>
            <div style="display: flex; justify-content: space-around; margin-top: 20px;">
                <div>
                    <div class="stat-label">رأس المال (شامل التمويل)</div>
                    <div class="big-stat">{grand_total_risk:,.0f} ريال</div>
                </div>
                <div>
                    <div class="stat-label">الإيراد المتوقع</div>
                    <div class="big-stat">{expected_revenue:,.0f} ريال</div>
                </div>
            </div>
            <div style="display: flex; justify-content: space-around; margin-top: 20px;">
                <div>
                    <div class="stat-label">صافي الربح</div>
                    <div class="big-stat" style="color:{color};">{net_profit:,.0f} ريال</div>
                </div>
                <div>
                    <div class="stat-label">العائد (ROI)</div>
                    <div class="big-stat" style="color:{color};">{roi_final:.1f}%</div>
                </div>
            </div>
            <br>
            <div style="background:#f9f9f9; padding:10px; border-radius:5px; font-size:14px;">
                تم البناء على بيانات سوقية لـ <b>{len(builds_raw)}</b> صفقة مشابهة في الحي.
            </div>
        </div>
        """, unsafe_allow_html=True)
    else:
        st.error("لا يمكن بناء البطاقة لعدم توفر بيانات البيع.")
