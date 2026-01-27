import streamlit as st
import pandas as pd
import data_bot  # المحرك الذكي

# إعداد الصفحة
st.set_page_config(page_title="المطور العقاري الذكي", layout="wide", page_icon="🏢")

# --- التنسيق الجمالي ---
st.markdown("""
<style>
    .market-card { background-color: #ffffff; padding: 15px; border-radius: 10px; border-top: 5px solid #3498db; margin-bottom: 10px; box-shadow: 0 2px 5px rgba(0,0,0,0.05); text-align: center; }
    .market-card h3 { font-size: 16px; color: #7f8c8d; margin-bottom: 5px; }
    .market-card h2 { font-size: 24px; font-weight: bold; color: #2c3e50; margin: 0; }
    [data-testid="stSidebar"] { background-color: #f8f9fa; border-left: 1px solid #ddd; }
</style>
""", unsafe_allow_html=True)

# --- دالة حساب المتوسط (مع التنظيف) ---
def get_avg_stats(df_input):
    if df_input.empty: return 0, 0, df_input
    
    # 1. التأكد أن سعر المتر رقمي
    df_input = df_input.copy()
    df_input['سعر_المتر'] = pd.to_numeric(df_input['سعر_المتر'], errors='coerce')
    
    # 2. استبعاد القيم الصفرية أو الفارغة
    clean = df_input[df_input['سعر_المتر'] > 100]
    
    if clean.empty: return 0, 0, df_input # البيانات موجودة لكن الأسعار خطأ
    
    # 3. حساب المتوسط (Median) لأنه أدق من Average
    return clean['سعر_المتر'].median(), len(clean), clean

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
    app_mode = st.radio("القسم:", ["📊 لوحة البيانات (Dashboard)", "🏗️ حاسبة التكاليف (Calculator)"])
    st.divider()
    
    if st.button("🔄 تحديث البيانات"):
        st.cache_data.clear()
        st.cache_resource.clear()
        st.rerun()

# ========================================================
# 📊 القسم الأول: الداشبورد
# ========================================================
if app_mode == "📊 لوحة البيانات (Dashboard)":
    if df.empty:
        st.warning("جاري سحب البيانات... يرجى الانتظار")
        st.stop()

    districts = sorted(df['الحي'].astype(str).unique())
    selected_dist = st.sidebar.selectbox("تصفية حسب الحي:", ["الكل"] + districts)
    
    if selected_dist != "الكل": filtered_df = df[df['الحي'] == selected_dist]
    else: filtered_df = df

    st.title(f"سجل البيانات العقارية: {selected_dist}")
    
    # ملخص الملفات
    if 'Source_File' in df.columns:
        with st.expander("📂 المصادر والملفات", expanded=False):
            stats = filtered_df['Source_File'].value_counts().reset_index()
            stats.columns = ['الملف', 'العدد']
            st.dataframe(stats, use_container_width=True)

    tab1, tab2 = st.tabs(["💰 الصفقات (Sold)", "🏷️ العروض (Ask)"])
    
    cols = ['Source_File', 'الحي', 'السعر', 'المساحة', 'سعر_المتر', 'نوع_العقار', 'اسم_المطور']
    valid_cols = [c for c in cols if c in filtered_df.columns]
    
    with tab1:
        data = filtered_df[filtered_df['Data_Category'].astype(str).str.contains('Sold')]
        st.dataframe(data[valid_cols], use_container_width=True)
    with tab2:
        data = filtered_df[filtered_df['Data_Category'].astype(str).str.contains('Ask')]
        st.dataframe(data[valid_cols], use_container_width=True)

