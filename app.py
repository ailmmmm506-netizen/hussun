import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
from fpdf import FPDF
import io
import datetime
import data_bot  # المحرك الذكي

# ---------------------------------------------------------
# 1. إعدادات الصفحة
# ---------------------------------------------------------
st.set_page_config(page_title="المطور العقاري الذكي", layout="wide", page_icon="🏗️")

st.markdown("""
<style>
    .market-card { background-color: #ffffff; padding: 20px; border-radius: 15px; border-top: 6px solid #3498db; box-shadow: 0 4px 10px rgba(0,0,0,0.05); text-align: center; height: 100%; }
    .market-card h2 { font-size: 28px; font-weight: bold; color: #2c3e50; margin: 10px 0; }
    .market-card h3 { font-size: 16px; color: #7f8c8d; font-weight: bold; }
    .stat-label { font-size: 13px; color: #95a5a6; margin-top: 5px; }
    [data-testid="stSidebar"] { background-color: #f8f9fa; border-left: 1px solid #ddd; }
</style>
""", unsafe_allow_html=True)

# ---------------------------------------------------------
# 2. تهيئة المتغيرات (لحفظ البيانات بين الصفحات)
# ---------------------------------------------------------
defaults = {
    'land_area': 375, 'land_price': 3500, 'tax_pct': 5.0, 'saei_pct': 2.5,
    'build_ratio': 2.3, 'turnkey_price': 1800, 'bone_price': 700,
    'units': 4, 'services': 15000, 'permits': 50000, 'marketing_pct': 2.5,
    'is_offplan': False, 'wafi_fees': 50000, 'calc_dist': None,
    'project_name': 'مشروع سكني', 'developer_name': 'المطور العقاري'
}
for key, val in defaults.items():
    if key not in st.session_state: st.session_state[key] = val

# ---------------------------------------------------------
# 3. الدوال المساعدة
# ---------------------------------------------------------
@st.cache_resource(show_spinner="جاري جلب البيانات...", ttl=3600)
def load_data(): return data_bot.RealEstateBot()

def get_clean_median(df_subset):
    if df_subset.empty: return 0, 0
    vals = pd.to_numeric(df_subset['سعر_المتر'], errors='coerce')
    vals = vals[(vals > 500) & (vals < 150000)]
    if vals.empty: return 0, 0
    return vals.median(), len(vals)

# كلاس الـ PDF
class PDFReport(FPDF):
    def header(self):
        self.set_font('Arial', 'B', 15)
        self.cell(0, 10, 'Real Estate Feasibility Study', 0, 1, 'C')
        self.ln(5)
    def footer(self):
        self.set_y(-15)
        self.set_font('Arial', 'I', 8)
        self.cell(0, 10, f'Page {self.page_no()}', 0, 0, 'C')

def create_investor_pdf(data, charts):
    pdf = PDFReport()
    pdf.add_page()
    pdf.set_auto_page_break(auto=True, margin=15)
    
    # Title
    pdf.set_font("Arial", "B", 16)
    try: pdf.cell(0, 10, f"Project: {data['project_name'].encode('latin-1', 'ignore').decode('latin-1')}", ln=True, align='C')
    except: pdf.cell(0, 10, "Project Report", ln=True, align='C')
    
    pdf.set_font("Arial", "", 12)
    pdf.cell(0, 10, f"Date: {datetime.date.today()}", ln=True, align='C')
    pdf.ln(10)

    # Summary
    pdf.set_fill_color(240, 240, 240)
    pdf.set_font("Arial", "B", 14)
    pdf.cell(0, 10, "1. Executive Summary", ln=True, fill=True)
    pdf.set_font("Arial", "", 11)
    # Note: FPDF standard doesn't support Arabic text rendering directly. 
    # We use summary_text placeholder or transliterated text.
    pdf.multi_cell(0, 8, "Investment Analysis Report generated via Smart Developer App.")
    pdf.ln(5)

    # Metrics
    pdf.set_font("Arial", "B", 12)
    pdf.cell(95, 10, "Metric", 1, 0, 'C', True)
    pdf.cell(95, 10, "Value", 1, 1, 'C', True)
    pdf.set_font("Arial", "", 11)
    metrics = [
        ("Land Area", f"{data['land_area']} sqm"),
        ("Total Investment", f"{data['grand_total']:,.0f} SAR"),
        ("Cost per SQM", f"{data['cost_sqm']:,.0f} SAR"),
        ("Market Price (Apt)", f"{data['market_apt']:,.0f} SAR/sqm"),
        ("Profit Margin", f"{data['margin']:.1f} %"),
    ]
    for metric, value in metrics:
        pdf.cell(95, 10, metric, 1)
        pdf.cell(95, 10, value, 1, 1)
    pdf.ln(10)

    # Charts
    pdf.set_font("Arial", "B", 14)
    pdf.cell(0, 10, "2. Financial Charts", ln=True, fill=True)
    pdf.ln(5)
    
    import tempfile
    for chart_img in charts:
        with io.BytesIO() as img_buffer:
            chart_img.savefig(img_buffer, format='png', dpi=100)
            img_buffer.seek(0)
            with tempfile.NamedTemporaryFile(delete=False, suffix=".png") as tmpfile:
                tmpfile.write(img_buffer.getvalue())
                pdf.image(tmpfile.name, x=None, y=None, w=170)
                pdf.ln(5)
    
    return pdf.output(dest='S').encode('latin-1')

