import streamlit as st
import pandas as pd
import data_bot  # المحرك الذكي

# إعداد الصفحة
st.set_page_config(page_title="المستشار العقاري - دراسة التكاليف", layout="wide", page_icon="🏗️")

# --- التنسيق ---
st.markdown("""
<style>
    .cost-card { background-color: #f8f9fa; padding: 20px; border-radius: 10px; border-left: 5px solid #2ecc71; margin-bottom: 10px; }
    .wafi-card { background-color: #fff3cd; padding: 20px; border-radius: 10px; border-left: 5px solid #ffc107; margin-bottom: 10px; }
    .total-row { font-weight: bold; font-size: 18px; background-color: #e9ecef; }
</style>
""", unsafe_allow_html=True)

# --- الاتصال بالمحرك (لجلب متوسطات السوق فقط) ---
@st.cache_resource
def load_bot():
    try: return data_bot.RealEstateBot()
    except: return None

if 'bot' not in st.session_state: st.session_state.bot = load_bot()
df = st.session_state.bot.df if hasattr(st.session_state.bot, 'df') else pd.DataFrame()

# ========================================================
# 🟢 القائمة الجانبية (مدخلات التكلفة الدقيقة)
# ========================================================
with st.sidebar:
    st.title("🏗️ حاسبة التكاليف")
    
    # 1. الأرض
    st.header("1️⃣ الأرض")
    land_area = st.number_input("مساحة الأرض (م²)", value=375, step=25)
    land_price = st.number_input("سعر المتر (ريال)", value=3500, step=50)
    tax_pct = st.number_input("ضريبة التصرفات (%)", value=5.0)
    comm_pct = st.number_input("السعي (%)", value=2.5)

    st.divider()

    # 2. البناء
    st.header("2️⃣ البناء والتطوير")
    build_ratio = st.slider("معامل البناء (FAR)", 1.0, 3.5, 2.3, help="إجمالي مسطح البناء / مساحة الأرض")
    # معادلة مسطح البناء
    bua = land_area * build_ratio
    st.info(f"مسطح البناء المتوقع: {bua:,.0f} م²")
    
    turnkey_price = st.number_input("سعر البناء (تسليم مفتاح)/م", value=1800)
    bone_price = st.number_input("سعر العظم (لحساب التأمين)/م", value=700, help="يستخدم فقط لحساب تأمين ملاذ")
    
    st.divider()

    # 3. الخدمات والرخص
    st.header("3️⃣ الخدمات والرخص")
    num_units = st.number_input("عدد الوحدات المتوقع", value=4, step=1)
    services_cost_per_unit = st.number_input("تكلفة العدادات والخدمات/وحدة", value=15000, help="مياه، كهرباء، صرف")
    permits_cost = st.number_input("إجمالي الرخص والتصاريح", value=25000, help="رخص البلدية، الدفاع المدني..")
    design_fees = st.number_input("تصميم وإشراف هندسي", value=40000)

    st.divider()

    # 4. نوع البيع (عادي vs خارطة)
    st.header("4️⃣ استراتيجية البيع")
    is_offplan = st.checkbox("بيع على الخارطة (Off-plan)?", value=False)
    
    wafi_fees = 0
    marketing_pct = 2.5 # افتراضي
    
    if is_offplan:
        st.caption("رسوم إضافية للبيع على الخارطة:")
        wafi_licence = st.number_input("رسوم رخصة وافي", value=10000)
        escrow_fees = st.number_input("رسوم أمين الحساب والمحاسب", value=40000)
        marketing_pct = st.number_input("نسبة التسويق (%)", value=3.5, help="عادة تكون أعلى في الخارطة")
        wafi_fees = wafi_licence + escrow_fees
    else:
        marketing_pct = st.number_input("نسبة التسويق (%)", value=2.5)


# ========================================================
# 🧮 المحرك الحسابي (تطبيق معادلتك)
# ========================================================

# 1. تكلفة الأرض
base_land_cost = land_area * land_price
land_tax_val = base_land_cost * (tax_pct / 100)
land_comm_val = base_land_cost * (comm_pct / 100)
total_land_cost = base_land_cost + land_tax_val + land_comm_val

# 2. تكلفة البناء
total_construction_cost = bua * turnkey_price # تسليم مفتاح
total_bone_cost = bua * bone_price # العظم لحساب التأمين

# 3. الرسوم المرتبطة
malath_insurance = total_bone_cost * 0.01 # حسب طلبك 1% من العظم
services_total = num_units * services_cost_per_unit

# 4. الطوارئ (إضافة مني لك)
contingency_pct = 0.02 # 2% احتياطي
sub_total_hard_costs = total_construction_cost + services_total + permits_cost + design_fees
contingency_val = sub_total_hard_costs * contingency_pct

