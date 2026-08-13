#!/usr/bin/env python3
"""
main.py / run_all.py — Unified Master Launcher for all 4 Telegram Bots:
1. Store Bot (Storefront, Referral Links, Catalog, User VIP Profile)
2. Admin Panel Bot (Inventory, 1-100 Stock Randomizer, Broadcast, Clients)
3. Admin Orders Bot (Order Alerts, Dispatch, Delivery)
4. Admin Payments Bot (Crypto Deposits, Proof Verifications, Balance Approvals)
"""

import asyncio
import logging
from store_bot import run_store_bot
from admin_panel_bot import run_panel_bot
from admin_orders_bot import run_orders_bot
from admin_payments_bot import run_payments_bot

logging.basicConfig(format="%(asctime)s — %(levelname)s — %(message)s", level=logging.INFO)

async def main():
    print("=" * 60)
    print("💎 STARTING ALL 4 STORE BOTS IN CONCURRENT ASYNC LOOP 💎")
    print("=" * 60)

    # Run all 4 bots in parallel
    tasks = [
        asyncio.create_task(run_store_bot()),
        asyncio.create_task(run_panel_bot()),
        asyncio.create_task(run_orders_bot()),
        asyncio.create_task(run_payments_bot()),
    ]

    await asyncio.gather(*tasks)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        print("\n🛑 Bots stopped.")
