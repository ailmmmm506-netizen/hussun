import streamlit as st
import pandas as pd
import data_bot

st.set_page_config(page_title="المطور العقاري الذكي", layout="wide", page_icon="🏢")

# تنسيق
st.markdown("""
<style>
    .market-card { background-color: #ffffff; padding: 15px; border-radius: 10px; border-top: 5px solid #3498db; box-shadow: 0 2px 5px rgba(0,0,0,0.05); text-align: center; margin-bottom: 10px; }
    .market-card h3 { font-size: 16px; color: #7f8c8d; margin-bottom: 5px; }
    .market-card h2 { font-size: 24px; font-weight: bold; color: #2c3e50; margin: 0; }
    [data-testid="stSidebar"] { background-color: #f8f9fa; border-left: 1px solid #ddd; }
</style>
""", unsafe_allow_html=True)

# دالة المتوسطات (بسيطة ومباشرة الآن)
def get_avg(df):
    if df.empty: return 0, 0
    # استبعاد القيم الشاذة المتطرفة جداً
    clean = df[(df['سعر_المتر'] > 100) & (df['سعر_المتر'] < 200000)]
    if clean.empty: return 0, 0
    return clean['سعر_المتر'].median(), len(clean)

# الاتصال
@st.cache_resource(show_spinner="جاري المعالجة...", ttl=3600)
def load_bot():
    return data_bot.RealEstateBot()

if 'bot' not in st.session_state: st.session_state.bot = load_bot()
df = st.session_state.bot.df if hasattr(st.session_state.bot, 'df') else pd.DataFrame()

# ==========================================
# القائمة الجانبية
# ==========================================
with st.sidebar:
    st.title("القائمة الرئيسية")
    app_mode = st.radio("القسم:", ["📊 لوحة البيانات", "🏗️ حاسبة التكاليف"])
    st.divider()
    
    if st.button("🔄 تحديث"):
        st.cache_data.clear()
        st.cache_resource.clear()
        st.rerun()

# ==========================================
# 📊 لوحة البيانات
# ==========================================
if app_mode == "📊 لوحة البيانات":
    if df.empty:
        st.warning("لا توجد بيانات. تأكد من الملفات.")
        st.stop()

    districts = sorted(df['الحي'].unique())
    selected_dist = st.sidebar.selectbox("الحي:", ["الكل"] + districts)
    
    filtered_df = df if selected_dist == "الكل" else df[df['الحي'] == selected_dist]
    
    st.title(f"سجل البيانات: {selected_dist}")
    
    # تبويبات العرض
    tab1, tab2 = st.tabs(["💰 الصفقات (Sold)", "🏷️ العروض (Ask)"])
    
    with tab1:
        st.caption("أنواع العقارات هنا: أرض / مبني فقط")
        sold_data = filtered_df[filtered_df['Data_Category'].str.contains('Sold')]
        st.dataframe(sold_data, use_container_width=True)
        
    with tab2:
        st.caption("أنواع العقارات هنا: شقة / فيلا / دور / أرض")
        ask_data = filtered_df[filtered_df['Data_Category'].str.contains('Ask')]
        st.dataframe(ask_data, use_container_width=True)

