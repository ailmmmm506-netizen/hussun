import streamlit as st
import numpy as np
import pandas as pd
import time

# --- إعدادات الصفحة ---
st.set_page_config(
    page_title="المطور العقاري برو | Real Estate Pro",
    layout="wide",
    page_icon="🏗️",
    initial_sidebar_state="expanded"
)

# --- تنسيق CSS احترافي ---
st.markdown("""
<style>
    .metric-card {background-color: #ffffff; padding: 15px; border-radius: 10px; border-left: 5px solid #1f77b4; box-shadow: 0 2px 5px rgba(0,0,0,0.1);}
    .highlight {color: #2e7d32; font-weight: bold;}
    .loss {color: #c62828; font-weight: bold;}
</style>
""", unsafe_allow_html=True)

# --- محرك التحليل المالي والزمني ---
class FinancialEngine:
    def __init__(self, inputs):
        self.inputs = inputs

    def generate_cash_flow(self):
        duration = self.inputs['duration']
        total_months = range(duration + 1)
        
        # 1. التكاليف (Outflows)
        land_cost = self.inputs['area'] * self.inputs['land_price']
        total_const = self.inputs['area'] * self.inputs['floors'] * self.inputs['const_cost']
        soft_costs = (land_cost + total_const) * (self.inputs['soft_cost_pct'] / 100)
        
        # توزيع التكاليف زمنياً
        # الشهر 0: شراء الأرض + 20% مصاريف إدارية
        costs_timeline = np.zeros(duration + 1)
        costs_timeline[0] = land_cost + (soft_costs * 0.2)
        
        # البناء يبدأ من الشهر 1 وينتهي قبل شهرين من النهاية
        const_months = max(1, duration - 3)
        monthly_const = total_const / const_months
        monthly_soft = (soft_costs * 0.8) / const_months
        
        for m in range(1, const_months + 1):
            costs_timeline[m] = monthly_const + monthly_soft

        # 2. الإيرادات (Inflows)
        # نفترض البيع يبدأ بعد اكتمال 60% من المشروع (على الخارطة) أو عند الانتهاء
        start_sales_month = int(duration * 0.6)
        sales_duration = duration - start_sales_month
        
        total_revenue = (self.inputs['area'] * self.inputs['floors'] * self.inputs['efficiency'] / 100) * self.inputs['sell_price']
        
        revenue_timeline = np.zeros(duration + 1)
        if sales_duration > 0:
            monthly_sales = total_revenue / sales_duration
            for m in range(start_sales_month, duration + 1):
                revenue_timeline[m] = monthly_sales
        else:
             revenue_timeline[duration] = total_revenue

        # 3. صافي التدفق التراكمي
        net_monthly = revenue_timeline - costs_timeline
        cumulative_cash = np.cumsum(net_monthly)
        
        df = pd.DataFrame({
            "الشهر": total_months,
            "مصاريف": -costs_timeline, # بالسالب للرسم
            "إيرادات": revenue_timeline,
            "صافي شهري": net_monthly,
            "تراكمي (السيولة)": cumulative_cash
        })
        
        return {
            "df": df,
            "total_cost": land_cost + total_const + soft_costs,
            "total_revenue": total_revenue,
            "profit": total_revenue - (land_cost + total_const + soft_costs),
            "roi": ((total_revenue - (land_cost + total_const + soft_costs)) / (land_cost + total_const + soft_costs)) * 100,
            "peak_cash_needed": abs(min(cumulative_cash)) # أقصى سيولة يحتاجها المشروع
        }

# --- الواجهة الجانبية (مدخلات دقيقة) ---
with st.sidebar:
    st.title("🏗️ مدخلات المشروع")
    
    with st.expander("1. بيانات الأرض", expanded=True):
        area = st.number_input("المساحة (م2)", 500, 10000, 800)
        land_price = st.number_input("سعر متر الأرض (ريال)", 1000, 20000, 3500)
    
    with st.expander("2. التطوير والبناء", expanded=True):
        floors = st.number_input("عدد الأدوار", 1.0, 50.0, 4.0)
        const_cost = st.number_input("تكلفة البناء (ريال/م2)", 1000, 5000, 2200)
        soft_cost_pct = st.slider("مصاريف إدارية وتسويق %", 5, 20, 12)
        duration = st.slider("مدة المشروع (أشهر)", 6, 36, 18)
    
    with st.expander("3. المبيعات", expanded=True):
        efficiency = st.slider("كفاءة البيع (الصافي) %", 60, 95, 80)
        # ميزة: حساب سعر البيع تلقائياً بناء على هامش ربح
        target_margin = st.number_input("هامش الربح المستهدف %", 15, 100, 25)
        # معادلة عكسية تقديرية لسعر البيع المقترح
        est_cost = (area * land_price) + (area * floors * const_cost * 1.15)
        est_rev = est_cost * (1 + target_margin/100)
        suggested_price = est_rev / (area * floors * efficiency / 100)
        
        st.info(f"سعر السوق المقترح: {suggested_price:,.0f} ريال")
        sell_price = st.number_input("سعر بيع المتر المعتمد (ريال)", 1000, 50000, int(suggested_price))

    btn_calc = st.button("📊 بدء التحليل المالي", type="primary")

