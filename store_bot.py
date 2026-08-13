#!/usr/bin/env python3
"""
store_bot.py — Customer Storefront Bot
Features:
- Premium Luxury UI Design with high-end emoji formatting
- Referral System with unique deep links & profile counters
- Dynamic Product Catalog with randomized live stock
- Crypto Deposit & Instant Balance Check
- Direct digital delivery & Order tracking
"""

import asyncio
import logging
import os
import urllib.parse
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
#  PREMIUM UI DESIGN HELPERS & KEYBOARDS
# ══════════════════════════════════════════════════════

def kb_main_menu(bot_username: str = ""):
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🛍️  Browse Catalog", callback_data="menu_catalog"),
         InlineKeyboardButton("💎  My Profile",     callback_data="menu_profile")],
        [InlineKeyboardButton("💳  Deposit Funds",   callback_data="menu_deposit"),
         InlineKeyboardButton("📦  My Orders",       callback_data="menu_orders")],
        [InlineKeyboardButton("🎁  Redeem Voucher",  callback_data="menu_redeem"),
         InlineKeyboardButton("⚡  Support & FAQ",   callback_data="menu_support")],
    ])

def kb_back_main():
    return InlineKeyboardMarkup([[InlineKeyboardButton("« 🏠 Return to Menu", callback_data="menu_home")]])

def kb_catalog_list(products):
    rows = []
    for p in products:
        stock_badge = f"🔥 {p['stock']} left" if p['stock'] < 10 else f"📦 {p['stock']} in stock"
        btn_text = f"💎 {p['name']}  •  ${p['price']:.2f}"
        rows.append([InlineKeyboardButton(btn_text, callback_data=f"view_p_{p['id']}")])
    rows.append([InlineKeyboardButton("« 🏠 Return to Menu", callback_data="menu_home")])
    return InlineKeyboardMarkup(rows)

def kb_product_detail(p):
    rows = [
        [InlineKeyboardButton(f"⚡ Instant Purchase (${p['price']:.2f})", callback_data=f"buy_p_{p['id']}_1")],
        [InlineKeyboardButton("« 🛍️ Catalog", callback_data="menu_catalog"),
         InlineKeyboardButton("🏠 Menu", callback_data="menu_home")]
    ]
    return InlineKeyboardMarkup(rows)

def kb_wallets(wallets):
    rows = []
    for w in wallets:
        if w["active"]:
            rows.append([InlineKeyboardButton(f"💳 {w['label']}", callback_data=f"dep_w_{w['key']}")])
    rows.append([InlineKeyboardButton("« 🏠 Return to Menu", callback_data="menu_home")])
    return InlineKeyboardMarkup(rows)

async def safe_ans(q, text="", alert=False):
    try:
        await q.answer(text, show_alert=alert)
    except BadRequest:
        pass

# ══════════════════════════════════════════════════════
#  COMMAND HANDLERS
# ══════════════════════════════════════════════════════

