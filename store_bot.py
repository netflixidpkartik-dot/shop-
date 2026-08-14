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
from translations import T

STORE_BOT_TOKEN = os.environ.get("STORE_TOKEN", "")
ADMIN_IDS = [7908702029]
HTML = "HTML"

logging.basicConfig(format="%(asctime)s — %(levelname)s — %(message)s", level=logging.INFO)
logging.getLogger("httpx").setLevel(logging.WARNING)

# ══════════════════════════════════════════════════════
#  PREMIUM EMOJI — tg-emoji with Unicode fallback
# ══════════════════════════════════════════════════════

def e(emoji_id: str, fallback: str) -> str:
    """Return tg-emoji tag for animated premium emoji in message text."""
    return f'<tg-emoji emoji-id="{emoji_id}">{fallback}</tg-emoji>'

def _strip_tg_emoji(text: str) -> str:
    """Remove tg-emoji tags, keeping the Unicode fallback inside."""
    import re as _re
    return _re.sub(r'<tg-emoji emoji-id="[^"]*">([^<]*)</tg-emoji>', r'\1', text)

# UI — animated premium emoji
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
E_HOME      = e("5278702045883292456", "🏠")
E_SETTING   = e("5341715473882955310", "⚙️")
E_FILE      = e("5357315181649076022", "🗂")
E_LINK      = e("5271604874419647061", "🔗")
E_SUPPORT   = e("5393387289118260399", "🎧")
E_REFRESH   = e("5366043289633962337", "🔃")

# Products — real brand animated emoji
E_ADOBE       = e("5298773244101281960", "❤️")
E_CHATGPT     = e("5796185041717433060", "🤖")
E_GEMINI      = e("6178962311072456422", "✨")
E_ANTIGRAV    = e("5319095375783569775", "🌟")
E_HIGGSFIELD  = e("6201693472731176318", "🎬")
E_YOUTUBE     = e("5291892070837921372", "▶️")
E_CAPCUT      = e("6124915477706705232", "✂️")
E_CLAUDE      = e("6174520215376763867", "🧠")
E_CURSOR      = e("6273793612715138423", "⚡")
E_LOVABLE     = e("6104729848675050039", "💜")
E_KLING       = e("6177161027558316737", "🎥")
E_SUNO        = e("5319101195464252717", "🎵")
E_PERPLEXITY  = e("5319118925089249250", "🔍")
E_HEYGEN      = e("5440613014338318469", "📹")
E_KREA        = e("6177161027558316737", "🎨")
E_GROK        = e("6179337489350663129", "🤔")
E_GAMMA       = e("5359320531944358335", "🛒")
E_FIGMA       = e("5393312805795407636", "🖌️")
E_MANUS       = e("6041825714708166055", "✨")

def clean_name(name: str) -> str:
    """Strip leading emoji characters from product name."""
    import re
    return re.sub(r'^[\U0001F000-\U0001FFFF\U00002600-\U000027BF\U0001F900-\U0001F9FF\u2702-\u27B0\u231A-\u231B\u23E9-\u23F3\u23F8-\u23FA\u25AA-\u25FE\u2614-\u2615\u2648-\u2653\u267F\u2693\u26A1\u26AA-\u26AB\u26BD-\u26BE\u26C4-\u26C5\u26CE\u26D4\u26EA\u26F2-\u26F3\u26F5\u26FA\u26FD\u2702\u2705\u2708-\u270D\u270F\uFE0F\u20E3\u200D\U0001FA00-\U0001FA6F\U0001FA70-\U0001FAFF]+\s*', '', name).strip()

def product_emoji(name: str) -> str:
    n = name.lower()
    if "adobe"       in n: return E_ADOBE
    if "chatgpt"     in n: return E_CHATGPT
    if "gemini"      in n: return E_GEMINI
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
    if "grok"        in n: return E_GROK
    if "gamma"       in n: return E_GAMMA
    if "figma"       in n: return E_FIGMA
    if "manus"       in n: return E_MANUS
    return E_CRYPTO

