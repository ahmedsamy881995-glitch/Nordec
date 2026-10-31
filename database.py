import sqlite3
from datetime import datetime
import os

DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "nordec_lab.db")

def get_connection():
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_connection()
    c = conn.cursor()

    # Users (simple)
    c.execute("""
    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT UNIQUE NOT NULL,
        full_name TEXT,
        role TEXT DEFAULT 'analyst',  -- admin, analyst, reviewer
        created_at TEXT
    )
    """)

    # Products / Oil types
    c.execute("""
    CREATE TABLE IF NOT EXISTS products (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        category TEXT,  -- Hydraulic, Gear, Engine, Turbine, Compressor, Other
        grade TEXT,     -- ISO VG 46, SAE 15W-40, etc.
        description TEXT,
        active INTEGER DEFAULT 1
    )
    """)

    # Tests library
    c.execute("""
    CREATE TABLE IF NOT EXISTS tests (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        method TEXT,        -- ASTM D445, ISO 3104, etc.
        unit TEXT,
        category TEXT,      -- Physical, Chemical, Wear, Performance
        description TEXT,
        active INTEGER DEFAULT 1
    )
    """)

    # Specifications per product-test
    c.execute("""
    CREATE TABLE IF NOT EXISTS product_specs (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        product_id INTEGER NOT NULL,
        test_id INTEGER NOT NULL,
        min_value REAL,
        max_value REAL,
        target_value REAL,
        notes TEXT,
        FOREIGN KEY (product_id) REFERENCES products(id),
        FOREIGN KEY (test_id) REFERENCES tests(id),
        UNIQUE(product_id, test_id)
    )
    """)

    # Samples
    c.execute("""
    CREATE TABLE IF NOT EXISTS samples (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        sample_code TEXT UNIQUE NOT NULL,
        product_id INTEGER,
        client_name TEXT,
        client_ref TEXT,
        equipment_id TEXT,
        equipment_type TEXT,
        collection_date TEXT,
        collector_name TEXT,
        collection_location TEXT,
        sampling_method TEXT,
        container_type TEXT,
        oil_hours REAL,
        total_hours REAL,
        oil_brand TEXT,
        condition_on_receipt TEXT,
        temperature_on_receipt REAL,
        notes TEXT,
        registered_by TEXT,
        registered_at TEXT,
        status TEXT DEFAULT 'Received',  -- Received, Testing, Completed, Reported
        FOREIGN KEY (product_id) REFERENCES products(id)
    )
    """)

    # Results
    c.execute("""
    CREATE TABLE IF NOT EXISTS results (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        sample_id INTEGER NOT NULL,
        test_id INTEGER NOT NULL,
        value REAL,
        value_text TEXT,          -- for non-numeric like Appearance
        unit TEXT,
        analyst TEXT,
        tested_at TEXT,
        instrument TEXT,
        conformity TEXT,          -- Pass, Fail, Conditional, N/A
        conformity_notes TEXT,
        reviewed_by TEXT,
        reviewed_at TEXT,
        notes TEXT,
        FOREIGN KEY (sample_id) REFERENCES samples(id),
        FOREIGN KEY (test_id) REFERENCES tests(id),
        UNIQUE(sample_id, test_id)
    )
    """)

    # Audit log
    c.execute("""
    CREATE TABLE IF NOT EXISTS audit_log (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        timestamp TEXT,
        user TEXT,
        action TEXT,
        entity_type TEXT,
        entity_id INTEGER,
        details TEXT
    )
    """)

    # COA records
    c.execute("""
    CREATE TABLE IF NOT EXISTS coas (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        sample_id INTEGER UNIQUE,
        generated_at TEXT,
        generated_by TEXT,
        version INTEGER DEFAULT 1,
        file_path TEXT,
        notes TEXT,
        FOREIGN KEY (sample_id) REFERENCES samples(id)
    )
    """)

    conn.commit()

    # Seed data if empty
    seed_data(conn)
    conn.close()

