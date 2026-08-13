#!/usr/bin/env python3
"""
TGAccsShop — Admin Bot
Manages products, wallet addresses, deposits and orders.
Shares the same tgaccs.db as the store bot.
"""

import asyncio
import sqlite3
import logging
from datetime import datetime
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application, CommandHandler, CallbackQueryHandler,
    MessageHandler, filters, ContextTypes,
)
from telegram.error import BadRequest

# ══════════════════════════════════════════════════════
#  CONFIG  ← change these
# ══════════════════════════════════════════════════════

ADMIN_BOT_TOKEN = "PUT_YOUR_ADMIN_BOT_TOKEN_HERE"   # get from @BotFather
ADMIN_IDS       = [123456789]                        # your Telegram user ID(s)
DB_FILE         = "tgaccs.db"                        # same DB as store bot

# ══════════════════════════════════════════════════════
#  DATABASE HELPERS
# ══════════════════════════════════════════════════════

def _db():
    return sqlite3.connect(DB_FILE)

# ── Products ───────────────────────────────────────────
def get_all_products():
    con = _db()
    rows = con.execute(
        "SELECT id,flag,country,age,price,stock,active FROM products ORDER BY id"
    ).fetchall()
    con.close()
    return [{"id":r[0],"flag":r[1],"country":r[2],"age":r[3],
             "price":r[4],"stock":r[5],"active":r[6]} for r in rows]

def get_product(pid):
    con = _db()
    r = con.execute(
        "SELECT id,flag,country,age,price,stock,active FROM products WHERE id=?", (pid,)
    ).fetchone()
    con.close()
    if not r: return None
    return {"id":r[0],"flag":r[1],"country":r[2],"age":r[3],
            "price":r[4],"stock":r[5],"active":r[6]}

def add_product(flag, country, age, price, stock):
    con = _db()
    con.execute(
        "INSERT INTO products (flag,country,age,price,stock,active) VALUES (?,?,?,?,?,1)",
        (flag, country, age, price, stock))
    con.commit()
    pid = con.execute("SELECT last_insert_rowid()").fetchone()[0]
    con.close(); return pid

def update_product_price(pid, price):
    con = _db()
    con.execute("UPDATE products SET price=? WHERE id=?", (price, pid))
    con.commit(); con.close()

def update_product_stock(pid, stock):
    con = _db()
    con.execute("UPDATE products SET stock=? WHERE id=?", (stock, pid))
    con.commit(); con.close()

def update_product_name(pid, country, age, flag):
    con = _db()
    con.execute("UPDATE products SET country=?,age=?,flag=? WHERE id=?", (country, age, flag, pid))
    con.commit(); con.close()

def toggle_product(pid):
    con = _db()
    con.execute("UPDATE products SET active = CASE WHEN active=1 THEN 0 ELSE 1 END WHERE id=?", (pid,))
    con.commit(); con.close()
    p = get_product(pid); return p["active"] if p else 0

def delete_product(pid):
    con = _db()
    con.execute("DELETE FROM products WHERE id=?", (pid,))
    con.commit(); con.close()

# ── Wallets ────────────────────────────────────────────
def get_all_wallets():
    con = _db()
    rows = con.execute("SELECT key,label,address,active FROM wallets ORDER BY key").fetchall()
    con.close()
    return [{"key":r[0],"label":r[1],"address":r[2],"active":r[3]} for r in rows]

def update_wallet_address(key, new_address):
    con = _db()
    con.execute("UPDATE wallets SET address=? WHERE key=?", (new_address, key))
    con.commit(); con.close()

def toggle_wallet(key):
    con = _db()
    con.execute("UPDATE wallets SET active = CASE WHEN active=1 THEN 0 ELSE 1 END WHERE key=?", (key,))
    con.commit(); con.close()
    r = con.execute("SELECT active FROM wallets WHERE key=?", (key,))
    con.close()

# ── Deposits ───────────────────────────────────────────
def get_pending_deposits():
    con = _db()
    rows = con.execute("""
        SELECT d.id,d.tg_id,d.ref,d.network,d.created_at,u.name,u.username
        FROM deposits d LEFT JOIN users u ON d.tg_id=u.tg_id
        WHERE d.status='pending' ORDER BY d.id DESC""").fetchall()
    con.close(); return rows

