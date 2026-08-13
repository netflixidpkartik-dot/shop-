#!/usr/bin/env python3
"""
admin_panel_bot.py — High-End VIP Admin Control Center
Features:
- Premium Glassmorphic / Terminal UI Layout
- Instant 1-Click Stock Randomizer (1–100)
- Full Product, Wallet & User Balance Control
- Broadcast & Mass Announcements with Live Counters
"""

import asyncio
import logging
import os
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, Bot
from telegram.ext import (
    Application, CommandHandler, CallbackQueryHandler,
    MessageHandler, filters, ContextTypes,
)
from telegram.error import BadRequest, TelegramError
import shared_db as db

PANEL_BOT_TOKEN = os.environ.get("PANEL_TOKEN", "")
STORE_BOT_TOKEN = os.environ.get("STORE_TOKEN", "")
ADMIN_IDS = [7908702029]

HTML = "HTML"
logging.basicConfig(format="%(asctime)s — %(levelname)s — %(message)s", level=logging.INFO)
logging.getLogger("httpx").setLevel(logging.WARNING)

def is_admin(uid):
    return uid in ADMIN_IDS

async def safe_ans(q, text="", alert=False):
    try:
        await q.answer(text, show_alert=alert)
    except BadRequest:
        pass

# ══════════════════════════════════════════════════════
#  PREMIUM ADMIN KEYBOARDS
# ══════════════════════════════════════════════════════

def kb_home():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("📦  Product Catalog",    callback_data="pnl_products"),
         InlineKeyboardButton("💳  Payment Wallets",   callback_data="pnl_wallets")],
        [InlineKeyboardButton("🎲  Randomize Stock",   callback_data="pnl_randomize"),
         InlineKeyboardButton("📢  VIP Announcement",   callback_data="pnl_announce")],
        [InlineKeyboardButton("👥  User Management",   callback_data="pnl_users"),
         InlineKeyboardButton("📊  Live Analytics",     callback_data="pnl_stats")],
        [InlineKeyboardButton("🎁  Redeem Codes",       callback_data="pnl_codes")],
    ])

def kb_back_home():
    return InlineKeyboardMarkup([[InlineKeyboardButton("« 🏠 Dashboard Home", callback_data="pnl_home")]])

def kb_product_list(products):
    rows = []
    for p in products:
        status_dot = "🟢" if p["active"] else "🔴"
        short = p["name"][:25] + "…" if len(p["name"]) > 25 else p["name"]
        rows.append([InlineKeyboardButton(
            f"{status_dot} #{p['id']} {short}  •  ${p['price']:.2f} (x{p['stock']})",
            callback_data=f"pnl_p_{p['id']}")])
    rows.append([
        InlineKeyboardButton("➕ Add Product", callback_data="pnl_add"),
        InlineKeyboardButton("« 🏠 Home", callback_data="pnl_home")
    ])
    return InlineKeyboardMarkup(rows)

def kb_product_actions(pid):
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("✏️ Name",  callback_data=f"pnl_pname_{pid}"),
         InlineKeyboardButton("💰 Price", callback_data=f"pnl_pprice_{pid}"),
         InlineKeyboardButton("📦 Stock", callback_data=f"pnl_pstock_{pid}")],
        [InlineKeyboardButton("📝 Delivery Payload", callback_data=f"pnl_pdel_{pid}")],
        [InlineKeyboardButton("🔁 Toggle Status", callback_data=f"pnl_ptoggle_{pid}"),
         InlineKeyboardButton("🗑 Delete", callback_data=f"pnl_pdelconfirm_{pid}")],
        [InlineKeyboardButton("« Back to Catalog", callback_data="pnl_products")],
    ])

