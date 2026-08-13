#!/usr/bin/env python3
"""run_all.py — Runs all 4 bots together in one process."""
import asyncio
import store_bot
import admin_panel_bot
import admin_orders_bot
import admin_payments_bot

async def main():
    await asyncio.gather(
        store_bot.run(),
        admin_panel_bot.run(),
        admin_orders_bot.run(),
        admin_payments_bot.run(),
    )

if __name__ == "__main__":
    asyncio.run(main())
