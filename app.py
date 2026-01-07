import streamlit as st
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import requests
import re
import random

# --- إعدادات الصفحة ---
st.set_page_config(
    page_title="المطور العقاري - النظام الخبير | v10.0",
    layout="wide",
    page_icon="💎",
    initial_sidebar_state="expanded"
)

# --- تنسيق CSS احترافي ---
st.markdown("""
<style>
    .main {background-color: #f8f9fa;}
    .stMetric {background-color: white; border-radius: 10px; padding: 15px; box-shadow: 0 2px 5px rgba(0,0,0,0.05);}
    .big-number {font-size: 28px; font-weight: bold; color: #1f77b4;}
    .tier-badge {padding: 5px 10px; border-radius: 5px; color: white; font-weight: bold; text-align: center; margin-bottom: 10px;}
    .tier-a {background-color: #27ae60;} /* Green */
    .tier-b {background-color: #f39c12;} /* Orange */
    .tier-c {background-color: #c0392b;} /* Red */
    .warning-box {background-color: #ffebee; color: #c62828; padding: 10px; border-radius: 5px; border: 1px solid #ef9a9a;}
    .success-box {background-color: #e8f5e9; color: #2e7d32; padding: 10px; border-radius: 5px; border: 1px solid #a5d6a7;}
</style>
""", unsafe_allow_html=True)

# --- دوال مساعدة ---
def parse_maps_link(link):
    if not link: return None, None
    match = re.search(r'@([-.\d]+),([-.\d]+)', link)
    if match: return float(match.group(1)), float(match.group(2))
    return 24.7136, 46.6753

# --- المحرك الذكي (Core Engine) ---
class ExpertEngine:
    def __init__(self, inputs):
        self.inputs = inputs

    def classify_project(self):
        # حساب النقاط بناءً على المعايير الـ 7
        score = 0
        # كل إجابة A=3, B=2, C=1
        score += self.inputs['q_ac']
        score += self.inputs['q_smart']
        score += self.inputs['q_floors']
        score += self.inputs['q_windows']
        score += self.inputs['q_sanitary']
        score += self.inputs['q_amenities']
        score += self.inputs['q_warranty']
        
        if score >= 18: return "Class A (فاخر)", "tier-a", self.inputs['price_a']
        elif score >= 12: return "Class B (متوسط)", "tier-b", self.inputs['price_b']
        else: return "Class C (اقتصادي)", "tier-c", self.inputs['price_c']

    def calculate_pricing_strategy(self, my_tier_price):
        exec_price = self.inputs['price_exec']
        
        # 1. حساب الفجوة (Gap Analysis)
        if my_tier_price > 0:
            gap = (my_tier_price - exec_price) / my_tier_price
        else:
            gap = 0
            
        # 2. تحديد الوزنة بناءً على صحة السوق
        if gap <= 0.10: # فجوة طبيعية (أقل من 10%) - سوق صحي
            weight_offer = 0.60
            weight_exec = 0.40
            market_status = "سوق صحي (متوازن)"
            color = "green"
        elif gap >= 0.20: # فجوة كبيرة (أكثر من 20%) - سوق متضخم/راكد
            weight_offer = 0.20
            weight_exec = 0.80 # نميل للواقعية أكثر
            market_status = "سوق حذر (فجوة سعرية عالية)"
            color = "red"
        else: # منطقة رمادية
            weight_offer = 0.50
            weight_exec = 0.50
            market_status = "سوق متوسط"
            color = "orange"
            
        # 3. السعر الموزون
        # نضيف علاوة 10% لسعر التنفيذ لأنه غالباً لمباني جاهزة/قديمة ومشروعك جديد
        adjusted_exec = exec_price * 1.10 
        base_price = (my_tier_price * weight_offer) + (adjusted_exec * weight_exec)
        
        # 4. علاوات المشروع (Premiums)
        premium = 0
        if self.inputs['is_corner']: premium += 0.03
        if self.inputs['on_park']: premium += 0.05
        if self.inputs['wide_street']: premium += 0.02
        
        final_price = base_price * (1 + premium)
        
        return final_price, market_status, gap*100

    def run_financials(self, final_price):
        land_cost = self.inputs['area'] * self.inputs['land_price']
        total_bua = self.inputs['area'] * self.inputs['floors']
        net_sellable = total_bua * (self.inputs['efficiency'] / 100)
        
        const_cost_total = total_bua * self.inputs['const_cost']
        soft_costs = (land_cost + const_cost_total) * (self.inputs['soft_pct'] / 100)
        total_dev_cost = land_cost + const_cost_total + soft_costs
        
        total_revenue = net_sellable * final_price
        net_profit = total_revenue - total_dev_cost
        roi = (net_profit / total_dev_cost) * 100
        breakeven = total_dev_cost / net_sellable if net_sellable > 0 else 0
        
        # Ticket Price Check
        unit_area_example = 150 # مساحة شقة نموذجية
        ticket_price = final_price * unit_area_example
        
        # Cash Flow
        duration = self.inputs['duration']
        timeline = range(duration + 1)
        cash_flow = np.zeros(duration + 1)
        cash_flow[0] = -(land_cost + soft_costs * 0.2)
        build_months = max(1, duration - 2)
        monthly_const = (const_cost_total + soft_costs * 0.8) / build_months
        for m in range(1, build_months + 1): cash_flow[m] -= monthly_const
        start_sales = int(duration * 0.5)
        sales_months = duration - start_sales + 1
        monthly_rev = total_revenue / sales_months
        for m in range(start_sales, duration + 1): 
            if m <= duration: cash_flow[m] += monthly_rev
        cumulative = np.cumsum(cash_flow)

        return {
            "profit": net_profit, "roi": roi, "breakeven": breakeven,
            "total_cost": total_dev_cost, "revenue": total_revenue,
            "peak_cash": abs(min(cumulative)), "cash_flow": pd.DataFrame({"الشهر": timeline, "السيولة": cumulative}),
            "ticket_price": ticket_price, "net_sellable": net_sellable
        }