def kb_wallet_list(wallets):
    rows = []
    for w in wallets:
        icon = "🟢" if w["active"] else "🔴"
        short_addr = w["address"][:18] + "…" if len(w["address"]) > 18 else w["address"]
        rows.append([InlineKeyboardButton(
            f"{icon} {w['label']}  •  {short_addr}",
            callback_data=f"pnl_w_{w['key']}")])
    rows.append([InlineKeyboardButton("« 🏠 Dashboard Home", callback_data="pnl_home")])
    return InlineKeyboardMarkup(rows)

def kb_wallet_actions(key):
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("✏️ Edit Address", callback_data=f"pnl_waddr_{key}"),
         InlineKeyboardButton("🔁 Enable/Disable", callback_data=f"pnl_wtoggle_{key}")],
        [InlineKeyboardButton("« Back to Wallets", callback_data="pnl_wallets")],
    ])

# ══════════════════════════════════════════════════════
#  ADMIN DASHBOARD COMMANDS
# ══════════════════════════════════════════════════════

async def cmd_start(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id):
        await update.message.reply_text("⛔ <b>Unauthorized Terminal Access.</b>", parse_mode=HTML)
        return

    u, o, po, r, pd = db.get_stats()
    dash_text = (
        f"╭──────── 👑 <b>EXECUTIVE ADMIN TERMINAL</b> 👑 ────────╮\n\n"
        f"👥 <b>Total Clients  :</b> <code>{u}</code>\n"
        f"📦 <b>Orders Volume  :</b> <code>{o}</code> (⏳ <b>{po}</b> active)\n"
        f"💰 <b>Settled Revenue:</b> <code>${r:.2f} USDT</code>\n"
        f"💳 <b>Pending Top-ups:</b> <code>{pd}</code>\n\n"
        f"╰────────────────────────────────────────────────╯"
    )
    await update.message.reply_text(dash_text, parse_mode=HTML, reply_markup=kb_home())

# ══════════════════════════════════════════════════════
#  CALLBACK QUERY DISPATCHER
# ══════════════════════════════════════════════════════

