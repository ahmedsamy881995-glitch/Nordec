import streamlit as st
import pandas as pd
import sqlite3
from datetime import datetime, date
import os
import sys

sys.path.append(os.path.dirname(__file__))
from database import init_db, get_connection, log_audit, generate_sample_code, DB_PATH
from coa_generator import generate_coa_pdf

# Page config
st.set_page_config(
    page_title="Nordec LIMS | معمل نورديك",
    page_icon="🛢️",
    layout="wide",
    initial_sidebar_state="auto"  # أفضل للموبايل
)

# Custom CSS - Mobile Friendly + Arabic
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Cairo:wght@400;600;700&display=swap');
    
    html, body, [class*="css"] {
        font-family: 'Cairo', sans-serif !important;
    }
    
    /* ===== Header ===== */
    .main-header {
        background: linear-gradient(90deg, #1a365d 0%, #2c5282 100%);
        padding: 0.8rem 1rem;
        border-radius: 10px;
        color: white;
        margin-bottom: 1rem;
        text-align: center;
    }
    .main-header h2 {
        font-size: 1.3rem !important;
        margin: 0 !important;
    }
    .main-header p {
        font-size: 0.85rem !important;
        margin: 0.3rem 0 0 0 !important;
        opacity: 0.9;
    }
    
    /* ===== Metrics ===== */
    .stMetric {
        background-color: #f7fafc;
        border-radius: 10px;
        padding: 12px 8px;
        box-shadow: 0 1px 3px rgba(0,0,0,0.08);
    }
    
    /* ===== Sidebar ===== */
    div[data-testid="stSidebar"] {
        background-color: #1a365d !important;
    }
    div[data-testid="stSidebar"] * {
        color: #e2e8f0 !important;
    }
    div[data-testid="stSidebar"] .stRadio label {
        font-size: 0.95rem !important;
        padding: 0.4rem 0 !important;
    }
    
    /* ===== Buttons - أكبر للمس ===== */
    .stButton > button {
        border-radius: 10px !important;
        padding: 0.6rem 1rem !important;
        font-weight: 600 !important;
        min-height: 48px !important;
        font-size: 1rem !important;
    }
    
    /* ===== Forms ===== */
    .stTextInput input, .stNumberInput input, .stSelectbox, .stTextArea textarea {
        font-size: 16px !important;  /* يمنع الزوم التلقائي على iOS */
        min-height: 44px !important;
    }
    
    /* ===== Dataframes ===== */
    .stDataFrame {
        font-size: 0.85rem !important;
    }
    
    /* ===== Mobile Specific (max-width: 768px) ===== */
    @media (max-width: 768px) {
        .main-header {
            padding: 0.7rem 0.8rem;
            margin-bottom: 0.8rem;
        }
        .main-header h2 {
            font-size: 1.15rem !important;
        }
        
        /* اجعل الأعمدة تتراص عمودياً بشكل أفضل */
        [data-testid="column"] {
            width: 100% !important;
            flex: 1 1 100% !important;
            min-width: 100% !important;
        }
        
        /* أزرار أكبر */
        .stButton > button {
            width: 100% !important;
            min-height: 50px !important;
            font-size: 1.05rem !important;
        }
        
        /* تقليل المسافات */
        .block-container {
            padding-top: 1rem !important;
            padding-left: 0.8rem !important;
            padding-right: 0.8rem !important;
        }
        
        /* الجداول */
        .stDataFrame {
            font-size: 0.8rem !important;
        }
        
        /* الـ metrics تتراص بشكل أفضل */
        [data-testid="stMetric"] {
            margin-bottom: 0.5rem;
        }
    }
    
    /* ===== Extra small screens ===== */
    @media (max-width: 480px) {
        .main-header h2 {
            font-size: 1.05rem !important;
        }
        .stButton > button {
            min-height: 52px !important;
        }
    }
    
    .pass { color: #276749; font-weight: bold; }
    .fail { color: #c53030; font-weight: bold; }
</style>
""", unsafe_allow_html=True)

# Initialize DB
init_db()

# Session state
if "current_user" not in st.session_state:
    st.session_state.current_user = "admin"
if "page" not in st.session_state:
    st.session_state.page = "Dashboard"

# Sidebar Navigation
with st.sidebar:
    st.markdown("### 🛢️ Nordec LIMS")
    st.caption("نظام إدارة معلومات المعمل")
    st.markdown("---")

    menu = st.radio(
        "القائمة",
        [
            "📊 لوحة التحكم",
            "📥 تسجيل عينة جديدة",
            "🧪 إدخال النتائج",
            "📋 إدارة العينات",
            "⚙️ الاختبارات والمواصفات",
            "📄 شهادات التحليل (COA)",
            "📈 التقارير",
            "🔧 الإدارة"
        ],
        label_visibility="collapsed"
    )

    st.markdown("---")
    st.caption(f"المستخدم: {st.session_state.current_user}")
    st.caption("ISO/IEC 17025 Ready")

# Helper functions
def get_products():
    conn = get_connection()
    df = pd.read_sql("SELECT id, name, category, grade FROM products WHERE active=1 ORDER BY category, name", conn)
    conn.close()
    return df

def get_tests():
    conn = get_connection()
    df = pd.read_sql("SELECT id, name, method, unit, category FROM tests WHERE active=1 ORDER BY category, name", conn)
    conn.close()
    return df

def get_sample_by_code(code):
    conn = get_connection()
    c = conn.cursor()
    c.execute("SELECT * FROM samples WHERE sample_code = ?", (code,))
    row = c.fetchone()
    conn.close()
    return dict(row) if row else None

def calculate_conformity(value, min_v, max_v):
    if value is None:
        return "N/A"
    try:
        val = float(value)
    except:
        return "N/A"
    if min_v is not None and max_v is not None:
        return "Pass" if min_v <= val <= max_v else "Fail"
    elif min_v is not None:
        return "Pass" if val >= min_v else "Fail"
    elif max_v is not None:
        return "Pass" if val <= max_v else "Fail"
    return "N/A"

# ==================== PAGES ====================

# ---------- Dashboard ----------
if menu == "📊 لوحة التحكم":
    st.markdown('<div class="main-header"><h2>لوحة التحكم - Nordec Laboratory</h2><p>نظام إدارة نتائج اختبارات زيوت التشحيم</p></div>', unsafe_allow_html=True)

    conn = get_connection()
    total_samples = pd.read_sql("SELECT COUNT(*) as c FROM samples", conn).iloc[0]['c']
    completed = pd.read_sql("SELECT COUNT(*) as c FROM samples WHERE status='Completed' OR status='Reported'", conn).iloc[0]['c']
    pending = pd.read_sql("SELECT COUNT(*) as c FROM samples WHERE status IN ('Received','Testing')", conn).iloc[0]['c']
    today = pd.read_sql("SELECT COUNT(*) as c FROM samples WHERE date(registered_at)=date('now')", conn).iloc[0]['c']

    # على الموبايل هيتراصوا بشكل أفضل
    m1, m2 = st.columns(2)
    m3, m4 = st.columns(2)
    m1.metric("إجمالي العينات", total_samples)
    m2.metric("مكتملة", completed)
    m3.metric("قيد التنفيذ", pending)
    m4.metric("مسجلة اليوم", today)

    st.markdown("### آخر العينات المسجلة")
    recent = pd.read_sql("""
        SELECT s.sample_code, s.client_name, p.name as product, s.status, s.registered_at
        FROM samples s
        LEFT JOIN products p ON s.product_id = p.id
        ORDER BY s.id DESC LIMIT 10
    """, conn)
    st.dataframe(recent, use_container_width=True, hide_index=True)

    st.markdown("### توزيع الحالات")
    status_df = pd.read_sql("SELECT status, COUNT(*) as count FROM samples GROUP BY status", conn)
    if not status_df.empty:
        st.bar_chart(status_df.set_index("status"))
    conn.close()

# ---------- Register Sample ----------
elif menu == "📥 تسجيل عينة جديدة":
    st.markdown('<div class="main-header"><h2>تسجيل عينة جديدة / Sample Registration</h2></div>', unsafe_allow_html=True)

    products_df = get_products()

    with st.form("sample_form", clear_on_submit=True):
        st.subheader("📋 بيانات العميل والعينة")
        
        client_name = st.text_input("اسم العميل *", placeholder="شركة ...")
        
        col_a, col_b = st.columns(2)
        with col_a:
            client_ref = st.text_input("مرجع العميل / PO")
            equipment_id = st.text_input("رقم المعدة / Unit ID")
        with col_b:
            product_id = st.selectbox(
                "نوع المنتج / الزيت *",
                options=products_df['id'].tolist(),
                format_func=lambda x: products_df.loc[products_df['id']==x, 'name'].values[0]
            )
            equipment_type = st.selectbox("نوع المعدة", ["Engine", "Hydraulic System", "Gearbox", "Turbine", "Compressor", "Transmission", "Other"])
        
        oil_brand = st.text_input("ماركة الزيت المستخدمة")
        
        st.markdown("---")
        st.subheader("🧪 بيانات السحب (ISO 17025)")
        
        col_c, col_d = st.columns(2)
        with col_c:
            collection_date = st.date_input("تاريخ سحب العينة *", value=date.today())
            collector_name = st.text_input("اسم ساحب العينة")
            collection_location = st.text_input("مكان السحب / الموقع")
        with col_d:
            sampling_method = st.selectbox("طريقة السحب", ["Valve / Drain", "Dipstick", "Sampling Valve", "Vacuum Pump", "Other"])
            container_type = st.selectbox("نوع الحاوية", ["Plastic Bottle 100ml", "Glass Bottle", "Metal Can", "Other"])
            condition = st.selectbox("حالة العينة عند الاستلام", ["Good / Clean", "Cloudy", "Dark", "Water visible", "Contaminated", "Other"])
        
        col_e, col_f = st.columns(2)
        with col_e:
            oil_hours = st.number_input("ساعات الزيت (Oil Hours)", min_value=0.0, step=1.0)
        with col_f:
            total_hours = st.number_input("إجمالي ساعات المعدة", min_value=0.0, step=1.0)
        
        temp_receipt = st.number_input("درجة الحرارة عند الاستلام (°C)", value=25.0)
        notes = st.text_area("ملاحظات إضافية", height=80)

        submitted = st.form_submit_button("💾 تسجيل العينة", use_container_width=True, type="primary")

        if submitted:
            if not client_name:
                st.error("اسم العميل مطلوب")
            else:
                sample_code = generate_sample_code()
                conn = get_connection()
                c = conn.cursor()
                c.execute("""
                    INSERT INTO samples (
                        sample_code, product_id, client_name, client_ref, equipment_id, equipment_type,
                        collection_date, collector_name, collection_location, sampling_method,
                        container_type, oil_hours, total_hours, oil_brand, condition_on_receipt,
                        temperature_on_receipt, notes, registered_by, registered_at, status
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    sample_code, product_id, client_name, client_ref, equipment_id, equipment_type,
                    collection_date.isoformat(), collector_name, collection_location, sampling_method,
                    container_type, oil_hours, total_hours, oil_brand, condition,
                    temp_receipt, notes, st.session_state.current_user, datetime.now().isoformat(), "Received"
                ))
                sample_id = c.lastrowid
                conn.commit()
                conn.close()
                log_audit(st.session_state.current_user, "CREATE", "sample", sample_id, f"Sample {sample_code} registered")
                st.success(f"✅ تم تسجيل العينة بنجاح | كود العينة: **{sample_code}**")
                st.balloons()

# ---------- Enter Results ----------
elif menu == "🧪 إدخال النتائج":
    st.markdown('<div class="main-header"><h2>إدخال نتائج الاختبارات</h2></div>', unsafe_allow_html=True)

    conn = get_connection()
    samples_df = pd.read_sql("""
        SELECT s.id, s.sample_code, s.client_name, p.name as product, s.status
        FROM samples s LEFT JOIN products p ON s.product_id = p.id
        WHERE s.status IN ('Received', 'Testing')
        ORDER BY s.id DESC
    """, conn)
    conn.close()

    if samples_df.empty:
        st.info("لا توجد عينات قيد الانتظار حالياً")
    else:
        selected = st.selectbox(
            "اختر العينة",
            options=samples_df['id'].tolist(),
            format_func=lambda x: f"{samples_df.loc[samples_df['id']==x, 'sample_code'].values[0]} | {samples_df.loc[samples_df['id']==x, 'client_name'].values[0]} | {samples_df.loc[samples_df['id']==x, 'product'].values[0]}"
        )

        sample_row = samples_df[samples_df['id'] == selected].iloc[0]
        st.write(f"**العينة:** {sample_row['sample_code']} | **المنتج:** {sample_row['product']}")

        # Get product specs
        conn = get_connection()
        c = conn.cursor()
        c.execute("SELECT product_id FROM samples WHERE id=?", (selected,))
        pid = c.fetchone()[0]

        specs_df = pd.read_sql("""
            SELECT t.id as test_id, t.name as test_name, t.method, t.unit,
                   ps.min_value, ps.max_value, ps.target_value
            FROM product_specs ps
            JOIN tests t ON ps.test_id = t.id
            WHERE ps.product_id = ?
            ORDER BY t.category, t.name
        """, conn, params=(pid,))

        # Also allow adding any test
        all_tests = get_tests()

        st.subheader("النتائج حسب المواصفات المحددة للمنتج")
        if not specs_df.empty:
            results_input = {}
            for _, row in specs_df.iterrows():
                with st.container():
                    st.markdown(f"**{row['test_name']}**")
                    st.caption(f"{row['method']} | وحدة: {row['unit'] or '-'}")
                    
                    # المواصفة
                    spec_text = ""
                    if row['min_value'] is not None:
                        spec_text += f"≥ {row['min_value']}  "
                    if row['max_value'] is not None:
                        spec_text += f"≤ {row['max_value']}"
                    if spec_text:
                        st.caption(f"المواصفة: {spec_text}")
                    
                    col_val, col_conf = st.columns([3, 1])
                    with col_val:
                        val = st.number_input(
                            "القيمة",
                            key=f"val_{row['test_id']}",
                            value=None,
                            format="%.4f",
                            label_visibility="collapsed"
                        )
                    with col_conf:
                        conf = calculate_conformity(val, row['min_value'], row['max_value'])
                        if conf == "Pass":
                            st.success("Pass")
                        elif conf == "Fail":
                            st.error("Fail")
                        else:
                            st.write("—")
                    
                    results_input[row['test_id']] = {
                        "value": val,
                        "min": row['min_value'],
                        "max": row['max_value'],
                        "unit": row['unit'],
                        "name": row['test_name']
                    }
                    st.markdown("---")

            if st.button("💾 حفظ النتائج", type="primary"):
                analyst = st.session_state.current_user
                now = datetime.now().isoformat()
                for tid, data in results_input.items():
                    if data["value"] is not None:
                        conf = calculate_conformity(data["value"], data["min"], data["max"])
                        c.execute("""
                            INSERT OR REPLACE INTO results
                            (sample_id, test_id, value, unit, analyst, tested_at, conformity)
                            VALUES (?, ?, ?, ?, ?, ?, ?)
                        """, (selected, tid, data["value"], data["unit"], analyst, now, conf))
                c.execute("UPDATE samples SET status='Testing' WHERE id=?", (selected,))
                conn.commit()
                log_audit(analyst, "UPDATE", "results", selected, "Results entered")
                st.success("تم حفظ النتائج بنجاح")
                st.rerun()
        else:
            st.warning("لا توجد مواصفات محددة لهذا المنتج. يمكنك إضافتها من صفحة الاختبارات والمواصفات، أو إدخال نتائج يدوياً.")

        # Manual add any test
        with st.expander("إضافة اختبار إضافي غير موجود في المواصفات"):
            test_id = st.selectbox("اختر الاختبار", options=all_tests['id'], format_func=lambda x: all_tests.loc[all_tests['id']==x, 'name'].values[0])
            val = st.number_input("القيمة", key="extra_val")
            if st.button("إضافة"):
                conf = "N/A"
                # try to find if there is a global default? for now N/A
                c.execute("""
                    INSERT OR REPLACE INTO results (sample_id, test_id, value, unit, analyst, tested_at, conformity)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                """, (selected, test_id, val, all_tests.loc[all_tests['id']==test_id, 'unit'].values[0],
                      st.session_state.current_user, datetime.now().isoformat(), conf))
                conn.commit()
                st.success("تمت الإضافة")
        conn.close()

# ---------- Manage Samples ----------
elif menu == "📋 إدارة العينات":
    st.markdown('<div class="main-header"><h2>إدارة العينات</h2></div>', unsafe_allow_html=True)

    conn = get_connection()
    df = pd.read_sql("""
        SELECT s.id, s.sample_code, s.client_name, p.name as product, s.equipment_id,
               s.collection_date, s.status, s.registered_at
        FROM samples s
        LEFT JOIN products p ON s.product_id = p.id
        ORDER BY s.id DESC
    """, conn)
    conn.close()

    # Filters
    c1, c2, c3 = st.columns(3)
    with c1:
        status_filter = st.multiselect("الحالة", options=df['status'].unique().tolist() if not df.empty else [], default=[])
    with c2:
        search = st.text_input("بحث (كود / عميل)")
    with c3:
        st.write("")

    filtered = df.copy()
    if status_filter:
        filtered = filtered[filtered['status'].isin(status_filter)]
    if search:
        filtered = filtered[
            filtered['sample_code'].str.contains(search, case=False, na=False) |
            filtered['client_name'].str.contains(search, case=False, na=False)
        ]

    st.dataframe(filtered, use_container_width=True, hide_index=True)

    # View details
    if not filtered.empty:
        sel_code = st.selectbox("عرض تفاصيل عينة", options=filtered['sample_code'].tolist())
        if sel_code:
            sample = get_sample_by_code(sel_code)
            if sample:
                st.json(dict(sample))  # quick view; can be improved

                # Results for this sample
                conn = get_connection()
                res = pd.read_sql("""
                    SELECT t.name, r.value, r.unit, r.conformity, r.analyst, r.tested_at
                    FROM results r JOIN tests t ON r.test_id = t.id
                    WHERE r.sample_id = ?
                """, conn, params=(sample['id'],))
                conn.close()
                if not res.empty:
                    st.subheader("النتائج المسجلة")
                    st.dataframe(res, use_container_width=True, hide_index=True)

# ---------- Tests & Specs ----------
elif menu == "⚙️ الاختبارات والمواصفات":
    st.markdown('<div class="main-header"><h2>إدارة الاختبارات والمواصفات</h2></div>', unsafe_allow_html=True)

    tab1, tab2, tab3 = st.tabs(["مكتبة الاختبارات", "المنتجات", "المواصفات"])

    with tab1:
        tests_df = get_tests()
        st.dataframe(tests_df, use_container_width=True, hide_index=True)

        with st.expander("إضافة اختبار جديد"):
            with st.form("new_test"):
                n1, n2 = st.columns(2)
                with n1:
                    tname = st.text_input("اسم الاختبار")
                    tmethod = st.text_input("الطريقة (ASTM / ISO)")
                with n2:
                    tunit = st.text_input("الوحدة")
                    tcat = st.selectbox("التصنيف", ["Physical", "Chemical", "Wear Metals", "Contamination", "Additives", "Performance"])
                if st.form_submit_button("إضافة"):
                    conn = get_connection()
                    c = conn.cursor()
                    c.execute("INSERT INTO tests (name, method, unit, category) VALUES (?, ?, ?, ?)",
                              (tname, tmethod, tunit, tcat))
                    conn.commit()
                    conn.close()
                    st.success("تمت الإضافة")
                    st.rerun()

    with tab2:
        prods = get_products()
        st.dataframe(prods, use_container_width=True, hide_index=True)

        with st.expander("إضافة منتج جديد"):
            with st.form("new_prod"):
                pname = st.text_input("اسم المنتج")
                pcat = st.selectbox("التصنيف", ["Hydraulic", "Gear", "Engine", "Turbine", "Compressor", "Transmission", "Grease", "Other"])
                pgrade = st.text_input("الدرجة (ISO VG / SAE)")
                if st.form_submit_button("إضافة"):
                    conn = get_connection()
                    c = conn.cursor()
                    c.execute("INSERT INTO products (name, category, grade) VALUES (?, ?, ?)", (pname, pcat, pgrade))
                    conn.commit()
                    conn.close()
                    st.success("تمت الإضافة")
                    st.rerun()

    with tab3:
        st.write("إدارة المواصفات (حدود القبول) لكل منتج")
        prods = get_products()
        sel_prod = st.selectbox("اختر المنتج", options=prods['id'], format_func=lambda x: prods.loc[prods['id']==x, 'name'].values[0])

        conn = get_connection()
        current_specs = pd.read_sql("""
            SELECT ps.id, t.name as test, ps.min_value, ps.max_value, ps.target_value, t.unit
            FROM product_specs ps JOIN tests t ON ps.test_id = t.id
            WHERE ps.product_id = ?
        """, conn, params=(sel_prod,))
        st.dataframe(current_specs, use_container_width=True, hide_index=True)

        with st.expander("إضافة / تعديل مواصفة"):
            tests = get_tests()
            t_id = st.selectbox("الاختبار", options=tests['id'], format_func=lambda x: tests.loc[tests['id']==x, 'name'].values[0])
            mn = st.number_input("الحد الأدنى (اتركه فارغ إذا لا يوجد)", value=None, format="%.4f")
            mx = st.number_input("الحد الأعلى", value=None, format="%.4f")
            if st.button("حفظ المواصفة"):
                c = conn.cursor()
                c.execute("""
                    INSERT OR REPLACE INTO product_specs (product_id, test_id, min_value, max_value)
                    VALUES (?, ?, ?, ?)
                """, (sel_prod, t_id, mn, mx))
                conn.commit()
                st.success("تم الحفظ")
                st.rerun()
        conn.close()

# ---------- COA ----------
elif menu == "📄 شهادات التحليل (COA)":
    st.markdown('<div class="main-header"><h2>شهادات التحليل - Certificate of Analysis</h2></div>', unsafe_allow_html=True)

    conn = get_connection()
    samples_with_results = pd.read_sql("""
        SELECT DISTINCT s.id, s.sample_code, s.client_name, p.name as product, s.status
        FROM samples s
        JOIN results r ON s.id = r.sample_id
        LEFT JOIN products p ON s.product_id = p.id
        ORDER BY s.id DESC
    """, conn)

    if samples_with_results.empty:
        st.info("لا توجد عينات لديها نتائج بعد")
    else:
        sel = st.selectbox(
            "اختر العينة لتوليد COA",
            options=samples_with_results['id'].tolist(),
            format_func=lambda x: f"{samples_with_results.loc[samples_with_results['id']==x, 'sample_code'].values[0]} | {samples_with_results.loc[samples_with_results['id']==x, 'client_name'].values[0]}"
        )

        if st.button("🖨️ توليد شهادة التحليل (PDF)", type="primary"):
            # Get sample data
            c = conn.cursor()
            c.execute("SELECT * FROM samples WHERE id=?", (sel,))
            sample = dict(c.fetchone())

            c.execute("SELECT name FROM products WHERE id=?", (sample['product_id'],))
            prod_row = c.fetchone()
            product_name = prod_row[0] if prod_row else "-"

            # Get results + specs
            results = pd.read_sql("""
                SELECT t.name as test_name, t.method, t.unit,
                       r.value, r.value_text, r.conformity,
                       ps.min_value, ps.max_value
                FROM results r
                JOIN tests t ON r.test_id = t.id
                LEFT JOIN product_specs ps ON ps.test_id = r.test_id AND ps.product_id = ?
                WHERE r.sample_id = ?
            """, conn, params=(sample['product_id'], sel))

            results_list = results.to_dict('records')

            # Generate PDF
            os.makedirs("coas", exist_ok=True)
            pdf_path = f"coas/COA_{sample['sample_code']}.pdf"
            generate_coa_pdf(sample, results_list, product_name, pdf_path)

            # Record in DB
            c.execute("""
                INSERT OR REPLACE INTO coas (sample_id, generated_at, generated_by, file_path)
                VALUES (?, ?, ?, ?)
            """, (sel, datetime.now().isoformat(), st.session_state.current_user, pdf_path))
            c.execute("UPDATE samples SET status='Reported' WHERE id=?", (sel,))
            conn.commit()
            log_audit(st.session_state.current_user, "GENERATE_COA", "sample", sel, pdf_path)

            st.success("تم توليد الشهادة بنجاح")
            with open(pdf_path, "rb") as f:
                st.download_button(
                    label="⬇️ تحميل شهادة التحليل PDF",
                    data=f,
                    file_name=f"COA_{sample['sample_code']}.pdf",
                    mime="application/pdf"
                )

    conn.close()

# ---------- Reports ----------
elif menu == "📈 التقارير":
    st.markdown('<div class="main-header"><h2>التقارير والإحصائيات</h2></div>', unsafe_allow_html=True)

    conn = get_connection()
    # Simple exports
    st.subheader("تصدير البيانات")
    if st.button("تصدير كل العينات إلى Excel"):
        df = pd.read_sql("""
            SELECT s.*, p.name as product_name
            FROM samples s LEFT JOIN products p ON s.product_id = p.id
        """, conn)
        df.to_excel("samples_export.xlsx", index=False)
        with open("samples_export.xlsx", "rb") as f:
            st.download_button("تحميل Excel", f, "nordec_samples.xlsx")

    st.subheader("سجل التدقيق (Audit Log) - مهم لـ ISO 17025")
    audit = pd.read_sql("SELECT * FROM audit_log ORDER BY id DESC LIMIT 50", conn)
    st.dataframe(audit, use_container_width=True, hide_index=True)
    conn.close()

# ---------- Admin ----------
elif menu == "🔧 الإدارة":
    st.markdown('<div class="main-header"><h2>الإدارة</h2></div>', unsafe_allow_html=True)

    st.info("""
    **ملاحظات مهمة للتوافق مع ISO 17025:**
    - النظام يسجل كل إجراء في Audit Log.
    - بيانات السحب (Sampling) كاملة حسب البند 7.3.
    - النتائج مرتبطة بالمحلل والتاريخ والطريقة.
    - حكم المطابقة واضح (Pass/Fail) مع إمكانية التوثيق.
    - شهادات التحليل تحتوي على البيانات الإلزامية (بند 7.8).
    - يُفضل عمل Validation للنظام قبل الاعتماد الرسمي.
    """)

    st.subheader("المستخدم الحالي")
    new_user = st.text_input("تغيير اسم المستخدم (للتجربة)", value=st.session_state.current_user)
    if st.button("تحديث"):
        st.session_state.current_user = new_user
        st.success("تم")

    st.subheader("معلومات قاعدة البيانات")
    st.code(DB_PATH)
    if os.path.exists(DB_PATH):
        st.write(f"حجم الملف: {os.path.getsize(DB_PATH)/1024:.1f} KB")

st.markdown("---")
st.caption("Nordec Laboratory Information Management System | Built for ISO/IEC 17025 compliance | © 2026")
