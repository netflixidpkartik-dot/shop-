#!/usr/bin/env python3
"""
store_bot.py — Nex Shop | Customer Storefront
Premium tg-emoji with automatic fallback to Unicode if bot lacks Fragment access.
"""

import asyncio
import logging
import os
import re
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
#  PREMIUM EMOJI — tg-emoji with Unicode fallback
# ══════════════════════════════════════════════════════

def e(emoji_id: str, fallback: str) -> str:
    return f'<tg-emoji emoji-id="{emoji_id}">{fallback}</tg-emoji>'

# UI
E_CONGRATS  = e("5461151367559141950", "🎉")
E_CHECK     = e("5206607081334906820", "✅")
E_SHIELD    = e("5251203410396458957", "🛡️")
E_CROSS     = e("5240241223632954241", "❌")
E_GLOBE     = e("5447410659077661506", "🌐")
E_TG        = e("5769499782842162900", "📱")
E_DOLLAR    = e("5197434882321567830", "💵")
E_USDT      = e("5935779811073989584", "💰")
E_GROWTH    = e("5429651785352501917", "📈")
E_CART      = e("5312361253610475399", "🛒")
E_CRYPTO    = e("6314536973860084922", "💎")
E_ADD       = e("5397916757333654639", "➕")
E_BITCOIN   = e("5935842277078342221", "₿")

# Products
E_ADOBE       = e("5298773244101281960", "❤️")   # real Adobe logo
E_CHATGPT     = e("5796185041717433060", "🤖")   # real ChatGPT logo
E_GEMINI      = e("6178962311072456422", "✨")    # real Gemini logo
E_ANTIGRAV    = e("5319095375783569775", "🌟")
E_HIGGSFIELD  = e("6201693472731176318", "🎬")   # real Higgsfield logo
E_YOUTUBE     = e("5291892070837921372", "▶️")   # real YouTube logo
E_CAPCUT      = e("6124915477706705232", "✂️")
E_CLAUDE      = e("6174520215376763867", "🧠")   # real Claude logo
E_CURSOR      = e("6273793612715138423", "⚡")   # real Cursor logo
E_LOVABLE     = e("6104729848675050039", "💜")   # real Lovable logo
E_KLING       = e("6177161027558316737", "🎥")   # real Krea/Kling logo
E_SUNO        = e("5319101195464252717", "🎵")
E_PERPLEXITY  = e("5319118925089249250", "🔍")
E_HEYGEN      = e("5440613014338318469", "📹")
E_KREA        = e("6177161027558316737", "🎨")   # real Krea logo

def clean_name(name: str) -> str:
    """Strip leading emoji characters from product name."""
    import re
    return re.sub(r'^[\U0001F000-\U0001FFFF\U00002600-\U000027BF\U0001F900-\U0001F9FF\u2702-\u27B0\u231A-\u231B\u23E9-\u23F3\u23F8-\u23FA\u25AA-\u25FE\u2614-\u2615\u2648-\u2653\u267F\u2693\u26A1\u26AA-\u26AB\u26BD-\u26BE\u26C4-\u26C5\u26CE\u26D4\u26EA\u26F2-\u26F3\u26F5\u26FA\u26FD\u2702\u2705\u2708-\u270D\u270F\uFE0F\u20E3\u200D\U0001FA00-\U0001FA6F\U0001FA70-\U0001FAFF]+\s*', '', name).strip()

def product_emoji(name: str) -> str:
    n = name.lower()
    if "adobe"       in n: return E_ADOBE
    if "chatgpt"     in n: return E_CHATGPT
    if "gemini"      in n: return f"{E_GEMINI}{E_ANTIGRAV}"
    if "higgsfield"  in n: return E_HIGGSFIELD
    if "youtube"     in n: return E_YOUTUBE
    if "capcut"      in n: return E_CAPCUT
    if "claude"      in n: return E_CLAUDE
    if "cursor"      in n: return E_CURSOR
    if "lovable"     in n: return E_LOVABLE
    if "kling"       in n: return E_KLING
    if "suno"        in n: return E_SUNO
    if "perplexity"  in n: return E_PERPLEXITY
    if "heygen"      in n: return E_HEYGEN
    if "krea"        in n: return E_KREA
    return E_CRYPTO

