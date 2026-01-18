import streamlit as st
import pandas as pd
import numpy as np
import data_bot  # استيراد المحرك

# إعداد الصفحة
st.set_page_config(page_title="المستشار العقاري - دراسة الجدوى الدقيقة", layout="wide", page_icon="⚖️")

# --- التنسيق الجمالي ---
st.markdown("""
<style>
    .header-style {font-size:22px; font-weight:bold; color:#1f77b4; margin-bottom:10px;}
    .metric-container {background-color:#f8f9fa; padding:15px; border-radius:8px; border:1px solid #ddd; text-align:center;}
    .big-num {font-size:24px; font-weight:bold; color:#2c3e50;}
    .label-text {font-size:14px; color:#7f8c8d;}
</style>
""", unsafe_allow_html=True)

# --- دالة التنظيف الذكي (Smart Cleaning) ---
def get_clean_stats(df_input, col='سعر_المتر'):
    """
    تقوم هذه الدالة بحذف القيم الشاذة (أعلى 10% وأقل 10%) 
    لإعطاء متوسط سعري دقيق يعكس واقع السوق.
    """
    if df_input.empty: return 0, 0, 0
    
    # 1. استبعاد القيم الصفرية أو السالبة
    clean_df = df_input[df_input[col] > 100].copy() # نفترض أن المتر لا يقل عن 100 ريال
    
    if clean_df.empty: return 0, 0, 0

    # 2. حساب الحدود (Quantiles) لاستبعاد الشواذ
    low_limit = clean_df[col].quantile(0.10) # استبعاد أرخص 10% (غالباً صفقات عائلية)
    high_limit = clean_df[col].quantile(0.90) # استبعاد أغلى 10% (غالباً أخطاء إدخال)
    
    # 3. الفلترة النهائية
    final_df = clean_df[(clean_df[col] >= low_limit) & (clean_df[col] <= high_limit)]
    
    if final_df.empty: return 0, 0, 0
    
    # إرجاع: المتوسط (Median)، أقل سعر حقيقي، أعلى سعر حقيقي
    return final_df[col].median(), final_df[col].min(), final_df[col].max()

# --- التأكد من الاتصال ---
if 'bot' not in st.session_state:
    with st.spinner("جاري تهيئة خوارزميات التدقيق..."):
        try:
            st.session_state.bot = data_bot.RealEstateBot()
        except: st.error("خطأ في الاتصال")

df = st.session_state.bot.df if hasattr(st.session_state.bot, 'df') else pd.DataFrame()

# --- القائمة الجانبية ---
with st.sidebar:
    st.header("⚙️ التحكم")
    if st.button("🔄 تحديث وتحليل البيانات", type="primary", use_container_width=True):
        st.cache_data.clear()
        for key in list(st.session_state.keys()): del st.session_state[key]
        st.rerun()
    
    st.divider()
    if not df.empty:
        st.success(f"✅ قاعدة البيانات: {len(df)} صفقة")
    else:
        st.error("❌ لا توجد بيانات")

# --- الواجهة الرئيسية ---
st.title("🏗️ دراسة الجدوى العقارية (المدققة)")
st.caption("يتم استخدام خوارزمية لاستبعاد الصفقات الشاذة (المنخفضة جداً أو المرتفعة جداً) لضمان دقة التقييم.")

if df.empty:
    st.warning("الرجاء تحديث البيانات من القائمة الجانبية.")
    st.stop()

# ========================================================
# 1. المدخلات (Inputs)
# ========================================================
with st.container():
    st.markdown("<div class='header-style'>1️⃣ محددات الدراسة</div>", unsafe_allow_html=True)
    
    districts = sorted(df['الحي'].unique()) if 'الحي' in df.columns else []
    
    col1, col2, col3 = st.columns(3)
    with col1:
        selected_dist = st.selectbox("📍 اختر الحي", districts)
    with col2:
        land_area = st.number_input("📐 مساحة الأرض (م²)", value=375)
    with c3:
        offer_price = st.number_input("💰 سعر المتر المعروض (ريال)", value=3500)

    col4, col5, col6 = st.columns(3)
    with col4:
        build_cost = st.number_input("🔨 تكلفة البناء للمتر (ريال)", value=1700, help="تكلفة العظم والتشطيب")
    with col5:
        build_ratio = st.slider("نسبة المسطحات (%)", 1.5, 3.5, 2.3)
    with col6:
        fees_pct = st.number_input("رسوم إضافية (%)", value=7.5, help="تشمل 5% ضريبة تصرفات + 2.5% سعي")

# ========================================================
# 2. المعالجة والتحليل (Processing)
# ========================================================

# فصل البيانات
lands_raw = df[(df['الحي'] == selected_dist) & (df['
