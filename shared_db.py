#!/usr/bin/env python3
"""
shared_db.py — MongoDB backend for Nex Shop.
Data persists permanently in MongoDB Atlas (free 512MB tier).

Setup:
  1. Create free cluster at https://mongodb.com/atlas
  2. Get connection string → add as MONGO_URI env variable on Railway
  3. All data (users, orders, deposits, products) survives restarts forever.
"""

import os
import random
from datetime import datetime, timezone

from pymongo import MongoClient, ASCENDING, DESCENDING
from pymongo.errors import DuplicateKeyError

# ── Connection ──────────────────────────────────────────────────────────────

MONGO_URI = os.environ.get("MONGO_URI", "mongodb://localhost:27017/")
DB_NAME   = os.environ.get("MONGO_DB_NAME", "nex_shop")

_mongo_client = None

def _db():
    global _mongo_client
    if _mongo_client is None:
        _mongo_client = MongoClient(MONGO_URI, serverSelectionTimeoutMS=8000)
    return _mongo_client[DB_NAME]

def _clean(doc):
    """Remove MongoDB _id, return plain dict."""
    if doc is None:
        return None
    d = dict(doc)
    d.pop("_id", None)
    return d

def _next_id(name):
    """Atomic auto-increment integer ID using counters collection."""
    result = _db().counters.find_one_and_update(
        {"_id": name},
        {"$inc": {"seq": 1}},
        upsert=True,
        return_document=True,
    )
    return result["seq"]

def _now():
    return datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")

# ── Master Catalog (prices & descriptions baked in) ─────────────────────────

_L30  = "\ud83d\udce7 Login format: Email & Password\n\ud83d\udee1\ufe0f 30 days warranty"
_L6M  = "\ud83d\udce7 Login format: Email & Password\n\ud83d\udee1\ufe0f 6 months warranty"
_L18M = "\ud83d\udce7 Login format: Email & Password\n\ud83d\udee1\ufe0f 18 months warranty"
_GIFT = "\ud83c\udf81 Gift link format \u2014 redeem on your email\n\ud83d\udee1\ufe0f 30 days warranty"
_TEAM = "\ud83d\udc65 Team account\n\ud83d\udce7 Login format: Email & Password\n\ud83d\udee1\ufe0f 30 days warranty\n\u26a0\ufe0f Warranty void if you leave the team"