# ========================================================
# 🏗️ القسم الثاني: الحاسبة + مسح السوق (The Fix)
# ========================================================
elif app_mode == "🏗️ حاسبة التكاليف (Calculator)":
    
    st.title("🏗️ حاسبة التكاليف ومسح السوق")
    
    # 1. إعدادات الموقع
    districts = sorted(df['الحي'].astype(str).unique())
    calc_dist = st.sidebar.selectbox("اختر الحي للتحليل:", districts)
    
    # 2. مدخلات التكلفة (مختصرة)
    land_area = st.sidebar.number_input("مساحة الأرض", 375)
    land_price = st.sidebar.number_input("سعر المتر", 3500)
    build_ratio = st.sidebar.slider("معامل البناء", 1.0, 3.5, 2.3)
    turnkey_price = st.sidebar.number_input("تكلفة البناء", 1800)
    
    bua = land_area * build_ratio
    total_est = (land_area * land_price * 1.05) + (bua * turnkey_price) # حسبة سريعة
    cost_sqm = total_est / bua
    
    st.info(f"💰 تكلفتك التقديرية للمتر (شامل): **{cost_sqm:,.0f} ريال**")

    # ==========================================================
    # 🧠 مسح السوق (Scanner) - التصحيح هنا
    # ==========================================================
    st.divider()
    st.header(f"📊 مسح أسعار العروض في {calc_dist}")
    
    # 1. فلترة البيانات للحي المختار فقط
    market_df = df[df['الحي'] == calc_dist].copy()
    
    # 2. فلترة العروض (Ask) فقط
    market_df = market_df[market_df['Data_Category'].astype(str).str.contains('Ask')]
    
    if market_df.empty:
        st.warning(f"لا توجد عروض مسجلة لحي {calc_dist}")
    else:
        # 🔥 تنظيف عمود نوع العقار من المسافات الزائدة لضمان المطابقة
        market_df['نوع_العقار'] = market_df['نوع_العقار'].astype(str).str.strip()
        
        # 1. الفلل
        villas = market_df[market_df['نوع_العقار'] == 'فيلا']
        avg_villa, cnt_villa, _ = get_avg_stats(villas)
        
        # 2. الشقق (الآن المطابقة ستكون دقيقة 100%)
        apts = market_df[market_df['نوع_العقار'] == 'شقة']
        avg_apt, cnt_apt, clean_apts = get_avg_stats(apts)
        
        # 3. الأدوار
        floors = market_df[market_df['نوع_العقار'] == 'دور']
        avg_floor, cnt_floor, _ = get_avg_stats(floors)
        
        # 4. المتوسط العام
        avg_all, cnt_all, _ = get_avg_stats(market_df[market_df['نوع_العقار'] != 'أرض'])

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
            
        with c2:
            st.markdown(f"""
            <div class="market-card">
                <h3>🏢 متوسط الشقق</h3>
                <h2>{avg_apt:,.0f}</h2>
                <small>عدد: {cnt_apt}</small>
            </div>
            """, unsafe_allow_html=True)
            # زر التأكد (Debug) للشقق
            if cnt_apt > 0:
                with st.expander("👁️ تفاصيل الشقق المحسوبة"):
                    st.dataframe(clean_apts[['السعر', 'المساحة', 'سعر_المتر', 'Source_File']], use_container_width=True)
            elif len(apts) > 0:
                st.error(f"وجدت {len(apts)} شقة لكن أسعارها غير منطقية (صفر أو فارغة) لذا لم أحسب المتوسط.")
                with st.expander("عرض البيانات المستبعدة"):
                    st.dataframe(apts, use_container_width=True)

        with c3:
            st.markdown(f"""
            <div class="market-card">
                <h3>🏘️ متوسط الأدوار</h3>
                <h2>{avg_floor:,.0f}</h2>
                <small>عدد: {cnt_floor}</small>
            </div>
            """, unsafe_allow_html=True)

        with c4:
            st.markdown(f"""
            <div class="market-card" style="border-top-color: #f1c40f;">
                <h3>📈 المتوسط العام</h3>
                <h2>{avg_all:,.0f}</h2>
                <small>عدد: {cnt_all}</small>
            </div>
            """, unsafe_allow_html=True)
            
        # شريط المقارنة
        st.divider()
        if avg_apt > 0:
            profit_margin = ((avg_apt - cost_sqm) / cost_sqm) * 100
            st.subheader(f"الربح المتوقع (شقق): {profit_margin:.1f}%")
            st.progress(min(max((profit_margin + 50)/100, 0.0), 1.0))
        else:
            st.info("لا تتوفر بيانات كافية للشقق لحساب هامش الربح.")