def approve_deposit_with_amount(dep_id, amount):
    con = _db()
    r = con.execute("SELECT tg_id FROM deposits WHERE id=?", (dep_id,)).fetchone()
    if r:
        con.execute("UPDATE deposits SET status='approved', amount=? WHERE id=?", (amount, dep_id))
        con.execute("UPDATE users SET balance=balance+? WHERE tg_id=?", (amount, r[0]))
        con.commit()
    con.close()
    return r[0] if r else None

def reject_deposit(dep_id):
    con = _db()
    con.execute("UPDATE deposits SET status='rejected' WHERE id=?", (dep_id,))
    con.commit(); con.close()

# ── Orders ─────────────────────────────────────────────
def get_recent_orders(limit=20):
    con = _db()
    rows = con.execute("""
        SELECT o.order_ref,o.product_label,o.price,o.status,o.created_at,u.name,u.username,o.tg_id
        FROM orders o LEFT JOIN users u ON o.tg_id=u.tg_id
        ORDER BY o.id DESC LIMIT ?""", (limit,)).fetchall()
    con.close(); return rows

def deliver_order(order_ref):
    con = _db()
    con.execute("UPDATE orders SET status='delivered' WHERE order_ref=?", (order_ref,))
    con.commit()
    r = con.execute("SELECT tg_id FROM orders WHERE order_ref=?", (order_ref,)).fetchone()
    con.close(); return r[0] if r else None

# ── Stats ──────────────────────────────────────────────
def get_stats():
    con = _db()
    u  = con.execute("SELECT COUNT(*) FROM users").fetchone()[0]
    o  = con.execute("SELECT COUNT(*) FROM orders").fetchone()[0]
    po = con.execute("SELECT COUNT(*) FROM orders WHERE status='pending'").fetchone()[0]
    r  = con.execute("SELECT COALESCE(SUM(price),0) FROM orders").fetchone()[0]
    pd = con.execute("SELECT COUNT(*) FROM deposits WHERE status='pending'").fetchone()[0]
    con.close(); return u, o, po, r, pd

# ── Redeem codes ───────────────────────────────────────
def create_redeem_code(code, amount, max_uses):
    con = _db()
    try:
        con.execute(
            "INSERT INTO redeem_codes (code,amount,max_uses,used,created_at) VALUES (?,?,?,0,?)",
            (code.upper(), amount, max_uses, datetime.now().isoformat()))
        con.commit(); con.close(); return True
    except Exception:
        con.close(); return False

# ── Users ──────────────────────────────────────────────
def get_all_users():
    con = _db()
    rows = con.execute(
        "SELECT tg_id,name,username,balance,created_at FROM users ORDER BY id DESC LIMIT 30"
        if con.execute("PRAGMA table_info(users)").fetchone() else
        "SELECT tg_id,name,username,balance FROM users ORDER BY tg_id DESC LIMIT 30"
    ).fetchall()
    con.close(); return rows

def set_user_balance(tg_id, amount):
    con = _db()
    con.execute("UPDATE users SET balance=? WHERE tg_id=?", (amount, tg_id))
    con.commit(); con.close()

# ══════════════════════════════════════════════════════
#  KEYBOARDS
# ══════════════════════════════════════════════════════

def kb_admin_home():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("📦 Products",        callback_data="adm_products"),
         InlineKeyboardButton("💳 Wallets",         callback_data="adm_wallets")],
        [InlineKeyboardButton("💰 Deposits",        callback_data="adm_deposits"),
         InlineKeyboardButton("📋 Orders",          callback_data="adm_orders")],
        [InlineKeyboardButton("👥 Users",           callback_data="adm_users"),
         InlineKeyboardButton("📊 Stats",           callback_data="adm_stats")],
        [InlineKeyboardButton("🎁 Redeem Codes",   callback_data="adm_codes")],
    ])

def kb_back_home():
    return InlineKeyboardMarkup([[InlineKeyboardButton("🏠 Admin Home", callback_data="adm_home")]])

