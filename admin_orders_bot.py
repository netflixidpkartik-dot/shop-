#!/usr/bin/env python3
"""
admin_orders_bot.py — Order Fulfillment & Auto-Delivery Dispatcher
Features:
- Real-time order notification polling loop
- 1-Click instant delivery via Store Bot
- Manual forwarding & custom delivery dispatch
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

ORDERS_BOT_TOKEN = os.environ.get("ORDERS_TOKEN", "")
STORE_BOT_TOKEN  = os.environ.get("STORE_TOKEN", "")
ADMIN_IDS        = [8104033602]  # Update with your Telegram User ID
NOTIFY_INTERVAL  = 10

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

async def send_to_customer(tg_id: int, dtype: str, dcontent: str, order_ref: str, qty: int) -> bool:
    caption = (
        f"╭──────── 💎 <b>ORDER DISPATCHED</b> 💎 ────────╮\n\n"
        f"📋 <b>Reference :</b> <code>{order_ref}</code>\n"
        f"🔢 <b>Quantity  :</b> <b>{qty}</b>\n\n"
        f"⚡ <i>Thank you for your purchase. Details below:</i>\n\n"
        f"╰──────────────────────────────────────────╯"
    )
    try:
        store = Bot(token=STORE_BOT_TOKEN)
        async with store:
            if dtype == "photo":
                await store.send_photo(tg_id, dcontent, caption=caption, parse_mode=HTML)
            elif dtype == "document":
                await store.send_document(tg_id, dcontent, caption=caption, parse_mode=HTML)
            elif dtype == "video":
                await store.send_video(tg_id, dcontent, caption=caption, parse_mode=HTML)
            else:
                await store.send_message(tg_id, f"{caption}\n\n<code>{dcontent}</code>", parse_mode=HTML)
        return True
    except TelegramError as e:
        logging.error(f"Delivery to {tg_id} failed: {e}")
        return False

async def send_raw_to_customer(tg_id: int, message, order_ref: str) -> bool:
    caption = f"💎 <b>Order Delivery:</b> <code>{order_ref}</code>"
    try:
        store = Bot(token=STORE_BOT_TOKEN)
        async with store:
            if message.photo:
                await store.send_photo(tg_id, message.photo[-1].file_id, caption=caption, parse_mode=HTML)
            elif message.document:
                await store.send_document(tg_id, message.document.file_id, caption=caption, parse_mode=HTML)
            elif message.video:
                await store.send_video(tg_id, message.video.file_id, caption=caption, parse_mode=HTML)
            elif message.text:
                await store.send_message(tg_id, f"{caption}\n\n<code>{message.text}</code>", parse_mode=HTML)
        return True
    except TelegramError as e:
        logging.error(f"Raw delivery to {tg_id} failed: {e}")
        return False

def kb_home():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("📋 Recent Orders", callback_data="ord_recent"),
         InlineKeyboardButton("📊 Stats",         callback_data="ord_stats")],
        [InlineKeyboardButton("📦 Manual Delivery Dispatch", callback_data="ord_deliver")],
    ])

def kb_back_home():
    return InlineKeyboardMarkup([[InlineKeyboardButton("« 🏠 Orders Terminal", callback_data="ord_home")]])

def kb_order_notify(order_ref, tg_id):
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("⚡ Deliver from DB", callback_data=f"ord_do_{order_ref}_{tg_id}")],
        [InlineKeyboardButton("📤 Send Custom File/Text", callback_data=f"ord_send_{order_ref}_{tg_id}")],
    ])

async def cmd_start(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id):
        await update.message.reply_text("⛔ Unauthorized.")
        return
    u, o, po, r, _ = db.get_stats()
    dash_text = (
        f"╭──────── 📦 <b>ORDER FULFILLMENT TERMINAL</b> ────────╮\n\n"
        f"📦 <b>Orders Lifetime:</b> <code>{o}</code> (⏳ <b>{po}</b> Pending)\n"
        f"💰 <b>Settled Volume :</b> <code>${r:.2f} USDT</code>\n\n"
        f"⚡ <i>New buyer transactions will trigger live alerts here.</i>\n\n"
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

    if data == "ord_home":
        u, o, po, r, _ = db.get_stats()
        await q.edit_message_text(
            f"📦 <b>Orders Terminal</b>\n\nOrders: <b>{o}</b> (⏳ <b>{po}</b> pending) | Revenue: <b>${r:.2f} USDT</b>",
            parse_mode=HTML, reply_markup=kb_home())

    elif data == "ord_recent":
        orders = db.get_recent_orders_admin(15)
        if not orders:
            await q.edit_message_text("📋 <i>No orders registered yet.</i>", parse_mode=HTML, reply_markup=kb_back_home())
            return
        lines = []
        for ref, name, price, qty, status, created, uname, username, tg_id in orders:
            icon = "🟢" if status == "delivered" else "⏳"
            who = f"@{username}" if username else str(tg_id)
            lines.append(f"{icon} <code>{ref}</code> — <b>{name}</b> (x{qty})\n   💰 ${price:.2f} | 👤 {uname} ({who})")
        await q.edit_message_text("📋 <b>Recent Orders:</b>\n\n" + "\n\n".join(lines[:10]), parse_mode=HTML, reply_markup=kb_back_home())

    elif data == "ord_stats":
        u, o, po, r, _ = db.get_stats()
        await q.edit_message_text(f"📊 <b>Orders Overview</b>\n\n👥 Clients: <b>{u}</b>\n📦 Volume: <b>{o}</b>\n💰 Revenue: <b>${r:.2f} USDT</b>",
            parse_mode=HTML, reply_markup=kb_back_home())

    elif data == "ord_deliver":
        ctx.user_data["action"] = "deliver_manual"
        await q.edit_message_text("📦 Send the Order Reference (e.g. <code>#ORD-12345</code>):", parse_mode=HTML,
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("« Cancel", callback_data="ord_home")]]))

    elif data.startswith("ord_do_"):
        rest = data[7:]
        parts = rest.rsplit("_", 1)
        order_ref, tg_id = parts[0], int(parts[1])
        result = db.deliver_order(order_ref)
        if not result:
            await q.edit_message_text(f"⚠️ Order <code>{order_ref}</code> not found.", parse_mode=HTML, reply_markup=kb_back_home())
            return
        customer_tg_id, dtype, dcontent, qty = result
        sent = await send_to_customer(customer_tg_id, dtype, dcontent, order_ref, qty)
        status_msg = "✅ <b>Dispatched to buyer via Store Bot!</b>" if sent else "⚠️ <b>Dispatch failed (buyer blocked bot).</b>"
        await q.edit_message_text(f"Order <code>{order_ref}</code>\n{status_msg}", parse_mode=HTML, reply_markup=kb_back_home())

    elif data.startswith("ord_send_"):
        rest = data[9:]
        parts = rest.rsplit("_", 1)
        order_ref, tg_id = parts[0], int(parts[1])
        ctx.user_data["action"] = "sending_product"
        ctx.user_data["deliver_ref"] = order_ref
        ctx.user_data["deliver_tg_id"] = tg_id
        await q.edit_message_text(
            f"📤 <b>Send Custom Product Payload</b>\n\nOrder: <code>{order_ref}</code>\n\n"
            f"Send the text, file, photo or key directly to this chat now:",
            parse_mode=HTML,
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("« Cancel", callback_data="ord_home")]])
        )

async def on_any_message(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id):
        return
    action = ctx.user_data.get("action")
    if not action:
        return

    if action == "deliver_manual":
        ctx.user_data.pop("action", None)
        order_ref = (update.message.text or "").strip()
        result = db.deliver_order(order_ref)
        if not result:
            await update.message.reply_text(f"⚠️ Order <code>{order_ref}</code> not found.", parse_mode=HTML)
            return
        customer_tg_id, dtype, dcontent, qty = result
        sent = await send_to_customer(customer_tg_id, dtype, dcontent, order_ref, qty)
        status_msg = "✅ Dispatched to client!" if sent else "⚠️ Failed to reach client."
        await update.message.reply_text(f"<code>{order_ref}</code> — {status_msg}", parse_mode=HTML, reply_markup=kb_back_home())

    elif action == "sending_product":
        ctx.user_data.pop("action", None)
        order_ref = ctx.user_data.pop("deliver_ref", "")
        tg_id = ctx.user_data.pop("deliver_tg_id", None)
        if not tg_id:
            await update.message.reply_text("⚠️ Missing recipient user ID.")
            return

        sent = await send_raw_to_customer(tg_id, update.message, order_ref)
        if sent:
            db.deliver_order(order_ref)
            await update.message.reply_text(f"✅ Product dispatched to client! Order <code>{order_ref}</code> marked completed.", parse_mode=HTML, reply_markup=kb_back_home())
        else:
            await update.message.reply_text("⚠️ Could not deliver. Client may have blocked the bot.", reply_markup=kb_back_home())

async def notify_loop(bot):
    while True:
        try:
            for row in db.get_unnotified_orders():
                oid, tg_id, ref, prod_name, price, qty, created, uname, username = row
                who = f"@{username}" if username else f"ID: {tg_id}"
                card = (
                    f"╭──────── 🛍️ <b>NEW ORDER REGISTERED</b> ────────╮\n\n"
                    f"👤 <b>Client   :</b> {uname} ({who})\n"
                    f"💎 <b>Product  :</b> <b>{prod_name}</b>\n"
                    f"🔢 <b>Quantity :</b> <code>x{qty}</code>\n"
                    f"💰 <b>Total    :</b> <code>${price:.2f} USDT</code>\n"
                    f"📋 <b>Ref      :</b> <code>{ref}</code>\n"
                    f"📅 <b>Time     :</b> <i>{created}</i>\n\n"
                    f"╰──────────────────────────────────────────╯"
                )
                for aid in ADMIN_IDS:
                    try:
                        await bot.send_message(aid, card, parse_mode=HTML, reply_markup=kb_order_notify(ref, tg_id))
                    except TelegramError as e:
                        logging.error(f"Notify admin {aid} error: {e}")
                db.mark_order_notified(oid)
        except Exception as e:
            logging.error(f"Orders notify_loop error: {e}")
        await asyncio.sleep(NOTIFY_INTERVAL)

async def run_orders_bot():
    if not ORDERS_BOT_TOKEN:
        print("⚠️ ORDERS_TOKEN is not set in environment.")
        return

    app = Application.builder().token(ORDERS_BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", cmd_start))
    app.add_handler(CallbackQueryHandler(on_callback))
    app.add_handler(MessageHandler((filters.TEXT | filters.PHOTO | filters.Document.ALL | filters.VIDEO) & ~filters.COMMAND, on_any_message))

    print("🚀 [3/4] Admin Orders Bot running...")
    async with app:
        await app.start()
        await app.updater.start_polling(allowed_updates=Update.ALL_TYPES)
        asyncio.create_task(notify_loop(app.bot))
        await asyncio.Event().wait()
        await app.updater.stop()
        await app.stop()

if __name__ == "__main__":
    asyncio.run(run_orders_bot())