# ==========================================
# 🏗️ حاسبة التكاليف + مسح السوق
# ==========================================
elif app_mode == "🏗️ حاسبة التكاليف":
    st.title("🏗️ حاسبة التكاليف ومسح السوق")
    
    # 1. إعدادات الموقع
    districts = sorted(df['الحي'].unique())
    calc_dist = st.sidebar.selectbox("اختر الحي للتحليل:", districts)
    
    # 2. مدخلات التكلفة (مختصرة للعرض، الكود الكامل عندك)
    land_area = st.sidebar.number_input("مساحة الأرض", 375)
    land_price = st.sidebar.number_input("سعر المتر", 3500)
    build_ratio = st.sidebar.slider("معامل البناء", 1.0, 3.5, 2.3)
    turnkey_price = st.sidebar.number_input("تكلفة البناء", 1800)
    
    # حساب سريع للتكلفة
    bua = land_area * build_ratio
    total_cost = (land_area * land_price * 1.075) + (bua * turnkey_price * 1.1) # تقريبي شامل
    cost_sqm = total_cost / bua
    
    st.info(f"💰 تكلفتك التقديرية للمتر (شامل الأرض والبناء): **{cost_sqm:,.0f} ريال**")

    # ==========================================
    # 🧠 مسح السوق (Scanner) - المنطق الجديد
    # ==========================================
    st.divider()
    st.header(f"📊 متوسطات أسعار العروض في {calc_dist}")
    
    # نفلتر على الحي + نوع الملف "عروض" فقط
    market_df = df[(df['الحي'] == calc_dist) & (df['Data_Category'].str.contains('Ask'))]
    
    if market_df.empty:
        st.warning(f"لا توجد عروض بيع مسجلة لحي {calc_dist}")
    else:
        # 1. الفلل
        villas = market_df[market_df['نوع_العقار'] == 'فيلا']
        avg_villa, cnt_villa = get_avg(villas)
        
        # 2. الشقق
        apts = market_df[market_df['نوع_العقار'] == 'شقة']
        avg_apt, cnt_apt = get_avg(apts)
        
        # 3. الأدوار
        floors = market_df[market_df['نوع_العقار'] == 'دور']
        avg_floor, cnt_floor = get_avg(floors)
        
        # 4. الأراضي (عروض)
        lands = market_df[market_df['نوع_العقار'] == 'أرض']
        avg_land, cnt_land = get_avg(lands)

        # 5. المتوسط العام (لكل العروض ما عدا الأراضي لأنها تشوه متوسط المبني)
        all_built = market_df[market_df['نوع_العقار'] != 'أرض']
        avg_all, cnt_all = get_avg(all_built)

        # عرض الكروت
        c1, c2, c3, c4 = st.columns(4)
        
        with c1:
            st.markdown(f"""
            <div class="market-card">
                <h3>🏠 متوسط الفلل</h3>
                <h2>{avg_villa:,.0f}</h2>
                <small>عدد: {cnt_villa}</small>
            </div>
            """, unsafe_allow_html=True)
            if cnt_villa > 0: st.dataframe(villas[['السعر', 'المساحة', 'سعر_المتر', 'Source_File']], height=100)

        with c2:
            st.markdown(f"""
            <div class="market-card">
                <h3>🏢 متوسط الشقق</h3>
                <h2>{avg_apt:,.0f}</h2>
                <small>عدد: {cnt_apt}</small>
            </div>
            """, unsafe_allow_html=True)
            if cnt_apt > 0: st.dataframe(apts[['السعر', 'المساحة', 'سعر_المتر', 'Source_File']], height=100)

        with c3:
            st.markdown(f"""
            <div class="market-card">
                <h3>🏘️ متوسط الأدوار</h3>
                <h2>{avg_floor:,.0f}</h2>
                <small>عدد: {cnt_floor}</small>
            </div>
            """, unsafe_allow_html=True)
            if cnt_floor > 0: st.dataframe(floors[['السعر', 'المساحة', 'سعر_المتر', 'Source_File']], height=100)

        with c4:
            st.markdown(f"""
            <div class="market-card" style="border-top-color: #f1c40f;">
                <h3>📈 متوسط (مبني) عام</h3>
                <h2>{avg_all:,.0f}</h2>
                <small>عدد: {cnt_all}</small>
            </div>
            """, unsafe_allow_html=True)
            
        # مقارنة سريعة
        st.divider()
        if avg_apt > 0:
            diff = ((avg_apt - cost_sqm) / cost_sqm) * 100
            st.metric("الربح المتوقع (مقارنة بالشقق)", f"{diff:.1f}%", delta_color="normal")
        else:
            st.info("لا توجد بيانات شقق للمقارنة")
