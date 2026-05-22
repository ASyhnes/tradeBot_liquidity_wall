import asyncio
import logging
import time
from enum import Enum, auto
from typing import Dict, Optional, List
from collections import deque

from hyperliquid.utils import constants
from hyperliquid.info import Info
from binance_radar import BinanceRadar

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s - %(message)s")
logger = logging.getLogger("sweep_hybride")

# --- CONFIGURATION INITIALE ---
class StrategyConfig:
    # --- RADAR (Macro) ---
    # Ramené temporairement à 2M USD pour essayer d'avoir des targets sur le marché actuel BTC
    GLOBAL_MIN_WALL_USD = 2_000_000   
    
    # --- GACHETTE (Micro) ---
    CVD_WINDOW_SEC = 300               # Fenêtre historique CVD (5 minutes)
    DIVERGENCE_CVD_DROP_USD = -200_000 # Divergence massives des ventes requises
    ARM_THRESHOLD_PCT = 0.002          # Distance par rapport à la cible (0.2%)
    
    # --- SECURITE ---
    COOLDOWN_MINUTES = 15              # Temps de repos obligatoire 

class StrategyState(Enum):
    STANDBY = auto()
    ARMED = auto()
    EXECUTION = auto()
    COOLDOWN = auto()

class StateMachine:
    def __init__(self, coin: str):
        self.coin = coin
        self.state = StrategyState.STANDBY
        self.recent_trades = deque(maxlen=2000)
        
        self.target_wall_price = 0.0
        self.target_wall_size_usd = 0.0
        self.target_type = None
        self.cooldown_start_time = 0.0

    def set_state(self, new_state: StrategyState, reason: str = ""):
        if self.state != new_state:
            logger.info(f"[{self.coin}] {self.state.name} -> {new_state.name} | {reason}")
            self.state = new_state
            
            # Reset ou configuration selon le nouveau statut
            if new_state == StrategyState.COOLDOWN:
                self.cooldown_start_time = time.time()
                self.target_wall_price = 0.0
                self.target_wall_size_usd = 0.0
                self.target_type = None
            elif new_state == StrategyState.STANDBY:
                self.target_wall_price = 0.0
                self.target_wall_size_usd = 0.0
                self.target_type = None

    def set_global_target(self, price: float, size_usd: float, target_type: str):
        """Reçoit une cible macro. Ignorée si en COOLDOWN ou déjà engagée."""
        if self.state in [StrategyState.COOLDOWN, StrategyState.EXECUTION]:
            return
        
        if size_usd >= StrategyConfig.GLOBAL_MIN_WALL_USD:
            # On update la cible seulement si différente
            if self.target_wall_price != price:
                logger.info(f"[{self.coin}] 📡 RADAR (MACRO): Cible verrouillée à {price}$ (Mur global {target_type} de {size_usd:,.0f} USD)")
                self.target_wall_price = price
                self.target_wall_size_usd = size_usd
                self.target_type = target_type

    def process_trade(self, trade_data: dict):
        """Reçoit le tick Micro d'Hyperliquid et traite le CVD."""
        now = time.time()
        side = trade_data.get("side")
        sz = float(trade_data.get("sz", 0))
        px = float(trade_data.get("px", 0))
        
        impact_usd = (px * sz) if side == "B" else -(px * sz)
        self.recent_trades.append({"ts": now, "px": px, "impact_usd": impact_usd})
        
        self.evaluate_state(px, now)

    def calculate_recent_cvd(self, now: float) -> float:
        cvd_sum = 0.0
        cutoff = now - StrategyConfig.CVD_WINDOW_SEC
        for t in reversed(self.recent_trades):
            if t["ts"] < cutoff:
                break
            cvd_sum += t["impact_usd"]
        return cvd_sum

    def evaluate_state(self, current_price: float, now: float, exchange_client=None):
        if self.state == StrategyState.COOLDOWN:
            elapsed = now - self.cooldown_start_time
            if elapsed >= (StrategyConfig.COOLDOWN_MINUTES * 60):
                self.set_state(StrategyState.STANDBY, "Fin de la période de repos.")
            return

        if self.state == StrategyState.STANDBY:
            if self.target_wall_price > 0:
                dist_pct = abs(self.target_wall_price - current_price) / current_price
                if dist_pct <= StrategyConfig.ARM_THRESHOLD_PCT:
                    self.set_state(StrategyState.ARMED, f"Prix Hyperliquid ({current_price}$) approche cible globale ({self.target_wall_price}$)")
                    
        elif self.state == StrategyState.ARMED:
            if self.target_wall_price > 0:
                dist_pct = abs(self.target_wall_price - current_price) / current_price
                if dist_pct > StrategyConfig.ARM_THRESHOLD_PCT * 2:
                    self.set_state(StrategyState.STANDBY, "Prix repoussé loin du mur (faux départ).")
                    return
            
            recent_cvd = self.calculate_recent_cvd(now)
            
            # Gachette : Transpercement du mur Cible ET chute/hausse validée du CVD
            trigger = False
            if self.target_type == "ASK" and current_price >= self.target_wall_price:
                # Si c'est une résistance, on s'attend à un rejet vendeur (Divergence négative)
                if recent_cvd < StrategyConfig.DIVERGENCE_CVD_DROP_USD:
                    trigger = True
            elif self.target_type == "BID" and current_price <= self.target_wall_price:
                # Si c'est un support, on s'attend à un rejet acheteur (Divergence positive)
                if recent_cvd > abs(StrategyConfig.DIVERGENCE_CVD_DROP_USD):
                    trigger = True

            if trigger:
                self.set_state(StrategyState.EXECUTION, f"🔥 SWEEP CONFIRMÉ ! Prix:{current_price}$ | CVD:{recent_cvd:,.0f}$")
                self.execute_trade(exchange_client)

    def execute_trade(self, exchange_client=None):
        # Envoyer l'ordre au marché via SDK exchange
        is_buy = True if self.target_type == "BID" else False
        side_str = "LONG" if is_buy else "SHORT"
        logger.warning(f"🔫 >>> EXECUTION ORDRE {side_str} {self.coin} AU MARCHE ! <<<")
        
        trade_size = 0.01  # Taille du trade test: 0.01 BTC ~ 800 USD
        executed_px = self.target_wall_price
        
        if exchange_client:
            try:
                logger.info(f"Envoi de l'ordre à HyperLiquid: market_open({self.coin}, is_buy={is_buy}, sz={trade_size})")
                res = exchange_client.market_open(self.coin, is_buy, trade_size)
                logger.info(f"Réponse HyperLiquid: {res}")
            except Exception as e:
                logger.error(f"Erreur lors du passage d'ordre: {e}")
        else:
            logger.warning("Aucun client exchange fourni. Trade simulé uniquement.")

        # Enregistrer le trade
        try:
            conn = sqlite3.connect('/home/syhnes/TradeBot/database/trades.db')
            cursor = conn.cursor()
            cursor.execute('''
                INSERT INTO trades (coin, side, action, size, price, reason)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', (self.coin, side_str.lower(), 'OPEN', trade_size, self.target_wall_price, 'SWEEP CONFIRMED'))
            conn.commit()
            conn.close()
        except Exception as e:
            logger.error(f"Erreur d'enregistrement DB: {e}")

        self.set_state(StrategyState.COOLDOWN, "Exécution terminée. Verrouillage COOLDOWN engagé.")



class WebsocketMonitor:
    """La Gâchette (Niveau Micro)"""
    def __init__(self, target_coins: List[str] = ["BTC"]):
        self.info = Info(constants.MAINNET_API_URL, skip_ws=False)
        self.machines = {coin: StateMachine(coin) for coin in target_coins}
        self.exchange_client = None

    def on_trades_message(self, message):
        data = message.get("data", [])
        for trade in data:
            coin = trade.get("coin")
            if coin in self.machines:
                self.machines[coin].process_trade(trade)

    def start(self):
        logger.info("Démarrage de la Gâchette Locale (Websocket Trades Hyperliquid)...")
        for coin in self.machines.keys():
            self.info.subscribe({"type": "trades", "coin": coin}, self.on_trades_message)

async def global_radar_loop(machines: Dict[str, StateMachine]):
    """Le Radar (Niveau Macro)"""
    logger.info("Démarrage du Radar Macro (Tâche de fond Binance)...")
    while True:
        try:
            if "BTC" in machines:
                wall = await BinanceRadar.fetch_largest_wall("BTCUSDT", min_wall_usd=StrategyConfig.GLOBAL_MIN_WALL_USD)
                
                if wall:
                    price = wall.get("price")
                    size_usd = wall.get("size_usd")
                    target_type = wall.get("type", "ASK")
                    machines["BTC"].set_global_target(price, size_usd, target_type)
                    
        except Exception as e:
            logger.error(f"[Radar] Erreur: {e}")
            
        await asyncio.sleep(60) # Scan toutes les minutes

async def main():
    target_coins = ["BTC"]
    
    # Init Niveau Micro (Websocket HL)
    monitor = WebsocketMonitor(target_coins)
    monitor.start() # Lance le thread interne du SDK
    
    # Init Niveau Macro (Polling API)
    await global_radar_loop(monitor.machines)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Arrêt du TradeBot Hybride.")
