#!/usr/bin/env python3
"""shared_db.py — All DB functions.
Uses Turso (free SQLite cloud) when TURSO_URL + TURSO_TOKEN are set.
Falls back to local SQLite for testing.
"""

import os, random
from datetime import datetime

TURSO_URL   = os.environ.get("TURSO_URL", "").strip()
TURSO_TOKEN = os.environ.get("TURSO_TOKEN", "").strip()
USE_TURSO   = bool(TURSO_URL and TURSO_TOKEN)

if USE_TURSO:
    import libsql_experimental as libsql
else:
    import sqlite3

LOCAL_DB = "xingmart.db"
DB_FILE  = LOCAL_DB   # kept for compatibility

def _db():
    if USE_TURSO:
        return libsql.connect(database=TURSO_URL, auth_token=TURSO_TOKEN)
    con = sqlite3.connect(LOCAL_DB)
    con.execute("PRAGMA journal_mode=WAL")
    return con

def init_db():
    con = _db()
    con.execute("""CREATE TABLE IF NOT EXISTS users (
        tg_id INTEGER PRIMARY KEY, name TEXT, username TEXT,
        created_at TEXT, balance REAL DEFAULT 0.0, lang TEXT DEFAULT 'en')""")
    try: con.execute("ALTER TABLE users ADD COLUMN lang TEXT DEFAULT 'en'")
    except: pass
    try: con.execute("ALTER TABLE users ADD COLUMN banned INTEGER DEFAULT 0")
    except: pass
    con.execute("""CREATE TABLE IF NOT EXISTS products (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT, price REAL, stock INTEGER DEFAULT 0,
        delivery_type TEXT DEFAULT 'text', delivery_content TEXT,
        active INTEGER DEFAULT 1)""")
    con.execute("""CREATE TABLE IF NOT EXISTS carts (
        tg_id INTEGER, product_id INTEGER, PRIMARY KEY (tg_id, product_id))""")
    con.execute("""CREATE TABLE IF NOT EXISTS orders (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        tg_id INTEGER, order_ref TEXT,
        product_id INTEGER, product_name TEXT,
        price REAL, quantity INTEGER DEFAULT 1,
        status TEXT DEFAULT 'pending',
        created_at TEXT, notified INTEGER DEFAULT 0)""")
    con.execute("""CREATE TABLE IF NOT EXISTS deposits (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        tg_id INTEGER, ref TEXT,
        amount REAL DEFAULT 0, network TEXT,
        txn_id TEXT, status TEXT DEFAULT 'pending',
        created_at TEXT, notified INTEGER DEFAULT 0)""")
    con.execute("""CREATE TABLE IF NOT EXISTS wallets (
        key TEXT PRIMARY KEY, label TEXT, address TEXT, active INTEGER DEFAULT 1)""")
    con.execute("""CREATE TABLE IF NOT EXISTS redeem_codes (
        code TEXT PRIMARY KEY, amount REAL,
        max_uses INTEGER, used INTEGER DEFAULT 0, created_at TEXT)""")

    r = con.execute("SELECT COUNT(*) FROM wallets").fetchone()
    if r and r[0] == 0:
        for row in [
            ("usdt_bep20","💵 USDT BEP-20 (BSC)","0x4C7894610C455d6381aCe22dce2468ccf95D2875"),
            ("usdt_eth",  "🔷 USDT ERC-20 (ETH)", "0x4C7894610C455d6381aCe22dce2468ccf95D2875"),
            ("btc",       "₿ Bitcoin (BTC)",       "bc1q0gtel9l8sczkrlv3ywdqkk9adln8f84zw0wczr"),
            ("ton",       "💎 TON",                "UQCAoTZkL0N_gxjDnV1-PC1rgqdPgfGDhtJs-YU2yHbkeZy-"),
            ("usdt_sol",  "🟣 USDT Solana (SPL)",  "CLiBT9JuTJCjpBkf4HXZMCimkzxJKX8PJxJtxHTd6iFe"),
            ("bnb",       "🟡 BNB (BSC)",          "0x4C7894610C455d6381aCe22dce2468ccf95D2875"),
        ]:
            con.execute("INSERT OR IGNORE INTO wallets (key,label,address,active) VALUES (?,?,?,1)", row)
    # ── Seed products if empty ────────────────────────
    p = con.execute("SELECT COUNT(*) FROM products").fetchone()
    if p and p[0] == 0:
        DELIVERY = "Contact @idoiii for delivery after order."
        _products = [
            ("Adobe Full App",              4.00,   69),
            ("Canva Edu 1Y",                8.00,   76),
            ("Canva Pro 1Y",               15.00,   72),
            ("CapCut 1M",                   3.00,   42),
            ("Cursor Pro 1M",              10.00,   40),
            ("Cursor Pro Plus",            25.00,    9),
            ("ElevenLabs 1M",              10.00,   87),
            ("ExpressVPN / NordVPN",        2.00,   71),
            ("Figma Pro 1Y",               16.00,    3),
            ("Gemini Pro 18M",              1.50,   82),
            ("Grok Super 7 Days",           3.00,   52),
            ("Grok Super 1M",               5.00,   91),
            ("Grok Super 3 Months",        16.00,   85),
            ("HeyGen Creator 1M",          25.00,   52),
            ("Highsfield Ultra 1M",        40.00,   28),
            ("Kiro Pro Max 1M",             8.00,   68),
            ("Kling Ultra 26K Credits",    80.00,   10),
            ("Lovable AI Pro 1M",          20.00,   93),
            ("Microsoft Office Slot 1Y",    8.00,   10),
            ("Suno Premium 1M",            14.00,   34),
            ("Xbox Game Pass Ultimate 1Y", 20.00,   50),
            ("Xbox Game Pass Ultimate 1M",  4.00,   50),
            ("Gemini Ultra Family 1M",     40.00,   97),
            ("ChatGPT Plus",                4.00,    7),
            ("ChatGPT Pro",                32.00,   60),
            ("Grok Super 1Y",              20.00,   19),
            ("Claude Pro",                 12.00,   18),
            ("Claude Max20 Slot",          70.00,   13),
            ("GPT x20 Pro",               30.00,   34),
            ("Claude Max5",                45.00,   45),
            ("Perplexity Pro 1Y",          10.00,   18),
            ("5 AI Combo",                 50.00,   50),
            ("OpenArt Wonder",             55.00,   18),
            ("OpenArt Essential",          10.00,   32),
            ("Netflix 1Y",                 10.00,   84),
            ("Netflix 1M",                  3.00,   26),
            ("YouTube 3M",                  3.00,   18),
            ("YouTube 1Y",                 12.00,   76),
            ("Claude Method",             200.00,  100),
            ("Gemini Ultra Method",       120.00,  100),
        ]
        for name, price, stock in _products:
            con.execute(
                "INSERT INTO products (name,price,stock,delivery_type,delivery_content,active) VALUES (?,?,?,?,?,1)",
                (name, price, stock, "text", DELIVERY))

    con.commit(); con.close()

