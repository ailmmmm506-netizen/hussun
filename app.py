import streamlit as st
import pandas as pd
import data_bot

st.set_page_config(page_title="المطور العقاري الذكي", layout="wide")

# --- التنسيق ---
st.markdown("""
<style>
    .market-card { background-color: #ffffff; padding: 20px; border-radius: 12px; border-top: 5px solid #3498db; box-shadow: 0 4px 6px rgba(0,0,0,0.05); text-align: center; height: 100%; }
    [data-testid="stSidebar"] { background-color: #f8f9fa; border-left: 1px solid #ddd; }
</style>
""", unsafe_allow_html=True)

# --- تحميل البيانات ---
@st.cache_resource(show_spinner="جاري المعالجة...", ttl=3600)
def load_data(): return data_bot.RealEstateBot()

# زر تحديث قوي (يمسح الكاش)
with st.sidebar:
    st.title("القائمة")
    app_mode = st.radio("الوضع:", ["🕵️‍♂️ فحص التصنيفات (Debug)", "📊 الداشبورد", "🏗️ حاسبة التكاليف"])
    st.divider()
    if st.button("🗑️ مسح الكاش وتحديث البيانات", type="primary", use_container_width=True):
        st.cache_data.clear()
        st.cache_resource.clear()
        for key in list(st.session_state.keys()):
            del st.session_state[key]
        st.rerun()

if 'bot' not in st.session_state: st.session_state.bot = load_data()
df = st.session_state.bot.df if hasattr(st.session_state.bot, 'df') else pd.DataFrame()

# ==========================================
# 🕵️‍♂️ 1. صفحة فحص التصنيفات (المطلوبة)
# ==========================================
if app_mode == "🕵️‍♂️ فحص التصنيفات (Debug)":
    st.title("🕵️‍♂️ التحقق من دقة تصنيف الكود")
    
    if df.empty:
        st.error("لا توجد بيانات.")
        st.stop()

    # التأكد من وجود العمود الخام لتجنب الخطأ
    if 'نوع_العقار_الخام' not in df.columns:
        st.error("⚠️ عمود 'نوع_العقار_الخام' غير موجود. الرجاء الضغط على زر 'مسح الكاش وتحديث البيانات' في القائمة الجانبية.")
        st.stop()

    # فلاتر للبحث
    c1, c2 = st.columns(2)
    with c1:
        dist_filter = st.selectbox("اختر الحي:", ["الكل"] + sorted(df['الحي'].astype(str).unique()))
    with c2:
        search_term = st.text_input("بحث في نوع العقار الأصلي (مثل: راس، تاون، شقق..):")

    # تطبيق الفلاتر
    debug_df = df.copy()
    if dist_filter != "الكل":
        debug_df = debug_df[debug_df['الحي'] == dist_filter]
    
    if search_term:
        # البحث في العمود الخام
        debug_df = debug_df[debug_df['نوع_العقار_الخام'].astype(str).str.contains(search_term, case=False, na=False)]

    st.divider()
    
    # --- الجدول المقارن ---
    st.markdown(f"### 📋 جدول المقارنة ({len(debug_df)} عقار)")
    
    # اختيار الأعمدة
    cols_to_show = ['Source_File', 'المساحة', 'نوع_العقار_الخام', 'نوع_العقار']
    
    # إعادة التسمية للعرض
    rename_map = {
        'Source_File': 'اسم الملف',
        'المساحة': 'المساحة (م²)',
        'نوع_العقار_الخام': '📝 التصنيف الأصلي (من الملف)',
        'نوع_العقار': '🤖 التصنيف البرمجي (المعالَج)'
    }
    
    st.dataframe(
        debug_df[cols_to_show].rename(columns=rename_map),
        use_container_width=True,
        height=600,
        column_config={
            "📝 التصنيف الأصلي (من الملف)": st.column_config.TextColumn(help="هذا ما هو مكتوب في ملف الإكسل"),
            "🤖 التصنيف البرمجي (المعالَج)": st.column_config.TextColumn(help="كيف صنف الكود هذا العقار (شقة/فيلا/دور/أرض)")
        }
    )

# ==========================================
# 📊 2. الداشبورد (للعرض العام)
# ==========================================
elif app_mode == "📊 الداشبورد":
    if df.empty: st.stop()
    dist = st.sidebar.selectbox("الحي:", ["الكل"] + sorted(df['الحي'].unique()))
    v_df = df if dist == "الكل" else df[df['الحي'] == dist]
    
    st.title(f"لوحة البيانات: {dist}")
    tab1, tab2 = st.tabs(["💰 الصفقات (Sold)", "🏷️ العروض (Ask)"])
    
    cols = ['Source_File', 'الحي', 'السعر', 'المساحة', 'سعر_المتر', 'نوع_العقار']
    with tab1:
        st.dataframe(v_df[v_df['Data_Category'].str.contains('Sold', na=False)][cols], use_container_width=True)
    with tab2:
        st.dataframe(v_df[v_df['Data_Category'].str.contains('Ask', na=False)][cols], use_container_width=True)

# ==========================================
# 🏗️ 3. حاسبة التكاليف
# ==========================================
elif app_mode == "🏗️ حاسبة التكاليف":
    st.title("🏗️ حاسبة التكاليف ومسح السوق")
    
    # ... (يمكنك وضع كود الحاسبة هنا) ...
    # مثال مبسط للعرض:
    dist_list = sorted(df['الحي'].unique()) if not df.empty else []
    calc_dist = st.sidebar.selectbox("اختر الحي:", dist_list)
    
    st.header(f"متوسط الأسعار في {calc_dist}")
    
    market = df[(df['الحي'] == calc_dist) & (df['Data_Category'].str.contains('Ask', na=False))]
    
    if not market.empty:
        c1, c2, c3, c4 = st.columns(4)
        types = {'فيلا': '🏠', 'شقة': '🏢', 'دور': '🏘️', 'أرض': '🌍'}
        
        for i, (ctype, icon) in enumerate(types.items()):
            subset = market[market['نوع_العقار'] == ctype]
            # حساب المتوسط (تنظيف القيم)
            vals = pd.to_numeric(subset['سعر_المتر'], errors='coerce')
            vals = vals[(vals > 100) & (vals < 150000)]
            avg = vals.median() if not vals.empty else 0
            
            with [c1, c2, c3, c4][i]:
                st.markdown(f"""
                <div class="market-card">
                    <h3>{icon} {ctype}</h3>
                    <h2>{avg:,.0f}</h2>
                    <small>العدد: {len(vals)}</small>
                </div>
                """, unsafe_allow_html=True)