async def cmd_start(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    if db.is_banned(user.id):
        return

    # Check for referral payload: /start ref_123456789
    referrer_id = None
    if ctx.args and len(ctx.args) > 0:
        arg = ctx.args[0]
        if arg.startswith("ref_"):
            try:
                ref_candidate = int(arg.replace("ref_", ""))
                if ref_candidate != user.id:
                    referrer_id = ref_candidate
            except ValueError:
                pass

    # Register or get user
    db.get_or_create_user(user.id, user.first_name, user.username or "", referrer_id)

    bot_info = await ctx.bot.get_me()
    ctx.bot_data["username"] = bot_info.username

    welcome_text = (
        f"╭──────── ✦ <b>Nex Shop</b> ✦ ────────╮\n\n"
        f"✨ <i>Welcome,</i> <b>{user.first_name}</b>!\n"
        f"Experience instant digital deliveries, VIP stock access,\n"
        f"and secure cryptocurrency settlements.\n\n"
        f"⚡ <b>Fast Auto-Delivery</b>  •  💎 <b>Verified Warranty</b>\n\n"
        f"╰──────────────────────────────────────────╯\n\n"
        f"👇 <i>Select an option from the terminal below:</i>"
    )

    await update.message.reply_text(
        welcome_text,
        parse_mode=HTML,
        reply_markup=kb_main_menu(bot_info.username)
    )

# ══════════════════════════════════════════════════════
#  CALLBACK QUERY ROUTER
# ══════════════════════════════════════════════════════

async def on_callback(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    data = q.data
    user = update.effective_user

    if db.is_banned(user.id):
        await safe_ans(q, "⛔ Access restricted.", alert=True)
        return

    bot_user = ctx.bot_data.get("username")
    if not bot_user:
        b = await ctx.bot.get_me()
        bot_user = b.username
        ctx.bot_data["username"] = bot_user

    u_data = db.get_user(user.id) or db.get_or_create_user(user.id, user.first_name, user.username or "")

    await safe_ans(q)

    # ── HOME ──────────────────────────────────────────
    if data == "menu_home":
        ctx.user_data.clear()
        home_text = (
            f"╭──────── ✦ <b>Nex Shop</b> ✦ ────────╮\n\n"
            f"👤 <b>Client:</b> <code>{user.first_name}</code>\n"
            f"💰 <b>Wallet:</b> <code>${u_data['balance']:.2f} USDT</code>\n"
            f"👥 <b>Referrals:</b> <code>{u_data.get('referral_count', 0)}</code>\n\n"
            f"╰──────────────────────────────────────────╯"
        )
        await q.edit_message_text(home_text, parse_mode=HTML, reply_markup=kb_main_menu(bot_user))

    # ── PROFILE & REFERRAL SYSTEM ─────────────────────
    elif data == "menu_profile":
        ref_link = f"https://t.me/{bot_user}?start=ref_{user.id}"
        orders = db.get_user_orders(user.id, limit=1)
        
        share_text = urllib.parse.quote(f"🔥 Check out the top-tier digital products store! Get instant delivery: {ref_link}")
        share_url = f"https://t.me/share/url?url={share_text}"

        profile_text = (
            f"╭──────── 💎 <b>CLIENT VIP PROFILE</b> 💎 ────────╮\n\n"
            f"🆔 <b>Account ID :</b> <code>{user.id}</code>\n"
            f"👤 <b>Client Tag :</b> @{user.username or 'NoUsername'}\n"
            f"💰 <b>Available  :</b> <code>${u_data['balance']:.2f} USDT</code>\n"
            f"📦 <b>Orders Done:</b> <code>{len(db.get_user_orders(user.id, 100))} orders</code>\n\n"
            f"👑 <b>AFFILIATE PROGRAM</b>\n"
            f"👥 <b>Total Invited:</b> <b>{u_data.get('referral_count', 0)} Members</b>\n\n"
            f"🔗 <b>Your Exclusive Referral Link:</b>\n"
            f"<code>{ref_link}</code>\n\n"
            f"<i>Share your link with friends. Every time a member registers, it tracks instantly under your account!</i>\n\n"
            f"╰──────────────────────────────────────────╯"
        )

        kb_profile = InlineKeyboardMarkup([
            [InlineKeyboardButton("📤 Share Referral Link", url=share_url)],
            [InlineKeyboardButton("💳 Top-up Balance", callback_data="menu_deposit"),
             InlineKeyboardButton("📦 Order History", callback_data="menu_orders")],
            [InlineKeyboardButton("« 🏠 Return to Menu", callback_data="menu_home")]
        ])

        await q.edit_message_text(profile_text, parse_mode=HTML, reply_markup=kb_profile)

    # ── CATALOG ───────────────────────────────────────
    elif data == "menu_catalog":
        products = db.get_all_products(active_only=True)
        if not products:
            await q.edit_message_text(
                "🛍️ <b>Catalog is currently updating.</b>\n<i>New batch arriving shortly.</i>",
                parse_mode=HTML,
                reply_markup=kb_back_main()
            )
            return

        catalog_text = (
            f"╭──────── 🛍️ <b>PRODUCT CATALOG</b> 🛍️ ────────╮\n\n"
            f"⚡ <i>Select a product to view specifications & instant buy:</i>\n\n"
            f"╰──────────────────────────────────────────╯"
        )
        await q.edit_message_text(catalog_text, parse_mode=HTML, reply_markup=kb_catalog_list(products))

    # ── PRODUCT DETAIL VIEW ───────────────────────────
    elif data.startswith("view_p_"):
        pid = int(data.replace("view_p_", ""))
        p = db.get_product(pid)
        if not p or not p["active"]:
            await safe_ans(q, "⚠️ Product currently unavailable.", alert=True)
            return

        stock_icon = "🟢 In Stock" if p['stock'] > 5 else ("🟡 Low Stock" if p['stock'] > 0 else "🔴 Sold Out")
        p_text = (
            f"╭─────── 💎 <b>{p['name']}</b> ───────╮\n\n"
            f"💰 <b>Price    :</b> <code>${p['price']:.2f} USDT</code>\n"
            f"📦 <b>Stock    :</b> <code>{p['stock']} available</code> ({stock_icon})\n"
            f"⚡ <b>Delivery :</b> <i>Instant Automatic Delivery</i>\n\n"
            f"<i>Your balance: ${u_data['balance']:.2f} USDT</i>\n\n"
            f"╰──────────────────────────────────────────╯"
        )
        await q.edit_message_text(p_text, parse_mode=HTML, reply_markup=kb_product_detail(p))

    # ── PURCHASE FLOW ─────────────────────────────────
    elif data.startswith("buy_p_"):
        parts = data.split("_")
        pid = int(parts[2])
        qty = int(parts[3]) if len(parts) > 3 else 1

        p = db.get_product(pid)
        if not p or not p["active"]:
            await safe_ans(q, "Product no longer available.", alert=True)
            return

        if p["stock"] < qty:
            await safe_ans(q, "⚠️ Not enough stock available.", alert=True)
            return

        total_cost = p["price"] * qty
        if u_data["balance"] < total_cost:
            deficit = total_cost - u_data["balance"]
            await safe_ans(q, f"⚠️ Insufficient balance. Please deposit ${deficit:.2f} USDT.", alert=True)
            dep_kb = InlineKeyboardMarkup([
                [InlineKeyboardButton("💳 Deposit Funds", callback_data="menu_deposit")],
                [InlineKeyboardButton("« Back to Product", callback_data=f"view_p_{pid}")]
            ])
            await q.edit_message_text(
                f"⚠️ <b>Insufficient Balance!</b>\n\n"
                f"Total Cost: <b>${total_cost:.2f} USDT</b>\n"
                f"Your Balance: <b>${u_data['balance']:.2f} USDT</b>\n"
                f"Needed: <b>${deficit:.2f} USDT</b>",
                parse_mode=HTML,
                reply_markup=dep_kb
            )
            return

        # Deduct balance & process order
        if db.deduct_balance(user.id, total_cost):
            order_res = db.create_order(user.id, pid, qty)
            if not order_res:
                # Refund if stock failed
                db.add_balance(user.id, total_cost)
                await safe_ans(q, "Order failed. Balance refunded.", alert=True)
                return

            ref, prod_name, total_price, dtype, dcontent = order_res
            
            # Send immediate delivery
            delivery_caption = (
                f"🎉 <b>ORDER COMPLETED & DELIVERED!</b>\n\n"
                f"📋 <b>Order Ref :</b> <code>{ref}</code>\n"
                f"💎 <b>Product   :</b> <b>{prod_name}</b>\n"
                f"🔢 <b>Quantity  :</b> {qty}\n"
                f"💰 <b>Total Paid:</b> ${total_price:.2f} USDT\n\n"
                f"🎁 <b>Your Delivery Details:</b>\n"
            )

            store = Bot(token=STORE_BOT_TOKEN)
            async with store:
                if dtype == "photo":
                    await store.send_photo(user.id, dcontent, caption=delivery_caption, parse_mode=HTML)
                elif dtype == "document":
                    await store.send_document(user.id, dcontent, caption=delivery_caption, parse_mode=HTML)
                elif dtype == "video":
                    await store.send_video(user.id, dcontent, caption=delivery_caption, parse_mode=HTML)
                else:
                    await store.send_message(user.id, f"{delivery_caption}\n<code>{dcontent}</code>", parse_mode=HTML)

            db.deliver_order(ref)

            await q.edit_message_text(
                f"✅ <b>Purchase Successful!</b>\n\n"
                f"Order <code>{ref}</code> has been dispatched directly to your chat above 👆\n"
                f"Remaining Balance: <b>${(u_data['balance'] - total_cost):.2f} USDT</b>",
                parse_mode=HTML,
                reply_markup=kb_back_main()
            )

    # ── DEPOSIT SYSTEM ────────────────────────────────
    elif data == "menu_deposit":
        wallets = db.get_all_wallets()
        dep_text = (
            f"╭──────── 💳 <b>DEPOSIT FUNDS</b> 💳 ────────╮\n\n"
            f"💰 <b>Current Balance:</b> <code>${u_data['balance']:.2f} USDT</code>\n\n"
            f"⚡ <i>Select your preferred crypto payment network:</i>\n\n"
            f"╰──────────────────────────────────────────╯"
        )
        await q.edit_message_text(dep_text, parse_mode=HTML, reply_markup=kb_wallets(wallets))

    elif data.startswith("dep_w_"):
        key = data.replace("dep_w_", "")
        wallets = {w["key"]: w for w in db.get_all_wallets()}
        w = wallets.get(key)
        if not w:
            await safe_ans(q, "Wallet unavailable.", alert=True)
            return

        ctx.user_data["dep_network"] = w["label"]

        w_text = (
            f"╭──────── 💳 <b>{w['label']}</b> ────────╮\n\n"
            f"📌 <b>Official Deposit Address:</b>\n"
            f"<code>{w['address']}</code>\n\n"
            f"⚠️ <i>Please only send tokens on the correct network.</i>\n\n"
            f"After sending, click <b>Submit TXN / Hash</b> below.\n"
            f"╰──────────────────────────────────────────╯"
        )

        w_kb = InlineKeyboardMarkup([
            [InlineKeyboardButton("✍️ Submit TXN / Hash", callback_data=f"dep_submit_{key}")],
            [InlineKeyboardButton("« 💳 Change Network", callback_data="menu_deposit"),
             InlineKeyboardButton("🏠 Menu", callback_data="menu_home")]
        ])
        await q.edit_message_text(w_text, parse_mode=HTML, reply_markup=w_kb)

    elif data.startswith("dep_submit_"):
        key = data.replace("dep_submit_", "")
        wallets = {w["key"]: w for w in db.get_all_wallets()}
        w = wallets.get(key, {})
        network_label = w.get("label", "Crypto")
        
        ctx.user_data["action"] = "waiting_deposit_txn"
        ctx.user_data["dep_network"] = network_label

        await q.edit_message_text(
            f"✍️ <b>Submit Transaction Proof ({network_label})</b>\n\n"
            f"Please send the <b>Transaction ID / Hash (TXN ID)</b> or screenshot in the chat now:\n\n"
            f"<i>Our staff verifies and credits your account instantly.</i>",
            parse_mode=HTML,
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("❌ Cancel", callback_data="menu_deposit")]])
        )

    # ── ORDERS HISTORY ────────────────────────────────
    elif data == "menu_orders":
        orders = db.get_user_orders(user.id, limit=10)
        if not orders:
            await q.edit_message_text(
                "📦 <b>You have no past orders yet.</b>\nBrowse our catalog to get started!",
                parse_mode=HTML,
                reply_markup=kb_back_main()
            )
            return

        lines = []
        for o in orders:
            status_emoji = "✅" if o['status'] == 'delivered' else "⏳"
            lines.append(
                f"{status_emoji} <code>{o['ref']}</code> — <b>{o['prod_name']}</b> (x{o['qty']})\n"
                f"   💰 ${o['price']:.2f} USDT  •  📅 <i>{o['created_at']}</i>"
            )

        orders_text = (
            f"╭──────── 📦 <b>ORDER HISTORY</b> 📦 ────────╮\n\n"
            + "\n\n".join(lines) +
            f"\n\n╰──────────────────────────────────────────╯"
        )
        await q.edit_message_text(orders_text, parse_mode=HTML, reply_markup=kb_back_main())

    # ── REDEEM VOUCHER ────────────────────────────────
    elif data == "menu_redeem":
        ctx.user_data["action"] = "waiting_redeem_code"
        await q.edit_message_text(
            "🎁 <b>Redeem Gift Voucher</b>\n\n"
            "Send your promo code in the chat:\n"
            "<i>Example: <code>VIP100</code> or <code>WELCOME5</code></i>",
            parse_mode=HTML,
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("❌ Cancel", callback_data="menu_home")]])
        )

    # ── SUPPORT ───────────────────────────────────────
    elif data == "menu_support":
        supp_text = (
            f"╭──────── ⚡ <b>SUPPORT & COMMUNITY</b> ⚡ ────────╮\n\n"
            f"💬 <b>24/7 Live Support:</b> Contact @NexIndo for issues, bulk orders, or custom requests.\n\n"
            f"🛡️ <b>Warranty Guarantee:</b> All goods are backed by instant replacement guarantee.\n\n"
            f"╰──────────────────────────────────────────╯"
        )
        await q.edit_message_text(supp_text, parse_mode=HTML, reply_markup=kb_back_main())

