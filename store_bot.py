#!/usr/bin/env python3
"""store_bot.py — Customer store with multi-language support. Bugs fixed."""

import asyncio, logging, os
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application, CommandHandler, CallbackQueryHandler,
    MessageHandler, filters, ContextTypes,
)
from telegram.error import BadRequest
import shared_db as db
from translations import t, LANGS

STORE_BOT_TOKEN = os.environ["STORE_TOKEN"]
BOT_NAME        = os.environ.get("BOT_NAME", "Anan Shop")
SUPPORT         = os.environ.get("SUPPORT_USERNAME", "@AnanAiShop")

HTML = "HTML"
logging.basicConfig(format="%(asctime)s — %(levelname)s — %(message)s", level=logging.INFO)
logging.getLogger("httpx").setLevel(logging.WARNING)

def L(uid): return db.get_lang(uid)

async def safe_ans(q, text="", alert=False):
    try: await q.answer(text, show_alert=alert)
    except BadRequest: pass

# ══════════════════════════════════════════════════════
#  KEYBOARDS
# ══════════════════════════════════════════════════════

def kb_main(lang="en"):
    return InlineKeyboardMarkup([
        [InlineKeyboardButton(t("btn_products",lang),  callback_data="products"),
         InlineKeyboardButton(t("btn_redeem",lang),    callback_data="redeem")],
        [InlineKeyboardButton(t("btn_profile",lang),   callback_data="profile"),
         InlineKeyboardButton(t("btn_orders",lang),    callback_data="history")],
        [InlineKeyboardButton(t("btn_wallet",lang),    callback_data="wallet")],
        [InlineKeyboardButton(t("btn_support",lang),   callback_data="support"),
         InlineKeyboardButton(t("btn_language",lang),  callback_data="language")],
    ])

def kb_back_main(lang="en"):
    return InlineKeyboardMarkup([[InlineKeyboardButton(t("btn_main_menu",lang), callback_data="main_menu")]])

def kb_products(products, lang="en"):
    rows = []
    for p in products:
        rows.append([InlineKeyboardButton(
            f"📦 {p['name']}  |  ${p['price']:.2f}  |  {p['stock']} left",
            callback_data=f"acc_{p['id']}")])
    rows.append([InlineKeyboardButton(t("btn_refresh",lang), callback_data="products"),
                 InlineKeyboardButton(t("btn_main_menu",lang), callback_data="main_menu")])
    return InlineKeyboardMarkup(rows)

def kb_product_detail(pid, lang="en"):
    return InlineKeyboardMarkup([
        [InlineKeyboardButton(t("btn_order_now",lang), callback_data=f"order_start_{pid}")],
        [InlineKeyboardButton(t("btn_back",lang),      callback_data="products"),
         InlineKeyboardButton(t("btn_main_menu",lang), callback_data="main_menu")],
    ])

def kb_qty(pid, price, stock, lang="en"):
    qtys  = [1, 2, 3, 5, 10]
    valid = [q for q in qtys if q <= stock]
    rows  = []
    row   = []
    for q in valid:
        row.append(InlineKeyboardButton(f"{q}  (${price*q:.2f})", callback_data=f"qty_{pid}_{q}"))
        if len(row) == 3: rows.append(row); row = []
    if row: rows.append(row)
    rows.append([InlineKeyboardButton(t("btn_custom_qty",lang), callback_data=f"qty_custom_{pid}")])
    rows.append([InlineKeyboardButton(t("btn_cancel",lang),     callback_data=f"acc_{pid}")])
    return InlineKeyboardMarkup(rows)

def kb_confirm_order(pid, qty, total, lang="en"):
    return InlineKeyboardMarkup([
        [InlineKeyboardButton(f"✅ {t('btn_confirm',lang)}  (${total:.2f})",
                              callback_data=f"co_{pid}_{qty}")],  # ← shorter prefix, no ambiguity
        [InlineKeyboardButton(t("btn_cancel",lang), callback_data="products")],
    ])

