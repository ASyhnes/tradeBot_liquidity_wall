import asyncio
from binance_radar import BinanceRadar
import logging

logging.basicConfig(level=logging.INFO)

async def test():
    # Tester avec un petit mur pour forcer la détection (ex: 2M USD)
    res = await BinanceRadar.fetch_largest_wall("BTCUSDT", min_wall_usd=2_000_000)
    print(f"Test 2M USD Wall: {res}")
    
asyncio.run(test())