MASTER_PRODUCTS = [
    # Adobe
    {"name": "Adobe Full App",          "price": 5.00,   "description": _L30},
    # CapCut
    {"name": "CapCut 1 Month",           "price": 2.00,   "description": "\ud83d\udce7 Login format: Email & Password\n\ud83d\udee1\ufe0f 30 days warranty"},
    {"name": "CapCut 6 Months",          "price": 7.00,   "description": "\ud83d\udce7 Login format: Email & Password\n\ud83d\udee1\ufe0f 6 months warranty"},
    {"name": "CapCut 12 Months",         "price": 11.00,  "description": "\ud83d\udce7 Login format: Email & Password\n\ud83d\udee1\ufe0f 12 months warranty"},
    # ChatGPT
    {"name": "ChatGPT Plus",             "price": 3.00,   "description": _L30},
    {"name": "ChatGPT Pro x20",          "price": 47.00,  "description": _L30},
    # Grok
    {"name": "Grok Super",               "price": 6.00,   "description": _L30},
    {"name": "Grok Heavy",               "price": 30.00,  "description": _L30},
    # Claude
    {"name": "Claude Pro",               "price": 11.50,  "description": _GIFT},
    {"name": "Claude Max5",              "price": 47.00,  "description": _GIFT},
    {"name": "Claude Max20",             "price": 84.00,  "description": _GIFT},
    # Cursor
    {"name": "Cursor Pro",               "price": 10.00,  "description": _L30},
    {"name": "Cursor Pro Plus",          "price": 28.00,  "description": _L30},
    {"name": "Cursor Ultra",             "price": 68.00,  "description": _L30},
    # ElevenLabs
    {"name": "ElevenLabs Creator 1M",    "price": 6.00,   "description": _L30},
    {"name": "ElevenLabs Pro 1M",        "price": 47.00,  "description": _L30},
    # Higgsfield
    {"name": "Higgsfield Pro",           "price": 18.00,  "description": _L30},
    {"name": "Higgsfield Max",           "price": 34.00,  "description": _L30},
    # Figma
    {"name": "Figma Starter 1M",         "price": 1.00,   "description": _L30},
    {"name": "Figma Professional 1M",    "price": 12.00,  "description": _L30},
    {"name": "Figma Team 1M",            "price": 34.00,  "description": _TEAM},
    # Gemini
    {"name": "Gemini Antigravity Ultra", "price": 52.00,  "description": "\ud83d\udc68\u200d\ud83d\udc69\u200d\ud83d\udc67 Family account \u2014 invite up to 5 members\n\ud83d\udcb3 25,000 credits included\n\ud83d\udee1\ufe0f 30 days warranty"},
    {"name": "Gemini Pro",               "price": 4.00,   "description": "\ud83d� Activation link \u2014 activate on your email\n\u23f3 Must activate within 30 days\n\ud83d\udee1\ufe0f 18 months warranty"},
    # Kling
    {"name": "Kling AI Pro 1M",          "price": 14.00,  "description": _L30},
    {"name": "Kling AI Premier 1M",      "price": 30.00,  "description": _L30},
    {"name": "Kling AI Ultra 1M",        "price": 85.00,  "description": _L30},
    # Kiro
    {"name": "Kiro ProPlus 1M",          "price": 18.00,  "description": _L30},
    {"name": "Kiro Pro Max 1M",          "price": 55.00,  "description": _L30},
    {"name": "Kiro Power 1M",            "price": 120.00, "description": _L30},
    # Lovable
    {"name": "Lovable Pro 1M",           "price": 14.00,  "description": _L30},
    {"name": "Lovable Business 1M",      "price": 32.00,  "description": _TEAM},
    # Manus
    {"name": "Manus Standard 1M",        "price": 9.00,   "description": _L30},
    {"name": "Manus 8k Credits 1M",      "price": 18.00,  "description": _L30},
    {"name": "Manus 40k Credits 1M",     "price": 125.00, "description": _L30},
    # YouTube
    {"name": "YouTube 1 Month",          "price": 2.00,   "description": "\ud83d\udce8 After ordering, send your email to the bot \u2014 upgrade delivered within 5 seconds\n\ud83d\udeab Do not leave the family group\n\ud83d\udee1\ufe0f 30 days warranty"},
    {"name": "YouTube 3 Months",         "price": 5.00,   "description": "\ud83d\udce8 After ordering, send your email to the bot \u2014 upgrade delivered within 5 seconds\n\ud83d\udeab Do not leave the family group\n\ud83d\udee1\ufe0f 90 days warranty"},
    {"name": "YouTube 6 Months",         "price": 9.00,   "description": "\ud83d\udce8 After ordering, send your email to the bot \u2014 upgrade delivered within 5 seconds\n\ud83d\udeab Do not leave the family group\n\ud83d\udee1\ufe0f 6 months warranty"},
    {"name": "YouTube 12 Months",        "price": 15.00,  "description": "\ud83d\udce8 After ordering, send your email to the bot \u2014 upgrade delivered within 5 seconds\n\ud83d\udeab Do not leave the family group\n\ud83d\udee1\ufe0f 12 months warranty"},
    # Others
    {"name": "Gamma Pro",                "price": 6.00,   "description": _L30},
    {"name": "Gamma Ultra 1M",           "price": 45.00,  "description": _L30},
    {"name": "Suno Premium 1M",          "price": 14.00,  "description": _L30},
    {"name": "Perplexity Pro",           "price": 14.00,  "description": "\ud83d\udd11 12-month activation code \u2014 redeem on your account\n\ud83d\udee1\ufe0f 6 months warranty"},
    {"name": "HeyGen 1M",               "price": 14.00,  "description": _L30},
    {"name": "Krea AI 1M",              "price": 19.00,  "description": _L30},
]

