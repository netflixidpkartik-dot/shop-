#!/usr/bin/env python3
"""
admin_payments_bot.py — Crypto Deposit Verification & Balance Approvals
Features:
- Real-time pending deposit alerts with TXN Hash lookup
- 1-Click balance credit & auto DM to client via Store Bot
- Rejection handler with error feedback
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

PAYMENTS_BOT_TOKEN = os.environ.get("PAYMENTS_TOKEN", "")
STORE_BOT_TOKEN    = os.environ.get("STORE_TOKEN", "")
ADMIN_IDS          = [7908702029]
NOTIFY_INTERVAL    = 10

HTML = "HTML"
logging.basicConfig(format="%(asctime)s — %(levelname)s — %(message)s", level=logging.INFO)
logging.getLogger("httpx").setLevel(logging.WARNING)

def e(eid, fallback=""):
    return f'<tg-emoji emoji-id="{eid}">{fallback}</tg-emoji>'

E_CRYPTO   = e("6314536973860084922", "💎")
E_CONGRATS = e("5461151367559141950", "🎉")
E_CART     = e("5312361253610475399", "🛒")
E_CHECK    = e("5206607081334906820", "✅")
E_USDT     = e("5935779811073989584", "💰")

def is_admin(uid):
    return uid in ADMIN_IDS

async def safe_ans(q, text="", alert=False):
    try:
        await q.answer(text, show_alert=alert)
    except BadRequest:
        pass

async def notify_customer(tg_id: int, text: str) -> bool:
    try:
        store = Bot(token=STORE_BOT_TOKEN)
        async with store:
            await store.send_message(tg_id, text, parse_mode=HTML)
        return True
    except TelegramError as e:
        logging.error(f"Notify client {tg_id} failed: {e}")
        return False

def kb_home():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("💰 Pending Deposits", callback_data="pay_pending"),
         InlineKeyboardButton("📊 Settlement Stats", callback_data="pay_stats")],
    ])

def kb_back_home():
    return InlineKeyboardMarkup([[InlineKeyboardButton("« 🏠 Payments Terminal", callback_data="pay_home")]])

def kb_proof_actions(dep_id, tg_id):
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("✅ Approve & Credit", callback_data=f"pay_approve_{dep_id}_{tg_id}"),
         InlineKeyboardButton("❌ Reject Transaction", callback_data=f"pay_reject_{dep_id}_{tg_id}")],
    ])

async def cmd_start(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id):
        await update.message.reply_text("⛔ Unauthorized.")
        return
    _, _, _, _, pd = db.get_stats()
    dash_text = (
        f"╭──────── 💳 <b>PAYMENTS & SETTLEMENT TERMINAL</b> ────────╮\n\n"
        f"⏳ <b>Pending Audits :</b> <code>{pd}</code>\n\n"
        f"⚡ <i>Client crypto deposits and hashes will alert instantly below.</i>\n\n"
        f"╰────────────────────────────────────────────────╯"
    )
    await update.message.reply_text(dash_text, parse_mode=HTML, reply_markup=kb_home())

async def on_callback(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    data = q.data
    uid = update.effective_user.id

    if not is_admin(uid):
        await safe_ans(q, "⛔ Unauthorized.", alert=True)
        return

    await safe_ans(q)

    if data == "pay_home":
        _, _, _, _, pd = db.get_stats()
        await q.edit_message_text(f"💳 <b>Payments Terminal</b>\n\nPending Verifications: <b>{pd}</b>", parse_mode=HTML, reply_markup=kb_home())

    elif data == "pay_pending":
        con = db._db()
        all_p = con.execute("""
            SELECT d.id, d.tg_id, d.ref, d.network, d.txn_id, d.created_at, u.name, u.username
            FROM deposits d LEFT JOIN users u ON d.tg_id=u.tg_id
            WHERE d.status='pending' ORDER BY d.id DESC LIMIT 20
        """).fetchall()
        con.close()

        if not all_p:
            await q.edit_message_text("✅ <b>All transactions settled. No pending deposits.</b>", parse_mode=HTML, reply_markup=kb_back_home())
            return

        rows = []
        for d in all_p:
            who = f"@{d['username']}" if d['username'] else str(d['tg_id'])
            rows.append([InlineKeyboardButton(
                f"💳 {d['ref']} • {d['name'] or who} • {d['network']}",
                callback_data=f"pay_view_{d['id']}_{d['tg_id']}")])
        rows.append([InlineKeyboardButton("« 🏠 Home", callback_data="pay_home")])

        await q.edit_message_text(f"💰 <b>Pending Top-ups ({len(all_p)})</b>", parse_mode=HTML, reply_markup=InlineKeyboardMarkup(rows))

    elif data.startswith("pay_view_"):
        rest = data[9:].split("_", 1)
        dep_id, tg_id = int(rest[0]), int(rest[1])
        con = db._db()
        d = con.execute("""
            SELECT d.id, d.tg_id, d.ref, d.network, d.txn_id, d.created_at, u.name, u.username
            FROM deposits d LEFT JOIN users u ON d.tg_id=u.tg_id WHERE d.id=?
        """, (dep_id,)).fetchone()
        con.close()

        if not d:
            await safe_ans(q, "Deposit not found.", alert=True)
            return

        who = f"@{d['username']}" if d['username'] else str(tg_id)
        card = (
            f"╭──────── 💳 <b>DEPOSIT AUDIT</b> ────────╮\n\n"
            f"📋 <b>Ref ID   :</b> <code>{d['ref']}</code>\n"
            f"👤 <b>Client   :</b> {d['name']} ({who})\n"
            f"🌐 <b>Network  :</b> <b>{d['network']}</b>\n"
            f"🔑 <b>TXN Hash :</b> <code>{d['txn_id'] or 'Screenshot Attached'}</code>\n"
            f"📅 <b>Time     :</b> <i>{d['created_at']}</i>\n\n"
            f"╰────────────────────────────────────╯"
        )
        await q.edit_message_text(card, parse_mode=HTML, reply_markup=kb_proof_actions(dep_id, tg_id))

    elif data.startswith("pay_approve_"):
        rest = data[12:].split("_", 1)
        dep_id, tg_id = int(rest[0]), int(rest[1])
        ctx.user_data["action"] = ("approve", dep_id, tg_id)
        await q.edit_message_text(
            "💰 <b>Enter exact amount in USDT to credit client wallet:</b>\n\n<i>Example: <code>20.00</code></i>",
            parse_mode=HTML,
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("« Cancel", callback_data="pay_pending")]])
        )

    elif data.startswith("pay_reject_"):
        rest = data[11:].split("_", 1)
        dep_id, tg_id = int(rest[0]), int(rest[1])
        db.reject_deposit(dep_id)
        
        await notify_customer(
            tg_id,
            "❌ <b>Deposit Verification Failed</b>\n\n"
            "Your transaction hash could not be confirmed on chain.\n"
            "If this was a mistake, please reach out to Support."
        )
        await q.edit_message_text("❌ <b>Deposit rejected and client notified.</b>", parse_mode=HTML, reply_markup=kb_back_home())

    elif data == "pay_stats":
        u, o, po, r, pd = db.get_stats()
        await q.edit_message_text(
            f"📊 <b>Financial Analytics</b>\n\n"
            f"⏳ <b>Pending Audits:</b> <code>{pd}</code>\n"
            f"💰 <b>Total Volume  :</b> <code>${r:.2f} USDT</code>\n"
            f"👥 <b>Active Users  :</b> <code>{u}</code>",
            parse_mode=HTML, reply_markup=kb_back_home()
        )

async def on_text(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id):
        return
    action = ctx.user_data.get("action")
    if not action or action[0] != "approve":
        return

    _, dep_id, tg_id = action
    ctx.user_data.pop("action", None)

    try:
        amount = float((update.message.text or "").strip())
        if amount <= 0:
            raise ValueError
    except ValueError:
        await update.message.reply_text("⚠️ Invalid amount.")
        return

    db.approve_deposit(dep_id, amount)

    await update.message.reply_text(
        f"✅ <b>Approved!</b> Credited <b>${amount:.2f} USDT</b> to client <code>{tg_id}</code>",
        parse_mode=HTML,
        reply_markup=kb_back_home()
    )

    # Dispatch confirmation to buyer via Store Bot
    await notify_customer(
        tg_id,
        f"╭──────── {E_CRYPTO} <b>DEPOSIT CONFIRMED</b> {E_CRYPTO} ────────╮\n\n"
        f"{E_CONGRATS} <b>+${amount:.2f} USDT</b> has been added to your wallet balance!\n\n"
        f"{E_CART} <i>You can now purchase any catalog item instantly.</i>\n\n"
        f"╰──────────────────────────────────────────╯"
    )

async def notify_loop(bot):
    while True:
        try:
            for row in db.get_unnotified_deposits():
                dep_id, tg_id, ref, network, txn_id, created, name, username = row
                who = f"@{username}" if username else f"ID: {tg_id}"
                card = (
                    f"╭──────── 💳 <b>NEW DEPOSIT REQUEST</b> ────────╮\n\n"
                    f"👤 <b>Client  :</b> {name} ({who})\n"
                    f"🌐 <b>Network :</b> <b>{network}</b>\n"
                    f"🔑 <b>TXN Hash:</b> <code>{txn_id or 'Image proof'}</code>\n"
                    f"📋 <b>Ref ID  :</b> <code>{ref}</code>\n"
                    f"📅 <b>Time    :</b> <i>{created}</i>\n\n"
                    f"╰──────────────────────────────────────────╯"
                )
                for aid in ADMIN_IDS:
                    try:
                        await bot.send_message(aid, card, parse_mode=HTML, reply_markup=kb_proof_actions(dep_id, tg_id))
                    except TelegramError as e:
                        logging.error(f"Notify admin {aid} error: {e}")
                db.mark_deposit_notified(dep_id)
        except Exception as e:
            logging.error(f"Payments notify_loop error: {e}")
        await asyncio.sleep(NOTIFY_INTERVAL)

async def run_payments_bot():
    if not PAYMENTS_BOT_TOKEN:
        print("⚠️ PAYMENTS_TOKEN is not set in environment.")
        return

    app = Application.builder().token(PAYMENTS_BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", cmd_start))
    app.add_handler(CallbackQueryHandler(on_callback))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, on_text))

    print("🚀 [4/4] Admin Payments Bot running...")
    async with app:
        await app.start()
        await app.updater.start_polling(allowed_updates=Update.ALL_TYPES)
        asyncio.create_task(notify_loop(app.bot))
        await asyncio.Event().wait()
        await app.updater.stop()
        await app.stop()

if __name__ == "__main__":
    asyncio.run(run_payments_bot())