# ══════════════════════════════════════════════════════
#  SAFE EDIT & SAFE REPLY
# ══════════════════════════════════════════════════════

async def safe_edit(q, text: str, reply_markup=None, parse_mode=HTML):
    """Safely edit the inline message or fallback to direct send.
    Fallback chain:
      1. HTML with tg-emoji (premium animated)
      2. HTML with tg-emoji stripped to Unicode fallback
      3. Plain text (no HTML)
      4. send_message to chat (new message)
    """
    if not q:
        return

    # Attempt 1: Full HTML with premium tg-emoji
    try:
        await q.edit_message_text(text, parse_mode=parse_mode, reply_markup=reply_markup)
        return
    except BadRequest as err:
        err_msg = str(err).lower()
        if "not modified" in err_msg:
            return
        logging.warning(f"safe_edit [1] tg-emoji failed: {err}")
    except Exception as err:
        logging.warning(f"safe_edit [1] exception: {err}")

    # Attempt 2: HTML with tg-emoji stripped to unicode fallback
    stripped = _strip_tg_emoji(text)
    try:
        await q.edit_message_text(stripped, parse_mode=parse_mode, reply_markup=reply_markup)
        return
    except BadRequest as err:
        if "not modified" in str(err).lower():
            return
        logging.warning(f"safe_edit [2] stripped-html failed: {err}")
    except Exception as err:
        logging.warning(f"safe_edit [2] exception: {err}")

    # Attempt 3: Plain text
    plain = re.sub(r'<[^>]+>', '', stripped)
    try:
        await q.edit_message_text(plain, parse_mode=None, reply_markup=reply_markup)
        return
    except Exception:
        pass

    # Attempt 4: Send directly to user chat
    try:
        chat_id = q.message.chat_id if q.message else q.from_user.id
        await q.get_bot().send_message(
            chat_id=chat_id,
            text=stripped,
            parse_mode=parse_mode,
            reply_markup=reply_markup
        )
    except Exception as ex:
        logging.error(f"safe_edit [4] send_message failed: {ex}")

async def safe_reply(message, text: str, reply_markup=None, parse_mode=HTML, **kwargs):
    """Safely send a reply message with tg-emoji, falling back gracefully."""
    if not message:
        return
    # Attempt 1: Full HTML with tg-emoji
    try:
        return await message.reply_text(text, parse_mode=parse_mode, reply_markup=reply_markup, **kwargs)
    except Exception as err:
        logging.warning(f"safe_reply [1] error: {err}")
    # Attempt 2: Strip tg-emoji tags, keep unicode fallback
    stripped = _strip_tg_emoji(text)
    try:
        return await message.reply_text(stripped, parse_mode=parse_mode, reply_markup=reply_markup, **kwargs)
    except Exception as err:
        logging.warning(f"safe_reply [2] error: {err}")
    # Attempt 3: Plain text
    plain = re.sub(r'<[^>]+>', '', stripped)
    try:
        return await message.reply_text(plain, parse_mode=None, reply_markup=reply_markup, **kwargs)
    except Exception as ex:
        logging.error(f"safe_reply [3] plain error: {ex}")

# ══════════════════════════════════════════════════════
#  KEYBOARDS
# ══════════════════════════════════════════════════════

def kb_main(lang="en"):
    return InlineKeyboardMarkup([
        [InlineKeyboardButton(T(lang,"btn_buy"),      callback_data="menu_buy")],
        [InlineKeyboardButton(T(lang,"btn_profile"),  callback_data="menu_profile"),
         InlineKeyboardButton(T(lang,"btn_history"),  callback_data="menu_orders")],
        [InlineKeyboardButton(T(lang,"btn_wallet"),   callback_data="menu_wallet"),
         InlineKeyboardButton(T(lang,"btn_reflink"),  callback_data="menu_reflink")],
        [InlineKeyboardButton(T(lang,"btn_support"),  callback_data="menu_support")],
        [InlineKeyboardButton(T(lang,"btn_language"), callback_data="menu_language")],
    ])