# ── Users ──────────────────────────────────────────────
def ensure_user(tg_id, name, username=""):
    con = _db()
    con.execute(
        "INSERT OR IGNORE INTO users (tg_id,name,username,created_at,balance,lang) VALUES (?,?,?,?,0.0,'en')",
        (tg_id, name, username, datetime.now().isoformat()))
    con.commit(); con.close()

def get_lang(tg_id):
    con = _db()
    r = con.execute("SELECT lang FROM users WHERE tg_id=?", (tg_id,)).fetchone()
    con.close(); return (r[0] or "en") if r else "en"

def set_lang(tg_id, lang):
    con = _db()
    con.execute("UPDATE users SET lang=? WHERE tg_id=?", (lang, tg_id))
    con.commit(); con.close()

def get_balance(tg_id):
    con = _db()
    r = con.execute("SELECT balance FROM users WHERE tg_id=?", (tg_id,)).fetchone()
    con.close(); return r[0] if r else 0.0

def deduct_balance(tg_id, amount):
    con = _db()
    con.execute("UPDATE users SET balance=balance-? WHERE tg_id=?", (amount, tg_id))
    con.commit(); con.close()

def add_balance(tg_id, amount):
    con = _db()
    con.execute("UPDATE users SET balance=balance+? WHERE tg_id=?", (amount, tg_id))
    con.commit(); con.close()

def get_user_info(tg_id):
    con = _db()
    r = con.execute("SELECT name,username,created_at,balance FROM users WHERE tg_id=?", (tg_id,)).fetchone()
    con.close(); return r

