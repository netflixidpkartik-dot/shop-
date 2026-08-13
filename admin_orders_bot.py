#!/usr/bin/env python3
"""admin_orders_bot.py — Order notifications & delivery.
FIX: Uses STORE bot token to deliver to customers (they only started store bot).
"""

import asyncio, logging, os
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, Bot
from telegram.ext import (
    Application, CommandHandler, CallbackQueryHandler,
    MessageHandler, filters, ContextTypes,
)
from telegram.error import BadRequest, TelegramError
import shared_db as db

ORDERS_BOT_TOKEN = os.environ["ORDERS_TOKEN"]
STORE_BOT_TOKEN  = os.environ["STORE_TOKEN"]   # ← used to send products to customers
ADMIN_IDS        = [8104033602]
NOTIFY_INTERVAL  = 15

HTML = "HTML"
logging.basicConfig(format="%(asctime)s — %(levelname)s — %(message)s", level=logging.INFO)
logging.getLogger("httpx").setLevel(logging.WARNING)

def is_admin(uid): return uid in ADMIN_IDS

async def safe_ans(q, text="", alert=False):
    try: await q.answer(text, show_alert=alert)
    except BadRequest: pass

async def send_to_customer(tg_id: int, dtype: str, dcontent: str,
                           order_ref: str, qty: int) -> bool:
    """Deliver product to customer via STORE bot."""
    caption = (
        f"✅ <b>Your order has arrived!</b>\n\n"
        f"📋 Ref      : <code>{order_ref}</code>\n"
        f"🔢 Quantity : <b>{qty}</b>"
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
                await store.send_message(
                    tg_id,
                    f"{caption}\n\n<code>{dcontent}</code>",
                    parse_mode=HTML)
        return True
    except TelegramError as e:
        logging.error(f"Delivery to {tg_id} failed: {e}")
        return False

async def send_raw_to_customer(tg_id: int, message, order_ref: str) -> bool:
    """Forward admin's raw message to customer via STORE bot."""
    caption = f"✅ <b>Your order has arrived!</b>\n📋 Ref: <code>{order_ref}</code>"
    try:
        store = Bot(token=STORE_BOT_TOKEN)
        async with store:
            if message.photo:
                await store.send_photo(tg_id, message.photo[-1].file_id,
                                       caption=caption, parse_mode=HTML)
            elif message.document:
                await store.send_document(tg_id, message.document.file_id,
                                          caption=caption, parse_mode=HTML)
            elif message.video:
                await store.send_video(tg_id, message.video.file_id,
                                       caption=caption, parse_mode=HTML)
            elif message.text:
                await store.send_message(
                    tg_id,
                    f"{caption}\n\n<code>{message.text}</code>",
                    parse_mode=HTML)
        return True
    except TelegramError as e:
        logging.error(f"Raw delivery to {tg_id} failed: {e}")
        return False

def kb_home():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("📋 Recent Orders", callback_data="ord_recent"),
         InlineKeyboardButton("📊 Stats",         callback_data="ord_stats")],
        [InlineKeyboardButton("📦 Deliver Order", callback_data="ord_deliver")],
    ])

def kb_back_home():
    return InlineKeyboardMarkup([[InlineKeyboardButton("🏠 Orders Home", callback_data="ord_home")]])

def kb_order_notify(order_ref, tg_id):
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("✅ Deliver (from DB)",     callback_data=f"ord_do_{order_ref}_{tg_id}")],
        [InlineKeyboardButton("📤 Send Product Manually", callback_data=f"ord_send_{order_ref}_{tg_id}")],
    ])