DEFAULT_WALLETS = [
    {"key": "usdt_erc20", "label": "USDT (ERC-20)",     "address": "0xYourERC20Address",  "active": 1},
    {"key": "usdt_bep20", "label": "USDT (BEP-20/BSC)", "address": "0xYourBEP20Address",  "active": 1},
    {"key": "usdt_trc20", "label": "USDT (TRC-20)",     "address": "TYourTRC20Address",    "active": 1},
    {"key": "btc",        "label": "Bitcoin (BTC)",     "address": "bc1YourBTCAddress",    "active": 1},
    {"key": "ton",        "label": "TON Coin",          "address": "EQYourTONAddress",     "active": 1},
    {"key": "ltc",        "label": "Litecoin (LTC)",    "address": "LYourLTCAddress",      "active": 1},
]

# ── Init ─────────────────────────────────────────────────────────────────────

def init_db():
    db = _db()

    # Only run full init once — skip on subsequent restarts
    if db.meta.find_one({"_id": "init_done"}):
        return

    # Indexes (background=True so they don't block)
    db.users.create_index("tg_id", unique=True, background=True)
    db.products.create_index("id", unique=True, background=True)
    db.products.create_index("name", background=True)
    db.deposits.create_index("id", unique=True, background=True)
    db.deposits.create_index("ref", background=True)
    db.orders.create_index("id", unique=True, background=True)
    db.orders.create_index("ref", background=True)
    db.wallets.create_index("key", unique=True, background=True)
    db.redeem_codes.create_index("code", unique=True, background=True)
    db.code_claims.create_index([("code", ASCENDING), ("tg_id", ASCENDING)], unique=True, background=True)

    # Seed wallets
    for w in DEFAULT_WALLETS:
        try:
            db.wallets.insert_one(w)
        except DuplicateKeyError:
            pass

    # Seed products (only if none exist)
    if db.products.count_documents({}) == 0:
        for item in MASTER_PRODUCTS:
            pid = _next_id("products")
            db.products.insert_one({
                "id": pid,
                "name": item["name"],
                "price": item["price"],
                "stock": random.randint(20, 95),
                "delivery_type": "text",
                "delivery_content": "Account/License Key",
                "description": item["description"],
                "active": 1,
            })

    # Mark init as done — never run full setup again
    db.meta.insert_one({"_id": "init_done"})

def ensure_all_products():
    db = _db()
    existing = {p["name"] for p in db.products.find({}, {"name": 1})}
    for item in MASTER_PRODUCTS:
        if item["name"] not in existing:
            pid = _next_id("products")
            db.products.insert_one({
                "id": pid,
                "name": item["name"],
                "price": item["price"],
                "stock": random.randint(20, 95),
                "delivery_type": "text",
                "delivery_content": "Account/License Key",
                "description": item["description"],
                "active": 1,
            })

def dedup_products():
    db = _db()
    seen = {}
    for p in db.products.find({}, {"id": 1, "name": 1}).sort("id", ASCENDING):
        if p["name"] in seen:
            db.products.delete_one({"id": p["id"]})
        else:
            seen[p["name"]] = p["id"]

def maybe_migrate_products():
    pass  # No-op — kept for compatibility

# ── Users ────────────────────────────────────────────────────────────────────

def get_or_create_user(tg_id, name="", username="", referrer_id=None):
    db = _db()
    doc = db.users.find_one({"tg_id": tg_id})
    if not doc:
        ref_id_valid = None
        if referrer_id and referrer_id != tg_id:
            if db.users.find_one({"tg_id": referrer_id}):
                ref_id_valid = referrer_id
        try:
            db.users.insert_one({
                "tg_id": tg_id,
                "name": name or "User",
                "username": username or "",
                "balance": 0.0,
                "total_deposited": 0.0,
                "is_banned": 0,
                "referred_by": ref_id_valid,
                "referral_count": 0,
                "first_order_done": 0,
                "lang": "en",
                "joined_at": _now(),
            })
        except DuplicateKeyError:
            pass
        if ref_id_valid:
            db.users.update_one({"tg_id": ref_id_valid}, {"$inc": {"referral_count": 1}})
        doc = db.users.find_one({"tg_id": tg_id})
    else:
        upd = {}
        if name:     upd["name"]     = name
        if username: upd["username"] = username
        if upd:
            db.users.update_one({"tg_id": tg_id}, {"$set": upd})
        doc = db.users.find_one({"tg_id": tg_id})
    return _clean(doc)

def get_user(tg_id):
    return _clean(_db().users.find_one({"tg_id": tg_id}))