def kb_products_list(products):
    rows = []
    for p in products:
        icon = "✅" if p["active"] else "🔴"
        rows.append([InlineKeyboardButton(
            f"{icon} [{p['id']}] {p['flag']} {p['country']} {p['age']} — ${p['price']:.2f} | 📦{p['stock']}",
            callback_data=f"adm_prod_{p['id']}")])
    rows.append([InlineKeyboardButton("➕ Add New Product", callback_data="adm_add_product")])
    rows.append([InlineKeyboardButton("🏠 Admin Home",      callback_data="adm_home")])
    return InlineKeyboardMarkup(rows)

def kb_product_actions(pid):
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("✏️ Edit Price",  callback_data=f"adm_ep_{pid}"),
         InlineKeyboardButton("📦 Edit Stock",  callback_data=f"adm_es_{pid}")],
        [InlineKeyboardButton("🏷 Edit Name",   callback_data=f"adm_en_{pid}"),
         InlineKeyboardButton("🔁 Toggle ON/OFF", callback_data=f"adm_toggle_{pid}")],
        [InlineKeyboardButton("🗑 Delete",       callback_data=f"adm_del_{pid}")],
        [InlineKeyboardButton("⬅️ Back",         callback_data="adm_products")],
    ])

def kb_wallets_list(wallets):
    rows = []
    for w in wallets:
        icon = "✅" if w["active"] else "🔴"
        short_addr = w["address"][:18] + "..." if len(w["address"]) > 18 else w["address"]
        rows.append([InlineKeyboardButton(
            f"{icon} {w['label']}  •  {short_addr}",
            callback_data=f"adm_wallet_{w['key']}")])
    rows.append([InlineKeyboardButton("🏠 Admin Home", callback_data="adm_home")])
    return InlineKeyboardMarkup(rows)

def kb_wallet_actions(key):
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("✏️ Change Address", callback_data=f"adm_wa_{key}"),
         InlineKeyboardButton("🔁 Toggle ON/OFF",  callback_data=f"adm_wt_{key}")],
        [InlineKeyboardButton("⬅️ Back",            callback_data="adm_wallets")],
    ])

def kb_deposit_actions(dep_id, tg_id):
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("✅ Approve",  callback_data=f"adm_dep_approve_{dep_id}_{tg_id}"),
         InlineKeyboardButton("❌ Reject",   callback_data=f"adm_dep_reject_{dep_id}")],
        [InlineKeyboardButton("⬅️ Back",     callback_data="adm_deposits")],
    ])

# ══════════════════════════════════════════════════════
#  LOGGING
# ══════════════════════════════════════════════════════

logging.basicConfig(format="%(asctime)s — %(levelname)s — %(message)s", level=logging.INFO)
logging.getLogger("httpx").setLevel(logging.WARNING)
logger = logging.getLogger(__name__)

HTML = "HTML"

async def safe_answer(q, text="", alert=False):
    try: await q.answer(text, show_alert=alert)
    except BadRequest: pass

def is_admin(user_id):
    return not ADMIN_IDS or user_id in ADMIN_IDS

# ══════════════════════════════════════════════════════
#  COMMAND HANDLERS
# ══════════════════════════════════════════════════════

async def cmd_start(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id):
        await update.message.reply_text("⛔ Unauthorised."); return
    u, o, po, r, pd = get_stats()
    await update.message.reply_text(
        f"🔧 <b>Admin Panel — TGAccsShop</b>\n\n"
        f"👥 Users        : <b>{u}</b>\n"
        f"📦 Total Orders : <b>{o}</b>  (⏳ {po} pending)\n"
        f"💰 Revenue      : <b>${r:.2f} USDT</b>\n"
        f"💳 Deposits     : ⏳ <b>{pd} pending</b>\n\n"
        f"Tap a section to manage:",
        parse_mode=HTML, reply_markup=kb_admin_home())

# ══════════════════════════════════════════════════════
#  CALLBACK HANDLER
# ══════════════════════════════════════════════════════