async def cmd_start(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id):
        await update.message.reply_text("⛔ Unauthorised."); return
    u, o, po, r, _ = db.get_stats()
    await update.message.reply_text(
        f"📦 <b>Admin Orders Bot</b>\n\n"
        f"📦 Orders  : <b>{o}</b>  (⏳ {po} pending)\n"
        f"💰 Revenue : <b>${r:.2f} USDT</b>\n\n"
        f"New order notifications appear here.\n"
        f"<b>Deliver (from DB)</b> — sends saved product content via store bot.\n"
        f"<b>Send Manually</b> — forward anything, goes via store bot.",
        parse_mode=HTML, reply_markup=kb_home())

async def on_callback(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    q    = update.callback_query
    data = q.data
    uid  = update.effective_user.id
    if not is_admin(uid): await safe_ans(q, "⛔ Unauthorised.", alert=True); return
    await safe_ans(q)

    if data == "ord_home":
        u, o, po, r, _ = db.get_stats()
        await q.edit_message_text(
            f"📦 <b>Orders Bot</b>\n\nOrders: <b>{o}</b> (⏳{po}) | Revenue: <b>${r:.2f}</b>",
            parse_mode=HTML, reply_markup=kb_home())

    elif data == "ord_recent":
        orders = db.get_recent_orders_admin(20)
        if not orders:
            await q.edit_message_text("📋 No orders yet.", reply_markup=kb_back_home()); return
        lines = []
        for ref, name, price, qty, status, created, uname, username, tg_id in orders:
            icon = "✅" if status == "delivered" else "⏳"
            who  = f"@{username}" if username else str(tg_id)
            lines.append(
                f"{icon} <code>{ref}</code>\n"
                f"   📦 {name} × {qty} — ${price:.2f}\n"
                f"   👤 {uname} ({who})")
        await q.edit_message_text(
            "📋 <b>Recent Orders</b>\n\n" + "\n\n".join(lines[:10]),
            parse_mode=HTML, reply_markup=kb_back_home())

    elif data == "ord_stats":
        u, o, po, r, pd = db.get_stats()
        await q.edit_message_text(
            f"📊 <b>Stats</b>\n\n👥 Users: <b>{u}</b>\n"
            f"📦 Orders: <b>{o}</b> (⏳{po})\n💰 Revenue: <b>${r:.2f}</b>",
            parse_mode=HTML, reply_markup=kb_back_home())

    elif data == "ord_deliver":
        ctx.user_data["action"] = "deliver_manual"
        await q.edit_message_text(
            "📦 Send the order reference (e.g. <code>#TG12345</code>):",
            parse_mode=HTML,
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("❌ Cancel", callback_data="ord_home")
            ]]))

    elif data.startswith("ord_do_"):
        # ord_do_#TG12345_123456789
        rest  = data[7:]; parts = rest.rsplit("_", 1)
        order_ref = parts[0]; tg_id = int(parts[1])
        result = db.deliver_order(order_ref)
        if not result:
            await q.edit_message_text(
                f"⚠️ Order <code>{order_ref}</code> not found.",
                parse_mode=HTML, reply_markup=kb_back_home()); return
        customer_tg_id, dtype, dcontent, qty = result
        sent = await send_to_customer(customer_tg_id, dtype, dcontent, order_ref, qty)
        status = "✅ Delivered to customer via store bot!" if sent else \
                 "⚠️ Delivery failed — customer may not have started store bot."
        await q.edit_message_text(
            f"Order <code>{order_ref}</code>\n{status}",
            parse_mode=HTML, reply_markup=kb_back_home())

    elif data.startswith("ord_send_"):
        # ord_send_#TG12345_123456789
        rest  = data[9:]; parts = rest.rsplit("_", 1)
        order_ref = parts[0]; tg_id = int(parts[1])
        ctx.user_data["action"]        = "sending_product"
        ctx.user_data["deliver_ref"]   = order_ref
        ctx.user_data["deliver_tg_id"] = tg_id
        await q.edit_message_text(
            f"📤 <b>Send Product Manually</b>\n\n"
            f"Order: <code>{order_ref}</code>\n\n"
            f"Forward or send the product content now.\n"
            f"<i>Text, photo, document, video — anything.</i>",
            parse_mode=HTML,
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("❌ Cancel", callback_data="ord_home")
            ]]))


