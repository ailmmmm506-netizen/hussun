import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
from fpdf import FPDF
import io
import datetime
import data_bot  # يعتمد على المحرك الذكي في التصنيف

# ---------------------------------------------------------
# 1. إعدادات الصفحة والتصميم
# ---------------------------------------------------------
st.set_page_config(page_title="المطور العقاري الذكي", layout="wide", page_icon="🏗️")

st.markdown("""
<style>
    /* تنسيق كروت السوق */
    .market-card { 
        background-color: #ffffff; 
        padding: 20px; 
        border-radius: 15px; 
        border-top: 6px solid #3498db; 
        box-shadow: 0 4px 10px rgba(0,0,0,0.05); 
        text-align: center; 
        height: 100%;
        transition: transform 0.2s;
    }
    .market-card:hover { transform: translateY(-5px); }
    .market-card h2 { font-size: 28px; font-weight: bold; color: #2c3e50; margin: 10px 0; }
    .market-card h3 { font-size: 16px; color: #7f8c8d; font-weight: bold; }
    .market-card .stat-label { font-size: 13px; color: #95a5a6; margin-top: 5px; }
    
    /* تنسيق السايدبار */
    [data-testid="stSidebar"] { background-color: #f8f9fa; border-left: 1px solid #ddd; }
    
    /* أشرطة التقدم */
    .stProgress > div > div > div > div { background-color: #2ecc71; }
</style>
""", unsafe_allow_html=True)

# ---------------------------------------------------------
# 2. تهيئة الذاكرة (Session State)
# ---------------------------------------------------------
defaults = {
    'land_area': 375, 'land_price': 3500, 'tax_pct': 5.0, 'saei_pct': 2.5,
    'build_ratio': 2.3, 'turnkey_price': 1800, 'bone_price': 700,
    'units': 4, 'services': 15000, 'permits': 50000, 'marketing_pct': 2.5,
    'is_offplan': False, 'wafi_fees': 50000, 'calc_dist': None,
    'grand_total': 0, 'cost_sqm': 0, 'project_name': 'مشروع سكني', 'developer_name': ''
}
for key, val in defaults.items():
    if key not in st.session_state:
        st.session_state[key] = val

# ---------------------------------------------------------
# 3. دوال مساعدة (Data & PDF)
# ---------------------------------------------------------
@st.cache_resource(show_spinner="جاري جلب وتحليل البيانات...", ttl=3600)
def load_data():
    return data_bot.RealEstateBot()

def get_clean_median(df_subset):
    """حساب الوسيط الحسابي مع استبعاد القيم الشاذة"""
    if df_subset.empty: return 0, 0
    vals = pd.to_numeric(df_subset['سعر_المتر'], errors='coerce')
    vals = vals[(vals > 500) & (vals < 150000)] 
    if vals.empty: return 0, 0
    return vals.median(), len(vals)

# كلاس PDF بسيط
class PDFReport(FPDF):
    def header(self):
        self.set_font('Arial', 'B', 15)
        self.cell(0, 10, 'Real Estate Feasibility Study', 0, 1, 'C')
        self.ln(5)
    def footer(self):
        self.set_y(-15)
        self.set_font('Arial', 'I', 8)
        self.cell(0, 10, f'Page {self.page_no()}', 0, 0, 'C')

def create_pdf(data, charts):
    pdf = PDFReport()
    pdf.add_page()
    
    # العنوان
    pdf.set_font("Arial", "B", 16)
    # ملاحظة: FPDF لا يدعم العربية مباشرة، لذا نستخدم الإنجليزية في العناوين الثابتة
    pdf.cell(0, 10, f"Project Financial Report", ln=True, align='C')
    pdf.set_font("Arial", "", 12)
    pdf.cell(0, 10, f"Date: {datetime.date.today()}", ln=True, align='C')
    pdf.ln(10)

    # الملخص
    pdf.set_fill_color(230, 230, 230)
    pdf.set_font("Arial", "B", 14)
    pdf.cell(0, 10, "1. Executive Summary", ln=True, fill=True)
    pdf.set_font("Arial", "", 11)
    pdf.multi_cell(0, 8, "This report analyzes the feasibility of a residential development project. It compares the estimated development costs against the current market rates.")
    pdf.ln(5)

    # الجدول المالي
    pdf.set_font("Arial", "B", 14)
    pdf.cell(0, 10, "2. Key Financial Metrics", ln=True, fill=True)
    pdf.set_font("Arial", "B", 12)
    
    metrics = [
        ("Land Area", f"{data['land_area']} sqm"),
        ("Total Investment", f"{data['grand_total']:,.0f} SAR"),
        ("Cost per SQM", f"{data['cost_sqm']:,.0f} SAR"),
        ("Market Price (Apt)", f"{data['market_apt']:,.0f} SAR"),
        ("Profit Margin", f"{data['margin']:.1f} %")
    ]
    
    for metric, value in metrics:
        pdf.cell(95, 10, metric, 1)
        pdf.cell(95, 10, value, 1, 1)
    pdf.ln(10)

    # الرسوم البيانية
    pdf.set_font("Arial", "B", 14)
    pdf.cell(0, 10, "3. Charts & Analysis", ln=True, fill=True)
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
# 4. تحميل البيانات
# ---------------------------------------------------------
if 'bot' not in st.session_state: st.session_state.bot = load_data()
df = st.session_state.bot.df if hasattr(st.session_state.bot, 'df') else pd.DataFrame()