def kb_wallet(lang="en"):
    return InlineKeyboardMarkup([
        [InlineKeyboardButton(t("btn_deposit",lang),   callback_data="deposit_menu")],
        [InlineKeyboardButton(t("btn_main_menu",lang), callback_data="main_menu")],
    ])

def kb_networks(wallets, lang="en"):
    rows = [[InlineKeyboardButton(label, callback_data=f"pay_net_{key}")]
            for key, (label, _) in wallets.items()]
    rows.append([InlineKeyboardButton(t("btn_cancel",lang), callback_data="wallet")])
    return InlineKeyboardMarkup(rows)

def kb_sent(key, lang="en"):
    return InlineKeyboardMarkup([
        [InlineKeyboardButton(t("btn_sent",lang),       callback_data=f"sent_{key}")],
        [InlineKeyboardButton(t("btn_change_net",lang), callback_data="deposit_menu")],
    ])

def kb_language():
    rows = [[InlineKeyboardButton(label, callback_data=f"setlang_{code}")]
            for code, label in LANGS.items()]
    rows.append([InlineKeyboardButton("🏠 Main Menu", callback_data="main_menu")])
    return InlineKeyboardMarkup(rows)

# ══════════════════════════════════════════════════════
#  HANDLERS
# ══════════════════════════════════════════════════════

