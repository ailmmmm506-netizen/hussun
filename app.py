import streamlit as st
import pandas as pd
import data_bot  # المحرك الذكي

# إعداد الصفحة
st.set_page_config(page_title="المطور العقاري الذكي", layout="wide", page_icon="🏢")

# --- التنسيق الجمالي ---
st.markdown("""
<style>
    .market-card { 
        background-color: #ffffff; 
        padding: 15px; 
        border-radius: 12px; 
        border-top: 5px solid #3498db; 
        box-shadow: 0 4px 6px rgba(0,0,0,0.05); 
        text-align: center; 
        height: 100%;
    }
    .market-card h3 { font-size: 16px; color: #7f8c8d; margin-bottom: 5px; font-weight: bold; }
    .market-card h2 { font-size: 26px; font-weight: bold; color: #2c3e50; margin: 0; }
    .market-card small { font-size: 13px; color: #95a5a6; display: block; margin-top: 5px; }
    [data-testid="stSidebar"] { background-color: #f8f9fa; border-left: 1px solid #ddd; }
    .stProgress > div > div > div > div { background-color: #2ecc71; }
</style>
""", unsafe_allow_html=True)

# --- دالة إحصائية دقيقة ---
def calculate_metrics(df_subset):
    if df_subset.empty: return 0, 0
    # تنظيف الأسعار
    df_clean = df_subset.copy()
    df_clean['سعر_المتر'] = pd.to_numeric(df_clean['سعر_المتر'], errors='coerce')
    # استبعاد القيم الشاذة (أقل من 500 أو أعلى من 150 ألف)
    df_clean = df_clean[(df_clean['سعر_المتر'] > 500) & (df_clean['سعر_المتر'] < 150000)]
    
    if df_clean.empty: return 0, 0
    return df_clean['سعر_المتر'].median(), len(df_clean)

# --- تحميل البيانات ---
@st.cache_resource(show_spinner="جاري تحليل السوق...", ttl=3600)
def load_data():
    return data_bot.RealEstateBot()

if 'bot' not in st.session_state: st.session_state.bot = load_data()
df = st.session_state.bot.df if hasattr(st.session_state.bot, 'df') else pd.DataFrame()

# ==========================================
# القائمة الجانبية
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
# 📊 لوحة البيانات
# ==========================================
if app_mode == "📊 لوحة البيانات (Dashboard)":
    if df.empty:
        st.error("لا توجد بيانات متاحة.")
        st.stop()

    districts = sorted(df['الحي'].astype(str).unique())
    selected_dist = st.sidebar.selectbox("تصفية حسب الحي:", ["الكل"] + districts)
    
    view_df = df if selected_dist == "الكل" else df[df['الحي'] == selected_dist]
    
    st.title(f"سجل البيانات: {selected_dist}")
    
    # تبويبات
    tab1, tab2 = st.tabs(["💰 الصفقات (Sold)", "🏷️ العروض (Ask)"])
    
    cols = ['Source_File', 'الحي', 'السعر', 'المساحة', 'سعر_المتر', 'نوع_العقار']
    
    with tab1:
        sold = view_df[view_df['Data_Category'].str.contains('Sold', na=False)]
        st.dataframe(sold[cols] if not sold.empty else pd.DataFrame(), use_container_width=True)
        
    with tab2:
        ask = view_df[view_df['Data_Category'].str.contains('Ask', na=False)]
        st.dataframe(ask[cols] if not ask.empty else pd.DataFrame(), use_container_width=True)

