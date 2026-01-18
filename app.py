import streamlit as st
import pandas as pd
import numpy as np
import data_bot  # المحرك

# إعداد الصفحة
st.set_page_config(page_title="دراسة الجدوى العقارية", layout="wide", page_icon="🏢")

# --- التنسيق الجمالي (CSS) ---
st.markdown("""
<style>
    .investor-card {
        background-color: #ffffff;
        border: 2px solid #1f77b4;
        border-radius: 15px;
        padding: 30px;
        box-shadow: 0 4px 8px rgba(0,0,0,0.1);
        text-align: center;
    }
    .card-title {
        color: #1f77b4;
        font-size: 28px;
        font-weight: bold;
        margin-bottom: 20px;
        border-bottom: 2px solid #eee;
        padding-bottom: 10px;
    }
    .big-stat {
        font-size: 32px;
        font-weight: bold;
        color: #2c3e50;
    }
    .stat-label {
        font-size: 16px;
        color: #7f8c8d;
    }
    .highlight-green { color: #27ae60; font-weight: bold; }
    .highlight-red { color: #c0392b; font-weight: bold; }
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
    with st.spinner("جاري الاتصال بقاعدة البيانات..."):
        try: st.session_state.bot = data_bot.RealEstateBot()
        except: st.error("خطأ في الاتصال")

df = st.session_state.bot.df if hasattr(st.session_state.bot, 'df') else pd.DataFrame()

# ========================================================
# 🟢 القائمة الجانبية (إدخال البيانات الأساسية)
# ========================================================
with st.sidebar:
    st.image("https://cdn-icons-png.flaticon.com/512/2642/2642226.png", width=60)
    st.header("بيانات المشروع الأساسية")
    
    if st.button("🔄 تحديث البيانات", type="primary"):
        st.cache_data.clear()
        for key in list(st.session_state.keys()): del st.session_state[key]
        st.rerun()

    if df.empty:
        st.warning("الرجاء انتظار البيانات...")
        st.stop()

    # المدخلات العامة (Global Inputs)
    districts = sorted(df['الحي'].unique()) if 'الحي' in df.columns else []
    selected_dist = st.selectbox("📍 الحي", districts)
    
    st.divider()
    land_area = st.number_input("📐 المساحة (م²)", value=375)
    offer_price = st.number_input("💰 سعر شراء الأرض (للمتر)", value=3500)

# ========================================================
# 🏭 المعالجة المركزية (تجهيز الأرقام لكل الشرائح)
# ========================================================
# 1. بيانات السوق
lands_raw = df[(df['الحي'] == selected_dist) & (df['نوع_العقار'].str.contains('أرض', na=False))]
builds_raw = df[(df['الحي'] == selected_dist) & (df['نوع_العقار'].str.contains('مبني', na=False))]
clean_land, _, _ = get_clean_stats(lands_raw)
clean_build, _, _ = get_clean_stats(builds_raw)

# ========================================================
# 📑 تقسيم الشاشة إلى 4 شرائح (Tabs)
# ========================================================
tab1, tab2, tab3, tab4 = st.tabs([
    "1️⃣ الموقع والسوق", 
    "2️⃣ تكاليف التطوير", 
    "3️⃣ تحليل المخاطر", 
    "4️⃣ ملخص المستثمر (النهاية)"
])

# --------------------------------------------------------
# الشريحة 1: الموقع وتحليل السوق
# --------------------------------------------------------
with tab1:
    st.header(f"📍 تحليل الموقع: حي {selected_dist}")
    
    col_map, col_stats = st.columns([1, 2])
    
    with col_map:
        st.info("🗺️ الموقع الجغرافي")
        # رابط ديناميكي لخرائط جوجل
        map_url = f"https://www.google.com/maps/search/?api=1&query=حي+{selected_dist}+الرياض"
        st.markdown(f"[![Open in Maps](https://upload.wikimedia.org/wikipedia/commons/thumb/a/aa/Google_Maps_icon_%282020%29.svg/100px-Google_Maps_icon_%282020%29.svg.png)]({map_url})")
        st.caption("اضغط الأيقونة لفتح الحي في خرائط Google")

    with col_stats:
        st.subheader("📊 مؤشرات أسعار السوق (المدققة)")
        
        m1, m2 = st.columns(2)
        with m1:
            st.markdown("#### 🟫 الأراضي")
            if clean_land > 0:
                st.metric("متوسط سعر المتر", f"{clean_land:,.0f} ريال")
                diff = ((offer_price - clean_land)/clean_land)*100
                if diff < 0: st.success(f"سعرنا أقل من السوق بـ {abs(diff):.1f}%")
                else: st.error(f"سعرنا أعلى من السوق بـ {diff:.1f}%")
            else: st.warning("بيانات غير كافية")
            
        with m2:
            st.markdown("#### 🏠 المباني (للمتر المسطح)")
            if clean_build > 0:
                st.metric("متوسط سعر البيع (شامل)", f"{clean_build:,.0f} ريال")
            else: st.warning("بيانات غير كافية")

# --------------------------------------------------------
# الشريحة 2: تكاليف البناء والتطوير
# --------------------------------------------------------
with tab2:
    st.header("🏗️ تفاصيل التكاليف")
    
    c_in1, c_in2, c_in3 = st.columns(3)
    with c_in1:
        build_ratio = st.number_input("نسبة البناء (%)", 1.0, 3.5, 2.3, step=0.1)
    with c_in2:
        cost_sqm = st.number_input("تكلفة التنفيذ للمتر (تسليم مفتاح)", value=1750)
    with c_in3:
        fees_pct = st.number_input("إدارية، إشراف، ورسوم (%)", value=8.0) # شاملة الضريبة والسعي والادارية

    # الحسابات
    # 1. الأرض
    land_base = land_area * offer_price
    # 2. البناء
    total_build_area = land_area * build_ratio
    exec_cost = total_build_area * cost_sqm
    # 3. الرسوم الشاملة (تحسب كنسبة من اجمالي الأرض والبناء أو حسب مدخلك)
    # هنا سنحسب الرسوم كنسبة من تكلفة البناء + ضريبة الأرض والسعي
    land_tax_broker = land_base * 0.075 # 5% ضريبة + 2.5% سعي
    admin_fees = exec_cost * (fees_pct / 100) # نسبة من تكلفة البناء للإشراف والادارة
    
    total_project_cost = land_base + land_tax_broker + exec_cost + admin_fees

    # العرض
    st.markdown("### 🧾 فاتورة المشروع التقديرية")
    cost_table = pd.DataFrame([
        {"البند": "قيمة الأرض", "التكلفة": land_base, "ملاحظات": f"{land_area}م x {offer_price}"},
        {"البند": "ضريبة وسعي (7.5%)", "التكلفة": land_tax_broker, "ملاحظات": "رسوم الشراء"},
        {"البند": "تكلفة البناء (تسليم مفتاح)", "التكلفة": exec_cost, "ملاحظات": f"مسطحات {total_build_area:.0f}م"},
        {"البند": "رسوم إدارية وإشراف", "التكلفة": admin_fees, "ملاحظات": "مكتب هندسي + خدمات"},
        {"البند": "🔴 الإجمالي الكلي", "التكلفة": total_project_cost, "ملاحظات": "رأس المال المطلوب"}
    ])
    st.dataframe(cost_table.style.format({"التكلفة": "{:,.0f}"}), use_container_width=True)

# --------------------------------------------------------
# الشريحة 3: تحليل المخاطر
# --------------------------------------------------------
with tab3:
    st.header("📉 تحليل المخاطر والحساسية")
    
    r1, r2 = st.columns(2)
    with r1:
        duration = st.number_input("مدة المشروع (أشهر)", value=14)
    with r2:
        finance_rate = st.number_input("نسبة التمويل/الفرصة البديلة (%)", value=0.0)

    # حساب التكلفة التمويلية
    fin_cost = total_project_cost * (finance_rate/100) * (duration/12)
    grand_total_risk = total_project_cost + fin_cost
    
    # الإيراد المتوقع
    expected_rev = land_area * clean_build # السعر الواقعي
    
    if clean_build > 0:
        # مصفوفة الحساسية
        st.subheader("مصفوفة الحساسية (ROI)")
        st.caption("توضح نسبة الربح بناءً على تغير تكلفة البناء (أعمدة) وتغير سعر البيع (صفوف)")
        
        price_changes = [-0.10, -0.05, 0, 0.05, 0.10] # صفوف
        cost_changes = [-0.10, -0.05, 0, 0.05, 0.10]  # أعمدة
        
        res_data = []
        for p in price_changes:
            row = []
            sell_p = expected_rev * (1 + p)
            for c in cost_changes:
                # نغير تكلفة البناء فقط
                build_c = (exec_cost + admin_fees) * (1 + c)
                total_c = land_base + land_tax_broker + build_c + fin_cost
                profit = sell_p - total_c
                roi = (profit/total_c)*100
                row.append(roi)
            res_data.append(row)
            
        df_sens = pd.DataFrame(res_data, 
                               index=[f"بيع {p:+.0%}" for p in price_changes],
                               columns=[f"تكلفة {c:+.0%}" for c in cost_changes])
        
        st.dataframe(df_sens.style.background_gradient(cmap="RdYlGn", vmin=-5, vmax=25).format("{:.1f}%"), use_container_width=True)
    else:
        st.warning("الرجاء توفير بيانات مباني لحساب المخاطر.")

# --------------------------------------------------------
# الشريحة 4: ملخص المستثمر (Executive Summary)
# --------------------------------------------------------
with tab4:
    if clean_build > 0:
        # الحسابات النهائية
        net_profit = expected_rev - grand_total_risk
        roi_final = (net_profit / grand_total_risk) * 100
        
        # تحديد التوصية ولون البطاقة
        status_color = "#27ae60" if roi_final > 15 else "#f39c12" if roi_final > 0 else "#c0392b"
        recommendation = "مشروع واعد ومربح" if roi_final > 15 else "مشروع متوسط المخاطر" if roi_final > 0 else "مشروع عالي المخاطر"

        # تصميم البطاقة (HTML)
        st.markdown(f"""
        <div class="investor-card" style="border-color: {status_color};">
            <div class="card-title">💎 ملخص الفرصة الاستثمارية</div>
            <p style="font-size:20px;">تطوير فيلا سكنية في <b>حي {selected_dist}</b></p>
            
            <table style="width:100%; margin-top:20px; border-collapse: collapse;">
                <tr>
                    <td style="padding:10px; border-bottom:1px solid #eee;">
                        <div class="stat-label">رأس المال المطلوب</div>
                        <div class="big-stat">{grand_total_risk:,.0f} ريال</div>
                    </td>
                    <td style="padding:10px; border-bottom:1px solid #eee;">
                        <div class="stat-label">الإيراد المتوقع</div>
                        <div class="big-stat">{expected_rev:,.0f} ريال</div>
                    </td>
                </tr>
                <tr>
                    <td style="padding:10px;">
                        <div class="stat-label">صافي الربح</div>
                        <div class="big-stat" style="color:{status_color};">{net_profit:,.0f} ريال</div>
                    </td>
                    <td style="padding:10px;">
                        <div class="stat-label">العائد على الاستثمار (ROI)</div>
                        <div class="big-stat" style="color:{status_color};">{roi_final:.1f}%</div>
                    </td>
                </tr>
            </table>
            
            <div style="margin-top:20px; background-color:#f9f9f9; padding:15px; border-radius:10px; text-align:right;">
                <b>📌 التوصية:</b> {recommendation}<br>
                <b>⏳ مدة المشروع:</b> {duration} شهر<br>
                <b>🏗️ مساحة الأرض:</b> {land_area} م²
            </div>
        </div>
        """, unsafe_allow_html=True)
        
        st.caption("💡 نصيحة: يمكنك أخذ لقطة شاشة (Screenshot) لهذه البطاقة ومشاركتها مباشرة مع المستثمرين.")
    else:
        st.error("لا يمكن إصدار ملخص لعدم توفر بيانات مقارنة كافية في الحي.")
