import os
import sqlite3
import random
from datetime import datetime

DB_PATH = os.environ.get("DB_PATH", "store_database.db")

def _db():
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    con = _db()
    with con:
        # Users table
        con.execute("""
            CREATE TABLE IF NOT EXISTS users (
                tg_id INTEGER PRIMARY KEY,
                name TEXT,
                username TEXT,
                balance REAL DEFAULT 0.0,
                is_banned INTEGER DEFAULT 0,
                referred_by INTEGER DEFAULT NULL,
                referral_count INTEGER DEFAULT 0,
                first_order_done INTEGER DEFAULT 0,
                joined_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        # Migration: add first_order_done if missing
        try:
            con.execute("ALTER TABLE users ADD COLUMN first_order_done INTEGER DEFAULT 0")
        except Exception:
            pass
        
        # Products table
        con.execute("""
            CREATE TABLE IF NOT EXISTS products (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                price REAL NOT NULL,
                stock INTEGER DEFAULT 50,
                delivery_type TEXT DEFAULT 'text',
                delivery_content TEXT DEFAULT '',
                active INTEGER DEFAULT 1
            )
        """)

        # Deposits table
        con.execute("""
            CREATE TABLE IF NOT EXISTS deposits (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                tg_id INTEGER NOT NULL,
                ref TEXT UNIQUE NOT NULL,
                network TEXT NOT NULL,
                txn_id TEXT DEFAULT '',
                amount REAL DEFAULT 0.0,
                status TEXT DEFAULT 'pending',
                notified INTEGER DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # Orders table
        con.execute("""
            CREATE TABLE IF NOT EXISTS orders (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                tg_id INTEGER NOT NULL,
                ref TEXT UNIQUE NOT NULL,
                prod_name TEXT NOT NULL,
                price REAL NOT NULL,
                qty INTEGER DEFAULT 1,
                status TEXT DEFAULT 'pending',
                delivery_content TEXT DEFAULT '',
                delivery_type TEXT DEFAULT 'text',
                notified INTEGER DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # Wallets table
        con.execute("""
            CREATE TABLE IF NOT EXISTS wallets (
                key TEXT PRIMARY KEY,
                label TEXT NOT NULL,
                address TEXT NOT NULL,
                active INTEGER DEFAULT 1
            )
        """)

        # Redeem Codes table
        con.execute("""
            CREATE TABLE IF NOT EXISTS redeem_codes (
                code TEXT PRIMARY KEY,
                amount REAL NOT NULL,
                max_uses INTEGER DEFAULT 1,
                used_count INTEGER DEFAULT 0
            )
        """)

        # Redeem Code Uses tracking
        con.execute("""
            CREATE TABLE IF NOT EXISTS code_claims (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                code TEXT NOT NULL,
                tg_id INTEGER NOT NULL,
                claimed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(code, tg_id)
            )
        """)

        # Referrals tracking
        con.execute("""
            CREATE TABLE IF NOT EXISTS referrals (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                referrer_id INTEGER NOT NULL,
                referred_id INTEGER UNIQUE NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # Seed default wallets if empty
        cur = con.execute("SELECT COUNT(*) as c FROM wallets")
        if cur.fetchone()["c"] == 0:
            con.execute("INSERT INTO wallets (key, label, address, active) VALUES ('usdt_trc20', 'USDT (TRC-20)', 'TFxxxxYourTRC20Addressxxxx', 1)")
            con.execute("INSERT INTO wallets (key, label, address, active) VALUES ('usdt_bep20', 'USDT (BEP-20 / BSC)', '0xYourBEP20Address', 1)")
            con.execute("INSERT INTO wallets (key, label, address, active) VALUES ('ton', 'TON Coin', 'EQYourTONAddress', 1)")
            con.execute("INSERT INTO wallets (key, label, address, active) VALUES ('sol', 'Solana (SOL)', 'YourSolanaAddress', 1)")

        # Seed the requested 16 products if table is empty
        p_cur = con.execute("SELECT COUNT(*) as c FROM products")
        if p_cur.fetchone()["c"] == 0:
            default_products = [
                "❤️ Adobe Full App",
                "🖥 CapCut (1M/6M/12M)",
                "😺 ChatGPT (Plus/Prox20)",
                "😀 Grok (Super/Heavy)",
                "🤶 Claude (Pro/Max5/Max20)",
                "✨ Cursor (Pro/Pro Plus /Ultra)",
                "🐦 ElevenLabs",
                "🥹 Higgsfield (Pro/Max)",
                "👨‍🎨 Figma",
                "🤖 Gemini (Antigravity Ultra / Pro)",
                "😮 Kling AI (Pro /Premier/Ultra)",
                "🙂 Kiro (ProPlus/Pro Max/ Power)",
                "✅ Lovable",
                "✨ Manus",
                "😊 YouTube (1M/3M/6M/12M)",
                "🛒 Gamma",
                "🎵 Suno Premium",
                "🔍 Perplexity Pro",
                "🎥 HeyGen",
                "🎨 Krea AI",
            ]
            for p_name in default_products:
                initial_stock = random.randint(15, 95)
                con.execute("""
                    INSERT INTO products (name, price, stock, delivery_type, delivery_content, active)
                    VALUES (?, 1.00, ?, 'text', '🔑 License Key / Account Credentials: Sent upon verification.', 1)
                """, (p_name, initial_stock))

    con.close()
    ensure_new_products()  # always adds missing new products safely

def reset_to_exact_product_list():
    """Wipes old products and seeds only the 16 exact products requested at $1.00 each."""
    con = _db()
    with con:
        con.execute("DELETE FROM products")
        default_products = [
            "❤️ Adobe Full App",
            "🖥 CapCut (1M/6M/12M)",
            "😺 ChatGPT (Plus/Prox20)",
            "😀 Grok (Super/Heavy)",
            "🤶 Claude (Pro/Max5/Max20)",
            "✨ Cursor (Pro/Pro Plus /Ultra)",
            "🐦 ElevenLabs",
            "🥹 Higgsfield (Pro/Max)",
            "👨‍🎨 Figma",
            "🤖 Gemini (Antigravity Ultra / Pro)",
            "😮 Kling AI (Pro /Premier/Ultra)",
            "🙂 Kiro (ProPlus/Pro Max/ Power)",
            "✅ Lovable",
            "✨ Manus",
            "😊 YouTube (1M/3M/6M/12M)",
            "🛒 Gamma",
            "🎵 Suno Premium",
            "🔍 Perplexity Pro",
            "🎥 HeyGen",
            "🎨 Krea AI",
        ]
        for p_name in default_products:
            stock = random.randint(20, 95)
            con.execute("""
                INSERT INTO products (name, price, stock, delivery_type, delivery_content, active)
                VALUES (?, 1.00, ?, 'text', '🔑 Account / License Key (Configurable in Admin Panel)', 1)
            """, (p_name, stock))
    con.close()

def ensure_new_products():
    """Adds new products to an existing DB without wiping data. Safe to call on every deploy."""
    new_products = [
        "🎵 Suno Premium",
        "🔍 Perplexity Pro",
        "🎥 HeyGen",
        "🎨 Krea AI",
    ]
    con = _db()
    with con:
        for p_name in new_products:
            exists = con.execute("SELECT id FROM products WHERE name = ?", (p_name,)).fetchone()
            if not exists:
                stock = random.randint(20, 95)
                con.execute("""
                    INSERT INTO products (name, price, stock, delivery_type, delivery_content, active)
                    VALUES (?, 1.00, ?, 'text', '🔑 Account / License Key (Configurable in Admin Panel)', 1)
                """, (p_name, stock))
    con.close()


# ── User Functions ────────────────────────────────────

def get_or_create_user(tg_id: int, name: str = "", username: str = "", referrer_id: int = None):
    con = _db()
    with con:
        row = con.execute("SELECT * FROM users WHERE tg_id = ?", (tg_id,)).fetchone()
        if not row:
            ref_id_valid = None
            if referrer_id and referrer_id != tg_id:
                ref_exists = con.execute("SELECT tg_id FROM users WHERE tg_id = ?", (referrer_id,)).fetchone()
                if ref_exists:
                    ref_id_valid = referrer_id

            con.execute("""
                INSERT INTO users (tg_id, name, username, balance, referred_by)
                VALUES (?, ?, ?, 0.0, ?)
            """, (tg_id, name or "User", username or "", ref_id_valid))

            if ref_id_valid:
                # Increment referrer's count
                con.execute("UPDATE users SET referral_count = referral_count + 1 WHERE tg_id = ?", (ref_id_valid,))
                con.execute("INSERT OR IGNORE INTO referrals (referrer_id, referred_id) VALUES (?, ?)", (ref_id_valid, tg_id))
            
            row = con.execute("SELECT * FROM users WHERE tg_id = ?", (tg_id,)).fetchone()
        else:
            # Update name/username in case they changed
            con.execute("UPDATE users SET name = ?, username = ? WHERE tg_id = ?", (name or row["name"], username or row["username"], tg_id))
    con.close()
    return dict(row)

def get_user(tg_id: int):
    con = _db()
    row = con.execute("SELECT * FROM users WHERE tg_id = ?", (tg_id,)).fetchone()
    con.close()
    return dict(row) if row else None

def get_user_total_spent(tg_id: int) -> float:
    con = _db()
    row = con.execute(
        "SELECT COALESCE(SUM(price), 0.0) as total FROM orders WHERE tg_id = ? AND status = 'delivered'",
        (tg_id,)
    ).fetchone()
    con.close()
    return row["total"] if row else 0.0

def maybe_pay_referral_commission(tg_id: int, order_amount: float):
    """Pay 10% commission to the referrer on the user's very first order only."""
    con = _db()
    with con:
        user = con.execute("SELECT referred_by, first_order_done FROM users WHERE tg_id = ?", (tg_id,)).fetchone()
        if not user or user["first_order_done"] == 1 or not user["referred_by"]:
            con.close()
            return
        commission = round(order_amount * 0.10, 4)
        con.execute("UPDATE users SET balance = balance + ? WHERE tg_id = ?", (commission, user["referred_by"]))
        con.execute("UPDATE users SET first_order_done = 1 WHERE tg_id = ?", (tg_id,))
    con.close()

def get_all_users():
    con = _db()
    rows = con.execute("SELECT tg_id, name, username, balance, referral_count FROM users ORDER BY joined_at DESC").fetchall()
    con.close()
    return [(r["tg_id"], r["name"], r["username"], r["balance"], r["referral_count"]) for r in rows]

def get_all_user_ids():
    con = _db()
    rows = con.execute("SELECT tg_id FROM users WHERE is_banned = 0").fetchall()
    con.close()
    return [r["tg_id"] for r in rows]

def set_balance(tg_id: int, amount: float):
    con = _db()
    with con:
        con.execute("UPDATE users SET balance = ? WHERE tg_id = ?", (amount, tg_id))
    con.close()

def add_balance(tg_id: int, amount: float):
    con = _db()
    with con:
        con.execute("UPDATE users SET balance = balance + ? WHERE tg_id = ?", (amount, tg_id))
    con.close()

def deduct_balance(tg_id: int, amount: float) -> bool:
    con = _db()
    with con:
        user = con.execute("SELECT balance FROM users WHERE tg_id = ?", (tg_id,)).fetchone()
        if not user or user["balance"] < amount:
            con.close()
            return False
        con.execute("UPDATE users SET balance = balance - ? WHERE tg_id = ?", (amount, tg_id))
    con.close()
    return True

def ban_user(tg_id: int):
    con = _db()
    with con:
        con.execute("UPDATE users SET is_banned = 1 WHERE tg_id = ?", (tg_id,))
    con.close()

def unban_user(tg_id: int):
    con = _db()
    with con:
        con.execute("UPDATE users SET is_banned = 0 WHERE tg_id = ?", (tg_id,))
    con.close()

def is_banned(tg_id: int) -> bool:
    con = _db()
    row = con.execute("SELECT is_banned FROM users WHERE tg_id = ?", (tg_id,)).fetchone()
    con.close()
    return bool(row and row["is_banned"] == 1)

def get_banned_users():
    con = _db()
    rows = con.execute("SELECT tg_id, name, username FROM users WHERE is_banned = 1").fetchall()
    con.close()
    return [(r["tg_id"], r["name"], r["username"]) for r in rows]

def find_tg_id_by_username(username: str):
    clean = username.lstrip("@").strip()
    con = _db()
    row = con.execute("SELECT tg_id FROM users WHERE LOWER(username) = LOWER(?)", (clean,)).fetchone()
    con.close()
    return row["tg_id"] if row else None

# ── Products Functions ────────────────────────────────

def get_all_products(active_only: bool = False):
    con = _db()
    query = "SELECT * FROM products" + (" WHERE active = 1" if active_only else "") + " ORDER BY id ASC"
    rows = con.execute(query).fetchall()
    con.close()
    return [dict(r) for r in rows]

def get_product(pid: int):
    con = _db()
    row = con.execute("SELECT * FROM products WHERE id = ?", (pid,)).fetchone()
    con.close()
    return dict(row) if row else None

def add_product(name: str, price: float, stock: int, dtype: str, dcontent: str) -> int:
    con = _db()
    with con:
        cur = con.execute("""
            INSERT INTO products (name, price, stock, delivery_type, delivery_content, active)
            VALUES (?, ?, ?, ?, ?, 1)
        """, (name, price, stock, dtype, dcontent))
        pid = cur.lastrowid
    con.close()
    return pid

def update_product(pid: int, **kwargs):
    con = _db()
    keys = []
    vals = []
    for k, v in kwargs.items():
        keys.append(f"{k} = ?")
        vals.append(v)
    vals.append(pid)
    with con:
        con.execute(f"UPDATE products SET {', '.join(keys)} WHERE id = ?", vals)
    con.close()

def delete_product(pid: int):
    con = _db()
    with con:
        con.execute("DELETE FROM products WHERE id = ?", (pid,))
    con.close()

def toggle_product(pid: int) -> bool:
    con = _db()
    with con:
        row = con.execute("SELECT active FROM products WHERE id = ?", (pid,)).fetchone()
        if not row:
            con.close()
            return False
        new_val = 0 if row["active"] == 1 else 1
        con.execute("UPDATE products SET active = ? WHERE id = ?", (new_val, pid))
    con.close()
    return bool(new_val)

def randomize_all_stocks(min_val: int = 1, max_val: int = 100) -> int:
    """Randomizes stock for all active products between min_val and max_val (default 1-100)."""
    con = _db()
    with con:
        rows = con.execute("SELECT id FROM products WHERE active = 1").fetchall()
        for r in rows:
            new_stock = random.randint(min_val, max_val)
            con.execute("UPDATE products SET stock = ? WHERE id = ?", (new_stock, r["id"]))
    con.close()
    return len(rows)

# ── Deposits & Orders ─────────────────────────────────

def create_deposit(tg_id: int, network: str, txn_id: str = "") -> str:
    ref = f"#DEP-{random.randint(10000, 99999)}"
    con = _db()
    with con:
        con.execute("""
            INSERT INTO deposits (tg_id, ref, network, txn_id, status)
            VALUES (?, ?, ?, ?, 'pending')
        """, (tg_id, ref, network, txn_id))
    con.close()
    return ref

def get_unnotified_deposits():
    con = _db()
    rows = con.execute("""
        SELECT d.id, d.tg_id, d.ref, d.network, d.txn_id, d.created_at, u.name, u.username
        FROM deposits d
        LEFT JOIN users u ON d.tg_id = u.tg_id
        WHERE d.notified = 0 AND d.status = 'pending'
    """).fetchall()
    con.close()
    return [(r["id"], r["tg_id"], r["ref"], r["network"], r["txn_id"], r["created_at"], r["name"], r["username"]) for r in rows]

def mark_deposit_notified(dep_id: int):
    con = _db()
    with con:
        con.execute("UPDATE deposits SET notified = 1 WHERE id = ?", (dep_id,))
    con.close()

def approve_deposit(dep_id: int, amount: float):
    con = _db()
    with con:
        row = con.execute("SELECT tg_id FROM deposits WHERE id = ?", (dep_id,)).fetchone()
        if row:
            tg_id = row["tg_id"]
            con.execute("UPDATE deposits SET status = 'approved', amount = ? WHERE id = ?", (amount, dep_id))
            con.execute("UPDATE users SET balance = balance + ? WHERE tg_id = ?", (amount, tg_id))
    con.close()

def reject_deposit(dep_id: int):
    con = _db()
    with con:
        con.execute("UPDATE deposits SET status = 'rejected' WHERE id = ?", (dep_id,))
    con.close()

def create_order(tg_id: int, prod_id: int, qty: int = 1):
    con = _db()
    with con:
        prod = con.execute("SELECT * FROM products WHERE id = ?", (prod_id,)).fetchone()
        if not prod or prod["stock"] < qty:
            con.close()
            return None
        
        total_price = prod["price"] * qty
        ref = f"#ORD-{random.randint(10000, 99999)}"
        
        con.execute("""
            INSERT INTO orders (tg_id, ref, prod_name, price, qty, status, delivery_content, delivery_type)
            VALUES (?, ?, ?, ?, ?, 'pending', ?, ?)
        """, (tg_id, ref, prod["name"], total_price, qty, prod["delivery_content"], prod["delivery_type"]))
        
        # Decrement stock (if reaches 0, stay at 0 or randomize)
        con.execute("UPDATE products SET stock = MAX(0, stock - ?) WHERE id = ?", (qty, prod_id))
    con.close()
    return ref, prod["name"], total_price, prod["delivery_type"], prod["delivery_content"]

def get_unnotified_orders():
    con = _db()
    rows = con.execute("""
        SELECT o.id, o.tg_id, o.ref, o.prod_name, o.price, o.qty, o.created_at, u.name, u.username
        FROM orders o
        LEFT JOIN users u ON o.tg_id = u.tg_id
        WHERE o.notified = 0 AND o.status = 'pending'
    """).fetchall()
    con.close()
    return [(r["id"], r["tg_id"], r["ref"], r["prod_name"], r["price"], r["qty"], r["created_at"], r["name"], r["username"]) for r in rows]

def mark_order_notified(order_id: int):
    con = _db()
    with con:
        con.execute("UPDATE orders SET notified = 1 WHERE id = ?", (order_id,))
    con.close()

def deliver_order(order_ref: str):
    con = _db()
    with con:
        row = con.execute("SELECT tg_id, delivery_type, delivery_content, qty FROM orders WHERE ref = ?", (order_ref,)).fetchone()
        if not row:
            con.close()
            return None
        con.execute("UPDATE orders SET status = 'delivered' WHERE ref = ?", (order_ref,))
    con.close()
    return row["tg_id"], row["delivery_type"], row["delivery_content"], row["qty"]

def get_user_orders(tg_id: int, limit: int = 10):
    con = _db()
    rows = con.execute("""
        SELECT ref, prod_name, price, qty, status, created_at
        FROM orders WHERE tg_id = ? ORDER BY id DESC LIMIT ?
    """, (tg_id, limit)).fetchall()
    con.close()
    return [dict(r) for r in rows]

def get_recent_orders_admin(limit: int = 20):
    con = _db()
    rows = con.execute("""
        SELECT o.ref, o.prod_name, o.price, o.qty, o.status, o.created_at, u.name, u.username, o.tg_id
        FROM orders o
        LEFT JOIN users u ON o.tg_id = u.tg_id
        ORDER BY o.id DESC LIMIT ?
    """, (limit)).fetchall()
    con.close()
    return [(r["ref"], r["prod_name"], r["price"], r["qty"], r["status"], r["created_at"], r["name"], r["username"], r["tg_id"]) for r in rows]

# ── Wallets & Stats ───────────────────────────────────

def get_all_wallets():
    con = _db()
    rows = con.execute("SELECT key, label, address, active FROM wallets").fetchall()
    con.close()
    return [dict(r) for r in rows]

def update_wallet(key: str, address: str):
    con = _db()
    with con:
        con.execute("UPDATE wallets SET address = ? WHERE key = ?", (address, key))
    con.close()

def toggle_wallet(key: str) -> bool:
    con = _db()
    with con:
        row = con.execute("SELECT active FROM wallets WHERE key = ?", (key,)).fetchone()
        if not row:
            con.close()
            return False
        new_val = 0 if row["active"] == 1 else 1
        con.execute("UPDATE wallets SET active = ? WHERE key = ?", (new_val, key))
    con.close()
    return bool(new_val)

def get_stats():
    con = _db()
    total_users = con.execute("SELECT COUNT(*) as c FROM users").fetchone()["c"]
    total_orders = con.execute("SELECT COUNT(*) as c FROM orders").fetchone()["c"]
    pending_orders = con.execute("SELECT COUNT(*) as c FROM orders WHERE status = 'pending'").fetchone()["c"]
    total_revenue = con.execute("SELECT COALESCE(SUM(amount), 0.0) as s FROM deposits WHERE status = 'approved'").fetchone()["s"]
    pending_deposits = con.execute("SELECT COUNT(*) as c FROM deposits WHERE status = 'pending'").fetchone()["c"]
    con.close()
    return total_users, total_orders, pending_orders, total_revenue, pending_deposits

# ── Redeem Codes ──────────────────────────────────────

def create_redeem_code(code: str, amount: float, max_uses: int = 1) -> bool:
    con = _db()
    try:
        with con:
            con.execute("INSERT INTO redeem_codes (code, amount, max_uses, used_count) VALUES (?, ?, ?, 0)",
                        (code.strip().upper(), amount, max_uses))
        con.close()
        return True
    except sqlite3.IntegrityError:
        con.close()
        return False

def claim_redeem_code(code: str, tg_id: int):
    con = _db()
    code_up = code.strip().upper()
    with con:
        rc = con.execute("SELECT * FROM redeem_codes WHERE code = ?", (code_up,)).fetchone()
        if not rc:
            con.close()
            return False, "⚠️ Invalid or non-existent redeem code."
        if rc["used_count"] >= rc["max_uses"]:
            con.close()
            return False, "❌ This code has reached its maximum limit."
        
        already = con.execute("SELECT id FROM code_claims WHERE code = ? AND tg_id = ?", (code_up, tg_id)).fetchone()
        if already:
            con.close()
            return False, "⚠️ You have already claimed this promo code."
        
        con.execute("INSERT INTO code_claims (code, tg_id) VALUES (?, ?)", (code_up, tg_id))
        con.execute("UPDATE redeem_codes SET used_count = used_count + 1 WHERE code = ?", (code_up,))
        con.execute("UPDATE users SET balance = balance + ? WHERE tg_id = ?", (rc["amount"], tg_id))
    con.close()
    return True, f"🎉 <b>Success!</b> ${rc['amount']:.2f} USDT added to your balance."

init_db()