# ==========================================
# 🏗️ حاسبة التكاليف + مسح السوق الدقيق
# ==========================================
elif app_mode == "🏗️ حاسبة التكاليف (Calculator)":
    
    st.title("🏗️ حاسبة التكاليف ومسح السوق")
    
    # --- المدخلات ---
    with st.sidebar:
        st.header("1️⃣ إعدادات الموقع")
        dist_list = sorted(df['الحي'].astype(str).unique()) if not df.empty else []
        calc_dist = st.selectbox("اختر الحي للتحليل:", dist_list)
        
        st.header("2️⃣ تكاليف المشروع")
        land_area = st.number_input("مساحة الأرض", 375)
        land_price = st.number_input("سعر المتر", 3500)
        build_ratio = st.slider("معامل البناء", 1.0, 3.5, 2.3)
        turnkey_price = st.number_input("تكلفة البناء", 1800)
        
        # حساب التكلفة المبدئية للمقارنة
        bua = land_area * build_ratio
        total_project_cost = (land_area * land_price * 1.075) + (bua * turnkey_price * 1.1)
        my_cost_sqm = total_project_cost / bua
        
        st.success(f"تكلفتك التقريبية للمتر: **{my_cost_sqm:,.0f} ريال**")

    # ==========================================
    # 🧠 مسح السوق (The Precision Fix)
    # ==========================================
    st.divider()
    st.header(f"📊 مسح أسعار العروض في حي {calc_dist}")
    
    # 1. عزل بيانات الحي والعروض فقط
    market_df = df[(df['الحي'] == calc_dist) & (df['Data_Category'].str.contains('Ask', na=False))].copy()
    
    if market_df.empty:
        st.warning(f"لا توجد عروض بيع مسجلة لحي {calc_dist}")
    else:
        # 2. تنظيف عمود النوع لضمان التطابق
        market_df['نوع_العقار'] = market_df['نوع_العقار'].astype(str).str.strip()
        
        # 3. فصل البيانات يدوياً للتأكد 100%
        # هنا الكود يجبر البيانات على الانفصال
        df_villas = market_df[market_df['نوع_العقار'] == 'فيلا']
        df_apts   = market_df[market_df['نوع_العقار'] == 'شقة']
        df_floors = market_df[market_df['نوع_العقار'] == 'دور']
        
        # 4. حساب المتوسطات
        avg_villa, n_villa = calculate_metrics(df_villas)
        avg_apt, n_apt     = calculate_metrics(df_apts)
        avg_floor, n_floor = calculate_metrics(df_floors)
        avg_all, n_all     = calculate_metrics(market_df[market_df['نوع_العقار'] != 'أرض'])

        # 5. عرض الكروت (بدون خلط)
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            st.markdown(f"""
            <div class="market-card">
                <h3>🏠 متوسط الفلل</h3>
                <h2>{avg_villa:,.0f}</h2>
                <small>عدد العروض: {n_villa}</small>
            </div>
            """, unsafe_allow_html=True)
            # عرض بيانات الفلل فقط للتأكد
            if n_villa > 0:
                with st.expander("بيانات الفلل"):
                    st.dataframe(df_villas[['السعر', 'المساحة', 'سعر_المتر', 'Source_File']], use_container_width=True)

        with col2:
            st.markdown(f"""
            <div class="market-card">
                <h3>🏢 متوسط الشقق</h3>
                <h2>{avg_apt:,.0f}</h2>
                <small>عدد العروض: {n_apt}</small>
            </div>
            """, unsafe_allow_html=True)
            # عرض بيانات الشقق فقط للتأكد
            if n_apt > 0:
                with st.expander("بيانات الشقق"):
                    st.dataframe(df_apts[['السعر', 'المساحة', 'سعر_المتر', 'Source_File']], use_container_width=True)
            else:
                st.caption("⚠️ لم يتم العثور على عقارات مصنفة كـ 'شقة'")

        with col3:
            st.markdown(f"""
            <div class="market-card">
                <h3>🏘️ متوسط الأدوار</h3>
                <h2>{avg_floor:,.0f}</h2>
                <small>عدد العروض: {n_floor}</small>
            </div>
            """, unsafe_allow_html=True)
            if n_floor > 0:
                with st.expander("بيانات الأدوار"):
                    st.dataframe(df_floors[['السعر', 'المساحة', 'سعر_المتر', 'Source_File']], use_container_width=True)

        with col4:
            st.markdown(f"""
            <div class="market-card" style="border-top-color: #f1c40f;">
                <h3>📈 المتوسط العام</h3>
                <h2>{avg_all:,.0f}</h2>
                <small>إجمالي العروض: {n_all}</small>
            </div>
            """, unsafe_allow_html=True)

        # 6. المقارنة والتحليل
        st.divider()
        st.subheader("💡 الجدوى الاقتصادية")
        
        def show_profit(label, market_avg):
            if market_avg > 0:
                margin = ((market_avg - my_cost_sqm) / my_cost_sqm) * 100
                st.write(f"**الربح المتوقع في {label}:**")
                st.progress(min(max((margin + 50)/100, 0.0), 1.0))
                st.caption(f"💰 الهامش: **{margin:.1f}%** (بيع السوق: {market_avg:,.0f})")
            else:
                st.info(f"لا توجد بيانات كافية لـ {label}")

        c1, c2 = st.columns(2)
        with c1:
            show_profit("الشقق 🏢", avg_apt)
            show_profit("الأدوار 🏘️", avg_floor)
        with c2:
            show_profit("الفلل 🏠", avg_villa)
