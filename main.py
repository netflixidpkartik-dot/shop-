#!/usr/bin/env python3
"""
main.py — Unified launcher for all Nex Shop bots + auto-randomize stock.
"""

import asyncio
import logging
import shared_db as db
from store_bot import run_store_bot
from admin_panel_bot import run_panel_bot
from admin_orders_bot import run_orders_bot
from admin_payments_bot import run_payments_bot

logging.basicConfig(format="%(asctime)s — %(levelname)s — %(message)s", level=logging.INFO)
log = logging.getLogger(__name__)

STOCK_RANDOMIZE_INTERVAL = 5 * 60  # every 5 minutes

async def auto_randomize_stock():
    """Randomizes all active product stocks (1–100) every 5 minutes."""
    while True:
        await asyncio.sleep(STOCK_RANDOMIZE_INTERVAL)
        try:
            count = db.randomize_all_stocks(min_val=1, max_val=100)
            log.info(f"🔄 Auto-randomized stock for {count} products.")
        except Exception as e:
            log.error(f"Auto-randomize error: {e}")

async def main():
    print("=" * 60)
    print("💎 STARTING ALL BOTS + AUTO-RANDOMIZE STOCK 💎")
    print("=" * 60)

    tasks = [
        asyncio.create_task(run_store_bot()),
        asyncio.create_task(run_panel_bot()),
        asyncio.create_task(run_orders_bot()),
        asyncio.create_task(run_payments_bot()),
        asyncio.create_task(auto_randomize_stock()),
    ]

    await asyncio.gather(*tasks)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        print("\n🛑 Bots stopped.")