async def cmd_start(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    db.ensure_user(user.id, user.first_name, user.username or "")
    lang = L(user.id)
    await update.message.reply_text(
        t("welcome", lang, bot=BOT_NAME, name=user.first_name),
        parse_mode=HTML, reply_markup=kb_main(lang))

async def on_callback(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    q    = update.callback_query
    data = q.data
    uid  = update.effective_user.id
    name = update.effective_user.first_name
    uname = update.effective_user.username or ""
    db.ensure_user(uid, name, uname)
    lang = L(uid)
    await safe_ans(q)

    # ── Main menu ──────────────────────────────────────
    if data == "main_menu":
        await q.edit_message_text("🏠", parse_mode=HTML, reply_markup=kb_main(lang))

    # ── Language picker ────────────────────────────────
    elif data == "language":
        await q.edit_message_text(t("lang_title",lang), parse_mode=HTML, reply_markup=kb_language())

    elif data.startswith("setlang_"):
        new_lang = data[8:]
        db.set_lang(uid, new_lang)
        lang = new_lang
        await q.edit_message_text(
            t("lang_set", lang),
            parse_mode=HTML, reply_markup=kb_main(lang))

    # ── Products ───────────────────────────────────────
    elif data == "products":
        prods = db.get_active_products()
        if not prods:
            await q.edit_message_text(t("no_products",lang), reply_markup=kb_back_main(lang)); return
        await q.edit_message_text(t("products_title",lang), parse_mode=HTML,
                                  reply_markup=kb_products(prods, lang))

    # ── Product detail ─────────────────────────────────
    elif data.startswith("acc_"):
        pid = int(data[4:])
        p   = db.get_product(pid)
        if not p: await safe_ans(q, "Not found.", alert=True); return
        text = (
            f"📦 <b>{p['name']}</b>\n"
            f"━━━━━━━━━━━━━━━━━━━━━━━━\n"
            f"{t('price_per_unit',lang)} : <b>${p['price']:.2f} USDT</b>\n"
            f"{t('stock_avail',lang)}    : <b>{p['stock']}</b>\n"
            f"{t('in_stock',lang)}"
        )
        await q.edit_message_text(text, parse_mode=HTML, reply_markup=kb_product_detail(pid, lang))

    # ── Start order ────────────────────────────────────
    elif data.startswith("order_start_"):
        pid = int(data[12:])
        p   = db.get_product(pid)
        if not p: await safe_ans(q, "Not found.", alert=True); return
        if p["stock"] < 1:
            await safe_ans(q, t("out_of_stock",lang), alert=True); return
        await q.edit_message_text(
            f"📦 <b>{p['name']}</b>\n\n"
            f"{t('price_per_unit',lang)}: <b>${p['price']:.2f}</b>\n"
            f"{t('max_avail',lang)}: <b>{p['stock']}</b>\n\n"
            f"{t('how_many',lang)}\n"
            f"<i>{t('tap_or_custom',lang)}</i>",
            parse_mode=HTML, reply_markup=kb_qty(pid, p["price"], p["stock"], lang))

    # ── Quick qty selected ─────────────────────────────
    elif data.startswith("qty_") and not data.startswith("qty_custom_"):
        parts = data.split("_")   # qty_PID_QTY
        pid   = int(parts[1])
        qty   = int(parts[2])
        await _show_order_summary(q, uid, pid, qty, lang)

    # ── Custom qty ─────────────────────────────────────
    elif data.startswith("qty_custom_"):
        pid = int(data[11:])
        p   = db.get_product(pid)
        if not p: return
        ctx.user_data["state"]     = "awaiting_qty"
        ctx.user_data["order_pid"] = pid
        await q.edit_message_text(
            f"{t('enter_qty',lang)}\n\n"
            f"📦 <b>{p['name']}</b>  —  ${p['price']:.2f}\n"
            f"{t('max_avail',lang)}: <b>{p['stock']}</b>",
            parse_mode=HTML,
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton(t("btn_cancel",lang), callback_data=f"acc_{pid}")
            ]]))

    # ── FIX: use "co_PID_QTY" prefix (no extra underscores) ──
    elif data.startswith("co_"):
        # co_PID_QTY  — split only on first two underscores
        rest  = data[3:]                   # "12_3"
        parts = rest.split("_", 1)
        pid   = int(parts[0])
        qty   = int(parts[1])
        await _place_order(q, ctx, uid, pid, qty, lang)

    # ── Wallet ─────────────────────────────────────────
    elif data == "wallet":
        bal = db.get_balance(uid)
        await q.edit_message_text(
            f"{t('wallet_title',lang)}\n\n"
            f"{t('wallet_bal',lang,bal=f'{bal:.2f}')}\n\n"
            f"{t('wallet_note',lang)}",
            parse_mode=HTML, reply_markup=kb_wallet(lang))

    # ── Deposit network ────────────────────────────────
    elif data == "deposit_menu":
        wallets = db.get_active_wallets()
        await q.edit_message_text(
            t("deposit_title",lang), parse_mode=HTML, reply_markup=kb_networks(wallets, lang))

    # ── Show address ───────────────────────────────────
    elif data.startswith("pay_net_"):
        key = data[8:]
        wallets = db.get_active_wallets()
        if key not in wallets:
            await safe_ans(q, "Network unavailable.", alert=True); return
        label, addr = wallets[key]
        ctx.user_data["dep_network"]       = key
        ctx.user_data["dep_network_label"] = label
        await q.edit_message_text(
            t("deposit_addr", lang, net=label, addr=addr),
            parse_mode=HTML, reply_markup=kb_sent(key, lang))

    # ── User tapped "I Have Sent" ──────────────────────
    elif data.startswith("sent_"):
        ctx.user_data["state"]       = "awaiting_txn"
        ctx.user_data["dep_ref"]     = db.new_ref("DEP")
        ctx.user_data["dep_network"] = ctx.user_data.get(
            "dep_network_label", ctx.user_data.get("dep_network","Unknown"))
        await q.edit_message_text(
            t("enter_txn", lang), parse_mode=HTML,
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton(t("btn_cancel",lang), callback_data="wallet")
            ]]))

    # ── Profile ────────────────────────────────────────
    elif data == "profile":
        row    = db.get_user_info(uid)
        orders = db.get_orders(uid)
        if row:
            n, uname2, created_at, balance = row
            text = (
                f"{t('profile_title',lang)}\n"
                f"━━━━━━━━━━━━━━━━━━━━━━━━\n"
                f"🆔 ID       : <code>{uid}</code>\n"
                f"👤 Name     : <b>{n}</b>\n"
                f"📛 Username : {'@'+uname2 if uname2 else '—'}\n"
                f"📅 Joined   : {(created_at or '')[:10]}\n"
                f"💰 Balance  : <b>${balance:.2f} USDT</b>\n"
                f"📦 Orders   : <b>{len(orders)}</b>"
            )
            await q.edit_message_text(text, parse_mode=HTML,
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton(t("btn_deposit",lang), callback_data="deposit_menu")],
                    [InlineKeyboardButton(t("btn_main_menu",lang), callback_data="main_menu")],
                ]))

    # ── History ────────────────────────────────────────
    elif data == "history":
        orders = db.get_orders(uid)
        if not orders:
            txt = t("no_orders", lang)
        else:
            lines = []
            for ref, pname, price, qty, status, created in orders[:20]:
                icon = "✅" if status == "delivered" else "⏳"
                lines.append(f"{icon} <code>{ref}</code>\n   📦 {pname} × {qty} — ${price:.2f}\n   📅 {created}")
            txt = t("orders_title",lang) + "\n\n" + "\n\n".join(lines)
        await q.edit_message_text(txt, parse_mode=HTML, reply_markup=kb_back_main(lang))

    # ── Redeem ─────────────────────────────────────────
    elif data == "redeem":
        ctx.user_data["state"] = "awaiting_redeem"
        await q.edit_message_text(
            t("redeem_prompt",lang), parse_mode=HTML,
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton(t("btn_cancel",lang), callback_data="main_menu")
            ]]))

    # ── Support ────────────────────────────────────────
    elif data == "support":
        await q.edit_message_text(
            t("support_text",lang,support=SUPPORT),
            parse_mode=HTML, reply_markup=kb_back_main(lang))