async def on_callback(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    q    = update.callback_query
    data = q.data
    user = update.effective_user
    if not is_admin(user.id):
        await safe_answer(q, "⛔ Unauthorised.", alert=True); return
    await safe_answer(q)

    # ── Home ──────────────────────────────────
    if data == "adm_home":
        u, o, po, r, pd = get_stats()
        await q.edit_message_text(
            f"🔧 <b>Admin Panel</b>\n\n"
            f"👥 Users: <b>{u}</b> | 📦 Orders: <b>{o}</b> (⏳{po})\n"
            f"💰 Revenue: <b>${r:.2f}</b> | 💳 Deposits: ⏳<b>{pd}</b>",
            parse_mode=HTML, reply_markup=kb_admin_home())

    # ══════════════════════════════════════════
    #  PRODUCTS
    # ══════════════════════════════════════════
    elif data == "adm_products":
        prods = get_all_products()
        await q.edit_message_text(
            f"📦 <b>Products</b>  ({len(prods)} total)\n\n"
            f"✅ = active  🔴 = hidden\nTap to edit:",
            parse_mode=HTML, reply_markup=kb_products_list(prods))

    elif data.startswith("adm_prod_"):
        pid = int(data[9:])
        p   = get_product(pid)
        if not p:
            await safe_answer(q, "Not found.", alert=True); return
        status = "✅ Active" if p["active"] else "🔴 Hidden"
        await q.edit_message_text(
            f"📦 <b>Product #{p['id']}</b>\n\n"
            f"{p['flag']} {p['country']} — {p['age']}\n"
            f"💰 Price  : <b>${p['price']:.2f} USDT</b>\n"
            f"📦 Stock  : <b>{p['stock']}</b>\n"
            f"Status   : {status}",
            parse_mode=HTML, reply_markup=kb_product_actions(pid))

    # Edit price
    elif data.startswith("adm_ep_"):
        pid = int(data[7:])
        ctx.user_data["action"] = ("edit_price", pid)
        await q.edit_message_text(
            f"✏️ <b>Edit Price — Product #{pid}</b>\n\nSend new price in USDT (e.g. <code>0.45</code>):",
            parse_mode=HTML,
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("❌ Cancel", callback_data=f"adm_prod_{pid}")]]))

    # Edit stock
    elif data.startswith("adm_es_"):
        pid = int(data[7:])
        ctx.user_data["action"] = ("edit_stock", pid)
        await q.edit_message_text(
            f"📦 <b>Edit Stock — Product #{pid}</b>\n\nSend new stock count (e.g. <code>50</code>):",
            parse_mode=HTML,
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("❌ Cancel", callback_data=f"adm_prod_{pid}")]]))

    # Edit name/label
    elif data.startswith("adm_en_"):
        pid = int(data[7:])
        ctx.user_data["action"] = ("edit_name", pid)
        await q.edit_message_text(
            f"🏷 <b>Edit Name — Product #{pid}</b>\n\n"
            f"Send in format:\n<code>FLAG COUNTRY AGE</code>\n\n"
            f"Example: <code>🇧🇩 Bangladesh 2Y+ Aged</code>",
            parse_mode=HTML,
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("❌ Cancel", callback_data=f"adm_prod_{pid}")]]))

    # Toggle on/off
    elif data.startswith("adm_toggle_"):
        pid    = int(data[11:])
        active = toggle_product(pid)
        status = "✅ Active" if active else "🔴 Hidden"
        await safe_answer(q, f"Product is now {status}", alert=True)
        p = get_product(pid)
        if p:
            await q.edit_message_text(
                f"📦 <b>Product #{p['id']}</b>\n\n"
                f"{p['flag']} {p['country']} — {p['age']}\n"
                f"💰 Price : <b>${p['price']:.2f}</b>\n"
                f"📦 Stock : <b>{p['stock']}</b>\n"
                f"Status  : {status}",
                parse_mode=HTML, reply_markup=kb_product_actions(pid))

    # Delete product
    elif data.startswith("adm_del_"):
        pid = int(data[8:])
        ctx.user_data["action"] = ("confirm_delete", pid)
        await q.edit_message_text(
            f"🗑 <b>Delete Product #{pid}?</b>\n\nThis cannot be undone.",
            parse_mode=HTML,
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("✅ Yes, Delete",  callback_data=f"adm_del_confirm_{pid}"),
                 InlineKeyboardButton("❌ Cancel",       callback_data=f"adm_prod_{pid}")],
            ]))

    elif data.startswith("adm_del_confirm_"):
        pid = int(data[16:])
        delete_product(pid)
        await safe_answer(q, f"Product #{pid} deleted.", alert=True)
        prods = get_all_products()
        await q.edit_message_text("📦 <b>Products</b>", parse_mode=HTML, reply_markup=kb_products_list(prods))

    # Add new product
    elif data == "adm_add_product":
        ctx.user_data["action"] = ("add_product", None)
        await q.edit_message_text(
            "➕ <b>Add New Product</b>\n\n"
            "Send details in this format:\n"
            "<code>FLAG COUNTRY AGE PRICE STOCK</code>\n\n"
            "Example:\n"
            "<code>🇧🇩 Bangladesh 1Y+ Aged 0.28 60</code>",
            parse_mode=HTML,
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("❌ Cancel", callback_data="adm_products")]]))

    # ══════════════════════════════════════════
    #  WALLETS
    # ══════════════════════════════════════════
    elif data == "adm_wallets":
        wallets = get_all_wallets()
        await q.edit_message_text(
            "💳 <b>Wallet Addresses</b>\n\n"
            "✅ = active  🔴 = hidden\nTap to edit:",
            parse_mode=HTML, reply_markup=kb_wallets_list(wallets))

    elif data.startswith("adm_wallet_"):
        key = data[11:]
        ws  = {w["key"]: w for w in get_all_wallets()}
        w   = ws.get(key)
        if not w:
            await safe_answer(q, "Not found.", alert=True); return
        status = "✅ Active" if w["active"] else "🔴 Hidden"
        await q.edit_message_text(
            f"💳 <b>{w['label']}</b>\n\n"
            f"Address : <code>{w['address']}</code>\n"
            f"Status  : {status}",
            parse_mode=HTML, reply_markup=kb_wallet_actions(key))

    elif data.startswith("adm_wa_"):
        key = data[7:]
        ctx.user_data["action"] = ("edit_wallet", key)
        ws = {w["key"]: w for w in get_all_wallets()}
        w  = ws.get(key, {})
        await q.edit_message_text(
            f"✏️ <b>Change Address — {w.get('label','')}</b>\n\n"
            f"Current:\n<code>{w.get('address','')}</code>\n\n"
            f"Send the new wallet address:",
            parse_mode=HTML,
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("❌ Cancel", callback_data=f"adm_wallet_{key}")]]))

    elif data.startswith("adm_wt_"):
        key = data[7:]
        toggle_wallet(key)
        wallets = get_all_wallets()
        w = next((x for x in wallets if x["key"] == key), None)
        status = ("✅ Active" if w["active"] else "🔴 Hidden") if w else "—"
        await safe_answer(q, f"Wallet is now {status}", alert=True)
        await q.edit_message_text("💳 <b>Wallet Addresses</b>", parse_mode=HTML, reply_markup=kb_wallets_list(wallets))

    # ══════════════════════════════════════════
    #  DEPOSITS
    # ══════════════════════════════════════════
    elif data == "adm_deposits":
        deps = get_pending_deposits()
        if not deps:
            await q.edit_message_text("✅ <b>No pending deposits.</b>", parse_mode=HTML, reply_markup=kb_back_home()); return
        rows = []
        for d in deps:
            dep_id, tg_id, ref, network, created, name, uname = d
            ustr = f"@{uname}" if uname else str(tg_id)
            rows.append([InlineKeyboardButton(
                f"💰 {ref} | {name or ustr} | {network}",
                callback_data=f"adm_dep_view_{dep_id}_{tg_id}")])
        rows.append([InlineKeyboardButton("🏠 Admin Home", callback_data="adm_home")])
        await q.edit_message_text(
            f"💰 <b>Pending Deposits ({len(deps)})</b>",
            parse_mode=HTML, reply_markup=InlineKeyboardMarkup(rows))

    elif data.startswith("adm_dep_view_"):
        parts  = data.split("_")
        dep_id = int(parts[3]); tg_id = int(parts[4])
        deps   = get_pending_deposits()
        d      = next((x for x in deps if x[0] == dep_id), None)
        if not d:
            await safe_answer(q, "Not found.", alert=True); return
        _, _, ref, network, created, name, uname = d
        await q.edit_message_text(
            f"💰 <b>Deposit Detail</b>\n\n"
            f"📋 Ref     : <code>{ref}</code>\n"
            f"👤 User    : {name} (<code>{tg_id}</code>)\n"
            f"🌐 Network : {network}\n"
            f"📅 Date    : {created}\n\n"
            f"Tap Approve to set amount and credit balance:",
            parse_mode=HTML, reply_markup=kb_deposit_actions(dep_id, tg_id))

    elif data.startswith("adm_dep_approve_"):
        parts  = data.split("_")
        dep_id = int(parts[3]); tg_id = int(parts[4])
        ctx.user_data["action"] = ("approve_deposit", dep_id, tg_id)
        await q.edit_message_text(
            f"💰 <b>Approve Deposit</b>\n\n"
            f"Send the amount in USDT to credit (e.g. <code>5.00</code>):",
            parse_mode=HTML,
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("❌ Cancel", callback_data="adm_deposits")]]))

    elif data.startswith("adm_dep_reject_"):
        dep_id = int(data[16:])
        reject_deposit(dep_id)
        await safe_answer(q, "Deposit rejected.", alert=True)
        await on_callback_adm_deposits(q, ctx)

    # ══════════════════════════════════════════
    #  ORDERS
    # ══════════════════════════════════════════
    elif data == "adm_orders":
        orders = get_recent_orders(20)
        if not orders:
            await q.edit_message_text("📋 No orders yet.", reply_markup=kb_back_home()); return
        lines = []
        for ref, label, price, status, created, name, uname, tg_id in orders:
            icon = "✅" if status == "delivered" else "⏳"
            lines.append(f"{icon} <code>{ref}</code> — {label} — ${price:.2f}\n   👤 {name or tg_id}")
        rows = [
            [InlineKeyboardButton("📦 Mark Order Delivered", callback_data="adm_deliver")],
            [InlineKeyboardButton("🏠 Admin Home", callback_data="adm_home")],
        ]
        await q.edit_message_text(
            "📋 <b>Recent Orders</b>\n\n" + "\n\n".join(lines[:10]),
            parse_mode=HTML, reply_markup=InlineKeyboardMarkup(rows))

    elif data == "adm_deliver":
        ctx.user_data["action"] = ("deliver_order", None)
        await q.edit_message_text(
            "📦 <b>Mark Order Delivered</b>\n\nSend the order reference (e.g. <code>#TG12345</code>):",
            parse_mode=HTML,
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("❌ Cancel", callback_data="adm_orders")]]))

    # ══════════════════════════════════════════
    #  USERS
    # ══════════════════════════════════════════
    elif data == "adm_users":
        users = get_all_users()
        lines = []
        for row in users:
            tg_id, name, uname, bal = row[0], row[1], row[2], row[3]
            lines.append(f"👤 <code>{tg_id}</code> — {name} — 💰${bal:.2f}")
        rows_kb = [
            [InlineKeyboardButton("💰 Set User Balance", callback_data="adm_set_bal")],
            [InlineKeyboardButton("🏠 Admin Home",       callback_data="adm_home")],
        ]
        await q.edit_message_text(
            "👥 <b>Users (last 30)</b>\n\n" + "\n".join(lines),
            parse_mode=HTML, reply_markup=InlineKeyboardMarkup(rows_kb))

    elif data == "adm_set_bal":
        ctx.user_data["action"] = ("set_balance_uid", None)
        await q.edit_message_text(
            "💰 <b>Set User Balance</b>\n\nSend: <code>USER_ID AMOUNT</code>\n\nExample: <code>123456789 10.00</code>",
            parse_mode=HTML,
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("❌ Cancel", callback_data="adm_users")]]))

    # ══════════════════════════════════════════
    #  STATS
    # ══════════════════════════════════════════
    elif data == "adm_stats":
        u, o, po, r, pd = get_stats()
        prods = get_all_products()
        active_p = sum(1 for p in prods if p["active"])
        await q.edit_message_text(
            f"📊 <b>Statistics</b>\n\n"
            f"👥 Total Users      : <b>{u}</b>\n"
            f"📦 Total Orders     : <b>{o}</b>\n"
            f"⏳ Pending Orders   : <b>{po}</b>\n"
            f"💰 Total Revenue    : <b>${r:.2f} USDT</b>\n"
            f"💳 Pending Deposits : <b>{pd}</b>\n"
            f"🛍 Active Products  : <b>{active_p}/{len(prods)}</b>",
            parse_mode=HTML, reply_markup=kb_back_home())

    # ══════════════════════════════════════════
    #  REDEEM CODES
    # ══════════════════════════════════════════
    elif data == "adm_codes":
        ctx.user_data["action"] = ("create_code", None)
        await q.edit_message_text(
            "🎁 <b>Create Redeem Code</b>\n\n"
            "Send in format:\n<code>CODE AMOUNT MAX_USES</code>\n\n"
            "Example:\n<code>SAVE5 5.00 10</code>",
            parse_mode=HTML,
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("❌ Cancel", callback_data="adm_home")]]))