# ---------------------------------------------------------
# 5. القائمة الجانبية (Sidebar)
# ---------------------------------------------------------
with st.sidebar:
    st.image("https://cdn-icons-png.flaticon.com/512/2642/2642226.png", width=80)
    st.title("القائمة الرئيسية")
    
    app_mode = st.radio("اختر النظام:", 
                        ["🏗️ الحاسبة والدراسة", 
                         "📑 تقرير المستثمر (PDF)",
                         "📊 لوحة البيانات (Dashboard)"])
    
    st.divider()
    if st.button("🗑️ تحديث البيانات ومسح الكاش", type="primary", use_container_width=True):
        st.cache_data.clear()
        st.cache_resource.clear()
        for key in list(st.session_state.keys()): del st.session_state[key]
        st.rerun()

# =========================================================
# 🏗️ التطبيق 1: الحاسبة والدراسة
# =========================================================
if app_mode == "🏗️ الحاسبة والدراسة":
    
    st.title("🏗️ دراسة الجدوى الشاملة")
    
    # --- أ) المدخلات ---
    with st.sidebar:
        st.header("1️⃣ الموقع")
        options = sorted(df['الحي'].astype(str).unique()) if not df.empty else []
        idx = 0
        if st.session_state.calc_dist in options: idx = options.index(st.session_state.calc_dist)
        st.session_state.calc_dist = st.selectbox("حي المشروع:", options, index=idx)
        
        st.header("2️⃣ الأرض")
        st.session_state.land_area = st.number_input("المساحة (م²)", value=st.session_state.land_area, step=25)
        st.session_state.land_price = st.number_input("سعر المتر (ريال)", value=st.session_state.land_price, step=50)
        st.session_state.tax_pct = st.number_input("الضريبة (%)", value=st.session_state.tax_pct)
        st.session_state.saei_pct = st.number_input("السعي (%)", value=st.session_state.saei_pct)
        
        st.header("3️⃣ البناء")
        st.session_state.build_ratio = st.slider("معامل البناء (FAR)", 1.0, 3.5, value=st.session_state.build_ratio)
        st.session_state.turnkey_price = st.number_input("سعر المتر (مفتاح)", value=st.session_state.turnkey_price)
        st.session_state.bone_price = st.number_input("سعر المتر (عظم) - للتأمين", value=st.session_state.bone_price)
        
        st.header("4️⃣ مصاريف أخرى")
        st.session_state.units = st.number_input("عدد الوحدات", value=st.session_state.units)
        st.session_state.services = st.number_input("تكلفة الخدمات/وحدة", value=st.session_state.services)
        st.session_state.permits = st.number_input("رخص وتصاميم", value=st.session_state.permits)
        st.session_state.marketing_pct = st.number_input("تسويق (%)", value=st.session_state.marketing_pct)
        st.session_state.is_offplan = st.checkbox("بيع على الخارطة (وافي)؟", value=st.session_state.is_offplan)
        if st.session_state.is_offplan:
            st.session_state.wafi_fees = st.number_input("رسوم وافي", value=st.session_state.wafi_fees)
        else:
            st.session_state.wafi_fees = 0

    # --- ب) محرك الحسابات ---
    bua = st.session_state.land_area * st.session_state.build_ratio
    
    base_land = st.session_state.land_area * st.session_state.land_price
    land_total = base_land * (1 + (st.session_state.tax_pct + st.session_state.saei_pct)/100)
    
    build_total = bua * st.session_state.turnkey_price
    malath = (bua * st.session_state.bone_price) * 0.01 
    
    services_total = st.session_state.units * st.session_state.services
    sub_total = land_total + build_total + malath + services_total + st.session_state.permits + st.session_state.wafi_fees
    
    contingency = sub_total * 0.02 
    marketing = (sub_total + contingency) * (st.session_state.marketing_pct / 100)
    
    grand_total = sub_total + contingency + marketing
    cost_sqm = grand_total / bua 

    st.session_state.grand_total = grand_total
    st.session_state.cost_sqm = cost_sqm

    # --- ج) عرض النتائج ---
    c1, c2, c3 = st.columns(3)
    with c1: st.metric("إجمالي التكلفة الاستثمارية", f"{grand_total:,.0f} ريال")
    with c2: st.metric("تكلفة المتر (شامل الأرض والبناء)", f"{cost_sqm:,.0f} ريال/م")
    with c3: st.metric("إجمالي مسطح البناء", f"{bua:,.0f} م²")
    
    st.divider()
    
    col_table, col_chart = st.columns([1, 1])
    with col_table:
        st.subheader("📑 تفاصيل الفاتورة")
        breakdown = [
            {"البند": "الأرض (مع ضريبة وسعي)", "التكلفة": land_total},
            {"البند": "البناء والتشطيب", "التكلفة": build_total},
            {"البند": "تأمين ملاذ (1% عظم)", "التكلفة": malath},
            {"البند": "خدمات (كهرباء/مياه)", "التكلفة": services_total},
            {"البند": "رخص وتصاميم", "التكلفة": st.session_state.permits},
            {"البند": "تسويق وعمولات", "التكلفة": marketing},
            {"البند": "احتياطي طوارئ (2%)", "التكلفة": contingency},
        ]
        if st.session_state.is_offplan: breakdown.append({"البند": "رسوم وافي", "التكلفة": st.session_state.wafi_fees})
        
        df_cost = pd.DataFrame(breakdown)
        df_cost['النسبة'] = df_cost['التكلفة'] / grand_total
        st.dataframe(df_cost, use_container_width=True, column_config={"التكلفة": st.column_config.NumberColumn(format="%d ريال"), "النسبة": st.column_config.ProgressColumn(format="%.1f%%")})

    with col_chart:
        st.subheader("توزيع الميزانية")
        st.bar_chart(df_cost.set_index("البند")['التكلفة'])

    # =========================================================
    # 🧠 د) ماسح السوق
    # =========================================================
    st.markdown("---")
    st.header(f"📊 مؤشرات السوق في حي {st.session_state.calc_dist}")
    
    market_df = df[(df['الحي'] == st.session_state.calc_dist) & (df['Data_Category'].str.contains('Ask', na=False))]
    
    if market_df.empty:
        st.warning(f"لا توجد عروض بيع مسجلة حالياً لحي {st.session_state.calc_dist} للمقارنة.")
    else:
        villas = market_df[market_df['نوع_العقار'] == 'فيلا']
        apts   = market_df[market_df['نوع_العقار'] == 'شقة']
        floors = market_df[market_df['نوع_العقار'] == 'دور']
        general = market_df[market_df['نوع_العقار'] != 'أرض']

        p_villa, n_villa = get_clean_median(villas)
        p_apt, n_apt     = get_clean_median(apts)
        p_floor, n_floor = get_clean_median(floors)
        p_gen, n_gen     = get_clean_median(general)

        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            st.markdown(f'<div class="market-card"><h3>🏠 الفلل</h3><h2>{p_villa:,.0f}</h2><div class="stat-label">عدد العروض: {n_villa}</div></div>', unsafe_allow_html=True)
            if n_villa > 0:
                with st.expander("تفاصيل الفلل"):
                    st.dataframe(villas[['السعر', 'المساحة', 'سعر_المتر']], use_container_width=True)

        with col2:
            st.markdown(f'<div class="market-card"><h3>🏢 الشقق</h3><h2>{p_apt:,.0f}</h2><div class="stat-label">عدد العروض: {n_apt}</div></div>', unsafe_allow_html=True)
            if n_apt > 0:
                with st.expander("تفاصيل الشقق"):
                    st.dataframe(apts[['السعر', 'المساحة', 'سعر_المتر']], use_container_width=True)

        with col3:
            st.markdown(f'<div class="market-card"><h3>🏘️ الأدوار</h3><h2>{p_floor:,.0f}</h2><div class="stat-label">عدد العروض: {n_floor}</div></div>', unsafe_allow_html=True)
            if n_floor > 0:
                with st.expander("تفاصيل الأدوار"):
                    st.dataframe(floors[['السعر', 'المساحة', 'سعر_المتر']], use_container_width=True)

        with col4:
            st.markdown(f'<div class="market-card" style="border-top-color: #f1c40f;"><h3>📈 العام</h3><h2>{p_gen:,.0f}</h2><div class="stat-label">إجمالي العروض: {n_gen}</div></div>', unsafe_allow_html=True)

        st.divider()
        st.subheader("💡 جدوى المشروع (مقارنة بالسوق)")
        def show_feasibility(label, market_price):
            if market_price > 0:
                margin = ((market_price - cost_sqm) / cost_sqm) * 100
                st.write(f"**الربح المتوقع في {label}:**")
                st.progress(min(max((margin+50)/100, 0.0), 1.0))
                icon = "🚀" if margin > 20 else "⚠️" if margin > 0 else "⛔"
                st.caption(f"{icon} الهامش: **{margin:.1f}%** (سعر السوق: {market_price:,.0f})")
            else:
                st.info(f"لا توجد بيانات {label}")

        k1, k2 = st.columns(2)
        with k1:
            show_feasibility("الشقق 🏢", p_apt)
            show_feasibility("الأدوار 🏘️", p_floor)
        with k2:
            show_feasibility("الفلل 🏠", p_villa)
            show_feasibility("المتوسط العام 📈", p_gen)