def set_balance(tg_id, amount):
    con = _db()
    con.execute("UPDATE users SET balance=? WHERE tg_id=?", (amount, tg_id))
    con.commit(); con.close()

def get_all_users():
    con = _db()
    rows = con.execute("SELECT tg_id,name,username,balance FROM users ORDER BY tg_id DESC LIMIT 50").fetchall()
    con.close(); return rows

# ── Bans ───────────────────────────────────────────────
def is_banned(tg_id):
    con = _db()
    r = con.execute("SELECT banned FROM users WHERE tg_id=?", (tg_id,)).fetchone()
    con.close(); return bool(r and r[0])

def ban_user(tg_id):
    con = _db()
    r = con.execute("SELECT tg_id FROM users WHERE tg_id=?", (tg_id,)).fetchone()
    if r: con.execute("UPDATE users SET banned=1 WHERE tg_id=?", (tg_id,)); con.commit()
    con.close(); return bool(r)

def unban_user(tg_id):
    con = _db()
    r = con.execute("SELECT tg_id FROM users WHERE tg_id=?", (tg_id,)).fetchone()
    if r: con.execute("UPDATE users SET banned=0 WHERE tg_id=?", (tg_id,)); con.commit()
    con.close(); return bool(r)

def find_tg_id_by_username(username):
    """Look up a user's tg_id by @username (or username without @). Only works
    if the user has interacted with the store bot before (i.e. exists in DB)."""
    uname = username.lstrip("@").strip().lower()
    con = _db()
    r = con.execute("SELECT tg_id FROM users WHERE LOWER(username)=?", (uname,)).fetchone()
    con.close(); return r[0] if r else None

def get_banned_users():
    con = _db()
    rows = con.execute(
        "SELECT tg_id,name,username FROM users WHERE banned=1 ORDER BY tg_id DESC").fetchall()
    con.close(); return rows

# ── Products ───────────────────────────────────────────
def get_active_products():
    con = _db()
    rows = con.execute(
        "SELECT id,name,price,stock,delivery_type,delivery_content FROM products WHERE active=1 ORDER BY id"
    ).fetchall()
    con.close()
    return [{"id":r[0],"name":r[1],"price":r[2],"stock":r[3],"delivery_type":r[4],"delivery_content":r[5]} for r in rows]

def get_all_products():
    con = _db()
    rows = con.execute("SELECT id,name,price,stock,delivery_type,active FROM products ORDER BY id").fetchall()
    con.close()
    return [{"id":r[0],"name":r[1],"price":r[2],"stock":r[3],"delivery_type":r[4],"active":r[5]} for r in rows]

def get_product(pid):
    con = _db()
    r = con.execute(
        "SELECT id,name,price,stock,delivery_type,delivery_content,active FROM products WHERE id=?", (pid,)
    ).fetchone()
    con.close()
    if not r: return None
    return {"id":r[0],"name":r[1],"price":r[2],"stock":r[3],"delivery_type":r[4],"delivery_content":r[5],"active":r[6]}

def add_product(name, price, stock, delivery_type, delivery_content):
    con = _db()
    con.execute("INSERT INTO products (name,price,stock,delivery_type,delivery_content,active) VALUES (?,?,?,?,?,1)",
                (name, price, stock, delivery_type, delivery_content))
    con.commit()
    pid = con.execute("SELECT last_insert_rowid()").fetchone()[0]
    con.close(); return pid

def update_product(pid, **kwargs):
    con = _db()
    for k, v in kwargs.items():
        con.execute(f"UPDATE products SET {k}=? WHERE id=?", (v, pid))
    con.commit(); con.close()

def toggle_product(pid):
    con = _db()
    con.execute("UPDATE products SET active=CASE WHEN active=1 THEN 0 ELSE 1 END WHERE id=?", (pid,))
    con.commit()
    r = con.execute("SELECT active FROM products WHERE id=?", (pid,)).fetchone()
    con.close(); return r[0] if r else 0

def delete_product(pid):
    con = _db()
    con.execute("DELETE FROM products WHERE id=?", (pid,))
    con.commit(); con.close()

def reduce_stock(pid, qty):
    con = _db()
    con.execute("UPDATE products SET stock=MAX(0,stock-?) WHERE id=?", (qty, pid))
    con.commit(); con.close()