def seed_data(conn):
    c = conn.cursor()
    c.execute("SELECT COUNT(*) FROM tests")
    if c.fetchone()[0] > 0:
        return

    # Common tests
    tests = [
        ("Kinematic Viscosity @ 40°C", "ASTM D445 / ISO 3104", "cSt", "Physical", "Viscosity at 40°C"),
        ("Kinematic Viscosity @ 100°C", "ASTM D445 / ISO 3104", "cSt", "Physical", "Viscosity at 100°C"),
        ("Viscosity Index (VI)", "ASTM D2270 / ISO 2909", "", "Physical", "Viscosity Index"),
        ("Density @ 15°C", "ASTM D4052", "g/cm³", "Physical", "Density"),
        ("Flash Point (COC)", "ASTM D92", "°C", "Physical", "Cleveland Open Cup Flash Point"),
        ("Flash Point (PMCC)", "ASTM D93", "°C", "Physical", "Pensky-Martens Closed Cup"),
        ("Pour Point", "ASTM D97", "°C", "Physical", "Pour Point"),
        ("Total Acid Number (TAN)", "ASTM D664 / D974", "mg KOH/g", "Chemical", "Acid Number"),
        ("Total Base Number (TBN)", "ASTM D2896 / D4739", "mg KOH/g", "Chemical", "Base Number"),
        ("Water Content (Karl Fischer)", "ASTM D6304", "ppm", "Chemical", "Water by KF"),
        ("Water Content (Distillation)", "ASTM D95", "% vol", "Chemical", "Water by distillation"),
        ("Appearance", "Visual", "", "Physical", "Visual appearance"),
        ("Color", "ASTM D1500", "", "Physical", "ASTM Color"),
        ("Foam Sequence I", "ASTM D892", "ml", "Performance", "Foaming tendency"),
        ("Demulsibility", "ASTM D1401", "min", "Performance", "Water separation"),
        ("Iron (Fe)", "ASTM D5185 / ICP", "ppm", "Wear Metals", "Wear metal Fe"),
        ("Copper (Cu)", "ASTM D5185 / ICP", "ppm", "Wear Metals", "Wear metal Cu"),
        ("Lead (Pb)", "ASTM D5185 / ICP", "ppm", "Wear Metals", "Wear metal Pb"),
        ("Aluminum (Al)", "ASTM D5185 / ICP", "ppm", "Wear Metals", "Wear metal Al"),
        ("Chromium (Cr)", "ASTM D5185 / ICP", "ppm", "Wear Metals", "Wear metal Cr"),
        ("Tin (Sn)", "ASTM D5185 / ICP", "ppm", "Wear Metals", "Wear metal Sn"),
        ("Silicon (Si)", "ASTM D5185 / ICP", "ppm", "Contamination", "Dirt / coolant"),
        ("Sodium (Na)", "ASTM D5185 / ICP", "ppm", "Contamination", "Coolant indicator"),
        ("Calcium (Ca)", "ASTM D5185 / ICP", "ppm", "Additives", "Detergent additive"),
        ("Zinc (Zn)", "ASTM D5185 / ICP", "ppm", "Additives", "Antiwear additive"),
        ("Phosphorus (P)", "ASTM D5185 / ICP", "ppm", "Additives", "Antiwear additive"),
        ("Magnesium (Mg)", "ASTM D5185 / ICP", "ppm", "Additives", "Detergent"),
        ("Sulfated Ash", "ASTM D874", "% wt", "Chemical", "Sulfated Ash"),
        ("Oxidation (FTIR)", "FTIR", "A/cm", "Chemical", "Oxidation by FTIR"),
        ("Nitration (FTIR)", "FTIR", "A/cm", "Chemical", "Nitration by FTIR"),
        ("Soot (FTIR)", "FTIR", "%", "Contamination", "Soot content"),
        ("Fuel Dilution", "GC / FTIR", "%", "Contamination", "Fuel dilution"),
        ("Glycol", "ASTM D2982", "", "Contamination", "Glycol contamination"),
    ]

    c.executemany(
        "INSERT INTO tests (name, method, unit, category, description) VALUES (?, ?, ?, ?, ?)",
        tests
    )

    # Common products
    products = [
        ("Hydraulic Oil ISO VG 32", "Hydraulic", "ISO VG 32", "Anti-wear hydraulic oil"),
        ("Hydraulic Oil ISO VG 46", "Hydraulic", "ISO VG 46", "Anti-wear hydraulic oil"),
        ("Hydraulic Oil ISO VG 68", "Hydraulic", "ISO VG 68", "Anti-wear hydraulic oil"),
        ("Gear Oil ISO VG 150", "Gear", "ISO VG 150", "Industrial gear oil"),
        ("Gear Oil ISO VG 220", "Gear", "ISO VG 220", "Industrial gear oil"),
        ("Gear Oil ISO VG 320", "Gear", "ISO VG 320", "Industrial gear oil"),
        ("Turbine Oil ISO VG 32", "Turbine", "ISO VG 32", "Steam / gas turbine oil"),
        ("Turbine Oil ISO VG 46", "Turbine", "ISO VG 46", "Steam / gas turbine oil"),
        ("Compressor Oil ISO VG 68", "Compressor", "ISO VG 68", "Air compressor oil"),
        ("Engine Oil SAE 15W-40", "Engine", "SAE 15W-40", "Heavy duty diesel engine oil"),
        ("Engine Oil SAE 10W-40", "Engine", "SAE 10W-40", "Multigrade engine oil"),
        ("ATF Dexron III", "Transmission", "Dexron III", "Automatic transmission fluid"),
        ("Grease NLGI 2", "Grease", "NLGI 2", "Multi-purpose grease"),
    ]

    c.executemany(
        "INSERT INTO products (name, category, grade, description) VALUES (?, ?, ?, ?)",
        products
    )

    # Example specs for Hydraulic ISO VG 46 (product_id will be 2 after insert)
    # We need to get ids
    conn.commit()

    # Add example specs
    c.execute("SELECT id FROM products WHERE name = 'Hydraulic Oil ISO VG 46'")
    prod = c.fetchone()
    if prod:
        pid = prod[0]
        specs = [
            # test_name, min, max
            ("Kinematic Viscosity @ 40°C", 41.4, 50.6),
            ("Kinematic Viscosity @ 100°C", 6.5, 8.5),
            ("Viscosity Index (VI)", 95, None),
            ("Density @ 15°C", 0.860, 0.890),
            ("Flash Point (COC)", 200, None),
            ("Pour Point", None, -15),
            ("Total Acid Number (TAN)", None, 1.5),
            ("Water Content (Karl Fischer)", None, 500),
            ("Appearance", None, None),  # visual
            ("Iron (Fe)", None, 50),
            ("Copper (Cu)", None, 30),
            ("Silicon (Si)", None, 30),
        ]
        for tname, mn, mx in specs:
            c.execute("SELECT id, unit FROM tests WHERE name = ?", (tname,))
            t = c.fetchone()
            if t:
                c.execute("""
                    INSERT OR IGNORE INTO product_specs (product_id, test_id, min_value, max_value)
                    VALUES (?, ?, ?, ?)
                """, (pid, t[0], mn, mx))

    # Specs for Gear ISO VG 220
    c.execute("SELECT id FROM products WHERE name = 'Gear Oil ISO VG 220'")
    prod = c.fetchone()
    if prod:
        pid = prod[0]
        specs = [
            ("Kinematic Viscosity @ 40°C", 198, 242),
            ("Kinematic Viscosity @ 100°C", 17, 22),
            ("Viscosity Index (VI)", 90, None),
            ("Flash Point (COC)", 220, None),
            ("Pour Point", None, -9),
            ("Total Acid Number (TAN)", None, 1.0),
            ("Water Content (Karl Fischer)", None, 300),
            ("Iron (Fe)", None, 100),
            ("Copper (Cu)", None, 50),
        ]
        for tname, mn, mx in specs:
            c.execute("SELECT id FROM tests WHERE name = ?", (tname,))
            t = c.fetchone()
            if t:
                c.execute("""
                    INSERT OR IGNORE INTO product_specs (product_id, test_id, min_value, max_value)
                    VALUES (?, ?, ?, ?)
                """, (pid, t[0], mn, mx))

    # Default user
    c.execute("INSERT OR IGNORE INTO users (username, full_name, role, created_at) VALUES (?, ?, ?, ?)",
              ("admin", "System Admin", "admin", datetime.now().isoformat()))
    c.execute("INSERT OR IGNORE INTO users (username, full_name, role, created_at) VALUES (?, ?, ?, ?)",
              ("analyst1", "Analyst One", "analyst", datetime.now().isoformat()))

    conn.commit()

def log_audit(user, action, entity_type, entity_id, details=""):
    conn = get_connection()
    c = conn.cursor()
    c.execute("""
        INSERT INTO audit_log (timestamp, user, action, entity_type, entity_id, details)
        VALUES (?, ?, ?, ?, ?, ?)
    """, (datetime.now().isoformat(), user, action, entity_type, entity_id, details))
    conn.commit()
    conn.close()

def generate_sample_code():
    """Generate unique sample code like NOR-2026-00001"""
    conn = get_connection()
    c = conn.cursor()
    year = datetime.now().year
    c.execute("SELECT COUNT(*) FROM samples WHERE sample_code LIKE ?", (f"NOR-{year}-%",))
    count = c.fetchone()[0] + 1
    conn.close()
    return f"NOR-{year}-{count:05d}"