# =========================================================
# 📑 التطبيق 2: تقرير المستثمر
# =========================================================
elif app_mode == "📑 تقرير المستثمر (PDF)":
    st.title("📑 إصدار التقرير الاستثماري")
    
    with st.expander("⚙️ بيانات التقرير والعنوان", expanded=True):
        c1, c2 = st.columns(2)
        st.session_state.project_name = c1.text_input("اسم المشروع", st.session_state.project_name)
        st.session_state.developer_name = c2.text_input("اسم المطور", st.session_state.developer_name)

    market_df = df[(df['الحي'] == st.session_state.calc_dist) & (df['Data_Category'].str.contains('Ask', na=False))]
    p_apt, _ = get_clean_median(market_df[market_df['نوع_العقار'] == 'شقة'])
    
    # Chart 1
    fig1, ax1 = plt.subplots(figsize=(5, 3))
    land_v = st.session_state.land_area * st.session_state.land_price
    build_v = st.session_state.land_area * st.session_state.build_ratio * st.session_state.turnkey_price
    rest_v = st.session_state.get('grand_total', 1) - land_v - build_v
    ax1.pie([land_v, build_v, rest_v], labels=['Land', 'Build', 'Other'], autopct='%1.1f%%', colors=['#3498db', '#e74c3c', '#95a5a6'])
    ax1.set_title("Cost Breakdown")

    # Chart 2
    fig2, ax2 = plt.subplots(figsize=(5, 3))
    ax2.bar(['My Cost', 'Market (Apt)'], [st.session_state.get('cost_sqm', 0), p_apt], color=['#2ecc71', '#3498db'])
    ax2.set_title("Competitiveness (SAR/SQM)")
    
    st.write("### معاينة الرسوم البيانية:")
    c_g1, c_g2 = st.columns(2)
    with c_g1: st.pyplot(fig1)
    with c_g2: st.pyplot(fig2)

    st.divider()
    
    if st.button("🖨️ تحميل التقرير (PDF)", type="primary"):
        report_data = {
            'project_name': st.session_state.project_name,
            'land_area': st.session_state.land_area,
            'grand_total': st.session_state.get('grand_total', 0),
            'cost_sqm': st.session_state.get('cost_sqm', 0),
            'market_apt': p_apt,
            'margin': ((p_apt - st.session_state.get('cost_sqm', 1))/st.session_state.get('cost_sqm', 1)*100) if p_apt > 0 else 0
        }
        
        pdf_bytes = create_pdf(report_data, [fig1, fig2])
        st.download_button("📥 تنزيل الملف", data=pdf_bytes, file_name="Feasibility_Report.pdf", mime="application/pdf")