# --- القائمة الجانبية (Inputs) ---
with st.sidebar:
    st.title("💎 إعدادات النظام الخبير")
    
    # 1. روبوت البيانات
    with st.expander("🤖 1. بيانات السوق (الروبوت)", expanded=True):
        city = st.text_input("الحي", "الرياض - الملقا")
        if st.button("جلب متوسطات السوق"):
            # محاكاة ذكية للبيانات
            st.session_state['m_a'] = 9500
            st.session_state['m_b'] = 7800
            st.session_state['m_c'] = 6200
            st.session_state['m_exec'] = 6500
            st.session_state['m_ticket'] = 1300000
            st.success("تم سحب البيانات!")

        price_a = st.number_input("سعر فئة A (المطورين)", value=st.session_state.get('m_a', 8500))
        price_b = st.number_input("سعر فئة B (المطورين)", value=st.session_state.get('m_b', 7200))
        price_c = st.number_input("سعر فئة C (المطورين)", value=st.session_state.get('m_c', 6000))
        price_exec = st.number_input("سعر الصفقات (التنفيذ)", value=st.session_state.get('m_exec', 6300), help="من البورصة العقارية")
        max_ticket = st.number_input("سقف سعر الشقة بالحي", value=st.session_state.get('m_ticket', 1200000), help="أعلى مبلغ يدفعه العميل في هذا الحي")

    # 2. تصنيف المشروع (7 Questions)
    with st.expander("🏗️ 2. تصنيف جودة مشروعك", expanded=True):
        st.caption("أجب بصدق ليقوم النظام بتصنيفك:")
        # Scoring: A=3, B=2, C=1
        q_ac = st.radio("التكييف", ["مخفي كامل (3)", "مخفي صالات (2)", "سبليت (1)"], index=1)
        q_smart = st.radio("التقنية", ["سمارت كامل (3)", "دخول ذكي (2)", "بدون (1)"], index=1)
        q_floors = st.radio("الأرضيات", ["رخام/بورسلان نخب (3)", "بورسلان عادي (2)", "سيراميك (1)"], index=1)
        q_windows = st.radio("النوافذ/الأبواب", ["بانوراما/خشب (3)", "دبل/WPC (2)", "تجاري (1)"], index=1)
        q_sanitary = st.radio("الصحية", ["معلق/مدفون (3)", "أرضي ماركة (2)", "تجاري (1)"], index=1)
        q_amenities = st.radio("المرافق", ["نادي/لاونج (3)", "تراس/سطح (2)", "بدون (1)"], index=1)
        q_warranty = st.radio("الضمانات", ["شامل+صيانة (3)", "هيكل+أساسي (2)", "الحد الأدنى (1)"], index=1)
        
        # Map inputs to scores
        score_map = {"3": 3, "2": 2, "1": 1}
        inputs_q = {
            'q_ac': score_map[q_ac[-2]], 'q_smart': score_map[q_smart[-2]],
            'q_floors': score_map[q_floors[-2]], 'q_windows': score_map[q_windows[-2]],
            'q_sanitary': score_map[q_sanitary[-2]], 'q_amenities': score_map[q_amenities[-2]],
            'q_warranty': score_map[q_warranty[-2]]
        }

    # 3. بيانات الأرض والتطوير
    with st.expander("📐 3. الأرض والتكاليف", expanded=False):
        map_link = st.text_input("رابط الموقع")
        area = st.number_input("المساحة (م2)", value=900)
        land_price = st.number_input("سعر الأرض", value=3500)
        street_w = st.checkbox("شارع > 25م؟")
        is_corner = st.checkbox("زاوية؟")
        on_park = st.checkbox("على حديقة؟")
        
        floors = st.number_input("عدد الأدوار", value=4.0)
        const_cost = st.number_input("تكلفة البناء", value=2200)
        soft_pct = st.slider("مصاريف %", 5, 20, 12)
        duration = st.slider("المدة", 12, 36, 18)
        efficiency = st.slider("كفاءة البيع %", 60, 95, 80)

    btn = st.button("🚀 تشغيل التحليل الشامل", type="primary")

# --- الواجهة الرئيسية ---
st.title(f"تقرير الجدوى الذكي: {city}")

