import aiohttp
import asyncio
import logging

logger = logging.getLogger("binance_radar")

class BinanceRadar:
    """
    Module Macro (Le Radar)
    Fetch l'Orderbook complet (L2) de Binance Futures (la plus grosse liquidité mondiale)
    via API REST toutes les X secondes pour y repérer les Murs institutionnels.
    """
    # Endpoint Binance Futures u-margined (USDT) depth
    # On précise limit=1000 (le max sans stream) pour voir loin dans le carnet
    BINANCE_FUTURES_DEPTH_URL = "https://fapi.binance.com/fapi/v1/depth"
    
    @classmethod
    async def fetch_largest_wall(cls, symbol: str = "BTCUSDT", min_wall_usd: float = 10_000_000) -> dict:
        """
        Interroge Binance, cherche le plus gros mur côté Vendeur (Asks)
        et le plus gros mur côté Acheteur (Bids) et retourne celui qui dépasse min_wall_usd.
        """
        try:
            async with aiohttp.ClientSession() as session:
                params = {"symbol": symbol, "limit": 1000}
                async with session.get(cls.BINANCE_FUTURES_DEPTH_URL, params=params, timeout=5) as response:
                    if response.status != 200:
                        logger.error(f"[Radar] Erreur Binance HTTP {response.status}")
                        return {}
                        
                    data = await response.json()
                    
                    # data format: {"lastUpdateId": 123, "bids": [["price", "qty"], ...], "asks": [...]}
                    asks = data.get("asks", [])
                    bids = data.get("bids", [])
                    
                    # -- Chercher le plus gros Ask (Vendeur / Résistance) --
                    max_ask_usd = 0.0
                    max_ask_price = 0.0
                    
                    for ask in asks:
                        price = float(ask[0])
                        qty = float(ask[1])
                        size_usd = price * qty
                        if size_usd > max_ask_usd:
                            max_ask_usd = size_usd
                            max_ask_price = price
                            
                    # -- Idem pour les Bids (Acheteur / Support) --
                    max_bid_usd = 0.0
                    max_bid_price = 0.0
                    
                    for bid in bids:
                        price = float(bid[0])
                        qty = float(bid[1])
                        size_usd = price * qty
                        if size_usd > max_bid_usd:
                            max_bid_usd = size_usd
                            max_bid_price = price
                            
                    result = {}
                    
                    # On retourne en priorité la Résistance pour les setup de Shorts (Liquidity Sweep haut)
                    if max_ask_usd >= min_wall_usd:
                        result["type"] = "ASK"
                        result["price"] = max_ask_price
                        result["size_usd"] = max_ask_usd
                    elif max_bid_usd >= min_wall_usd:
                        result["type"] = "BID"
                        result["price"] = max_bid_price
                        result["size_usd"] = max_bid_usd
                        
                    return result
                    
        except Exception as e:
            logger.error(f"[Radar] Erreur réseau Binance: {e}")
            return {}

# --- Test autonome ---
if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    async def test():
        # Test finding walls bigger than 5M$ on BTC
        res = await BinanceRadar.fetch_largest_wall("BTCUSDT", min_wall_usd=5_000_000)
        print(f"Plus gros mur détecté : {res}")
    asyncio.run(test())