# ══════════════════════════════════════════════════════
#  ORDER HELPERS
# ══════════════════════════════════════════════════════

async def _show_order_summary(q, uid, pid, qty, lang):
    p = db.get_product(pid)
    if not p: await safe_ans(q, "Not found.", alert=True); return
    if qty > p["stock"]:
        await safe_ans(q, f"Only {p['stock']} left!", alert=True); return
    total = round(p["price"] * qty, 4)
    await q.edit_message_text(
        f"{t('order_summary',lang)}\n\n"
        f"{t('product_label',lang)} : <b>{p['name']}</b>\n"
        f"{t('quantity_label',lang)}: <b>{qty}</b>\n"
        f"{t('price_ea',lang)}      : <b>${p['price']:.2f}</b>\n"
        f"━━━━━━━━━━━━━━━━━━━━━━━━\n"
        f"{t('total_label',lang)}   : <b>${total:.2f} USDT</b>\n\n"
        f"{t('your_balance',lang)}: <b>${db.get_balance(uid):.2f} USDT</b>",
        parse_mode=HTML,
        reply_markup=kb_confirm_order(pid, qty, total, lang))

async def _place_order(q, ctx, uid, pid, qty, lang):
    """FIX: called from co_ callback. All errors handled here."""
    p = db.get_product(pid)
    if not p:
        await q.edit_message_text("❌ Product not found.", reply_markup=kb_back_main(lang)); return
    if qty < 1 or qty > p["stock"]:
        await safe_ans(q, f"Stock: {p['stock']}. Invalid qty.", alert=True); return

    total   = round(p["price"] * qty, 4)
    balance = db.get_balance(uid)

    if balance < total:
        needed = round(total - balance, 4)
        await q.edit_message_text(
            f"{t('insuf_bal',lang)}\n\n"
            f"{t('order_total',lang)} : <b>${total:.2f} USDT</b>\n"
            f"👛 {t('bal_label',lang)}: <b>${balance:.2f} USDT</b>\n"
            f"━━━━━━━━━━━━━━━━━━━━━━━━\n"
            f"{t('need_more',lang,n=f'${needed:.2f} USDT')}",
            parse_mode=HTML,
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton(t("btn_deposit",lang),   callback_data="deposit_menu")],
                [InlineKeyboardButton(t("btn_main_menu",lang), callback_data="main_menu")],
            ])); return

    # ── All good — place order ──────────────────────────
    db.deduct_balance(uid, total)
    order_ref = db.new_ref("TG")
    db.save_order(uid, p, order_ref, qty)
    db.reduce_stock(pid, qty)
    new_bal = db.get_balance(uid)

    await q.edit_message_text(
        f"{t('order_placed',lang)}\n\n"
        f"{t('product_label',lang)} : <b>{p['name']}</b>\n"
        f"{t('quantity_label',lang)}: <b>{qty}</b>\n"
        f"{t('total_label',lang)}   : <b>${total:.2f} USDT</b>\n"
        f"{t('order_ref',lang)}     : <code>{order_ref}</code>\n"
        f"{t('bal_label',lang)}     : <b>${new_bal:.2f} USDT</b>\n\n"
        f"{t('delivery_note',lang,support=SUPPORT)}",
        parse_mode=HTML,
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton(t("btn_history",lang),  callback_data="history")],
            [InlineKeyboardButton(t("btn_continue",lang), callback_data="products")],
        ]))