async def on_any_message(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id): return
    action = ctx.user_data.get("action")
    if not action: return

    # ── Manual order ref input ─────────────────────────
    if action == "deliver_manual":
        ctx.user_data.pop("action")
        order_ref = (update.message.text or "").strip()
        result    = db.deliver_order(order_ref)
        if not result:
            await update.message.reply_text(
                f"⚠️ Not found: <code>{order_ref}</code>", parse_mode=HTML); return
        customer_tg_id, dtype, dcontent, qty = result
        sent = await send_to_customer(customer_tg_id, dtype, dcontent, order_ref, qty)
        status = "✅ Delivered via store bot!" if sent else \
                 "⚠️ Failed — customer may not have started store bot."
        await update.message.reply_text(
            f"<code>{order_ref}</code> — {status}",
            parse_mode=HTML, reply_markup=kb_back_home())

    # ── Admin forwards product manually ───────────────
    elif action == "sending_product":
        ctx.user_data.pop("action")
        order_ref = ctx.user_data.pop("deliver_ref", "")
        tg_id     = ctx.user_data.pop("deliver_tg_id", None)
        if not tg_id:
            await update.message.reply_text("⚠️ Error: no target user."); return

        sent = await send_raw_to_customer(tg_id, update.message, order_ref)
        if sent:
            db.deliver_order(order_ref)
            await update.message.reply_text(
                f"✅ Product sent to customer via store bot!\n"
                f"Order <code>{order_ref}</code> marked as delivered.",
                parse_mode=HTML, reply_markup=kb_back_home())
        else:
            await update.message.reply_text(
                f"⚠️ Could not deliver to customer {tg_id}.\n"
                f"They may not have started the store bot.",
                reply_markup=kb_back_home())


async def notify_loop(bot):
    """Poll DB for new orders and notify admin."""
    while True:
        try:
            for row in db.get_unnotified_orders():
                oid, tg_id, ref, prod_name, price, qty, created, uname, username = row
                who  = f"@{username}" if username else f"ID:{tg_id}"
                unit = round(price / qty, 4) if qty else price
                text = (
                    f"🛍 <b>New Order!</b>\n\n"
                    f"👤 Customer  : {uname} ({who})\n"
                    f"📦 Product   : <b>{prod_name}</b>\n"
                    f"🔢 Quantity  : <b>{qty}</b>\n"
                    f"💰 Unit Price: <b>${unit:.2f}</b>\n"
                    f"💵 Total     : <b>${price:.2f} USDT</b>\n"
                    f"📋 Ref       : <code>{ref}</code>\n"
                    f"📅 Time      : {created}"
                )
                for aid in ADMIN_IDS:
                    try:
                        await bot.send_message(aid, text, parse_mode=HTML,
                                               reply_markup=kb_order_notify(ref, tg_id))
                    except TelegramError as e:
                        logging.error(f"Notify admin {aid}: {e}")
                db.mark_order_notified(oid)
        except Exception as e:
            logging.error(f"notify_loop: {e}")
        await asyncio.sleep(NOTIFY_INTERVAL)


async def run():
    app = Application.builder().token(ORDERS_BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", cmd_start))
    app.add_handler(CallbackQueryHandler(on_callback))
    app.add_handler(MessageHandler(
        (filters.TEXT | filters.PHOTO | filters.Document.ALL | filters.VIDEO)
        & ~filters.COMMAND,
        on_any_message))
    print("✅ Admin Orders Bot running...")
    async with app:
        await app.start()
        await app.updater.start_polling(allowed_updates=Update.ALL_TYPES)
        asyncio.create_task(notify_loop(app.bot))
        await asyncio.Event().wait()
        await app.updater.stop()
        await app.stop()

if __name__ == "__main__":
    asyncio.run(run())