# --- الواجهة الرئيسية ---
st.title("نظام تحليل الجدوى والتدفقات النقدية")

if btn_calc:
    inputs = {
        "area": area, "land_price": land_price, "floors": floors,
        "const_cost": const_cost, "soft_cost_pct": soft_cost_pct,
        "duration": duration, "efficiency": efficiency, "sell_price": sell_price
    }
    
    engine = FinancialEngine(inputs)
    results = engine.generate_cash_flow()
    
    # 1. الملخص التنفيذي
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("صافي الربح", f"{results['profit']:,.0f} ريال")
    col2.metric("العائد ROI", f"{results['roi']:.1f}%", delta_color="normal" if results['roi'] > 20 else "inverse")
    col3.metric("أقصى سيولة مطلوبة (رأس المال)", f"{results['peak_cash_needed']:,.0f} ريال", help="أقصى مبلغ تدفعه من جيبك قبل أن تبدأ البيع يغطي التكاليف")
    col4.metric("إجمالي التكلفة", f"{results['total_cost']:,.0f} ريال")
    
    st.markdown("---")
    
    # 2. الرسم البياني للتدفقات (أهم جزء للموثوقية)
    st.subheader("📈 تحليل السيولة (Cash Flow)")
    tab1, tab2 = st.tabs(["المنحنى التراكمي (J-Curve)", "جدول التدفقات الشهرية"])
    
    with tab1:
        st.caption("هذا الرسم يوضح متى ستحتاج لدفع المال (تحت الصفر) ومتى تبدأ بجني الأرباح (فوق الصفر).")
        st.line_chart(results['df'].set_index("الشهر")['تراكمي (السيولة)'])
        
        if results['roi'] < 0:
            st.error("⚠️ تحذير: المشروع يحقق خسارة في نهايته. راجع سعر البيع أو تكلفة الأرض.")
        else:
            breakeven_month = results['df'][results['df']['تراكمي (السيولة)'] >= 0].index.min()
            if pd.notna(breakeven_month):
                st.success(f"✅ نقطة التعادل (Break-even): تسترد رأس مالك في الشهر رقم **{breakeven_month}**.")
    
    with tab2:
        st.dataframe(results['df'].style.format("{:,.0f}"))

    st.markdown("---")
    
    # 3. تقرير الحساسية (تحليل المخاطر)
    st.subheader("🎲 تحليل المخاطر (Sensitivity Analysis)")
    st.caption("ماذا لو انخفض سعر البيع أو زادت التكاليف؟")
    
    risk_data = []
    base_roi = results['roi']
    
    for p_change in [-10, -5, 0, 5, 10]: # تغيير سعر البيع
        rev_change = results['total_revenue'] * (1 + p_change/100)
        profit_change = rev_change - results['total_cost']
        roi_change = (profit_change / results['total_cost']) * 100
        risk_data.append(roi_change)
        
    risk_df = pd.DataFrame(
        [risk_data], 
        columns=["-10%", "-5%", "السعر الحالي", "+5%", "+10%"],
        index=["تغير العائد ROI"]
    )
    
    st.dataframe(risk_df.style.background_gradient(cmap="RdYlGn", vmin=0, vmax=40).format("{:.1f}%"))

else:
    st.info("👈 قم بتعبئة بيانات المشروع في القائمة الجانبية بدقة لضمان نتيجة موثوقة.")
    st.markdown("""
    ### لماذا هذا التحليل موثوق؟
    * **لا يعتمد على الصدفة:** الحسابات دقيقة بناءً على معطياتك.
    * **يحسب عامل الوقت:** يوضح لك متى تحتاج الكاش (Cash Burn).
    * **يحدد نقطة التعادل:** متى يرجع لك رأس مالك بالضبط.
    """)