if btn:
    # تجميع المدخلات
    all_inputs = {
        'price_a': price_a, 'price_b': price_b, 'price_c': price_c, 'price_exec': price_exec,
        'area': area, 'land_price': land_price, 'floors': floors, 'const_cost': const_cost,
        'soft_pct': soft_pct, 'duration': duration, 'efficiency': efficiency,
        'is_corner': is_corner, 'on_park': on_park, 'wide_street': street_w,
        **inputs_q
    }
    
    engine = ExpertEngine(all_inputs)
    
    # 1. التصنيف
    tier_name, tier_class, comp_price = engine.classify_project()
    
    # 2. التسعير
    rec_price, mkt_status, gap_pct = engine.calculate_pricing_strategy(comp_price)
    
    # 3. المالية
    fin = engine.run_financials(rec_price)
    
    # --- العرض (Tabs) ---
    t1, t2, t3, t4 = st.tabs(["🧠 تحليل التسعير", "💰 الجدوى المالية", "📉 التدفقات", "📋 التقرير"])
    
    with t1:
        c1, c2 = st.columns([1, 2])
        
        with c1:
            st.subheader("تصنيف المشروع")
            st.markdown(f"<div class='tier-badge {tier_class}' style='font-size:20px;'>{tier_name}</div>", unsafe_allow_html=True)
            st.caption(f"تمت مقارنتك بمتوسط: {comp_price:,.0f} ريال")
            
            st.divider()
            st.metric("صحة السوق", mkt_status, delta=f"الفجوة {gap_pct:.1f}%", delta_color="inverse")
            
        with c2:
            st.subheader("🎯 السعر الموصى به")
            st.markdown(f"<div class='big-number'>{rec_price:,.0f} ريال / م2</div>", unsafe_allow_html=True)
            
            # Ticket Price Check
            st.write("---")
            st.write("📊 **اختبار القدرة الشرائية (Ticket Price):**")
            col_t1, col_t2 = st.columns(2)
            col_t1.metric("سعر الشقة المقدر (150م)", f"{fin['ticket_price']:,.0f} ريال")
            col_t2.metric("سقف الحي", f"{max_ticket:,.0f} ريال")
            
            if fin['ticket_price'] > max_ticket:
                diff = fin['ticket_price'] - max_ticket
                st.markdown(f"""
                <div class='warning-box'>
                ⚠️ <b>تنبيه هام:</b> سعر الشقة الإجمالي يتجاوز قدرة الحي بـ {diff:,.0f} ريال.<br>
                الحل: إما تقليل مساحات الشقق (صغر الوحدات) أو تقليل المواصفات لخفض السعر.
                </div>
                """, unsafe_allow_html=True)
            else:
                st.markdown("<div class='success-box'>✅ ممتاز: السعر الإجمالي للشقة ضمن النطاق المقبول في الحي.</div>", unsafe_allow_html=True)

    with t2:
        k1, k2, k3, k4 = st.columns(4)
        k1.metric("صافي الربح", f"{fin['profit']:,.0f} ﷼")
        k2.metric("العائد ROI", f"{fin['roi']:.2f}%", delta_color="normal" if fin['roi']>25 else "inverse")
        k3.metric("نقطة التعادل", f"{fin['breakeven']:,.0f} ﷼")
        k4.metric("رأس المال المطلوب", f"{fin['peak_cash']:,.0f} ﷼")
        
        st.subheader("تحليل الرسم البياني")
        # مقارنة سعرك مع السوق والتكلفة
        fig, ax = plt.subplots(figsize=(8, 3))
        items = ['تكلفتك', 'تنفيذ السوق', 'منافسينك', 'سعرك المقترح']
        vals = [fin['breakeven'], price_exec, comp_price, rec_price]
        colors = ['red', 'gray', 'orange', 'green']
        bars = ax.barh(items, vals, color=colors)
        for bar in bars:
            width = bar.get_width()
            ax.text(width, bar.get_y() + bar.get_height()/2, f'{width:,.0f}', ha='left', va='center')
        st.pyplot(fig)

    with t3:
        st.line_chart(fin['cash_flow'].set_index("الشهر")['السيولة'])
        st.dataframe(fin['cash_flow'].style.format("{:,.0f}"))

    with t4:
        pitch = f"""
        **دراسة جدوى مبدئية - {city}**
        تصنيف المشروع: {tier_name}
        
        **التسعير:**
        - سعر العرض (المنافسين): {comp_price} ريال
        - سعر التنفيذ (السوق): {price_exec} ريال
        - السعر المعتمد للدراسة: {rec_price:,.0f} ريال
        
        **النتائج:**
        - الربح المتوقع: {fin['profit']:,.0f} ريال
        - العائد: {fin['roi']:.2f}%
        - ملاحظة السقف السعري: {"⚠️ مرتفع" if fin['ticket_price'] > max_ticket else "✅ مناسب"}
        """
        st.text_area("نص التقرير", pitch, height=300)

else:
    st.info("👈 ابدأ بتعبئة بيانات السوق والتصنيف في القائمة الجانبية.")