# ── Cart ───────────────────────────────────────────────
def get_cart(tg_id):
    con = _db()
    ids = {r[0] for r in con.execute("SELECT product_id FROM carts WHERE tg_id=?", (tg_id,)).fetchall()}
    con.close()
    return [p for p in get_active_products() if p["id"] in ids]

def add_to_cart(tg_id, pid):
    con = _db(); con.execute("INSERT OR IGNORE INTO carts VALUES (?,?)", (tg_id, pid))
    con.commit(); con.close()

def remove_from_cart(tg_id, pid):
    con = _db(); con.execute("DELETE FROM carts WHERE tg_id=? AND product_id=?", (tg_id, pid))
    con.commit(); con.close()

def clear_cart(tg_id):
    con = _db(); con.execute("DELETE FROM carts WHERE tg_id=?", (tg_id,))
    con.commit(); con.close()

# ── Orders ─────────────────────────────────────────────
def save_order(tg_id, product, order_ref, quantity=1):
    con = _db(); now = datetime.now().strftime("%d/%m/%Y %H:%M")
    total_price = round(product["price"] * quantity, 4)
    con.execute(
        "INSERT INTO orders (tg_id,order_ref,product_id,product_name,price,quantity,status,created_at,notified) "
        "VALUES (?,?,?,?,?,?,'pending',?,0)",
        (tg_id, order_ref, product["id"], product["name"], total_price, quantity, now))
    con.commit(); con.close()

def get_orders(tg_id):
    con = _db()
    rows = con.execute(
        "SELECT order_ref,product_name,price,quantity,status,created_at FROM orders WHERE tg_id=? ORDER BY id DESC",
        (tg_id,)).fetchall()
    con.close(); return rows

def get_unnotified_orders():
    con = _db()
    rows = con.execute("""
        SELECT o.id,o.tg_id,o.order_ref,o.product_name,o.price,o.quantity,o.created_at,u.name,u.username
        FROM orders o LEFT JOIN users u ON o.tg_id=u.tg_id
        WHERE o.notified=0 ORDER BY o.id""").fetchall()
    con.close(); return rows

def mark_order_notified(oid):
    con = _db(); con.execute("UPDATE orders SET notified=1 WHERE id=?", (oid,))
    con.commit(); con.close()

def deliver_order(order_ref):
    con = _db()
    con.execute("UPDATE orders SET status='delivered' WHERE order_ref=?", (order_ref,))
    con.commit()
    r = con.execute(
        "SELECT o.tg_id, p.delivery_type, p.delivery_content, o.quantity "
        "FROM orders o LEFT JOIN products p ON o.product_id=p.id WHERE o.order_ref=?",
        (order_ref,)).fetchone()
    con.close(); return r

def get_recent_orders_admin(limit=20):
    con = _db()
    rows = con.execute("""
        SELECT o.order_ref,o.product_name,o.price,o.quantity,o.status,o.created_at,
               u.name,u.username,o.tg_id
        FROM orders o LEFT JOIN users u ON o.tg_id=u.tg_id
        ORDER BY o.id DESC LIMIT ?""", (limit,)).fetchall()
    con.close(); return rows

# ── Deposits ───────────────────────────────────────────
def save_deposit_txn(tg_id, ref, network, txn_id):
    con = _db(); now = datetime.now().strftime("%d/%m/%Y %H:%M")
    con.execute(
        "INSERT INTO deposits (tg_id,ref,network,txn_id,status,created_at,notified) VALUES (?,?,?,?,'pending',?,0)",
        (tg_id, ref, network, txn_id, now))
    con.commit(); con.close()

def get_pending_deposits():
    con = _db()
    rows = con.execute("""
        SELECT d.id,d.tg_id,d.ref,d.network,d.txn_id,d.created_at,u.name,u.username
        FROM deposits d LEFT JOIN users u ON d.tg_id=u.tg_id
        WHERE d.status='pending' ORDER BY d.id DESC LIMIT 20""").fetchall()
    con.close(); return rows

def get_unnotified_deposits():
    con = _db()
    rows = con.execute("""
        SELECT d.id,d.tg_id,d.ref,d.network,d.txn_id,d.created_at,u.name,u.username
        FROM deposits d LEFT JOIN users u ON d.tg_id=u.tg_id
        WHERE d.notified=0 ORDER BY d.id""").fetchall()
    con.close(); return rows