# ---------------------------------------------------------
# 4. الواجهة والتحميل
# ---------------------------------------------------------
if 'bot' not in st.session_state: st.session_state.bot = load_data()
df = st.session_state.bot.df if hasattr(st.session_state.bot, 'df') else pd.DataFrame()

with st.sidebar:
    st.image("https://cdn-icons-png.flaticon.com/512/2642/2642226.png", width=80)
    st.title("القائمة الرئيسية")
    app_mode = st.radio("الوضع:", ["🏗️ الحاسبة والدراسة", "📑 تقرير المستثمر (PDF)", "📊 لوحة البيانات"])
    st.divider()
    if st.button("🗑️ تحديث ومسح الكاش", type="primary"):
        st.cache_data.clear()
        st.cache_resource.clear()
        st.rerun()

# =========================================================
# 🏗️ صفحة 1: الحاسبة والدراسة (تم استرجاع المزايا القديمة)
# =========================================================
if app_mode == "🏗️ الحاسبة والدراسة":
    st.title("🏗️ حاسبة التطوير وماسح السوق")
    
    # 1. المدخلات
    with st.expander("📝 مدخلات المشروع والتكاليف", expanded=True):
        c1, c2 = st.columns(2)
        with c1:
            st.subheader("الأرض")
            # اختيار الحي من القائمة وحفظه في الذاكرة
            options = sorted(df['الحي'].astype(str).unique()) if not df.empty else []
            # محاولة تحديد الحي المختار سابقاً
            idx = 0
            if st.session_state.calc_dist in options: idx = options.index(st.session_state.calc_dist)
            st.session_state.calc_dist = st.selectbox("الحي:", options, index=idx)
            
            st.session_state.land_area = st.number_input("مساحة الأرض", value=st.session_state.land_area)
            st.session_state.land_price = st.number_input("سعر المتر", value=st.session_state.land_price)
            st.session_state.tax_pct = st.number_input("الضريبة %", value=st.session_state.tax_pct)
        
        with c2:
            st.subheader("البناء")
            st.session_state.build_ratio = st.slider("معامل البناء", 1.0, 3.5, value=st.session_state.build_ratio)
            st.session_state.turnkey_price = st.number_input("سعر البناء (مفتاح)", value=st.session_state.turnkey_price)
            st.session_state.units = st.number_input("عدد الوحدات", value=st.session_state.units)
            st.session_state.marketing_pct = st.number_input("تسويق %", value=st.session_state.marketing_pct)

    # 2. الحسابات
    bua = st.session_state.land_area * st.session_state.build_ratio
    land_cost = (st.session_state.land_area * st.session_state.land_price) * (1 + (st.session_state.tax_pct+st.session_state.saei_pct)/100)
    build_cost = bua * st.session_state.turnkey_price
    others = (st.session_state.units * st.session_state.services) + st.session_state.permits + st.session_state.wafi_fees
    sub_total = land_cost + build_cost + others
    grand_total = sub_total * (1 + (2 + st.session_state.marketing_pct)/100) # + طوارئ وتسويق
    cost_sqm = grand_total / bua

    # حفظ النتائج
    st.session_state.grand_total = grand_total
    st.session_state.cost_sqm = cost_sqm
    
    # عرض النتائج الرقمية
    k1, k2, k3 = st.columns(3)
    k1.metric("إجمالي التكلفة", f"{grand_total:,.0f} ريال")
    k2.metric("تكلفة المتر (علينا)", f"{cost_sqm:,.0f} ريال")
    k3.metric("مسطح البناء", f"{bua:,.0f} م²")

    # 3. ماسح السوق (تم إرجاعه هنا كما طلبت)
    st.divider()
    st.header(f"📊 مؤشرات السوق في {st.session_state.calc_dist}")
    
    market_df = df[(df['الحي'] == st.session_state.calc_dist) & (df['Data_Category'].str.contains('Ask', na=False))]
    
    if market_df.empty:
        st.warning("لا توجد بيانات عروض كافية في هذا الحي للمقارنة.")
    else:
        # حساب المتوسطات
        p_villa, n_villa = get_clean_median(market_df[market_df['نوع_العقار'] == 'فيلا'])
        p_apt, n_apt     = get_clean_median(market_df[market_df['نوع_العقار'] == 'شقة'])
        p_floor, n_floor = get_clean_median(market_df[market_df['نوع_العقار'] == 'دور'])
        
        # عرض الكروت
        c1, c2, c3, c4 = st.columns(4)
        with c1: st.markdown(f'<div class="market-card"><h3>🏠 الفلل</h3><h2>{p_villa:,.0f}</h2><div class="stat-label">عدد: {n_villa}</div></div>', unsafe_allow_html=True)
        with c2: st.markdown(f'<div class="market-card"><h3>🏢 الشقق</h3><h2>{p_apt:,.0f}</h2><div class="stat-label">عدد: {n_apt}</div></div>', unsafe_allow_html=True)
        with c3: st.markdown(f'<div class="market-card"><h3>🏘️ الأدوار</h3><h2>{p_floor:,.0f}</h2><div class="stat-label">عدد: {n_floor}</div></div>', unsafe_allow_html=True)
        
        # مقارنة الجدوى فوراً
        st.divider()
        st.subheader("💡 الجدوى (مقارنة بالسوق)")
        def show_margin(label, market_price):
            if market_price > 0:
                marg = ((market_price - cost_sqm) / cost_sqm) * 100
                st.write(f"**الربح في {label}:**")
                st.progress(min(max((marg+50)/100, 0.0), 1.0))
                st.caption(f"الهامش: {marg:.1f}% (السوق: {market_price:,.0f})")
        
        m1, m2 = st.columns(2)
        with m1: show_margin("الشقق", p_apt)
        with m2: show_margin("الفلل", p_villa)