# ══════════════════════════════════════════════════════
#  MESSAGE HANDLER
# ══════════════════════════════════════════════════════

async def on_text(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    uid   = update.effective_user.id
    name  = update.effective_user.first_name
    uname = update.effective_user.username or ""
    text  = (update.message.text or "").strip()
    state = ctx.user_data.get("state")
    db.ensure_user(uid, name, uname)
    lang = L(uid)

    # ── Custom quantity ────────────────────────────────
    if state == "awaiting_qty":
        pid = ctx.user_data.get("order_pid")
        p   = db.get_product(pid) if pid else None
        if not p:
            ctx.user_data.pop("state", None)
            await update.message.reply_text("⚠️ Product not found.", reply_markup=kb_back_main(lang)); return
        try:
            qty = int(text)
            if qty < 1: raise ValueError
        except ValueError:
            await update.message.reply_text(t("invalid_qty",lang)); return
        if qty > p["stock"]:
            await update.message.reply_text(t("stock_limit",lang,n=p["stock"])); return
        ctx.user_data.pop("state",None); ctx.user_data.pop("order_pid",None)
        total = round(p["price"] * qty, 4)
        await update.message.reply_text(
            f"{t('order_summary',lang)}\n\n"
            f"{t('product_label',lang)} : <b>{p['name']}</b>\n"
            f"{t('quantity_label',lang)}: <b>{qty}</b>\n"
            f"{t('price_ea',lang)}      : <b>${p['price']:.2f}</b>\n"
            f"━━━━━━━━━━━━━━━━━━━━━━━━\n"
            f"{t('total_label',lang)}   : <b>${total:.2f} USDT</b>\n\n"
            f"{t('your_balance',lang)}: <b>${db.get_balance(uid):.2f} USDT</b>",
            parse_mode=HTML,
            reply_markup=kb_confirm_order(pid, qty, total, lang))

    # ── TXN ID ─────────────────────────────────────────
    elif state == "awaiting_txn":
        ctx.user_data.pop("state",None)
        ref     = ctx.user_data.pop("dep_ref", db.new_ref("DEP"))
        network = ctx.user_data.pop("dep_network","Unknown")
        db.save_deposit_txn(uid, ref, network, text)
        await update.message.reply_text(
            t("dep_submitted",lang,txn=text,ref=ref),
            parse_mode=HTML, reply_markup=kb_back_main(lang))

    # ── Redeem code ────────────────────────────────────
    elif state == "awaiting_redeem":
        ctx.user_data.pop("state",None)
        amount, msg = db.try_redeem(uid, text)
        if amount:
            await update.message.reply_text(
                t("redeem_ok",lang,amount=f"{amount:.2f}",bal=f"{db.get_balance(uid):.2f}"),
                parse_mode=HTML, reply_markup=kb_back_main(lang))
        else:
            await update.message.reply_text(msg, reply_markup=kb_back_main(lang))


async def run():
    db.init_db()
    app = Application.builder().token(STORE_BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", cmd_start))
    app.add_handler(CallbackQueryHandler(on_callback))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, on_text))
    print("✅ Store Bot running...")
    async with app:
        await app.start()
        await app.updater.start_polling(allowed_updates=Update.ALL_TYPES)
        await asyncio.Event().wait()
        await app.updater.stop()
        await app.stop()

if __name__ == "__main__":
    asyncio.run(run())