def mark_deposit_notified(dep_id):
    con = _db(); con.execute("UPDATE deposits SET notified=1 WHERE id=?", (dep_id,))
    con.commit(); con.close()

def approve_deposit(dep_id, amount):
    con = _db()
    r = con.execute("SELECT tg_id FROM deposits WHERE id=?", (dep_id,)).fetchone()
    if r:
        con.execute("UPDATE deposits SET status='approved',amount=? WHERE id=?", (amount, dep_id))
        con.execute("UPDATE users SET balance=balance+? WHERE tg_id=?", (amount, r[0]))
        con.commit()
    con.close(); return r[0] if r else None

def reject_deposit(dep_id):
    con = _db()
    r = con.execute("SELECT tg_id FROM deposits WHERE id=?", (dep_id,)).fetchone()
    con.execute("UPDATE deposits SET status='rejected' WHERE id=?", (dep_id,))
    con.commit(); con.close()
    return r[0] if r else None

# ── Wallets ────────────────────────────────────────────
def get_active_wallets():
    con = _db()
    rows = con.execute("SELECT key,label,address FROM wallets WHERE active=1").fetchall()
    con.close(); return {r[0]: (r[1], r[2]) for r in rows}

def get_all_wallets():
    con = _db()
    rows = con.execute("SELECT key,label,address,active FROM wallets").fetchall()
    con.close()
    return [{"key":r[0],"label":r[1],"address":r[2],"active":r[3]} for r in rows]

def update_wallet(key, address):
    con = _db(); con.execute("UPDATE wallets SET address=? WHERE key=?", (address, key))
    con.commit(); con.close()

def toggle_wallet(key):
    con = _db()
    con.execute("UPDATE wallets SET active=CASE WHEN active=1 THEN 0 ELSE 1 END WHERE key=?", (key,))
    con.commit()
    r = con.execute("SELECT active FROM wallets WHERE key=?", (key,)).fetchone()
    con.close(); return r[0] if r else 0

# ── Redeem Codes ───────────────────────────────────────
def create_redeem_code(code, amount, max_uses):
    con = _db()
    try:
        con.execute("INSERT INTO redeem_codes (code,amount,max_uses,used,created_at) VALUES (?,?,?,0,?)",
                    (code.upper(), amount, max_uses, datetime.now().isoformat()))
        con.commit(); con.close(); return True
    except: con.close(); return False

def try_redeem(tg_id, code):
    con = _db()
    r = con.execute("SELECT amount,max_uses,used FROM redeem_codes WHERE code=?", (code.upper(),)).fetchone()
    if not r: con.close(); return None, "❌ Invalid code."
    amount, max_uses, used = r
    if used >= max_uses: con.close(); return None, "❌ Code already used up."
    con.execute("UPDATE redeem_codes SET used=used+1 WHERE code=?", (code.upper(),))
    con.execute("UPDATE users SET balance=balance+? WHERE tg_id=?", (amount, tg_id))
    con.commit(); con.close(); return amount, "ok"

# ── Stats ──────────────────────────────────────────────
def get_stats():
    con = _db()
    u  = con.execute("SELECT COUNT(*) FROM users").fetchone()[0]
    o  = con.execute("SELECT COUNT(*) FROM orders").fetchone()[0]
    po = con.execute("SELECT COUNT(*) FROM orders WHERE status='pending'").fetchone()[0]
    r  = con.execute("SELECT COALESCE(SUM(price),0) FROM orders").fetchone()[0]
    pd = con.execute("SELECT COUNT(*) FROM deposits WHERE status='pending'").fetchone()[0]
    con.close(); return u, o, po, r, pd

def new_ref(prefix):
    return f"#{prefix}{random.randint(10000,99999)}"

# ── Announcements ──────────────────────────────────────
def get_all_user_ids():
    con = _db()
    rows = con.execute("SELECT tg_id FROM users").fetchall()
    con.close(); return [r[0] for r in rows]

def randomize_all_stocks():
    con = _db()
    products = con.execute("SELECT id FROM products WHERE active=1").fetchall()
    for (pid,) in products:
        con.execute("UPDATE products SET stock=? WHERE id=?", (random.randint(1, 99), pid))
    con.commit()
    count = len(products)
    con.close(); return count