def get_lang(uid):
    return get_user_lang(uid)

def get_user_lang(uid):
    doc = _db().users.find_one({"tg_id": uid}, {"lang": 1})
    return (doc or {}).get("lang", "en") or "en"

def set_user_lang(tg_id, lang):
    _db().users.update_one({"tg_id": tg_id}, {"$set": {"lang": lang}})

def get_user_total_spent(tg_id):
    r = list(_db().orders.aggregate([
        {"$match": {"tg_id": tg_id, "status": "delivered"}},
        {"$group": {"_id": None, "t": {"$sum": "$price"}}}
    ]))
    return r[0]["t"] if r else 0.0

def get_user_total_deposited(tg_id):
    r = list(_db().deposits.aggregate([
        {"$match": {"tg_id": tg_id, "status": "approved"}},
        {"$group": {"_id": None, "t": {"$sum": "$amount"}}}
    ]))
    return r[0]["t"] if r else 0.0

def maybe_pay_referral_commission(tg_id, order_amount):
    db = _db()
    user = db.users.find_one({"tg_id": tg_id}, {"referred_by": 1, "first_order_done": 1})
    if user and user.get("first_order_done") == 0 and user.get("referred_by"):
        commission = round(order_amount * 0.10, 4)
        db.users.update_one({"tg_id": user["referred_by"]}, {"$inc": {"balance": commission}})
        db.users.update_one({"tg_id": tg_id}, {"$set": {"first_order_done": 1}})

def get_all_users():
    docs = _db().users.find(
        {}, {"tg_id": 1, "name": 1, "username": 1, "balance": 1, "referral_count": 1}
    ).sort("joined_at", DESCENDING)
    return [
        (d["tg_id"], d.get("name",""), d.get("username",""), d.get("balance",0.0), d.get("referral_count",0))
        for d in docs
    ]

def get_all_user_ids():
    return [d["tg_id"] for d in _db().users.find({"is_banned": 0}, {"tg_id": 1})]

def set_balance(tg_id, amount):
    _db().users.update_one({"tg_id": tg_id}, {"$set": {"balance": amount}})

def add_balance(tg_id, amount):
    _db().users.update_one({"tg_id": tg_id}, {"$inc": {"balance": amount}})

def deduct_balance(tg_id, amount):
    result = _db().users.find_one_and_update(
        {"tg_id": tg_id, "balance": {"$gte": amount}},
        {"$inc": {"balance": -amount}},
    )
    return result is not None

def ban_user(tg_id):
    _db().users.update_one({"tg_id": tg_id}, {"$set": {"is_banned": 1}})

def unban_user(tg_id):
    _db().users.update_one({"tg_id": tg_id}, {"$set": {"is_banned": 0}})

def is_banned(tg_id):
    doc = _db().users.find_one({"tg_id": tg_id}, {"is_banned": 1})
    return bool(doc and doc.get("is_banned") == 1)

def get_banned_users():
    docs = _db().users.find({"is_banned": 1}, {"tg_id": 1, "name": 1, "username": 1})
    return [(d["tg_id"], d.get("name",""), d.get("username","")) for d in docs]

def find_tg_id_by_username(username):
    clean = username.lstrip("@").strip()
    doc = _db().users.find_one(
        {"username": {"$regex": f"^{clean}$", "$options": "i"}}, {"tg_id": 1}
    )
    return doc["tg_id"] if doc else None

# ── Products ──────────────────────────────────────────────────────────────────

def get_all_products(active_only=False):
    query = {"active": 1} if active_only else {}
    return [_clean(d) for d in _db().products.find(query).sort("id", ASCENDING)]

def get_product(pid):
    return _clean(_db().products.find_one({"id": pid}))

def add_product(name, price, stock, dtype, dcontent, description=""):
    pid = _next_id("products")
    _db().products.insert_one({
        "id": pid, "name": name, "price": price, "stock": stock,
        "delivery_type": dtype, "delivery_content": dcontent,
        "description": description, "active": 1,
    })
    return pid

def update_product(pid, **kwargs):
    _db().products.update_one({"id": pid}, {"$set": kwargs})

def delete_product(pid):
    _db().products.delete_one({"id": pid})