# =========================================================
# 📑 صفحة 2: تقرير المستثمر (الإضافة الجديدة)
# =========================================================
elif app_mode == "📑 تقرير المستثمر (PDF)":
    st.title("📑 إصدار التقرير")
    
    # إعدادات التقرير
    with st.expander("⚙️ بيانات التقرير", expanded=True):
        c1, c2 = st.columns(2)
        st.session_state.project_name = c1.text_input("اسم المشروع", st.session_state.project_name)
        st.session_state.developer_name = c2.text_input("اسم المطور", st.session_state.developer_name)
    
    # تجهيز الرسوم البيانية
    market_df = df[(df['الحي'] == st.session_state.calc_dist) & (df['Data_Category'].str.contains('Ask', na=False))]
    p_apt, _ = get_clean_median(market_df[market_df['نوع_العقار'] == 'شقة'])
    
    # Chart 1: التكاليف
    fig1, ax1 = plt.subplots(figsize=(4, 3))
    land_v = st.session_state.land_area * st.session_state.land_price
    build_v = st.session_state.land_area * st.session_state.build_ratio * st.session_state.turnkey_price
    rest_v = st.session_state.get('grand_total', 1) - land_v - build_v
    ax1.pie([land_v, build_v, rest_v], labels=['Land', 'Build', 'Other'], autopct='%1.1f%%', colors=['#3498db', '#e74c3c', '#95a5a6'])
    ax1.set_title("Cost Breakdown")

    # Chart 2: السعر
    fig2, ax2 = plt.subplots(figsize=(4, 3))
    ax2.bar(['My Cost', 'Market Price'], [st.session_state.get('cost_sqm', 0), p_apt], color=['#2ecc71', '#3498db'])
    ax2.set_title("Competitiveness")
    
    # عرض معاينة
    st.pyplot(fig1)
    st.pyplot(fig2)

    if st.button("🖨️ تحميل التقرير (PDF)"):
        data_rep = {
            'project_name': st.session_state.project_name,
            'land_area': st.session_state.land_area,
            'grand_total': st.session_state.get('grand_total', 0),
            'cost_sqm': st.session_state.get('cost_sqm', 0),
            'market_apt': p_apt,
            'margin': ((p_apt - st.session_state.get('cost_sqm', 1))/st.session_state.get('cost_sqm', 1)*100)
        }
        pdf_bytes = create_investor_pdf(data_rep, [fig1, fig2])
        st.download_button("📥 تنزيل الملف", data=pdf_bytes, file_name="Report.pdf", mime="application/pdf")

# =========================================================
# 📊 صفحة 3: الداشبورد
# =========================================================
elif app_mode == "📊 لوحة البيانات":
    if df.empty: st.stop()
    st.title(f"فحص البيانات")
    dist = st.selectbox("الحي:", ["الكل"] + sorted(df['الحي'].unique()))
    v_df = df if dist == "الكل" else df[df['الحي'] == dist]
    st.dataframe(v_df[['Source_File', 'الحي', 'السعر', 'المساحة', 'نوع_العقار']], use_container_width=True)
