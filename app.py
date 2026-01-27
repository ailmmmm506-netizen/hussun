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
    .market-card:hover { transform: translateY(-5px); transition: transform 0.2s; }
    .report-card { background-color: #fcfcfc; padding: 25px; border: 1px solid #eee; border-radius: 10px; margin-bottom: 20px; }
    [data-testid="stSidebar"] { background-color: #f8f9fa; border-left: 1px solid #ddd; }
</style>
""", unsafe_allow_html=True)

# ---------------------------------------------------------
# 2. تهيئة المتغيرات (Session State) لحفظ البيانات
# ---------------------------------------------------------
# نحفظ المدخلات هنا عشان نقدر نستخدمها في صفحة التقرير
defaults = {
    'land_area': 375, 'land_price': 3500, 'tax_pct': 5.0, 'saei_pct': 2.5,
    'build_ratio': 2.3, 'turnkey_price': 1800, 'bone_price': 700,
    'units': 4, 'services': 15000, 'permits': 50000, 'marketing_pct': 2.5,
    'is_offplan': False, 'wafi_fees': 50000, 'calc_dist': None,
    'project_name': 'مشروع تطوير سكني فاخر', 'developer_name': 'شركة التطوير العقاري'
}
for key, val in defaults.items():
    if key not in st.session_state:
        st.session_state[key] = val

# ---------------------------------------------------------
# 3. دوال مساعدة (PDF & Data)
# ---------------------------------------------------------
@st.cache_resource(show_spinner="جاري جلب البيانات...", ttl=3600)
def load_data(): return data_bot.RealEstateBot()

def get_clean_median(df_subset):
    if df_subset.empty: return 0, 0
    vals = pd.to_numeric(df_subset['سعر_المتر'], errors='coerce')
    vals = vals[(vals > 500) & (vals < 150000)]
    if vals.empty: return 0, 0
    return vals.median(), len(vals)

# كلاس الـ PDF المخصص (يدعم العربية بشكل محدود أو الإنجليزية، سنستخدم الإنجليزية للأرقام والعربية للعنوان إذا كان الخط مدعوماً)
# ملاحظة: FPDF العادي لا يدعم العربية جيداً بدون خطوط خارجية.
# لحل بسيط وسريع، سنقوم بإنشاء تقرير بتنسيق نظيف جداً (أرقام ومصطلحات إنجليزية/لاتينية) أو نستخدم مكتبة بديلة.
# هنا سأستخدم حيلة: رسم الرسوم البيانية كصور وإدراجها، وكتابة النصوص الأساسية.
# لضمان عمل الكود عند الجميع، سأجعل التقرير PDF بتصميم "Dashbaord Image" أو نصوص إنجليزية للأرقام ومصطلحات عربية بحروف لاتينية (Transliteration) لو لم يتوفر خط عربي، 
# **لكن الأفضل** سأستخدم مكتبة `matplotlib` لكتابة النص العربي داخل الصور ثم وضعها في الـ PDF.

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
    
    # Title Section
    pdf.set_font("Arial", "B", 16)
    pdf.cell(0, 10, f"Project: {data['project_name']}", ln=True, align='C')
    pdf.set_font("Arial", "", 12)
    pdf.cell(0, 10, f"Date: {datetime.date.today()}", ln=True, align='C')
    pdf.ln(10)

    # Executive Summary
    pdf.set_fill_color(240, 240, 240)
    pdf.set_font("Arial", "B", 14)
    pdf.cell(0, 10, "1. Executive Summary", ln=True, fill=True)
    pdf.set_font("Arial", "", 11)
    pdf.multi_cell(0, 8, f"{data['summary_text']}")
    pdf.ln(5)

    # Key Metrics Table
    pdf.set_font("Arial", "B", 12)
    pdf.cell(95, 10, "Metric", 1, 0, 'C', True)
    pdf.cell(95, 10, "Value", 1, 1, 'C', True)
    
    pdf.set_font("Arial", "", 11)
    metrics = [
        ("Land Area", f"{data['land_area']} sqm"),
        ("Total Built-up Area (BUA)", f"{data['bua']:,.0f} sqm"),
        ("Total Investment", f"{data['grand_total']:,.0f} SAR"),
        ("Cost per SQM (BUA)", f"{data['cost_sqm']:,.0f} SAR"),
        ("Market Price (Apt)", f"{data['market_apt']:,.0f} SAR/sqm"),
        ("Expected Profit Margin", f"{data['margin']:.1f} %"),
    ]
    for metric, value in metrics:
        pdf.cell(95, 10, metric, 1)
        pdf.cell(95, 10, value, 1, 1)
    pdf.ln(10)

    # Charts Section
    pdf.set_font("Arial", "B", 14)
    pdf.cell(0, 10, "2. Financial Analysis & Charts", ln=True, fill=True)
    pdf.ln(5)
    
    # Save charts to temporary files and add to PDF
    for chart_img in charts:
        with io.BytesIO() as img_buffer:
            chart_img.savefig(img_buffer, format='png', dpi=100)
            img_buffer.seek(0)
            # FPDF requires a file path or strict buffer handling. 
            # We will use a temp file workaround usually, but Streamlit + FPDF + BytesIO can be tricky.
            # Simplified:
            import tempfile
            with tempfile.NamedTemporaryFile(delete=False, suffix=".png") as tmpfile:
                tmpfile.write(img_buffer.getvalue())
                pdf.image(tmpfile.name, x=None, y=None, w=180)
    
    return pdf.output(dest='S').encode('latin-1')

# ---------------------------------------------------------
# 4. الواجهة الرئيسية
# ---------------------------------------------------------
if 'bot' not in st.session_state: st.session_state.bot = load_data()
df = st.session_state.bot.df if hasattr(st.session_state.bot, 'df') else pd.DataFrame()

with st.sidebar:
    st.image("https://cdn-icons-png.flaticon.com/512/2642/2642226.png", width=80)
    st.title("القائمة الرئيسية")
    # القوائم
    app_mode = st.radio("الوضع:", 
        ["🏗️ الحاسبة (إدخال البيانات)", 
         "📊 الداشبورد (فحص البيانات)", 
         "📑 تقرير المستثمر (Touting)"])
    
    st.divider()
    if st.button("🗑️ تحديث ومسح الكاش", type="primary"):
        st.cache_data.clear()
        st.cache_resource.clear()
        st.rerun()

# =========================================================
# 🏗️ صفحة 1: الحاسبة (إدخال البيانات)
# =========================================================
if app_mode == "🏗️ الحاسبة (إدخال البيانات)":
    st.title("🏗️ دراسة تكاليف المشروع")
    
    # نستخدم Session State عشان نحفظ القيم لما ننتقل لصفحة التقرير
    with st.form("calc_form"):
        c1, c2 = st.columns(2)
        with c1:
            st.subheader("1️⃣ الأرض والموقع")
            st.session_state.calc_dist = st.selectbox("الحي:", sorted(df['الحي'].astype(str).unique()) if not df.empty else [], index=0)
            st.session_state.land_area = st.number_input("مساحة الأرض (م²)", value=st.session_state.land_area)
            st.session_state.land_price = st.number_input("سعر المتر (ريال)", value=st.session_state.land_price)
            st.session_state.tax_pct = st.number_input("الضريبة %", value=st.session_state.tax_pct)
        
        with c2:
            st.subheader("2️⃣ التطوير والبناء")
            st.session_state.build_ratio = st.slider("معامل البناء", 1.0, 3.5, value=st.session_state.build_ratio)
            st.session_state.turnkey_price = st.number_input("سعر البناء (مفتاح)", value=st.session_state.turnkey_price)
            st.session_state.units = st.number_input("عدد الوحدات", value=st.session_state.units)
            st.session_state.marketing_pct = st.number_input("نسبة التسويق %", value=st.session_state.marketing_pct)

        submitted = st.form_submit_button("💾 حفظ وحساب التكاليف", type="primary")
    
    # الحسابات (تظهر دائماً بناءً على القيم المحفوظة)
    bua = st.session_state.land_area * st.session_state.build_ratio
    land_total = (st.session_state.land_area * st.session_state.land_price) * (1 + (st.session_state.tax_pct + st.session_state.saei_pct)/100)
    build_total = bua * st.session_state.turnkey_price
    others = (st.session_state.units * st.session_state.services) + st.session_state.permits + st.session_state.wafi_fees
    sub_total = land_total + build_total + others
    marketing = sub_total * (st.session_state.marketing_pct/100)
    grand_total = sub_total + marketing + (sub_total * 0.02) # طوارئ
    cost_sqm = grand_total / bua

    # حفظ النتائج في Session State
    st.session_state.grand_total = grand_total
    st.session_state.cost_sqm = cost_sqm
    st.session_state.bua = bua

    st.success(f"✅ تم الحفظ! تكلفة المتر البيعي: **{cost_sqm:,.0f} ريال**")
    st.info("👈 انتقل الآن إلى صفحة **'تقرير المستثمر'** لرؤية التحليل النهائي وتصدير الملف.")

# =========================================================
# 📊 صفحة 2: الداشبورد (للفحص السريع)
# =========================================================
elif app_mode == "📊 الداشبورد (فحص البيانات)":
    # (نفس كود الداشبورد السابق المختصر)
    if df.empty: st.stop()
    st.title("لوحة بيانات السوق")
    dist = st.selectbox("الحي:", ["الكل"] + sorted(df['الحي'].unique()))
    v_df = df if dist == "الكل" else df[df['الحي'] == dist]
    st.dataframe(v_df[['Source_File', 'الحي', 'السعر', 'المساحة', 'نوع_العقار']], use_container_width=True)

# =========================================================
# 📑 صفحة 3: تقرير المستثمر (الجديدة كلياً)
# =========================================================
elif app_mode == "📑 تقرير المستثمر (Touting)":
    st.title("📑 ملخص الدراسة (للمستثمرين)")

    # 1. إعدادات التقرير
    with st.expander("⚙️ إعدادات التقرير (اسم المشروع والشعار)", expanded=True):
        c1, c2 = st.columns(2)
        st.session_state.project_name = c1.text_input("اسم المشروع", st.session_state.project_name)
        st.session_state.developer_name = c2.text_input("اسم المطور", st.session_state.developer_name)
        
        # خانة "ملخص الدراسة" الجديدة التي طلبتها
        summary_text = st.text_area("📝 ملخص الدراسة والفرصة الاستثمارية (اكتب هنا ما سيظهر في مقدمة التقرير)", 
                                    value="فرصة استثمارية واعدة في حي حيوي، مع هامش ربح متوقع يتجاوز 25%. يتميز المشروع بتصميم عصري وكفاءة في التكاليف.",
                                    height=100)

    # 2. جلب بيانات السوق للمقارنة
    market_df = df[(df['الحي'] == st.session_state.calc_dist) & (df['Data_Category'].str.contains('Ask', na=False))]
    
    # متوسطات السوق
    p_apt, _ = get_clean_median(market_df[market_df['نوع_العقار'] == 'شقة'])
    p_villa, _ = get_clean_median(market_df[market_df['نوع_العقار'] == 'فيلا'])
    
    my_cost = st.session_state.get('cost_sqm', 0)
    profit_margin = ((p_apt - my_cost) / my_cost * 100) if p_apt > 0 else 0

    # 3. عرض التقرير التفاعلي
    st.divider()
    st.markdown(f"### 💎 {st.session_state.project_name}")
    st.markdown(f"**الحي:** {st.session_state.calc_dist} | **المطور:** {st.session_state.developer_name}")
    
    # كروت المؤشرات
    k1, k2, k3, k4 = st.columns(4)
    k1.metric("إجمالي الاستثمار", f"{st.session_state.get('grand_total',0)/1000000:,.1f} M ريال")
    k2.metric("تكلفة المتر (علينا)", f"{my_cost:,.0f} ريال")
    k3.metric("سعر السوق (شقق)", f"{p_apt:,.0f} ريال")
    k4.metric("هامش الربح المتوقع", f"{profit_margin:.1f}%", delta_color="normal")

    # الرسوم البيانية (Charts)
    col_g1, col_g2 = st.columns(2)
    
    # Chart 1: توزيع التكاليف
    with col_g1:
        st.subheader("توزيع التكاليف")
        land_val = st.session_state.land_area * st.session_state.land_price
        build_val = st.session_state.land_area * st.session_state.build_ratio * st.session_state.turnkey_price
        other_val = st.session_state.get('grand_total', 0) - land_val - build_val
        
        fig1, ax1 = plt.subplots(figsize=(5, 5))
        ax1.pie([land_val, build_val, other_val], labels=['Land', 'Construction', 'Others'], autopct='%1.1f%%', startangle=90, colors=['#3498db', '#e74c3c', '#95a5a6'])
        st.pyplot(fig1)

    # Chart 2: المقارنة بالسوق
    with col_g2:
        st.subheader("تنافسية السعر")
        fig2, ax2 = plt.subplots(figsize=(5, 4))
        categories = ['My Cost', 'Market (Apt)', 'Market (Villa)']
        values = [my_cost, p_apt, p_villa]
        colors = ['#2ecc71', '#3498db', '#9b59b6']
        bars = ax2.bar(categories, values, color=colors)
        ax2.set_ylabel('SAR / SQM')
        st.pyplot(fig2)

    # 4. زر التصدير PDF
    st.divider()
    st.subheader("🖨️ تصدير الدراسة")
    
    if st.button("توليد ملف PDF جاهز للطباعة"):
        # تجهيز البيانات للتصدير
        report_data = {
            'project_name': st.session_state.project_name,
            'summary_text': summary_text, # النص الذي كتبته
            'land_area': st.session_state.land_area,
            'bua': st.session_state.get('bua', 0),
            'grand_total': st.session_state.get('grand_total', 0),
            'cost_sqm': my_cost,
            'market_apt': p_apt,
            'margin': profit_margin
        }
        
        # إنشاء PDF
        pdf_bytes = create_investor_pdf(report_data, [fig1, fig2])
        
        st.download_button(
            label="📥 تحميل التقرير (PDF)",
            data=pdf_bytes,
            file_name="Feasibility_Study.pdf",
            mime="application/pdf"
        )