# ══════════════════════════════════════════════════════
#  SAFE EDIT — tries tg-emoji first, falls back to plain
# ══════════════════════════════════════════════════════

def _strip_tg_emoji(text: str) -> str:
    """Remove tg-emoji tags, keeping the fallback emoji inside."""
    return re.sub(r'<tg-emoji emoji-id="[^"]*">([^<]*)</tg-emoji>', r'\1', text)

async def safe_edit(q, text: str, reply_markup=None, parse_mode=HTML):
    """Edit message with tg-emoji. Falls back to Unicode if bot lacks Fragment."""
    try:
        await q.edit_message_text(text, parse_mode=parse_mode, reply_markup=reply_markup)
    except BadRequest as err:
        if "tg-emoji" in str(err).lower() or "entity" in str(err).lower() or "parse" in str(err).lower():
            fallback = _strip_tg_emoji(text)
            try:
                await q.edit_message_text(fallback, parse_mode=parse_mode, reply_markup=reply_markup)
            except BadRequest:
                await q.edit_message_text(
                    re.sub(r'<[^>]+>', '', fallback),
                    reply_markup=reply_markup
                )
        else:
            raise

async def safe_reply(message, text: str, reply_markup=None, parse_mode=HTML, **kwargs):
    """Send message with tg-emoji. Falls back to Unicode if bot lacks Fragment."""
    try:
        await message.reply_text(text, parse_mode=parse_mode, reply_markup=reply_markup, **kwargs)
    except BadRequest as err:
        if "tg-emoji" in str(err).lower() or "entity" in str(err).lower() or "parse" in str(err).lower():
            fallback = _strip_tg_emoji(text)
            try:
                await message.reply_text(fallback, parse_mode=parse_mode, reply_markup=reply_markup, **kwargs)
            except BadRequest:
                await message.reply_text(
                    re.sub(r'<[^>]+>', '', fallback),
                    reply_markup=reply_markup
                )
        else:
            raise

# ══════════════════════════════════════════════════════
#  KEYBOARDS
# ══════════════════════════════════════════════════════

def kb_main():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🛒 Buy", callback_data="menu_buy")],
        [InlineKeyboardButton("👤 Profile",          callback_data="menu_profile"),
         InlineKeyboardButton("🔵 Purchase history", callback_data="menu_orders")],
        [InlineKeyboardButton("🎀 Wallet",           callback_data="menu_wallet"),
         InlineKeyboardButton("🔗 API Link",         callback_data="menu_api")],
        [InlineKeyboardButton("💬 Support",          callback_data="menu_support")],
        [InlineKeyboardButton("🌐 Language",         callback_data="menu_language")],
    ])

def kb_back_main():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("↩️ Back to main menu", callback_data="menu_home")]
    ])

def kb_products(products):
    """Buttons use clean names (no emoji) — emoji appear in the message text above."""
    rows = []
    for p in products:
        label = clean_name(p["name"])
        if len(label) > 50:
            label = label[:48] + "…"
        rows.append([InlineKeyboardButton(label, callback_data=f"view_p_{p['id']}")])
    rows.append([InlineKeyboardButton("🔄 Refresh", callback_data="menu_buy"),
                 InlineKeyboardButton("↩️ Main menu", callback_data="menu_home")])
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
        InlineKeyboardButton("🔄 Refresh balance",   callback_data="menu_wallet"),
        InlineKeyboardButton("↩️ Back to main menu", callback_data="menu_home"),
    ])
    return InlineKeyboardMarkup(rows)

async def safe_ans(q, text="", alert=False):
    try:
        await q.answer(text, show_alert=alert)
    except Exception:
        pass

# ══════════════════════════════════════════════════════
#  ERROR HANDLER
# ══════════════════════════════════════════════════════

async def error_handler(update: object, ctx: ContextTypes.DEFAULT_TYPE):
    logging.error(f"Update error: {ctx.error}", exc_info=ctx.error)

# ══════════════════════════════════════════════════════
#  /start
# ══════════════════════════════════════════════════════