# =========================================================
# 📊 التطبيق 3: لوحة البيانات
# =========================================================
elif app_mode == "📊 لوحة البيانات (Dashboard)":
    if df.empty: st.stop()
    
    districts = sorted(df['الحي'].astype(str).unique())
    selected_dist = st.sidebar.selectbox("تصفية حسب الحي:", ["الكل"] + districts)
    view_df = df if selected_dist == "الكل" else df[df['الحي'] == selected_dist]
    
    st.title(f"سجل البيانات العقارية: {selected_dist}")
    
    c1, c2 = st.columns(2)
    with c1: st.metric("عدد الصفقات (Sold)", len(view_df[view_df['Data_Category'].str.contains('Sold', na=False)]))
    with c2: st.metric("عدد العروض (Ask)", len(view_df[view_df['Data_Category'].str.contains('Ask', na=False)]))
    
    st.divider()

    tab1, tab2 = st.tabs(["💰 سجل الصفقات", "🏷️ عروض السوق"])
    cols = ['Source_File', 'الحي', 'السعر', 'المساحة', 'سعر_المتر', 'نوع_العقار']
    
    with tab1: st.dataframe(view_df[view_df['Data_Category'].str.contains('Sold', na=False)][cols], use_container_width=True)
    with tab2: st.dataframe(view_df[view_df['Data_Category'].str.contains('Ask', na=False)][cols], use_container_width=True)
