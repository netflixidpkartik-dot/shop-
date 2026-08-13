#!/usr/bin/env python3
"""
store_bot.py — Nex Shop | Customer Storefront
UI matches reference design exactly.
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

STORE_BOT_TOKEN = os.environ.get("STORE_TOKEN", "")
ADMIN_IDS = [7908702029]

HTML = "HTML"
logging.basicConfig(format="%(asctime)s — %(levelname)s — %(message)s", level=logging.INFO)
logging.getLogger("httpx").setLevel(logging.WARNING)

# ══════════════════════════════════════════════════════
#  KEYBOARDS — Exact layout from reference screenshots
# ══════════════════════════════════════════════════════

def kb_main():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🛒 Buy", callback_data="menu_buy")],
        [InlineKeyboardButton("👤 Profile",            callback_data="menu_profile"),
         InlineKeyboardButton("🔵 Purchase history",   callback_data="menu_orders")],
        [InlineKeyboardButton("🎀 Wallet",             callback_data="menu_wallet"),
         InlineKeyboardButton("🔗 API Link",           callback_data="menu_api")],
        [InlineKeyboardButton("💬 Support",            callback_data="menu_support")],
        [InlineKeyboardButton("🌐 Language",           callback_data="menu_language")],
    ])

def kb_back_main():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("↩️ Back to main menu", callback_data="menu_home")]
    ])

def kb_products(products):
    rows = []
    for p in products:
        label = f"{p['name']} | ${p['price']:.2f}"
        if len(label) > 55:
            label = f"{p['name'][:42]}… | ${p['price']:.2f}"
        rows.append([InlineKeyboardButton(label, callback_data=f"view_p_{p['id']}")])
    rows.append([InlineKeyboardButton("🔄 Refresh products", callback_data="menu_buy")])
    rows.append([InlineKeyboardButton("↩️ Back to main menu", callback_data="menu_home")])
    return InlineKeyboardMarkup(rows)

def kb_product_detail(pid):
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("✅ Buy now", callback_data=f"buy_p_{pid}_1")],
        [InlineKeyboardButton("↩️ Back to catalog", callback_data="menu_buy")],
    ])

def kb_wallet_topup(wallets):
    rows = []
    icons = {"usdt_bep20": "🟡", "usdt_trc20": "🔴", "ton": "💎", "sol": "🟣"}
    for w in wallets:
        if w["active"]:
            ico = icons.get(w["key"], "💳")
            rows.append([InlineKeyboardButton(
                f"{ico} Top up {w['label']}", callback_data=f"dep_w_{w['key']}")])
    rows.append([
        InlineKeyboardButton("🔄 Refresh balance",     callback_data="menu_wallet"),
        InlineKeyboardButton("↩️ Back to main menu",   callback_data="menu_home"),
    ])
    return InlineKeyboardMarkup(rows)

async def safe_ans(q, text="", alert=False):
    try:
        await q.answer(text, show_alert=alert)
    except BadRequest:
        pass

# ══════════════════════════════════════════════════════
#  /start COMMAND
# ══════════════════════════════════════════════════════

async def cmd_start(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    if db.is_banned(user.id):
        return

    # Parse referral arg
    referrer_id = None
    if ctx.args:
        arg = ctx.args[0]
        if arg.startswith("ref_"):
            try:
                candidate = int(arg.replace("ref_", ""))
                if candidate != user.id:
                    referrer_id = candidate
            except ValueError:
                pass

    db.get_or_create_user(user.id, user.first_name, user.username or "", referrer_id)

    bot_info = await ctx.bot.get_me()
    ctx.bot_data["username"] = bot_info.username
    ref_link = f"https://t.me/{bot_info.username}?start=ref_{user.id}"

    # Referral info message (matches pinned message in screenshot)
    await update.message.reply_text(
        f"• Share your bot link with your referral code.\n"
        f"• When the invited user places their first order, you receive 10% of the order value.\n"
        f"• Each new user is rewarded only once.\n"
        f"• Self-referrals are not allowed.\n\n"
        f"🔗 Your referral link:\n"
        f"{ref_link}",
        parse_mode=HTML,
        disable_web_page_preview=True
    )

    # Main menu message
    await update.message.reply_text(
        "🎪 Please choose a menu:",
        reply_markup=kb_main()
    )

# ══════════════════════════════════════════════════════
#  CALLBACK ROUTER
# ══════════════════════════════════════════════════════

async def on_callback(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    data = q.data
    user = update.effective_user

    if db.is_banned(user.id):
        await safe_ans(q, "⛔ Restricted.", alert=True)
        return

    bot_user = ctx.bot_data.get("username")
    if not bot_user:
        b = await ctx.bot.get_me()
        bot_user = b.username
        ctx.bot_data["username"] = bot_user

    u_data = db.get_user(user.id) or db.get_or_create_user(user.id, user.first_name, user.username or "")
    await safe_ans(q)

    # ── HOME ─────────────────────────────────────────
    if data == "menu_home":
        ctx.user_data.clear()
        await q.edit_message_text("🎪 Please choose a menu:", reply_markup=kb_main())

    # ── BUY / PRODUCT LIST ────────────────────────────
    elif data == "menu_buy":
        products = db.get_all_products(active_only=True)
        if not products:
            await q.edit_message_text(
                "🛒 No products available right now.\n\nCheck back soon!",
                reply_markup=kb_back_main()
            )
            return
        await q.edit_message_text("🛍️ Products", reply_markup=kb_products(products))

    # ── PRODUCT DETAIL ────────────────────────────────
    elif data.startswith("view_p_"):
        pid = int(data.replace("view_p_", ""))
        p = db.get_product(pid)
        if not p or not p["active"]:
            await safe_ans(q, "⚠️ This product is unavailable.", alert=True)
            return

        stock_icon = "✅ In stock" if p["stock"] > 0 else "❌ Out of stock"
        await q.edit_message_text(
            f"<b>{p['name']}</b>\n\n"
            f"💰 Price: <b>${p['price']:.2f}</b>\n"
            f"📦 Stock: {p['stock']} ({stock_icon})\n"
            f"⚡ Delivery: Instant\n\n"
            f"💳 Your balance: <b>${u_data['balance']:.2f}</b>",
            parse_mode=HTML,
            reply_markup=kb_product_detail(pid)
        )

    # ── PURCHASE ──────────────────────────────────────
    elif data.startswith("buy_p_"):
        parts = data.split("_")
        pid = int(parts[2])
        qty = int(parts[3]) if len(parts) > 3 else 1
        p = db.get_product(pid)

        if not p or not p["active"]:
            await safe_ans(q, "Product unavailable.", alert=True)
            return
        if p["stock"] < qty:
            await safe_ans(q, "❌ Out of stock.", alert=True)
            return

        total_cost = p["price"] * qty
        if u_data["balance"] < total_cost:
            deficit = round(total_cost - u_data["balance"], 4)
            await q.edit_message_text(
                f"❌ <b>Insufficient balance!</b>\n\n"
                f"Cost:    <b>${total_cost:.2f}</b>\n"
                f"Balance: <b>${u_data['balance']:.2f}</b>\n"
                f"Top up:  <b>${deficit:.2f} more needed</b>",
                parse_mode=HTML,
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("🎀 Top up wallet", callback_data="menu_wallet")],
                    [InlineKeyboardButton("↩️ Back", callback_data=f"view_p_{pid}")],
                ])
            )
            return

        if not db.deduct_balance(user.id, total_cost):
            await safe_ans(q, "Balance error. Please retry.", alert=True)
            return

        order_res = db.create_order(user.id, pid, qty)
        if not order_res:
            db.add_balance(user.id, total_cost)  # refund
            await safe_ans(q, "Order failed (out of stock). Refunded.", alert=True)
            return

        ref, prod_name, total_price, dtype, dcontent = order_res

        # Pay 10% referral commission on first order
        db.maybe_pay_referral_commission(user.id, total_cost)

        # Auto-deliver instantly
        delivery_text = (
            f"✅ <b>Order delivered!</b>\n\n"
            f"📋 Order: <code>{ref}</code>\n"
            f"🛍️ Product: <b>{prod_name}</b>\n"
            f"💰 Paid: <b>${total_price:.2f}</b>\n\n"
            f"🎁 <b>Your delivery:</b>\n"
        )

        store = Bot(token=STORE_BOT_TOKEN)
        async with store:
            try:
                if dtype == "photo":
                    await store.send_photo(user.id, dcontent, caption=delivery_text, parse_mode=HTML)
                elif dtype == "document":
                    await store.send_document(user.id, dcontent, caption=delivery_text, parse_mode=HTML)
                elif dtype == "video":
                    await store.send_video(user.id, dcontent, caption=delivery_text, parse_mode=HTML)
                else:
                    await store.send_message(
                        user.id, f"{delivery_text}\n<code>{dcontent}</code>", parse_mode=HTML
                    )
            except TelegramError as e:
                logging.error(f"Delivery to {user.id} failed: {e}")

        db.deliver_order(ref)
        new_balance = u_data["balance"] - total_cost
        await q.edit_message_text(
            f"✅ <b>Purchase successful!</b>\n\n"
            f"Order <code>{ref}</code> has been delivered above 👆\n"
            f"New balance: <b>${new_balance:.2f}</b>",
            parse_mode=HTML,
            reply_markup=kb_back_main()
        )

    # ── PROFILE ───────────────────────────────────────
    elif data == "menu_profile":
        uname = f"@{user.username}" if user.username else user.first_name
        total_spent = db.get_user_total_spent(user.id)
        ref_link = f"https://t.me/{bot_user}?start=ref_{user.id}"

        await q.edit_message_text(
            f"👤 <b>Customer profile</b>\n\n"
            f"Name: <b>{uname}</b>\n"
            f"Total spent: <b>${total_spent:.2f}</b>\n"
            f"👥 Referrals: <b>{u_data.get('referral_count', 0)}</b>\n\n"
            f"🔗 Your referral link:\n"
            f"<code>{ref_link}</code>",
            parse_mode=HTML,
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("↩️ Back to main menu", callback_data="menu_home")]
            ])
        )

    # ── WALLET ────────────────────────────────────────
    elif data == "menu_wallet":
        uname = f"@{user.username}" if user.username else user.first_name
        total_spent = db.get_user_total_spent(user.id)
        wallets = db.get_all_wallets()

        await q.edit_message_text(
            f"👤 <b>Customer profile</b>\n\n"
            f"Name: <b>{uname}</b>\n"
            f"Total spent: <b>${total_spent:.2f}</b>\n\n"
            f"🎀 <b>Your wallet</b>\n\n"
            f"USD/USDT: <b>${u_data['balance']:.2f}</b>",
            parse_mode=HTML,
            reply_markup=kb_wallet_topup(wallets)
        )

    # ── DEPOSIT — NETWORK SELECTED ────────────────────
    elif data.startswith("dep_w_"):
        key = data.replace("dep_w_", "")
        wallets = {w["key"]: w for w in db.get_all_wallets()}
        w = wallets.get(key)
        if not w:
            await safe_ans(q, "Wallet unavailable.", alert=True)
            return

        ctx.user_data["action"] = "waiting_deposit_txn"
        ctx.user_data["dep_network"] = w["label"]

        await q.edit_message_text(
            f"⚠️ Allowed difference: 0.02 USDT. The received amount must be exact "
            f"(network fees are NOT included, please add fees when sending).\n\n"
            f"<b>USDT receiving address ({w['label']}):</b>\n"
            f"<code>{w['address']}</code>\n\n"
            f"Scan or copy the correct wallet address.\n\n"
            f"⚠️ After completing the transfer, please send the TxID or transaction hash in this chat so the system can confirm it.",
            parse_mode=HTML,
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("↩️ Back to wallet", callback_data="menu_wallet")]
            ])
        )

    # ── PURCHASE HISTORY ──────────────────────────────
    elif data == "menu_orders":
        orders = db.get_user_orders(user.id, limit=15)
        if not orders:
            await q.edit_message_text(
                "🔵 <b>Purchase history</b>\n\nNo purchases yet.",
                parse_mode=HTML,
                reply_markup=kb_back_main()
            )
            return

        lines = []
        for o in orders:
            icon = "✅" if o["status"] == "delivered" else "⏳"
            date = o["created_at"][:10]
            lines.append(f"{icon} <b>{o['prod_name']}</b> — ${o['price']:.2f}\n   📅 {date}")

        await q.edit_message_text(
            "🔵 <b>Purchase history</b>\n\n" + "\n\n".join(lines),
            parse_mode=HTML,
            reply_markup=kb_back_main()
        )

    # ── SUPPORT ───────────────────────────────────────
    elif data == "menu_support":
        await q.edit_message_text(
            f"🎪 <b>Quick support:</b>\n\n"
            f"📱 Telegram: @NexIndo\n\n"
            f"Contact us for faster help and issue handling.",
            parse_mode=HTML,
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("💬 Contact @NexIndo", url="https://t.me/NexIndo")],
                [InlineKeyboardButton("↩️ Back to main menu", callback_data="menu_home")],
            ])
        )

    # ── LANGUAGE ─────────────────────────────────────
    elif data == "menu_language":
        await q.edit_message_text(
            "🌐 <b>Choose language:</b>",
            parse_mode=HTML,
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("🇻🇳 Tiếng Việt", callback_data="lang_vi"),
                 InlineKeyboardButton("🇺🇸 English",    callback_data="lang_en")],
                [InlineKeyboardButton("🇨🇳 中文",        callback_data="lang_zh"),
                 InlineKeyboardButton("🇷🇺 Русский",     callback_data="lang_ru")],
                [InlineKeyboardButton("🇰🇷 한국어",       callback_data="lang_ko"),
                 InlineKeyboardButton("🇮🇷 فارسی",       callback_data="lang_fa")],
                [InlineKeyboardButton("🇮🇳 हिन्दी",       callback_data="lang_hi")],
                [InlineKeyboardButton("↩️ Back to main menu", callback_data="menu_home")],
            ])
        )

    elif data.startswith("lang_"):
        await safe_ans(q, "✅ Language selected.", alert=False)
        await q.edit_message_text("🎪 Please choose a menu:", reply_markup=kb_main())

    # ── API LINK ──────────────────────────────────────
    elif data == "menu_api":
        await q.edit_message_text(
            f"🔗 <b>API Link</b>\n\n"
            f"Your user API key:\n"
            f"<code>nex_{user.id}</code>\n\n"
            f"<i>Contact @NexIndo for API integration support.</i>",
            parse_mode=HTML,
            reply_markup=kb_back_main()
        )

# ══════════════════════════════════════════════════════
#  MESSAGE HANDLER (for text inputs after prompts)
# ══════════════════════════════════════════════════════

async def on_user_message(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    if db.is_banned(user.id):
        return

    action = ctx.user_data.get("action")
    if not action:
        return

    if action == "waiting_deposit_txn":
        ctx.user_data.pop("action", None)
        network = ctx.user_data.pop("dep_network", "USDT")
        txn_text = (
            update.message.text
            or (update.message.caption if update.message.caption else None)
            or "Screenshot uploaded"
        ).strip()

        ref = db.create_deposit(user.id, network, txn_text)
        await update.message.reply_text(
            f"✅ <b>Deposit submitted!</b>\n\n"
            f"📋 Ref: <code>{ref}</code>\n"
            f"🌐 Network: <b>{network}</b>\n"
            f"🔑 TxID: <code>{txn_text}</code>\n\n"
            f"Your balance will be updated after verification by our team.",
            parse_mode=HTML,
            reply_markup=kb_back_main()
        )

# ══════════════════════════════════════════════════════
#  RUNNER
# ══════════════════════════════════════════════════════

async def run_store_bot():
    if not STORE_BOT_TOKEN:
        print("⚠️ STORE_TOKEN is not set.")
        return

    app = Application.builder().token(STORE_BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", cmd_start))
    app.add_handler(CallbackQueryHandler(on_callback))
    app.add_handler(MessageHandler(
        (filters.TEXT | filters.PHOTO | filters.Document.ALL) & ~filters.COMMAND,
        on_user_message
    ))

    print("🚀 [1/4] Nex Shop Store Bot running (Reference UI)...")
    async with app:
        await app.start()
        await app.updater.start_polling(allowed_updates=Update.ALL_TYPES)
        await asyncio.Event().wait()
        await app.updater.stop()
        await app.stop()

if __name__ == "__main__":
    asyncio.run(run_store_bot())