async def cmd_start(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    if db.is_banned(user.id):
        return

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

    await safe_reply(
        update.message,
        f"• Share your bot link with your referral code.\n"
        f"• When the invited user places their first order, you receive 10% of the order value.\n"
        f"• Each new user is rewarded only once.\n"
        f"• Self-referrals are not allowed.\n\n"
        f"🔗 Your referral link:\n{ref_link}",
        parse_mode=None,
        disable_web_page_preview=True
    )

    await safe_reply(
        update.message,
        f"{E_CONGRATS} Please choose a menu:",
        reply_markup=kb_main()
    )

# ══════════════════════════════════════════════════════
#  CALLBACKS
# ══════════════════════════════════════════════════════

async def on_callback(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    data = q.data
    user = update.effective_user
    await safe_ans(q)

    if db.is_banned(user.id):
        await q.answer("Restricted.", show_alert=True)
        return

    bot_user = ctx.bot_data.get("username")
    if not bot_user:
        b = await ctx.bot.get_me()
        bot_user = b.username
        ctx.bot_data["username"] = bot_user

    u_data = db.get_user(user.id) or db.get_or_create_user(
        user.id, user.first_name, user.username or "")

    # ── HOME ─────────────────────────────────────────
    if data == "menu_home":
        ctx.user_data.clear()
        await safe_edit(q, f"{E_CONGRATS} Please choose a menu:", reply_markup=kb_main(), parse_mode=HTML)

    # ── BUY / CATALOG ─────────────────────────────────
    elif data == "menu_buy":
        products = db.get_all_products(active_only=True)
        if not products:
            await safe_edit(q, f"{E_CROSS} No products available.", reply_markup=kb_back_main())
            return
        # Build catalog text: premium emoji show in MESSAGE TEXT
        lines = [f"{E_CART} <b>Products</b>\n"]
        for p in products:
            pemoji = product_emoji(p["name"])
            pname  = clean_name(p["name"])
            lines.append(f"{pemoji} {pname} — <b>${p['price']:.2f}</b>")
        catalog_text = "\n".join(lines)
        await safe_edit(q, catalog_text, reply_markup=kb_products(products))

    # ── PRODUCT DETAIL ────────────────────────────────
    elif data.startswith("view_p_"):
        pid = int(data.replace("view_p_", ""))
        p = db.get_product(pid)
        if not p or not p["active"]:
            await q.answer("This product is unavailable.", show_alert=True)
            return
        pemoji = product_emoji(p["name"])
        pname  = clean_name(p["name"])
        stock_txt = f"{E_CHECK} In stock" if p["stock"] > 0 else f"{E_CROSS} Out of stock"
        await safe_edit(
            q,
            f"{pemoji} <b>{pname}</b>\n\n"
            f"{E_DOLLAR} Price: <b>${p['price']:.2f}</b>\n"
            f"{E_CART} Stock: <b>{p['stock']}</b>  {stock_txt}\n"
            f"{E_SHIELD} Delivery: <b>Instant</b>\n\n"
            f"{E_USDT} Your balance: <b>${u_data['balance']:.2f}</b>",
            reply_markup=kb_product_detail(pid)
        )

    # ── PURCHASE ──────────────────────────────────────
    elif data.startswith("buy_p_"):
        parts = data.split("_")
        pid = int(parts[2])
        qty = int(parts[3]) if len(parts) > 3 else 1
        p = db.get_product(pid)

        if not p or not p["active"]:
            await q.answer("Product unavailable.", show_alert=True)
            return
        if p["stock"] < qty:
            await q.answer("Out of stock.", show_alert=True)
            return

        total_cost = p["price"] * qty
        if u_data["balance"] < total_cost:
            deficit = round(total_cost - u_data["balance"], 4)
            await safe_edit(
                q,
                f"{E_CROSS} <b>Insufficient balance!</b>\n\n"
                f"{E_DOLLAR} Cost: <b>${total_cost:.2f}</b>\n"
                f"{E_USDT} Balance: <b>${u_data['balance']:.2f}</b>\n"
                f"{E_ADD} Need: <b>${deficit:.2f} more</b>",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("🎀 Top up wallet", callback_data="menu_wallet")],
                    [InlineKeyboardButton("↩️ Back", callback_data=f"view_p_{pid}")],
                ])
            )
            return

        if not db.deduct_balance(user.id, total_cost):
            await q.answer("Balance error. Please retry.", show_alert=True)
            return

        order_res = db.create_order(user.id, pid, qty)
        if not order_res:
            db.add_balance(user.id, total_cost)
            await q.answer("Out of stock. Refunded.", show_alert=True)
            return

        ref, prod_name, total_price, dtype, dcontent = order_res
        db.maybe_pay_referral_commission(user.id, total_cost)

        pemoji = product_emoji(prod_name)
        delivery_text = (
            f"{E_CONGRATS} <b>Order delivered!</b>\n\n"
            f"📋 Order: <code>{ref}</code>\n"
            f"{pemoji} Product: <b>{prod_name}</b>\n"
            f"{E_DOLLAR} Paid: <b>${total_price:.2f}</b>\n\n"
            f"{E_SHIELD} <b>Your delivery:</b>\n"
        )

        store = Bot(token=STORE_BOT_TOKEN)
        async with store:
            try:
                plain_delivery = _strip_tg_emoji(delivery_text)
                if dtype == "photo":
                    await store.send_photo(user.id, dcontent, caption=plain_delivery, parse_mode=HTML)
                elif dtype == "document":
                    await store.send_document(user.id, dcontent, caption=plain_delivery, parse_mode=HTML)
                elif dtype == "video":
                    await store.send_video(user.id, dcontent, caption=plain_delivery, parse_mode=HTML)
                else:
                    await store.send_message(
                        user.id, f"{plain_delivery}\n<code>{dcontent}</code>", parse_mode=HTML
                    )
            except TelegramError as e_err:
                logging.error(f"Delivery failed: {e_err}")

        db.deliver_order(ref)
        new_bal = u_data["balance"] - total_cost
        await safe_edit(
            q,
            f"{E_CHECK} <b>Purchase successful!</b>\n\n"
            f"Order <code>{ref}</code> delivered above\n"
            f"{E_USDT} New balance: <b>${new_bal:.2f}</b>",
            reply_markup=kb_back_main()
        )

    # ── PROFILE ───────────────────────────────────────
    elif data == "menu_profile":
        uname = f"@{user.username}" if user.username else user.first_name
        total_spent = db.get_user_total_spent(user.id)
        ref_link = f"https://t.me/{bot_user}?start=ref_{user.id}"
        await safe_edit(
            q,
            f"👤 <b>Customer profile</b>\n\n"
            f"Name: <b>{uname}</b>\n"
            f"{E_DOLLAR} Total spent: <b>${total_spent:.2f}</b>\n"
            f"{E_GROWTH} Referrals: <b>{u_data.get('referral_count', 0)}</b>\n\n"
            f"🔗 Your referral link:\n<code>{ref_link}</code>",
            reply_markup=kb_back_main()
        )

    # ── WALLET ────────────────────────────────────────
    elif data == "menu_wallet":
        uname = f"@{user.username}" if user.username else user.first_name
        total_spent = db.get_user_total_spent(user.id)
        wallets = db.get_all_wallets()
        await safe_edit(
            q,
            f"👤 <b>Customer profile</b>\n\n"
            f"Name: <b>{uname}</b>\n"
            f"{E_DOLLAR} Total spent: <b>${total_spent:.2f}</b>\n\n"
            f"🎀 <b>Your wallet</b>\n\n"
            f"{E_USDT} USD/USDT: <b>${u_data['balance']:.2f}</b>",
            reply_markup=kb_wallet_topup(wallets)
        )

    # ── DEPOSIT ───────────────────────────────────────
    elif data.startswith("dep_w_"):
        key = data.replace("dep_w_", "")
        wallets = {w["key"]: w for w in db.get_all_wallets()}
        w = wallets.get(key)
        if not w:
            await q.answer("Wallet unavailable.", show_alert=True)
            return
        ctx.user_data["action"] = "waiting_deposit_txn"
        ctx.user_data["dep_network"] = w["label"]
        await safe_edit(
            q,
            f"⚠️ Allowed difference: 0.02 USDT. The received amount must be exact "
            f"(network fees are NOT included, please add fees when sending).\n\n"
            f"{E_CRYPTO} <b>USDT receiving address ({w['label']}):</b>\n"
            f"<code>{w['address']}</code>\n\n"
            f"Scan or copy the correct wallet address.\n\n"
            f"⚠️ After completing the transfer, please send the TxID or transaction hash "
            f"in this chat so the system can confirm it.",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("↩️ Back to wallet", callback_data="menu_wallet")]
            ])
        )

    # ── PURCHASE HISTORY ──────────────────────────────
    elif data == "menu_orders":
        orders = db.get_user_orders(user.id, limit=15)
        if not orders:
            await safe_edit(q, "🔵 <b>Purchase history</b>\n\nNo purchases yet.",
                            reply_markup=kb_back_main())
            return
        lines = []
        for o in orders:
            icon = E_CHECK if o["status"] == "delivered" else "⏳"
            date = o["created_at"][:10]
            lines.append(
                f"{icon} <b>{o['prod_name']}</b>\n"
                f"   {E_DOLLAR} ${o['price']:.2f}  •  📅 {date}"
            )
        await safe_edit(
            q,
            "🔵 <b>Purchase history</b>\n\n" + "\n\n".join(lines),
            reply_markup=kb_back_main()
        )

    # ── SUPPORT ───────────────────────────────────────
    elif data == "menu_support":
        await safe_edit(
            q,
            f"{E_CONGRATS} <b>Quick support:</b>\n\n"
            f"{E_TG} Telegram: @NexIndo\n\n"
            f"Contact us for faster help and issue handling.",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("💬 Contact @NexIndo", url="https://t.me/NexIndo")],
                [InlineKeyboardButton("↩️ Back to main menu", callback_data="menu_home")],
            ])
        )

    # ── LANGUAGE ─────────────────────────────────────
    elif data == "menu_language":
        await safe_edit(
            q,
            f"{E_GLOBE} <b>Choose language:</b>",
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
        await safe_edit(q, f"{E_CONGRATS} Please choose a menu:",
                        reply_markup=kb_main(), parse_mode=HTML)

    # ── API ───────────────────────────────────────────
    elif data == "menu_api":
        await safe_edit(
            q,
            f"🔗 <b>API Link</b>\n\n"
            f"Your user API key:\n<code>nex_{user.id}</code>\n\n"
            f"<i>Contact @NexIndo for API integration support.</i>",
            reply_markup=kb_back_main()
        )

# ══════════════════════════════════════════════════════
#  MESSAGE HANDLER
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
        await safe_reply(
            update.message,
            f"{E_CHECK} <b>Deposit submitted!</b>\n\n"
            f"📋 Ref: <code>{ref}</code>\n"
            f"{E_GLOBE} Network: <b>{network}</b>\n"
            f"{E_BITCOIN} TxID: <code>{txn_text}</code>\n\n"
            f"Your balance will be updated after verification.",
            reply_markup=kb_back_main()
        )

# ══════════════════════════════════════════════════════
#  RUNNER
# ══════════════════════════════════════════════════════

async def run_store_bot():
    if not STORE_BOT_TOKEN:
        print("STORE_TOKEN is not set.")
        return

    app = Application.builder().token(STORE_BOT_TOKEN).build()
    app.add_error_handler(error_handler)
    app.add_handler(CommandHandler("start", cmd_start))
    app.add_handler(CallbackQueryHandler(on_callback))
    app.add_handler(MessageHandler(
        (filters.TEXT | filters.PHOTO | filters.Document.ALL) & ~filters.COMMAND,
        on_user_message
    ))

    print("[1/4] Nex Shop Store Bot running...")
    async with app:
        await app.start()
        await app.updater.start_polling(allowed_updates=Update.ALL_TYPES)
        await asyncio.Event().wait()
        await app.updater.stop()
        await app.stop()

if __name__ == "__main__":
    asyncio.run(run_store_bot())