async def on_callback_adm_deposits(q, ctx):
    """Helper to refresh deposits list."""
    deps = get_pending_deposits()
    if not deps:
        await q.edit_message_text("✅ <b>No pending deposits.</b>", parse_mode=HTML, reply_markup=kb_back_home()); return
    rows = []
    for d in deps:
        dep_id, tg_id, ref, network, created, name, uname = d
        ustr = f"@{uname}" if uname else str(tg_id)
        rows.append([InlineKeyboardButton(
            f"💰 {ref} | {name or ustr} | {network}",
            callback_data=f"adm_dep_view_{dep_id}_{tg_id}")])
    rows.append([InlineKeyboardButton("🏠 Admin Home", callback_data="adm_home")])
    await q.edit_message_text(
        f"💰 <b>Pending Deposits ({len(deps)})</b>",
        parse_mode=HTML, reply_markup=InlineKeyboardMarkup(rows))


# ══════════════════════════════════════════════════════
#  MESSAGE HANDLER  — handles all text input for actions
# ══════════════════════════════════════════════════════

async def on_message(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id): return
    text   = (update.message.text or "").strip()
    action = ctx.user_data.get("action")
    if not action: return
    ctx.user_data.pop("action", None)
    kind = action[0]

    # ── Edit price ─────────────────────────────
    if kind == "edit_price":
        pid = action[1]
        try:
            price = float(text)
            if price <= 0: raise ValueError
        except ValueError:
            await update.message.reply_text("⚠️ Invalid price. Send a number like <code>0.45</code>", parse_mode=HTML)
            return
        update_product_price(pid, price)
        p = get_product(pid)
        await update.message.reply_text(
            f"✅ Price updated!\n\n{p['flag']} {p['country']} {p['age']}\n💰 New price: <b>${price:.2f} USDT</b>",
            parse_mode=HTML, reply_markup=kb_back_home())

    # ── Edit stock ─────────────────────────────
    elif kind == "edit_stock":
        pid = action[1]
        try:
            stock = int(text)
            if stock < 0: raise ValueError
        except ValueError:
            await update.message.reply_text("⚠️ Invalid stock. Send a whole number like <code>50</code>", parse_mode=HTML)
            return
        update_product_stock(pid, stock)
        await update.message.reply_text(
            f"✅ Stock updated to <b>{stock}</b> for product #{pid}",
            parse_mode=HTML, reply_markup=kb_back_home())

    # ── Edit name ──────────────────────────────
    elif kind == "edit_name":
        pid   = action[1]
        parts = text.split(" ", 2)
        if len(parts) < 3:
            await update.message.reply_text(
                "⚠️ Format: <code>FLAG COUNTRY AGE</code>\nExample: <code>🇧🇩 Bangladesh 2Y+ Aged</code>",
                parse_mode=HTML); return
        flag, country, age = parts
        update_product_name(pid, country, age, flag)
        await update.message.reply_text(
            f"✅ Updated: {flag} {country} — {age}", reply_markup=kb_back_home())

    # ── Add product ────────────────────────────
    elif kind == "add_product":
        parts = text.split(" ", 4)
        if len(parts) < 5:
            await update.message.reply_text(
                "⚠️ Format: <code>FLAG COUNTRY AGE PRICE STOCK</code>\n"
                "Example: <code>🇧🇩 Bangladesh 1Y+ Aged 0.28 60</code>",
                parse_mode=HTML); return
        flag, country, age = parts[0], parts[1], parts[2]
        try:
            price = float(parts[3]); stock = int(parts[4])
        except ValueError:
            await update.message.reply_text("⚠️ Price must be a decimal, stock must be a whole number."); return
        pid = add_product(flag, country, age, price, stock)
        await update.message.reply_text(
            f"✅ Product added! ID #{pid}\n{flag} {country} — {age} | ${price:.2f} | 📦{stock}",
            reply_markup=kb_back_home())

    # ── Edit wallet address ────────────────────
    elif kind == "edit_wallet":
        key     = action[1]
        new_addr = text.strip()
        if len(new_addr) < 10:
            await update.message.reply_text("⚠️ Address too short. Try again."); return
        update_wallet_address(key, new_addr)
        await update.message.reply_text(
            f"✅ Wallet address updated!\n\n<code>{new_addr}</code>",
            parse_mode=HTML, reply_markup=kb_back_home())

    # ── Approve deposit ────────────────────────
    elif kind == "approve_deposit":
        dep_id, tg_id = action[1], action[2]
        try:
            amount = float(text)
            if amount < 1: raise ValueError
        except ValueError:
            await update.message.reply_text("⚠️ Enter a valid amount ≥ 1.00"); return
        approve_deposit_with_amount(dep_id, amount)
        await update.message.reply_text(
            f"✅ Approved! <b>${amount:.2f} USDT</b> added to user <code>{tg_id}</code>",
            parse_mode=HTML, reply_markup=kb_back_home())
        try:
            await update.get_bot().send_message(
                tg_id,
                f"✅ <b>Funds Added!</b>\n\n💰 <b>${amount:.2f} USDT</b> credited to your wallet.\n"
                f"You can now buy accounts!",
                parse_mode=HTML)
        except Exception: pass

    # ── Deliver order ──────────────────────────
    elif kind == "deliver_order":
        ref    = text.strip()
        tg_id  = deliver_order(ref)
        if not tg_id:
            await update.message.reply_text(f"⚠️ Order <code>{ref}</code> not found.", parse_mode=HTML); return
        await update.message.reply_text(
            f"✅ Order <code>{ref}</code> marked as delivered.", parse_mode=HTML, reply_markup=kb_back_home())
        try:
            await update.get_bot().send_message(
                tg_id,
                f"✅ <b>Order Delivered!</b>\n\nYour order <code>{ref}</code> has been delivered.\n"
                f"Thank you for shopping with TGAccsShop!",
                parse_mode=HTML)
        except Exception: pass

    # ── Set user balance ───────────────────────
    elif kind == "set_balance_uid":
        parts = text.split()
        if len(parts) < 2:
            await update.message.reply_text("⚠️ Format: <code>USER_ID AMOUNT</code>", parse_mode=HTML); return
        try:
            uid    = int(parts[0])
            amount = float(parts[1])
        except ValueError:
            await update.message.reply_text("⚠️ Invalid format."); return
        set_user_balance(uid, amount)
        await update.message.reply_text(
            f"✅ Balance set to <b>${amount:.2f}</b> for <code>{uid}</code>",
            parse_mode=HTML, reply_markup=kb_back_home())

    # ── Create redeem code ─────────────────────
    elif kind == "create_code":
        parts = text.split()
        if len(parts) < 3:
            await update.message.reply_text(
                "⚠️ Format: <code>CODE AMOUNT MAX_USES</code>", parse_mode=HTML); return
        try:
            code      = parts[0].upper()
            amount    = float(parts[1])
            max_uses  = int(parts[2])
        except ValueError:
            await update.message.reply_text("⚠️ Invalid format."); return
        ok = create_redeem_code(code, amount, max_uses)
        if ok:
            await update.message.reply_text(
                f"✅ Code created!\n\n🎁 <code>{code}</code>\n💰 ${amount:.2f} × {max_uses} uses",
                parse_mode=HTML, reply_markup=kb_back_home())
        else:
            await update.message.reply_text(f"⚠️ Code <code>{code}</code> already exists.", parse_mode=HTML)


# ══════════════════════════════════════════════════════
#  MAIN
# ══════════════════════════════════════════════════════

async def run():
    app = Application.builder().token(ADMIN_BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", cmd_start))
    app.add_handler(CallbackQueryHandler(on_callback))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, on_message))
    print("✅ Admin Bot running...")
    async with app:
        await app.start()
        await app.updater.start_polling(allowed_updates=Update.ALL_TYPES)
        await asyncio.Event().wait()
        await app.updater.stop()
        await app.stop()

if __name__ == "__main__":
    asyncio.run(run())