# ══════════════════════════════════════════════════════
#  MESSAGE INPUT HANDLER
# ══════════════════════════════════════════════════════

async def on_user_message(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    if db.is_banned(user.id):
        return

    action = ctx.user_data.get("action")
    if not action:
        return

    # ── TXN Submission ────────────────────────────────
    if action == "waiting_deposit_txn":
        ctx.user_data.pop("action", None)
        network = ctx.user_data.pop("dep_network", "USDT")
        txn_text = (update.message.text or update.message.caption or "Uploaded Screenshot").strip()

        ref = db.create_deposit(user.id, network, txn_text)
        await update.message.reply_text(
            f"✅ <b>Deposit Request Received!</b>\n\n"
            f"📋 <b>Reference:</b> <code>{ref}</code>\n"
            f"🌐 <b>Network  :</b> {network}\n"
            f"🔑 <b>TXN Hash :</b> <code>{txn_text}</code>\n\n"
            f"<i>Our administrative system is reviewing your transaction. You will be notified as soon as funds are credited.</i>",
            parse_mode=HTML,
            reply_markup=kb_back_main()
        )

    # ── Redeem Code Submission ────────────────────────
    elif action == "waiting_redeem_code":
        ctx.user_data.pop("action", None)
        code = (update.message.text or "").strip()
        ok, msg = db.claim_redeem_code(code, user.id)
        await update.message.reply_text(msg, parse_mode=HTML, reply_markup=kb_back_main())

# ══════════════════════════════════════════════════════
#  APPLICATION RUNNER
# ══════════════════════════════════════════════════════

async def run_store_bot():
    if not STORE_BOT_TOKEN:
        print("⚠️ STORE_TOKEN is not set in environment.")
        return

    app = Application.builder().token(STORE_BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", cmd_start))
    app.add_handler(CallbackQueryHandler(on_callback))
    app.add_handler(MessageHandler(filters.TEXT | filters.PHOTO | filters.Document.ALL, on_user_message))

    print("🚀 [1/4] Store Bot running with VIP UI & Referral System...")
    async with app:
        await app.start()
        await app.updater.start_polling(allowed_updates=Update.ALL_TYPES)
        await asyncio.Event().wait()
        await app.updater.stop()
        await app.stop()

if __name__ == "__main__":
    asyncio.run(run_store_bot())