# 5. الإجمالي
grand_total_cost = (
    total_land_cost + 
    total_construction_cost + 
    malath_insurance + 
    services_total + 
    permits_cost + 
    design_fees + 
    wafi_fees + 
    contingency_val
)

# متوسط التكلفة للمتر المبيع
cost_per_built_meter = grand_total_cost / bua

# ========================================================
# 📊 العرض (الداشبورد)
# ========================================================
st.title("💰 التحليل المالي للتكاليف")

if is_offplan:
    st.warning("⚠️ وضع التحليل: **بيع على الخارطة** (تمت إضافة رسوم وافي وأمين الحساب)")
else:
    st.success("✅ وضع التحليل: **تطوير تقليدي** (بيع بعد البناء)")

# --- 1. الملخص العلوي ---
col1, col2, col3 = st.columns(3)
with col1:
    st.metric("إجمالي تكلفة المشروع", f"{grand_total_cost:,.0f} ريال")
with col2:
    st.metric("تكلفة المتر (على المسطح)", f"{cost_per_built_meter:,.0f} ريال/م", help="شامل الأرض والبناء وكل المصاريف")
with col3:
    st.metric("مسطح البناء الإجمالي", f"{bua:,.0f} م²")

st.divider()

# --- 2. الجدول التفصيلي (فاتورة المشروع) ---
st.subheader("📑 تفاصيل التكاليف")

cost_breakdown = [
    # الأرض
    {"البند": "قيمة الأرض الأساسية", "التكلفة": base_land_cost, "النسبة": (base_land_cost/grand_total_cost)},
    {"البند": f"ضريبة ({tax_pct}%) + سعي ({comm_pct}%)", "التكلفة": land_tax_val + land_comm_val, "النسبة": ((land_tax_val + land_comm_val)/grand_total_cost)},
    
    # البناء
    {"البند": "تكلفة البناء (تسليم مفتاح)", "التكلفة": total_construction_cost, "النسبة": (total_construction_cost/grand_total_cost)},
    {"البند": "تأمين ملاذ (1% من العظم)", "التكلفة": malath_insurance, "النسبة": (malath_insurance/grand_total_cost)},
    
    # الخدمات والتصميم
    {"البند": f"عدادات وخدمات ({num_units} وحدات)", "التكلفة": services_total, "النسبة": (services_total/grand_total_cost)},
    {"البند": "رخص + تصميم وإشراف", "التكلفة": permits_cost + design_fees, "النسبة": ((permits_cost+design_fees)/grand_total_cost)},
    {"البند": "احتياطي طوارئ (2%)", "التكلفة": contingency_val, "النسبة": (contingency_val/grand_total_cost)},
]

# إضافة بنود وافي إذا كان بيع على الخارطة
if is_offplan:
    cost_breakdown.append({"البند": "⭐ رسوم وافي وأمين الحساب", "التكلفة": wafi_fees, "النسبة": (wafi_fees/grand_total_cost)})

# تحويل لجدول
df_costs = pd.DataFrame(cost_breakdown)
df_costs['النسبة'] = (df_costs['النسبة'] * 100).map('{:.1f}%'.format)

# عرض الجدول
st.dataframe(
    df_costs,
    column_config={
        "البند": st.column_config.TextColumn("البند", width="medium"),
        "التكلفة": st.column_config.NumberColumn("القيمة (ريال)", format="%d"),
        "النسبة": st.column_config.TextColumn("الوزن النسبي"),
    },
    use_container_width=True
)

# --- 3. الرسم البياني ---
st.subheader("🍰 توزيع الكعكة (أين تذهب أموالك؟)")
chart_df = df_costs.copy()
chart_df.set_index('البند', inplace=True)
st.bar_chart(chart_df['التكلفة'])

# --- 4. نصيحة الكود ---
st.divider()
if is_offplan:
    st.markdown("""
    ### 💡 مميزات وعيوب البيع على الخارطة في هذا المشروع:
    * **الميزة:** لا تحتاج لدفع تكلفة البناء (2. البناء) من جيبك بالكامل، ستمولها من دفعات المشترين.
    * **التكلفة:** دفعت زيادة **{:,} ريال** (رسوم وافي وأمين حساب).
    * **النصيحة:** تأكد أن السيولة في "حساب الضمان" تغطي دفعات المقاول في وقتها لتجنب تعثر المشروع.
    """.format(wafi_fees))
else:
    st.markdown("""
    ### 💡 التطوير التقليدي:
    * **الميزة:** حرية كاملة في التصرف، لا يوجد مدقق حسابات خارجي يصرف لك الدفعات.
    * **العبء:** يجب أن توفر مبلغ **{:,} ريال** (إجمالي التكلفة) كاملاً قبل البدء أو عبر تمويل بنكي بفوائد.
    """.format(grand_total_cost))