async def on_callback(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    data = q.data
    uid = update.effective_user.id

    if not is_admin(uid):
        await safe_ans(q, "⛔ Unauthorized.", alert=True)
        return

    await safe_ans(q)

    # ── HOME ──────────────────────────────────────────
    if data == "pnl_home":
        u, o, po, r, pd = db.get_stats()
        dash_text = (
            f"╭──────── 👑 <b>EXECUTIVE ADMIN TERMINAL</b> 👑 ────────╮\n\n"
            f"👥 <b>Total Clients  :</b> <code>{u}</code>\n"
            f"📦 <b>Orders Volume  :</b> <code>{o}</code> (⏳ <b>{po}</b> active)\n"
            f"💰 <b>Settled Revenue:</b> <code>${r:.2f} USDT</code>\n"
            f"💳 <b>Pending Top-ups:</b> <code>{pd}</code>\n\n"
            f"╰────────────────────────────────────────────────╯"
        )
        await q.edit_message_text(dash_text, parse_mode=HTML, reply_markup=kb_home())

    # ── RANDOMIZE STOCK (1-100) ───────────────────────
    elif data == "pnl_randomize":
        await q.edit_message_text(
            "🎲 <b>Randomize All Products Stock?</b>\n\n"
            "This will instantly reassign random stock between <b>1 to 100</b> for all active products.\n\n"
            "<i>Do you wish to proceed?</i>",
            parse_mode=HTML,
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("⚡ Confirm & Randomize (1-100)", callback_data="pnl_randomize_confirm")],
                [InlineKeyboardButton("« Cancel", callback_data="pnl_home")]
            ])
        )

    elif data == "pnl_randomize_confirm":
        count = db.randomize_all_stocks(min_val=1, max_val=100)
        prods = db.get_all_products(active_only=True)
        lines = [f"• <b>{p['name']}</b> → 📦 <code>{p['stock']} units</code>" for p in prods[:10]]
        
        await q.edit_message_text(
            f"🎉 <b>Success! Stock Randomized (1–100)</b>\n\n"
            f"<b>{count} Active Products Updated:</b>\n\n"
            + "\n".join(lines) + ("\n<i>...and more</i>" if len(prods) > 10 else ""),
            parse_mode=HTML,
            reply_markup=kb_back_home()
        )

    # ── PRODUCTS SECTION ──────────────────────────────
    elif data == "pnl_products":
        prods = db.get_all_products()
        await q.edit_message_text(
            f"📦 <b>Product Inventory ({len(prods)} Total)</b>\n🟢 = Active  •  🔴 = Hidden",
            parse_mode=HTML,
            reply_markup=kb_product_list(prods)
        )

    elif data.startswith("pnl_p_") and not any(data.startswith(x) for x in
          ["pnl_pname_","pnl_pprice_","pnl_pstock_","pnl_pdel_","pnl_ptoggle_","pnl_pdelconfirm_","pnl_pdelete_"]):
        pid = int(data[6:])
        p = db.get_product(pid)
        if not p:
            await safe_ans(q, "Product not found.", alert=True)
            return

        status = "🟢 Active (Visible)" if p["active"] else "🔴 Hidden (Offline)"
        p_card = (
            f"╭─────── 📦 <b>PRODUCT SPEC #{pid}</b> ───────╮\n\n"
            f"🏷️ <b>Name     :</b> <b>{p['name']}</b>\n"
            f"💰 <b>Price    :</b> <code>${p['price']:.2f} USDT</code>\n"
            f"📦 <b>Stock    :</b> <code>{p['stock']} units</code>\n"
            f"⚡ <b>Delivery :</b> <i>{p['delivery_type']}</i>\n"
            f"📊 <b>Status   :</b> {status}\n\n"
            f"╰──────────────────────────────────────────╯"
        )
        await q.edit_message_text(p_card, parse_mode=HTML, reply_markup=kb_product_actions(pid))

    elif data.startswith("pnl_pname_"):
        pid = int(data[10:])
        ctx.user_data["action"] = ("edit_name", pid)
        await q.edit_message_text(f"✏️ <b>Enter new name for product #{pid}:</b>", parse_mode=HTML,
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("« Cancel", callback_data=f"pnl_p_{pid}")]]))

    elif data.startswith("pnl_pprice_"):
        pid = int(data[11:])
        ctx.user_data["action"] = ("edit_price", pid)
        await q.edit_message_text(f"💰 <b>Enter new price (e.g. <code>4.99</code>):</b>", parse_mode=HTML,
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("« Cancel", callback_data=f"pnl_p_{pid}")]]))

    elif data.startswith("pnl_pstock_"):
        pid = int(data[11:])
        ctx.user_data["action"] = ("edit_stock", pid)
        await q.edit_message_text(f"📦 <b>Enter new stock integer (e.g. <code>75</code>):</b>", parse_mode=HTML,
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("« Cancel", callback_data=f"pnl_p_{pid}")]]))

    elif data.startswith("pnl_pdel_") and not data.startswith("pnl_pdelconfirm_"):
        pid = int(data[9:])
        ctx.user_data["action"] = ("edit_delivery", pid)
        await q.edit_message_text(
            f"📝 <b>Edit Delivery Payload — Product #{pid}</b>\n\n"
            f"Forward or send the exact text, license, photo or video content buyers receive automatically:",
            parse_mode=HTML,
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("« Cancel", callback_data=f"pnl_p_{pid}")]]))

    elif data.startswith("pnl_ptoggle_"):
        pid = int(data[12:])
        active = db.toggle_product(pid)
        status_text = "🟢 Active" if active else "🔴 Hidden"
        await safe_ans(q, f"Product is now {status_text}", alert=True)
        p = db.get_product(pid)
        if p:
            await q.edit_message_text(f"📦 <b>Product #{pid}</b> updated to {status_text}", parse_mode=HTML,
                                      reply_markup=kb_product_actions(pid))

    elif data.startswith("pnl_pdelconfirm_"):
        pid = int(data[16:])
        await q.edit_message_text(
            f"🗑 <b>Permanently Delete Product #{pid}?</b>\n<i>This action cannot be undone.</i>",
            parse_mode=HTML,
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("💥 Yes, Delete", callback_data=f"pnl_pdelete_{pid}")],
                [InlineKeyboardButton("« Cancel", callback_data=f"pnl_p_{pid}")]
            ])
        )

    elif data.startswith("pnl_pdelete_"):
        pid = int(data[12:])
        db.delete_product(pid)
        await safe_ans(q, "Product deleted.", alert=True)
        await q.edit_message_text("📦 <b>Product deleted successfully.</b>", parse_mode=HTML,
                                  reply_markup=kb_product_list(db.get_all_products()))

    elif data == "pnl_add":
        ctx.user_data["action"] = ("add_step1", None)
        await q.edit_message_text(
            "➕ <b>Add Product — Step 1/2 (Delivery Content)</b>\n\n"
            "Send or forward the payload buyers will receive after purchase:\n"
            "<i>Text, accounts, photo, document, or license file.</i>",
            parse_mode=HTML,
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("« Cancel", callback_data="pnl_products")]])
        )

    # ── WALLETS SECTION ───────────────────────────────
    elif data == "pnl_wallets":
        await q.edit_message_text("💳 <b>Crypto Settlement Wallets</b>", parse_mode=HTML,
                                  reply_markup=kb_wallet_list(db.get_all_wallets()))

    elif data.startswith("pnl_w_") and not any(data.startswith(x) for x in ["pnl_waddr_","pnl_wtoggle_"]):
        key = data[6:]
        ws = {w["key"]: w for w in db.get_all_wallets()}
        w = ws.get(key)
        if not w:
            await safe_ans(q, "Wallet not found.", alert=True)
            return

        status = "🟢 Enabled" if w["active"] else "🔴 Disabled"
        w_card = (
            f"╭─────── 💳 <b>{w['label']}</b> ───────╮\n\n"
            f"📌 <b>Address :</b>\n<code>{w['address']}</code>\n\n"
            f"📊 <b>Status  :</b> {status}\n\n"
            f"╰──────────────────────────────────────────╯"
        )
        await q.edit_message_text(w_card, parse_mode=HTML, reply_markup=kb_wallet_actions(key))

    elif data.startswith("pnl_waddr_"):
        key = data[10:]
        ctx.user_data["action"] = ("edit_wallet", key)
        await q.edit_message_text(
            f"✏️ <b>Enter new crypto address for {key}:</b>",
            parse_mode=HTML,
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("« Cancel", callback_data=f"pnl_w_{key}")]]))

    elif data.startswith("pnl_wtoggle_"):
        key = data[12:]
        active = db.toggle_wallet(key)
        await safe_ans(q, f"Wallet is now {'Enabled' if active else 'Disabled'}", alert=True)
        await q.edit_message_text("💳 <b>Crypto Settlement Wallets</b>", parse_mode=HTML,
                                  reply_markup=kb_wallet_list(db.get_all_wallets()))

    # ── USERS & REFERRAL MANAGEMENT ───────────────────
    elif data == "pnl_users":
        users = db.get_all_users()
        lines = [f"👤 <code>{r[0]}</code> — {r[1]} — 💰${r[3]:.2f} (👥 Ref: {r[4]})" for r in users[:15]]
        await q.edit_message_text(
            f"╭──────── 👥 <b>CLIENT DIRECTORY ({len(users)})</b> ────────╮\n\n"
            + "\n".join(lines) +
            f"\n\n╰────────────────────────────────────────────────╯",
            parse_mode=HTML,
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("💰 Adjust Balance", callback_data="pnl_setbal")],
                [InlineKeyboardButton("🚫 Ban Client",     callback_data="pnl_ban"),
                 InlineKeyboardButton("✅ Unban Client",   callback_data="pnl_unban")],
                [InlineKeyboardButton("📋 Banned Blacklist", callback_data="pnl_banned_list")],
                [InlineKeyboardButton("« 🏠 Home",         callback_data="pnl_home")],
            ])
        )

    elif data == "pnl_setbal":
        ctx.user_data["action"] = ("set_balance", None)
        await q.edit_message_text(
            "💰 <b>Format:</b> <code>USER_ID AMOUNT</code>\n\n<i>Example: <code>123456789 25.00</code></i>",
            parse_mode=HTML,
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("« Cancel", callback_data="pnl_users")]]))

    elif data == "pnl_ban":
        ctx.user_data["action"] = ("ban_user", None)
        await q.edit_message_text(
            "🚫 <b>Enter User ID or @username to Blacklist:</b>",
            parse_mode=HTML,
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("« Cancel", callback_data="pnl_users")]]))

    elif data == "pnl_unban":
        ctx.user_data["action"] = ("unban_user", None)
        await q.edit_message_text(
            "✅ <b>Enter User ID or @username to Unban:</b>",
            parse_mode=HTML,
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("« Cancel", callback_data="pnl_users")]]))

    elif data == "pnl_banned_list":
        banned = db.get_banned_users()
        if not banned:
            await q.edit_message_text("📋 <b>Blacklist is currently clean.</b>", parse_mode=HTML,
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("« Back", callback_data="pnl_users")]]))
            return
        lines = [f"🚫 <code>{tg_id}</code> — {name}" for tg_id, name, _ in banned]
        await q.edit_message_text("📋 <b>Banned Accounts:</b>\n\n" + "\n".join(lines), parse_mode=HTML,
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("« Back", callback_data="pnl_users")]]))

    # ── ANNOUNCEMENTS / BROADCAST ─────────────────────
    elif data == "pnl_announce":
        user_count = len(db.get_all_user_ids())
        ctx.user_data["action"] = ("announce", None)
        await q.edit_message_text(
            f"📢 <b>VIP Broadcast Terminal</b>\n\n"
            f"👥 Target Audience: <b>{user_count} Active Clients</b>\n\n"
            f"Send your message below (supports text, photo, video, bold, markdown):\n",
            parse_mode=HTML,
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("« Cancel", callback_data="pnl_home")]])
        )

    # ── REDEEM CODES ──────────────────────────────────
    elif data == "pnl_codes":
        ctx.user_data["action"] = ("create_code", None)
        await q.edit_message_text(
            "🎁 <b>Format:</b> <code>CODE AMOUNT MAX_USES</code>\n\n<i>Example: <code>VIP10 10.00 50</code></i>",
            parse_mode=HTML,
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("« Cancel", callback_data="pnl_home")]]))

    # ── STATS ─────────────────────────────────────────
    elif data == "pnl_stats":
        u, o, po, r, pd = db.get_stats()
        prods = db.get_all_products()
        await q.edit_message_text(
            f"╭──────── 📊 <b>METRICS & ANALYTICS</b> ────────╮\n\n"
            f"👥 <b>Total Registered:</b> <code>{u} users</code>\n"
            f"📦 <b>Orders Processed:</b> <code>{o}</code> (⏳ <code>{po}</code> pending)\n"
            f"💰 <b>Settled Volume  :</b> <code>${r:.2f} USDT</code>\n"
            f"💳 <b>Pending Top-ups :</b> <code>{pd}</code>\n"
            f"🛍️ <b>Active Catalog  :</b> <code>{sum(1 for p in prods if p['active'])}/{len(prods)} active</code>\n\n"
            f"╰──────────────────────────────────────────╯",
            parse_mode=HTML,
            reply_markup=kb_back_home()
        )