def toggle_product(pid):
    doc = _db().products.find_one({"id": pid}, {"active": 1})
    if not doc:
        return False
    new_val = 0 if doc["active"] == 1 else 1
    _db().products.update_one({"id": pid}, {"$set": {"active": new_val}})
    return bool(new_val)

def randomize_all_stocks(min_val=1, max_val=100):
    db = _db()
    active = list(db.products.find({"active": 1}, {"id": 1}))
    for p in active:
        db.products.update_one({"id": p["id"]}, {"$set": {"stock": random.randint(min_val, max_val)}})
    return len(active)

# ── Wallets ───────────────────────────────────────────────────────────────────

def get_all_wallets():
    return [_clean(d) for d in _db().wallets.find({})]

def update_wallet(key, address):
    _db().wallets.update_one({"key": key}, {"$set": {"address": address}})

def toggle_wallet(key):
    doc = _db().wallets.find_one({"key": key}, {"active": 1})
    if not doc:
        return False
    new_val = 0 if doc.get("active", 1) == 1 else 1
    _db().wallets.update_one({"key": key}, {"$set": {"active": new_val}})
    return bool(new_val)

# ── Deposits ──────────────────────────────────────────────────────────────────

def create_deposit(tg_id, network, txn_id=""):
    ref = f"#DEP-{random.randint(10000, 99999)}"
    dep_id = _next_id("deposits")
    _db().deposits.insert_one({
        "id": dep_id, "tg_id": tg_id, "ref": ref,
        "network": network, "txn_id": txn_id,
        "amount": 0.0, "status": "pending",
        "notified": 0, "created_at": _now(),
    })
    return ref

def approve_deposit(dep_id, amount):
    db = _db()
    doc = db.deposits.find_one({"id": dep_id}, {"tg_id": 1})
    if not doc:
        return
    db.deposits.update_one({"id": dep_id}, {"$set": {"status": "approved", "amount": amount}})
    db.users.update_one({"tg_id": doc["tg_id"]}, {"$inc": {"balance": amount, "total_deposited": amount}})

def reject_deposit(dep_id):
    _db().deposits.update_one({"id": dep_id}, {"$set": {"status": "rejected"}})

def get_pending_deposits(limit=20):
    """Return list of dicts for all pending deposits (used by admin_payments_bot)."""
    db = _db()
    result = []
    for d in db.deposits.find({"status": "pending"}).sort("id", DESCENDING).limit(limit):
        u = db.users.find_one({"tg_id": d["tg_id"]}, {"name": 1, "username": 1}) or {}
        result.append({
            "id": d["id"], "tg_id": d["tg_id"], "ref": d["ref"],
            "network": d["network"], "txn_id": d.get("txn_id", ""),
            "created_at": d.get("created_at", ""),
            "name": u.get("name", str(d["tg_id"])),
            "username": u.get("username", ""),
        })
    return result

def get_deposit_by_id(dep_id):
    """Return single deposit dict with user info (used by admin_payments_bot)."""
    db = _db()
    d = db.deposits.find_one({"id": dep_id})
    if not d:
        return None
    u = db.users.find_one({"tg_id": d["tg_id"]}, {"name": 1, "username": 1}) or {}
    return {
        "id": d["id"], "tg_id": d["tg_id"], "ref": d["ref"],
        "network": d["network"], "txn_id": d.get("txn_id", ""),
        "created_at": d.get("created_at", ""),
        "name": u.get("name", str(d["tg_id"])),
        "username": u.get("username", ""),
    }

def get_unnotified_deposits():
    db = _db()
    result = []
    for d in db.deposits.find({"status": "pending", "notified": 0}):
        u = db.users.find_one({"tg_id": d["tg_id"]}, {"name": 1, "username": 1}) or {}
        result.append((
            d["id"], d["tg_id"], d["ref"], d["network"],
            d.get("txn_id", ""), d.get("created_at", ""),
            u.get("name", ""), u.get("username", "")
        ))
    return result

def mark_deposit_notified(dep_id):
    _db().deposits.update_one({"id": dep_id}, {"$set": {"notified": 1}})

# ── Orders ────────────────────────────────────────────────────────────────────

