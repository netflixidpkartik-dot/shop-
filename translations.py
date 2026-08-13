# translations.py — All UI strings for store_bot

LANGS = {
    "en": "🇬🇧 English",
    "zh": "🇨🇳 中文",
    "ru": "🇷🇺 Русский",
    "ng": "🇳🇬 Naija",
}

T = {
    # Welcome
    "welcome": {
        "en": "🚀 <b>Welcome to {bot}, {name}!</b>\n\n🎯 How it works:\n1. Browse Products\n2. Select quantity\n3. Confirm & pay from wallet\n4. Receive within 5–10 min!\n\nChoose an option below:",
        "zh": "🚀 <b>欢迎来到 {bot}，{name}！</b>\n\n🎯 使用方法：\n1. 浏览商品\n2. 选择数量\n3. 用钱包确认付款\n4. 5–10 分钟内收货！\n\n请选择：",
        "ru": "🚀 <b>Добро пожаловать в {bot}, {name}!</b>\n\n🎯 Как это работает:\n1. Просмотр товаров\n2. Выбор количества\n3. Подтверди и оплати с кошелька\n4. Получишь в течение 5–10 минут!\n\nВыбери опцию:",
        "ng": "🚀 <b>Welcome to {bot}, {name}!</b>\n\n🎯 How e work:\n1. Browse Products\n2. Pick how many you want\n3. Pay from your wallet\n4. You go receive am in 5–10 mins!\n\nChoose wetin you want:",
    },
    # Buttons
    "btn_products":  {"en":"🛍 Products",       "zh":"🛍 商品",          "ru":"🛍 Товары",       "ng":"🛍 Products"},
    "btn_redeem":    {"en":"🎁 Redeem Code",    "zh":"🎁 兑换码",        "ru":"🎁 Промокод",     "ng":"🎁 Redeem Code"},
    "btn_profile":   {"en":"👤 My Profile",     "zh":"👤 我的资料",      "ru":"👤 Профиль",      "ng":"👤 My Profile"},
    "btn_orders":    {"en":"📋 My Orders",      "zh":"📋 我的订单",      "ru":"📋 Заказы",       "ng":"📋 My Orders"},
    "btn_wallet":    {"en":"👛 Wallet",         "zh":"👛 钱包",          "ru":"👛 Кошелёк",      "ng":"👛 Wallet"},
    "btn_support":   {"en":"🆘 Support",        "zh":"🆘 客服",          "ru":"🆘 Поддержка",    "ng":"🆘 Support"},
    "btn_language":  {"en":"🌐 Language",       "zh":"🌐 语言",          "ru":"🌐 Язык",         "ng":"🌐 Language"},
    "btn_main_menu": {"en":"🏠 Main Menu",      "zh":"🏠 主菜单",        "ru":"🏠 Главное меню", "ng":"🏠 Main Menu"},
    "btn_refresh":   {"en":"🔄 Refresh",        "zh":"🔄 刷新",          "ru":"🔄 Обновить",     "ng":"🔄 Refresh"},
    "btn_order_now": {"en":"🛒 Order Now",      "zh":"🛒 立即购买",      "ru":"🛒 Заказать",     "ng":"🛒 Order Now"},
    "btn_back":      {"en":"⬅️ Back",           "zh":"⬅️ 返回",          "ru":"⬅️ Назад",        "ng":"⬅️ Back"},
    "btn_confirm":   {"en":"✅ Confirm",         "zh":"✅ 确认",           "ru":"✅ Подтвердить",  "ng":"✅ Confirm"},
    "btn_cancel":    {"en":"❌ Cancel",          "zh":"❌ 取消",           "ru":"❌ Отмена",        "ng":"❌ Cancel"},
    "btn_deposit":   {"en":"💳 Deposit Funds",  "zh":"💳 充值",           "ru":"💳 Пополнить",    "ng":"💳 Deposit Funds"},
    "btn_sent":      {"en":"✅ I Have Sent Payment","zh":"✅ 我已付款",   "ru":"✅ Оплата отправлена","ng":"✅ I Don Send Am"},
    "btn_change_net":{"en":"⬅️ Change Network", "zh":"⬅️ 更换网络",      "ru":"⬅️ Сменить сеть", "ng":"⬅️ Change Network"},
    "btn_custom_qty":{"en":"✏️ Enter Custom Quantity","zh":"✏️ 自定义数量","ru":"✏️ Своё количество","ng":"✏️ Type Your Number"},
    "btn_history":   {"en":"📋 My Orders",      "zh":"📋 我的订单",      "ru":"📋 Мои заказы",   "ng":"📋 My Orders"},
    "btn_continue":  {"en":"🛍 Continue Shopping","zh":"🛍 继续购物",    "ru":"🛍 Продолжить",   "ng":"🛍 Continue Shopping"},
    # Products
    "products_title":{"en":"🛍 <b>PRODUCTS</b>\n\n💡 Choose a product:","zh":"🛍 <b>商品列表</b>\n\n💡 请选择：","ru":"🛍 <b>ТОВАРЫ</b>\n\n💡 Выбери товар:","ng":"🛍 <b>PRODUCTS</b>\n\n💡 Pick wetin you want:"},
    "no_products":   {"en":"😔 No products right now. Check back soon!","zh":"😔 暂无商品，请稍后再来！","ru":"😔 Нет товаров. Проверь позже!","ng":"😔 No products now. Come back later!"},
    "in_stock":      {"en":"✅ IN STOCK","zh":"✅ 有货","ru":"✅ В наличии","ng":"✅ E DEY"},
    "out_of_stock":  {"en":"❌ Out of stock!","zh":"❌ 缺货！","ru":"❌ Нет в наличии!","ng":"❌ E don finish!"},
    "price_per_unit":{"en":"💰 Price","zh":"💰 价格","ru":"💰 Цена","ng":"💰 Price"},
    "stock_avail":   {"en":"📦 Stock","zh":"📦 库存","ru":"📦 Остаток","ng":"📦 Stock"},
    # Quantity
    "how_many":      {"en":"<b>How many do you need?</b>","zh":"<b>你需要多少个？</b>","ru":"<b>Сколько вам нужно?</b>","ng":"<b>How many you want?</b>"},
    "tap_or_custom": {"en":"Tap a quantity or enter custom.","zh":"点击数量或自定义输入。","ru":"Нажми на кол-во или введи своё.","ng":"Tap number or type your own."},
    "enter_qty":     {"en":"✏️ <b>Enter Quantity</b>\n\nType the number you want:","zh":"✏️ <b>输入数量</b>\n\n请输入你想要的数量：","ru":"✏️ <b>Введи количество</b>\n\nНапиши нужное количество:","ng":"✏️ <b>Type Quantity</b>\n\nHow many you want? Type am:"},
    "max_avail":     {"en":"📦 Max available","zh":"📦 最多可购","ru":"📦 Максимум","ng":"📦 Max wey dey"},
    "invalid_qty":   {"en":"⚠️ Please enter a valid number (e.g. 3).","zh":"⚠️ 请输入有效数字（例如：3）。","ru":"⚠️ Введи корректное число (напр. 3).","ng":"⚠️ Enter correct number (e.g. 3)."},
    "stock_limit":   {"en":"⚠️ Only {n} in stock! Enter a lower quantity.","zh":"⚠️ 库存只有 {n} 个！请输入更小的数量。","ru":"⚠️ Только {n} в наличии! Введи меньше.","ng":"⚠️ Only {n} remain! Enter smaller number."},
    # Order summary
    "order_summary": {"en":"🛒 <b>Order Summary</b>","zh":"🛒 <b>订单确认</b>","ru":"🛒 <b>Сводка заказа</b>","ng":"🛒 <b>Order Summary</b>"},
    "product_label": {"en":"📦 Product","zh":"📦 商品","ru":"📦 Товар","ng":"📦 Product"},
    "quantity_label":{"en":"🔢 Quantity","zh":"🔢 数量","ru":"🔢 Количество","ng":"🔢 Quantity"},
    "price_ea":      {"en":"💰 Price ea","zh":"💰 单价","ru":"💰 Цена/шт","ng":"💰 Price each"},
    "total_label":   {"en":"💵 Total","zh":"💵 总价","ru":"💵 Итого","ng":"💵 Total"},
    "your_balance":  {"en":"Your balance","zh":"您的余额","ru":"Ваш баланс","ng":"Your balance"},
    # Order placed
    "order_placed":  {"en":"✅ <b>Order Placed!</b>","zh":"✅ <b>订单已提交！</b>","ru":"✅ <b>Заказ оформлен!</b>","ng":"✅ <b>Order Don Enter!</b>"},
    "delivery_note": {"en":"⏳ <b>Your product will be delivered within 5–10 minutes.</b>\nNot received? Contact {support}","zh":"⏳ <b>您的商品将在 5–10 分钟内发货。</b>\n未收到？联系 {support}","ru":"⏳ <b>Товар будет доставлен в течение 5–10 минут.</b>\nНе получил? Пиши {support}","ng":"⏳ <b>Your product go reach you in 5–10 minutes.</b>\nYou no receive am? Contact {support}"},
    "order_ref":     {"en":"📋 Ref","zh":"📋 订单号","ru":"📋 Номер","ng":"📋 Ref"},
    "bal_label":     {"en":"👛 Balance","zh":"👛 余额","ru":"👛 Баланс","ng":"👛 Balance"},
    # Insufficient balance
    "insuf_bal":     {"en":"❌ <b>Insufficient Balance</b>","zh":"❌ <b>余额不足</b>","ru":"❌ <b>Недостаточно средств</b>","ng":"❌ <b>Money No Enough</b>"},
    "order_total":   {"en":"💵 Order Total","zh":"💵 订单金额","ru":"💵 Сумма заказа","ng":"💵 Order Total"},
    "need_more":     {"en":"⚠️ You need <b>{n}</b> more.","zh":"⚠️ 你还需要 <b>{n}</b> USDT。","ru":"⚠️ Нужно ещё <b>{n}</b>.","ng":"⚠️ You need <b>{n}</b> more."},
    # Wallet
    "wallet_title":  {"en":"👛 <b>Your Wallet</b>","zh":"👛 <b>我的钱包</b>","ru":"👛 <b>Мой кошелёк</b>","ng":"👛 <b>Your Wallet</b>"},
    "wallet_bal":    {"en":"💰 Balance: <b>{bal} USDT</b>","zh":"💰 余额：<b>{bal} USDT</b>","ru":"💰 Баланс: <b>{bal} USDT</b>","ng":"💰 Balance: <b>{bal} USDT</b>"},
    "wallet_note":   {"en":"Deposit funds to start buying.\n<i>Min deposit: $1.00 USDT</i>","zh":"充值后即可购买。\n<i>最低充值：$1.00 USDT</i>","ru":"Пополни кошелёк для покупок.\n<i>Мин. пополнение: $1.00 USDT</i>","ng":"Add money to your wallet to buy.\n<i>Min: $1.00 USDT</i>"},
    # Deposit
    "deposit_title": {"en":"💳 <b>Deposit Funds</b>\n\nMinimum: <b>$1.00 USDT</b>\n\nSelect a payment network:","zh":"💳 <b>充值</b>\n\n最低：<b>$1.00 USDT</b>\n\n选择支付网络：","ru":"💳 <b>Пополнение</b>\n\nМинимум: <b>$1.00 USDT</b>\n\nВыбери сеть:","ng":"💳 <b>Deposit Money</b>\n\nMinimum: <b>$1.00 USDT</b>\n\nChoose network:"},
    "deposit_addr":  {"en":"💳 <b>Deposit via {net}</b>\n\n📬 <b>Send to this address:</b>\n<code>{addr}</code>\n\nAfter sending, tap the button below.","zh":"💳 <b>通过 {net} 充值</b>\n\n📬 <b>发送至：</b>\n<code>{addr}</code>\n\n转账后点击下方按钮。","ru":"💳 <b>Пополнение через {net}</b>\n\n📬 <b>Отправь на адрес:</b>\n<code>{addr}</code>\n\nПосле отправки нажми кнопку.","ng":"💳 <b>Deposit via {net}</b>\n\n📬 <b>Send to this address:</b>\n<code>{addr}</code>\n\nAfter you send am, tap button below."},
    "enter_txn":     {"en":"🔑 <b>Enter Transaction ID</b>\n\nPlease send your <b>Transaction ID (TXN ID / Hash)</b>.\n\n<i>You can find it in your wallet's transaction history.</i>","zh":"🔑 <b>输入交易 ID</b>\n\n请发送您的 <b>交易 ID（TXN ID / Hash）</b>。\n\n<i>可在您钱包的交易记录中找到。</i>","ru":"🔑 <b>Введи ID транзакции</b>\n\nОтправь <b>Transaction ID (TXN ID / Hash)</b>.\n\n<i>Его можно найти в истории кошелька.</i>","ng":"🔑 <b>Send Your TXN ID</b>\n\nSend your <b>Transaction ID (TXN ID / Hash)</b>.\n\n<i>You go find am for your wallet history.</i>"},
    "dep_submitted": {"en":"✅ <b>Deposit Request Submitted!</b>\n\n⚡ Your payment is being verified.\n📋 Status : <b>Pending</b>\n🔑 TXN ID : <code>{txn}</code>\n⏳ Time   : 3 Hours (Max)\n\n📌 Reference: <code>{ref}</code>","zh":"✅ <b>充值申请已提交！</b>\n\n⚡ 正在验证您的付款。\n📋 状态：<b>审核中</b>\n🔑 交易ID：<code>{txn}</code>\n⏳ 时间：最多 3 小时\n\n📌 参考编号：<code>{ref}</code>","ru":"✅ <b>Заявка на пополнение подана!</b>\n\n⚡ Идёт проверка платежа.\n📋 Статус: <b>Ожидание</b>\n🔑 TXN ID: <code>{txn}</code>\n⏳ Время: максимум 3 часа\n\n📌 Номер: <code>{ref}</code>","ng":"✅ <b>Deposit Request Don Enter!</b>\n\n⚡ Dem dey verify your payment.\n📋 Status: <b>Pending</b>\n🔑 TXN ID: <code>{txn}</code>\n⏳ Time: 3 Hours Max\n\n📌 Reference: <code>{ref}</code>"},
    # Profile
    "profile_title": {"en":"👤 <b>My Profile</b>","zh":"👤 <b>我的资料</b>","ru":"👤 <b>Мой профиль</b>","ng":"👤 <b>My Profile</b>"},
    # Orders history
    "no_orders":     {"en":"📋 <b>My Orders</b>\n\nNo orders yet!","zh":"📋 <b>我的订单</b>\n\n暂无订单！","ru":"📋 <b>Мои заказы</b>\n\nЗаказов нет!","ng":"📋 <b>My Orders</b>\n\nYou never order anything yet!"},
    "orders_title":  {"en":"📋 <b>My Orders</b>","zh":"📋 <b>我的订单</b>","ru":"📋 <b>Мои заказы</b>","ng":"📋 <b>My Orders</b>"},
    # Redeem
    "redeem_prompt": {"en":"🎁 <b>Redeem Code</b>\n\nSend your code:","zh":"🎁 <b>兑换码</b>\n\n请发送您的兑换码：","ru":"🎁 <b>Промокод</b>\n\nВведи код:","ng":"🎁 <b>Redeem Code</b>\n\nSend your code:"},
    "redeem_ok":     {"en":"🎉 <b>Redeemed!</b>\n\n💰 <b>${amount} USDT</b> added!\nBalance: <b>${bal} USDT</b>","zh":"🎉 <b>兑换成功！</b>\n\n💰 已添加 <b>${amount} USDT</b>！\n余额：<b>${bal} USDT</b>","ru":"🎉 <b>Активировано!</b>\n\n💰 <b>${amount} USDT</b> зачислено!\nБаланс: <b>${bal} USDT</b>","ng":"🎉 <b>E Don Work!</b>\n\n💰 <b>${amount} USDT</b> don enter your wallet!\nBalance: <b>${bal} USDT</b>"},
    # Support
    "support_text":  {"en":"🆘 <b>Support</b>\n\nContact us: {support}","zh":"🆘 <b>客服</b>\n\n联系我们：{support}","ru":"🆘 <b>Поддержка</b>\n\nСвяжитесь: {support}","ng":"🆘 <b>Support</b>\n\nContact us: {support}"},
    # Language picker
    "lang_title":    {"en":"🌐 <b>Select Language</b>","zh":"🌐 <b>选择语言</b>","ru":"🌐 <b>Выбор языка</b>","ng":"🌐 <b>Choose Language</b>"},
    "lang_set":      {"en":"✅ Language set to English!","zh":"✅ 语言已设置为中文！","ru":"✅ Язык изменён на Русский!","ng":"✅ Language don change to Naija!"},
    # Deposit approved (sent to customer)
    "dep_approved":  {"en":"✅ <b>Deposit Approved!</b>\n\n💰 <b>${amount} USDT</b> added to your wallet.\nYou can now purchase products!","zh":"✅ <b>充值已通过！</b>\n\n💰 <b>${amount} USDT</b> 已添加到您的钱包。\n现在可以购买商品了！","ru":"✅ <b>Пополнение одобрено!</b>\n\n💰 <b>${amount} USDT</b> зачислено на кошелёк.\nМожно покупать!","ng":"✅ <b>Deposit Approved!</b>\n\n💰 <b>${amount} USDT</b> don enter your wallet.\nYou fit buy products now!"},
    # Deposit rejected
    "dep_rejected":  {"en":"❌ <b>Deposit Rejected</b>\n\nYour TXN ID could not be verified.\nContact support if you think this is wrong.","zh":"❌ <b>充值被拒绝</b>\n\n您的交易ID无法验证。\n如有疑问请联系客服。","ru":"❌ <b>Пополнение отклонено</b>\n\nTXN ID не подтверждён.\nОбратись в поддержку, если считаешь иначе.","ng":"❌ <b>Deposit Rejected</b>\n\nYour TXN ID no verify.\nContact support if you think say e dey correct."},
}

def t(key, lang="en", **kwargs):
    """Get translated string."""
    text = T.get(key, {}).get(lang) or T.get(key, {}).get("en", key)
    if kwargs:
        try: text = text.format(**kwargs)
        except Exception: pass
    return text