# ══════════════════════════════════════════════════════
#  MESSAGE PARSER & PROCESSOR
# ══════════════════════════════════════════════════════

async def _get_payload(message):
    if message.photo:    return "photo", message.photo[-1].file_id
    if message.document: return "document", message.document.file_id
    if message.video:    return "video", message.video.file_id
    if message.text:     return "text", message.text
    if message.caption:  return "text", message.caption
    return "text", ""

async def on_any_message(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id):
        return

    action = ctx.user_data.get("action")
    if not action:
        return

    kind = action[0]
    message = update.message

    # ── Broadcast ─────────────────────────────────────
    if kind == "announce":
        ctx.user_data.pop("action", None)
        user_ids = db.get_all_user_ids()
        await message.reply_text(f"📢 <i>Dispatching broadcast to {len(user_ids)} clients...</i>", parse_mode=HTML)
        sent = failed = 0
        store = Bot(token=STORE_BOT_TOKEN)
        async with store:
            for uid in user_ids:
                try:
                    if message.photo:
                        await store.send_photo(uid, message.photo[-1].file_id, caption=message.caption or "", parse_mode=HTML)
                    elif message.document:
                        await store.send_document(uid, message.document.file_id, caption=message.caption or "", parse_mode=HTML)
                    elif message.video:
                        await store.send_video(uid, message.video.file_id, caption=message.caption or "", parse_mode=HTML)
                    elif message.text:
                        await store.send_message(uid, message.text, parse_mode=HTML)
                    sent += 1
                    await asyncio.sleep(0.04)
                except TelegramError:
                    failed += 1

        await message.reply_text(
            f"✅ <b>Broadcast Completed!</b>\n\n"
            f"🟢 Successfully Delivered: <b>{sent}</b>\n"
            f"🔴 Failed / Inactive     : <b>{failed}</b>",
            parse_mode=HTML,
            reply_markup=kb_back_home()
        )

    # ── Add Product ───────────────────────────────────
    elif kind == "add_step1":
        dtype, dcontent = await _get_payload(message)
        if not dcontent:
            await message.reply_text("⚠️ Content payload empty. Try again.")
            return
        ctx.user_data["action"] = ("add_step2", None)
        ctx.user_data["new_dtype"] = dtype
        ctx.user_data["new_dcontent"] = dcontent
        await message.reply_text(
            f"✅ <b>Step 1/2 Saved ({dtype})!</b>\n\n"
            f"Now send product details in format:\n"
            f"<code>NAME | PRICE | STOCK</code>\n\n"
            f"<i>Example: <code>VIP Premium Account | 9.99 | 50</code></i>",
            parse_mode=HTML
        )

    elif kind == "add_step2":
        parts = [x.strip() for x in (message.text or "").split("|")]
        if len(parts) < 3:
            await message.reply_text("⚠️ Format: <code>NAME | PRICE | STOCK</code>", parse_mode=HTML)
            return
        try:
            name, price, stock = parts[0], float(parts[1]), int(parts[2])
        except ValueError:
            await message.reply_text("⚠️ Price must be decimal, stock must be an integer.")
            return

        dtype = ctx.user_data.pop("new_dtype", "text")
        dcontent = ctx.user_data.pop("new_dcontent", "")
        ctx.user_data.pop("action", None)

        pid = db.add_product(name, price, stock, dtype, dcontent)
        await message.reply_text(
            f"🎉 <b>Product #{pid} Created!</b>\n\n"
            f"💎 <b>{name}</b>\n"
            f"💰 ${price:.2f} USDT  •  📦 {stock} in stock",
            parse_mode=HTML,
            reply_markup=kb_back_home()
        )

    # ── Edit Attributes ───────────────────────────────
    elif kind == "edit_name":
        pid = action[1]
        ctx.user_data.pop("action", None)
        db.update_product(pid, name=message.text.strip())
        await message.reply_text("✅ Name updated!", reply_markup=kb_back_home())

    elif kind == "edit_price":
        pid = action[1]
        ctx.user_data.pop("action", None)
        try:
            val = float(message.text.strip())
            db.update_product(pid, price=val)
            await message.reply_text(f"✅ Price set to ${val:.2f}", reply_markup=kb_back_home())
        except ValueError:
            await message.reply_text("⚠️ Invalid decimal.")

    elif kind == "edit_stock":
        pid = action[1]
        ctx.user_data.pop("action", None)
        try:
            val = int(message.text.strip())
            db.update_product(pid, stock=val)
            await message.reply_text(f"✅ Stock updated to {val}", reply_markup=kb_back_home())
        except ValueError:
            await message.reply_text("⚠️ Invalid number.")

    elif kind == "edit_delivery":
        pid = action[1]
        ctx.user_data.pop("action", None)
        dtype, dcontent = await _get_payload(message)
        db.update_product(pid, delivery_type=dtype, delivery_content=dcontent)
        await message.reply_text("✅ Delivery payload updated!", reply_markup=kb_back_home())

    elif kind == "edit_wallet":
        key = action[1]
        ctx.user_data.pop("action", None)
        addr = (message.text or "").strip()
        db.update_wallet(key, addr)
        await message.reply_text("✅ Wallet address updated!", reply_markup=kb_back_home())

    elif kind == "set_balance":
        ctx.user_data.pop("action", None)
        parts = (message.text or "").split()
        if len(parts) >= 2:
            try:
                db.set_balance(int(parts[0]), float(parts[1]))
                await message.reply_text(f"✅ User {parts[0]} balance set to ${float(parts[1]):.2f}", reply_markup=kb_back_home())
            except ValueError:
                await message.reply_text("⚠️ Invalid number format.")

    elif kind == "ban_user":
        ctx.user_data.pop("action", None)
        raw = (message.text or "").strip()
        tg_id = int(raw) if raw.lstrip("-").isdigit() else db.find_tg_id_by_username(raw)
        if tg_id:
            db.ban_user(tg_id)
            await message.reply_text(f"🚫 User <code>{tg_id}</code> blacklisted.", parse_mode=HTML, reply_markup=kb_back_home())
        else:
            await message.reply_text("⚠️ User not found.")

    elif kind == "unban_user":
        ctx.user_data.pop("action", None)
        raw = (message.text or "").strip()
        tg_id = int(raw) if raw.lstrip("-").isdigit() else db.find_tg_id_by_username(raw)
        if tg_id:
            db.unban_user(tg_id)
            await message.reply_text(f"✅ User <code>{tg_id}</code> unbanned.", parse_mode=HTML, reply_markup=kb_back_home())
        else:
            await message.reply_text("⚠️ User not found.")

    elif kind == "create_code":
        ctx.user_data.pop("action", None)
        parts = (message.text or "").split()
        if len(parts) >= 3:
            try:
                ok = db.create_redeem_code(parts[0], float(parts[1]), int(parts[2]))
                msg = f"🎉 Voucher <code>{parts[0].upper()}</code> generated!" if ok else "⚠️ Code already exists."
                await message.reply_text(msg, parse_mode=HTML, reply_markup=kb_back_home())
            except ValueError:
                await message.reply_text("⚠️ Invalid format.")

# ══════════════════════════════════════════════════════
#  RUNNER
# ══════════════════════════════════════════════════════

async def run_panel_bot():
    if not PANEL_BOT_TOKEN:
        print("⚠️ PANEL_TOKEN is not set in environment.")
        return

    app = Application.builder().token(PANEL_BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", cmd_start))
    app.add_handler(CallbackQueryHandler(on_callback))
    app.add_handler(MessageHandler(filters.TEXT | filters.PHOTO | filters.Document.ALL | filters.VIDEO, on_any_message))

    print("🚀 [2/4] Admin Panel Bot running with Executive UI...")
    async with app:
        await app.start()
        await app.updater.start_polling(allowed_updates=Update.ALL_TYPES)
        await asyncio.Event().wait()
        await app.updater.stop()
        await app.stop()

if __name__ == "__main__":
    asyncio.run(run_panel_bot())