def create_order(tg_id, prod_id, qty=1):
    db = _db()
    # Atomically deduct stock
    product = db.products.find_one_and_update(
        {"id": prod_id, "active": 1, "stock": {"$gte": qty}},
        {"$inc": {"stock": -qty}},
    )
    if not product:
        return None

    ref = f"#ORD-{random.randint(10000, 99999)}"
    total_price = product["price"] * qty
    oid = _next_id("orders")
    db.orders.insert_one({
        "id": oid, "tg_id": tg_id, "ref": ref,
        "prod_name": product["name"], "price": total_price, "qty": qty,
        "status": "pending",
        "delivery_type": product["delivery_type"],
        "delivery_content": product["delivery_content"],
        "notified": 0, "created_at": _now(),
    })
    return ref, product["name"], total_price, product["delivery_type"], product["delivery_content"]

def get_user_orders(tg_id, limit=10):
    docs = _db().orders.find({"tg_id": tg_id}).sort("id", DESCENDING).limit(limit)
    return [_clean(d) for d in docs]

def get_recent_orders_admin(limit=20):
    db = _db()
    result = []
    for o in db.orders.find({}).sort("id", DESCENDING).limit(limit):
        u = db.users.find_one({"tg_id": o["tg_id"]}, {"name": 1, "username": 1}) or {}
        result.append((
            o["ref"], o["prod_name"], o["price"], o["qty"],
            o["status"], o.get("created_at", ""),
            u.get("name", ""), u.get("username", ""), o["tg_id"]
        ))
    return result

def get_unnotified_orders():
    db = _db()
    result = []
    for o in db.orders.find({"notified": 0, "status": "pending"}):
        u = db.users.find_one({"tg_id": o["tg_id"]}, {"name": 1, "username": 1}) or {}
        result.append((
            o["id"], o["tg_id"], o["ref"], o["prod_name"], o["price"], o["qty"],
            o.get("created_at", ""), u.get("name", ""), u.get("username", "")
        ))
    return result

def mark_order_notified(order_id):
    _db().orders.update_one({"id": order_id}, {"$set": {"notified": 1}})

def deliver_order(order_ref):
    db = _db()
    order = db.orders.find_one({"ref": order_ref})
    if not order:
        return None
    db.orders.update_one({"ref": order_ref}, {"$set": {"status": "delivered"}})
    return order["tg_id"], order["delivery_type"], order["delivery_content"], order["qty"]

# ── Stats ─────────────────────────────────────────────────────────────────────

def get_stats():
    db = _db()
    users   = db.users.count_documents({})
    orders  = db.orders.count_documents({})
    pending = db.orders.count_documents({"status": "pending"})
    rev     = list(db.deposits.aggregate([
        {"$match": {"status": "approved"}},
        {"$group": {"_id": None, "t": {"$sum": "$amount"}}}
    ]))
    revenue = rev[0]["t"] if rev else 0.0
    pdeps   = db.deposits.count_documents({"status": "pending"})
    return users, orders, pending, revenue, pdeps

# ── Redeem Codes ──────────────────────────────────────────────────────────────

def create_redeem_code(code, amount, max_uses=1):
    try:
        _db().redeem_codes.insert_one({
            "code": code.strip().upper(),
            "amount": amount,
            "max_uses": max_uses,
            "used_count": 0,
        })
        return True
    except DuplicateKeyError:
        return False

def claim_redeem_code(code, tg_id):
    db = _db()
    code = code.strip().upper()
    if db.code_claims.find_one({"code": code, "tg_id": tg_id}):
        return False, "You have already claimed this promo code."
    rc = db.redeem_codes.find_one_and_update(
        {"code": code, "$expr": {"$lt": ["$used_count", "$max_uses"]}},
        {"$inc": {"used_count": 1}},
        return_document=True,
    )
    if not rc:
        return False, "Invalid or expired redeem code."
    try:
        db.code_claims.insert_one({"code": code, "tg_id": tg_id, "claimed_at": _now()})
    except DuplicateKeyError:
        return False, "You have already claimed this promo code."
    db.users.update_one({"tg_id": tg_id}, {"$inc": {"balance": rc["amount"]}})
    return True, f"Success! ${rc['amount']:.2f} USDT added to your balance."

# Alias for backward compat
def redeem_code(tg_id, code):
    return claim_redeem_code(code, tg_id)

# ── Boot ──────────────────────────────────────────────────────────────────────

init_db()