def kb_back_main(lang="en"):
    return InlineKeyboardMarkup([
        [InlineKeyboardButton(T(lang,"btn_back_main"), callback_data="menu_home")]
    ])

def kb_products(products):
    rows = []
    for p in products:
        name = clean_name(p["name"])
        # product_emoji() returns a tg-emoji tag — strip it to get just the unicode fallback for button label
        raw_emoji = product_emoji(name)
        unicode_emoji = re.sub(r'<tg-emoji emoji-id="[^"]*">([^<]*)</tg-emoji>', r'\1', raw_emoji)
        label = f"{unicode_emoji} {name}"
        if len(label) > 52:
            label = label[:50] + "…"
        rows.append([InlineKeyboardButton(label, callback_data=f"view_p_{p['id']}")])
    rows.append([InlineKeyboardButton("🔃 Refresh", callback_data="menu_buy"),
                 InlineKeyboardButton("🏠 Main menu", callback_data="menu_home")])
    return InlineKeyboardMarkup(rows)

def kb_product_detail(pid):
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("✅ Buy now", callback_data=f"buy_p_{pid}_1")],
        [InlineKeyboardButton("↩️ Back to catalog", callback_data="menu_buy")],
    ])

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
    lang = db.get_user_lang(user.id)
    bot_info = await ctx.bot.get_me()
    ctx.bot_data["username"] = bot_info.username

    welcome_text = f"{E_CONGRATS} Welcome to <b>Nex Shop</b>! {E_CART}\n\nPlease choose an option below:"
    await safe_reply(
        update.message,
        welcome_text,
        reply_markup=kb_main(lang)
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
        return

    bot_user = ctx.bot_data.get("username")
    if not bot_user:
        b = await ctx.bot.get_me()
        bot_user = b.username
        ctx.bot_data["username"] = bot_user

    u_data = db.get_user(user.id) or db.get_or_create_user(
        user.id, user.first_name, user.username or "")
    lang = db.get_user_lang(user.id)

    # ── HOME ─────────────────────────────────────────
    if data == "menu_home":
        ctx.user_data.clear()
        lang = db.get_user_lang(user.id)
        welcome_text = f"{E_CONGRATS} Welcome to <b>Nex Shop</b>! {E_CART}\n\nPlease choose an option below:"
        await safe_edit(q, welcome_text, reply_markup=kb_main(lang), parse_mode=HTML)

    # ── BUY / CATALOG ─────────────────────────────────
    elif data == "menu_buy":
        products = db.get_all_products(active_only=True)
        if not products:
            await safe_edit(q, f"{E_CROSS} No products available.", reply_markup=kb_back_main(lang))
            return
        await safe_edit(q, f"{E_CART} <b>Products Catalog</b>\n\n{E_CRYPTO} Select a product below to purchase:", reply_markup=kb_products(products))

    # ── PRODUCT DETAIL ────────────────────────────────
    elif data.startswith("view_p_"):
        pid = int(data.replace("view_p_", ""))
        p = db.get_product(pid)
        if not p or not p["active"]:
            await safe_edit(q, f"{E_CROSS} This product is unavailable.", reply_markup=kb_back_main(lang))
            return
        pemoji = product_emoji(p["name"])
        pname  = clean_name(p["name"])
        stock_txt = f"{E_CHECK} In stock ({p['stock']})" if p["stock"] > 0 else f"{E_CROSS} Out of stock"
        desc_line = ""
        if p.get("description"):
            desc_line = f"\n\n📝 <i>{p['description']}</i>"
        await safe_edit(
            q,
            f"{pemoji} <b>{pname}</b>\n\n"
            f"{E_DOLLAR} Price: <b>${p['price']:.2f}</b>\n"
            f"{E_CART} Stock: {stock_txt}\n"
            f"⏱ Delivery: <b>5–10 minutes</b>\n\n"
            f"{E_USDT} Your balance: <b>${u_data['balance']:.2f}</b>"
            + desc_line,
            reply_markup=kb_product_detail(pid)
        )

    # ── PURCHASE ──────────────────────────────────────
    elif data.startswith("buy_p_"):
        parts = data.split("_")
        pid   = int(parts[2])
        qty   = int(parts[3]) if len(parts) > 3 else 1
        p = db.get_product(pid)

        if not p or not p["active"]:
            await safe_edit(q, f"{E_CROSS} <b>Product unavailable.</b>", reply_markup=kb_back_main(lang))
            return
        if p["stock"] < qty:
            await safe_edit(q, f"{E_CROSS} <b>Out of stock!</b>\n\nThis item is currently sold out.", reply_markup=kb_back_main(lang))
            return

        total_cost = p["price"] * qty
        fresh_user = db.get_user(user.id)
        current_balance = (fresh_user["balance"] if fresh_user else 0.0) or 0.0

        # Insufficient Balance Screen
        if current_balance < total_cost:
            deficit = round(total_cost - current_balance, 2)
            pname = clean_name(p["name"])
            pemoji = product_emoji(p["name"])
            insufficient_text = (
                f"{E_CROSS} <b>Insufficient Balance!</b>\n\n"
                f"{pemoji} <b>{pname}</b>\n"
                f"{E_DOLLAR} Cost: <b>${total_cost:.2f}</b>\n"
                f"{E_USDT} Your Balance: <b>${current_balance:.2f}</b>\n"
                f"{E_ADD} Needed: <b>${deficit:.2f} more</b>\n\n"
                f"<i>Please top up your wallet to place this order.</i>"
            )
            insufficient_kb = InlineKeyboardMarkup([
                [InlineKeyboardButton("💳 Top up Wallet", callback_data="menu_wallet")],
                [InlineKeyboardButton("↩️ Back to Product", callback_data=f"view_p_{pid}"),
                 InlineKeyboardButton("🛍️ Catalog", callback_data="menu_buy")],
            ])
            await safe_edit(q, insufficient_text, reply_markup=insufficient_kb)
            return

        if not db.deduct_balance(user.id, total_cost):
            await safe_edit(q, f"{E_CROSS} <b>Balance error. Please retry.</b>", reply_markup=kb_back_main(lang))
            return

        try:
            order_res = db.create_order(user.id, pid, qty)
        except Exception as e:
            logging.error(f"create_order error: {e}")
            db.add_balance(user.id, total_cost)
            await safe_edit(q, f"{E_CROSS} <b>Order error. Balance refunded.</b>", reply_markup=kb_back_main(lang))
            return

        if not order_res:
            db.add_balance(user.id, total_cost)
            await safe_edit(q, f"{E_CROSS} <b>Out of stock. Balance refunded.</b>", reply_markup=kb_back_main(lang))
            return

        ref, prod_name, total_price, dtype, dcontent = order_res
        db.maybe_pay_referral_commission(user.id, total_cost)
        new_bal = current_balance - total_cost

        pname = clean_name(prod_name)
        pemoji = product_emoji(prod_name)
        confirm_text = (
            f"{E_CONGRATS} <b>Order Placed Successfully!</b> {E_CHECK}\n\n"
            f"{pemoji} <b>{pname}</b>\n"
            f"{E_DOLLAR} Paid: <b>${total_price:.2f}</b>\n"
            f"{E_USDT} New Balance: <b>${new_bal:.2f}</b>\n\n"
            f"{E_FILE} <b>Order ID:</b> <code>{ref}</code>\n\n"
            f"⏱ <b>Kindly wait for your order.</b> It will be delivered within <b>5–10 minutes</b>.\n\n"
            f"📩 <i>If still not received, contact @NexIndo with your Order ID.</i>"
        )
        confirm_kb = InlineKeyboardMarkup([
            [InlineKeyboardButton("🗂 Purchase history", callback_data="menu_orders")],
            [InlineKeyboardButton("🛍 Keep Shopping",    callback_data="menu_buy"),
             InlineKeyboardButton("🏠 Main Menu",        callback_data="menu_home")],
        ])

        # 1. Update current card
        await safe_edit(q, confirm_text, reply_markup=confirm_kb)

        # 2. Also send as new message to chat
        try:
            await ctx.bot.send_message(
                chat_id=user.id,
                text=confirm_text,
                parse_mode=HTML,
                reply_markup=confirm_kb
            )
        except Exception as err:
            logging.error(f"Confirmation send_message error: {err}")

    # ── PROFILE ─────────────────────────────────
    elif data == "menu_profile":
        uname = f"@{user.username}" if user.username else user.first_name
        total_spent = db.get_user_total_spent(user.id)
        total_deposited = db.get_user_total_deposited(user.id)
        ref_count = u_data.get('referral_count', 0)
        ref_link = f"https://t.me/{bot_user}?start=ref_{user.id}"
        await safe_edit(
            q,
            f"{E_SETTING} <b>Customer Profile</b>\n\n"
            f"{E_SETTING} Name: <b>{uname}</b>\n"
            f"{E_USDT} Balance: <b>${u_data['balance']:.2f}</b>\n"
            f"{E_DOLLAR} Total deposited: <b>${total_deposited:.2f}</b>\n"
            f"{E_GROWTH} Total spent: <b>${total_spent:.2f}</b>\n"
            f"{E_LINK} Referrals: <b>{ref_count}</b>\n\n"
            f"{E_LINK} <b>Your referral link:</b>\n<code>{ref_link}</code>",
            reply_markup=kb_back_main(lang)
        )

    # ── REFERRAL LINK ─────────────────────────────
    elif data == "menu_reflink":
        ref_link = f"https://t.me/{bot_user}?start=ref_{user.id}"
        ref_count = u_data.get('referral_count', 0)
        await safe_edit(
            q,
            f"{E_LINK} <b>Your Referral Link</b>\n\n"
            f"<code>{ref_link}</code>\n\n"
            f"{E_LINK} Referrals made: <b>{ref_count}</b>\n"
            f"{E_DOLLAR} Earn <b>10%</b> commission on every friend's first order!",
            reply_markup=kb_back_main(lang)
        )

    # ── WALLET ─────────────────────────────────
    elif data == "menu_wallet":
        uname = f"@{user.username}" if user.username else user.first_name
        total_deposited = db.get_user_total_deposited(user.id)
        total_spent = db.get_user_total_spent(user.id)
        wallets = db.get_all_wallets()
        rows_kb = []
        icons = {"usdt_erc20":"🔵","usdt_bep20":"🟡","usdt_trc20":"🔴",
                 "btc":"₿","ton":"💎","ltc":"⚪"}
        for w in wallets:
            if w["active"]:
                ico = icons.get(w["key"], "💳")
                rows_kb.append([InlineKeyboardButton(
                    f"{ico} Top up {w['label']}", callback_data=f"dep_w_{w['key']}")
                ])
        rows_kb.append([InlineKeyboardButton("🔃 Refresh balance", callback_data="menu_wallet"),
                        InlineKeyboardButton("🏠 Main menu", callback_data="menu_home")])
        await safe_edit(
            q,
            f"{E_USDT} <b>My Wallet</b> {E_CRYPTO}\n\n"
            f"{E_USDT} Balance: <b>${u_data['balance']:.2f}</b>\n"
            f"{E_DOLLAR} Total deposited: <b>${total_deposited:.2f}</b>\n"
            f"{E_GROWTH} Total spent: <b>${total_spent:.2f}</b>\n\n"
            f"{E_USDT} <b>Select a network below to top up:</b>",
            reply_markup=InlineKeyboardMarkup(rows_kb)
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
            f"{E_CRYPTO} <b>{w['label']} Receiving Address:</b>\n"
            f"<code>{w['address']}</code>\n\n"
            f"⚠️ Allowed difference: 0.02 USDT. Please send exact amount (include network fees).\n\n"
            f"📩 After transfer, send the <b>TxID or screenshot</b> in this chat for verification.",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("🏠 Back to wallet", callback_data="menu_wallet")]
            ])
        )

    # ── PURCHASE HISTORY ──────────────────────────────
    elif data == "menu_orders":
        orders = db.get_user_orders(user.id, limit=15)
        if not orders:
            await safe_edit(q, f"{E_FILE} <b>Purchase history</b>\n\nNo purchases registered yet.",
                            reply_markup=kb_back_main(lang))
            return
        lines = []
        for o in orders:
            icon = E_CHECK if o["status"] == "delivered" else "⏳"
            status_label = "Delivered" if o["status"] == "delivered" else "Processing (5-10m)"
            date = o["created_at"][:16]
            pemoji = product_emoji(o["prod_name"])
            pname = clean_name(o["prod_name"])
            lines.append(
                f"{icon} {pemoji} <b>{pname}</b>\n"
                f"   {E_FILE} <code>{o['ref']}</code> | {E_DOLLAR} <b>${o['price']:.2f}</b>\n"
                f"   📅 {date} | <i>{status_label}</i>"
            )
        await safe_edit(
            q,
            f"{E_FILE} <b>Purchase history</b>\n\n" + "\n\n".join(lines),
            reply_markup=kb_back_main(lang)
        )

    # ── SUPPORT ───────────────────────────────────────
    elif data == "menu_support":
        await safe_edit(
            q,
            f"{E_SUPPORT} <b>Nex Shop Support</b> {E_SHIELD}\n\n"
            f"{E_SUPPORT} Need help with an order, deposit, or have questions?\n\n"
            f"{E_TG} Official Support: @NexIndo\n"
            f"⏱ Fast response within minutes!",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("💬 Contact @NexIndo", url="https://t.me/NexIndo")],
                [InlineKeyboardButton("🏠 Back to main menu", callback_data="menu_home")],
            ])
        )

    # ── LANGUAGE ─────────────────────────────────────
    elif data == "menu_language":
        await safe_edit(
            q,
            f"{E_GLOBE} <b>Choose Language / 选择语言:</b>",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("🇨🇳 Chinese",    callback_data="lang_zh"),
                 InlineKeyboardButton("🇷🇺 Russian",    callback_data="lang_ru")],
                [InlineKeyboardButton("🇻🇳 Vietnamese", callback_data="lang_vi"),
                 InlineKeyboardButton("🇳🇬 Nigerian",   callback_data="lang_ng")],
                [InlineKeyboardButton("🇺🇸 English",     callback_data="lang_en")],
                [InlineKeyboardButton(T(lang,"btn_back_main"), callback_data="menu_home")],
            ])
        )

    elif data.startswith("lang_"):
        new_lang = data.replace("lang_", "")
        db.set_user_lang(user.id, new_lang)
        welcome_text = f"{E_CONGRATS} Welcome to <b>Nex Shop</b>! {E_CART}\n\nPlease choose an option below:"
        await safe_edit(q, welcome_text,
                        reply_markup=kb_main(new_lang), parse_mode=HTML)

    # ── API ───────────────────────────────────────────
    elif data == "menu_api":
        await safe_edit(
            q,
            f"🔗 <b>API Link</b>\n\n"
            f"Your user API key:\n<code>nex_{user.id}</code>\n\n"
            f"<i>Contact @NexIndo for API integration support.</i>",
            reply_markup=kb_back_main(lang)
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
            f"{E_FILE} Ref: <code>{ref}</code>\n"
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
