from __future__ import annotations

import asyncio
import contextlib
import logging
import os
import time
import sqlite3

from collections import defaultdict, deque
from contextlib import asynccontextmanager
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Any, Deque, DefaultDict, Dict, List, Optional

from dotenv import load_dotenv
from eth_account import Account
from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from hyperliquid.exchange import Exchange
from hyperliquid.info import Info
from hyperliquid.utils.constants import MAINNET_API_URL
from starlette.templating import Jinja2Templates

from sweep_strategy import WebsocketMonitor, global_radar_loop, StrategyState


BASE_DIR = Path(__file__).resolve().parent
load_dotenv(BASE_DIR / ".env")

logging.basicConfig(
    level=os.getenv("FASTAPI_LOG_LEVEL", "info").upper(),
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
)
LOGGER = logging.getLogger("tradebot")
ROUTE_PREFIX = "/TBtrade"


def env_required(name: str) -> str:
    value = os.getenv(name, "").strip()
    if not value:
        raise RuntimeError(f"Missing required environment variable: {name}")
    return value


def env_optional(name: str) -> Optional[str]:
    value = os.getenv(name, "").strip()
    return value or None


def env_float(name: str, default: float) -> float:
    raw_value = os.getenv(name)
    if raw_value is None or not raw_value.strip():
        return default
    return float(raw_value)


def env_int(name: str, default: int) -> int:
    raw_value = os.getenv(name)
    if raw_value is None or not raw_value.strip():
        return default
    return int(raw_value)


def env_bool(name: str, default: bool = False) -> bool:
    raw_value = os.getenv(name)
    if raw_value is None or not raw_value.strip():
        return default
    return raw_value.strip().lower() in {"1", "true", "yes", "on"}


@dataclass(slots=True)
class Settings:
    private_key: Optional[str]
    account_address: Optional[str]
    base_url: str
    monitor_interval_seconds: float
    take_profit_pct: float
    stop_loss_pct: float
    trailing_stop_pct: float
    flow_reversal_pct: float
    flow_window: int
    action_cooldown_seconds: int
    host: str
    port: int
    testnet: bool


@dataclass(slots=True)
class RuntimePosition:
    coin: str
    side: str
    size: float
    entry_price: float
    current_price: float
    pnl_pct: float
    unrealized_pnl: float
    signal: str


@dataclass(slots=True)
class RuntimeAlert:
    coin: str
    reason: str
    message: str
    timestamp: str


@dataclass(slots=True)
class RuntimeState:
    monitoring_status: str = "inactive"
    last_checked_at: Optional[str] = None
    last_error: Optional[str] = None
    balance_usdc: float = 0.0
    account_value: float = 0.0
    total_unrealized_pnl: float = 0.0
    positions: List[Dict[str, Any]] = field(default_factory=list)
    alerts: List[Dict[str, Any]] = field(default_factory=list)
    last_alert: Optional[str] = None
    strategy_status: str = "STANDBY"
    target_wall_price: float = 0.0
    target_wall_size: float = 0.0
    recent_cvd: float = 0.0

    def as_dict(self) -> Dict[str, Any]:
        return {
            "monitoring_status": self.monitoring_status,
            "last_checked_at": self.last_checked_at,
            "last_error": self.last_error,
            "balance_usdc": round(self.balance_usdc, 6),
            "account_value": round(self.account_value, 6),
            "total_unrealized_pnl": round(self.total_unrealized_pnl, 6),
            "positions": self.positions or [],
            "alerts": self.alerts or [],
            "last_alert": self.last_alert,
            "strategy_status": self.strategy_status,
            "target_wall_price": self.target_wall_price,
            "target_wall_size": self.target_wall_size,
            "recent_cvd": self.recent_cvd,
        }


SETTINGS = Settings(
    private_key=env_optional("HL_PRIVATE_KEY"),
    account_address=env_optional("HL_ACCOUNT_ADDRESS"),
    base_url=os.getenv("HL_BASE_URL", MAINNET_API_URL),
    monitor_interval_seconds=env_float("HL_MONITOR_INTERVAL_SECONDS", 10.0),
    take_profit_pct=env_float("HL_TAKE_PROFIT_PCT", 0.02),
    stop_loss_pct=env_float("HL_STOP_LOSS_PCT", 0.01),
    trailing_stop_pct=env_float("HL_TRAILING_STOP_PCT", 0.005),
    flow_reversal_pct=env_float("HL_FLOW_REVERSAL_PCT", 0.01),
    flow_window=env_int("HL_FLOW_WINDOW", 4),
    action_cooldown_seconds=env_int("HL_ACTION_COOLDOWN_SECONDS", 30),
    host=os.getenv("FASTAPI_HOST", "127.0.0.1"),
    port=env_int("FASTAPI_PORT", 8000),
    testnet=env_bool("HL_TESTNET", False),
)

if SETTINGS.flow_window < 2:
    raise RuntimeError("HL_FLOW_WINDOW must be at least 2")

TEMPLATES = Jinja2Templates(directory=str(BASE_DIR / "templates"))
APP_STATE = RuntimeState(positions=[], alerts=[])
STATE_LOCK = asyncio.Lock()
PRICE_HISTORY: DefaultDict[str, Deque[float]] = defaultdict(lambda: deque(maxlen=SETTINGS.flow_window))
FAVORABLE_EXTREMES: Dict[str, float] = {}
LAST_ACTION_AT: Dict[str, float] = {}
INFO_CLIENT: Optional[Info] = None
EXCHANGE_CLIENT: Optional[Exchange] = None
MONITOR_TASK: Optional[asyncio.Task[None]] = None


def create_clients() -> tuple[Info, Exchange]:
    if not SETTINGS.private_key or not SETTINGS.account_address:
        raise RuntimeError("Hyperliquid credentials are not configured")

    wallet = Account.from_key(SETTINGS.private_key)
    if wallet.address.lower() != SETTINGS.account_address.lower():
        LOGGER.warning(
            "HL_ACCOUNT_ADDRESS (%s) differs from the wallet derived from HL_PRIVATE_KEY (%s).",
            SETTINGS.account_address,
            wallet.address,
        )

    info_client = Info(SETTINGS.base_url, skip_ws=True)
    exchange_client = Exchange(
        wallet=wallet,
        base_url=SETTINGS.base_url,
        account_address=SETTINGS.account_address,
    )
    return info_client, exchange_client


def normalize_number(value: Any, default: float = 0.0) -> float:
    try:
        if value is None:
            return default
        return float(value)
    except (TypeError, ValueError):
        return default


def safe_mid_price(mids: Dict[str, Any], coin: str, fallback: float = 0.0) -> float:
    return normalize_number(mids.get(coin), fallback)


def pnl_pct(entry_price: float, current_price: float, size: float) -> float:
    if entry_price <= 0 or current_price <= 0 or size == 0:
        return 0.0
    direction = 1.0 if size > 0 else -1.0
    return direction * ((current_price - entry_price) / entry_price) * 100.0


def format_timestamp() -> str:
    return time.strftime("%Y-%m-%d %H:%M:%S UTC", time.gmtime())


def build_position_snapshot(raw_position: Dict[str, Any], current_price: float) -> RuntimePosition:
    position = raw_position.get("position", {})
    size = normalize_number(position.get("szi"))
    entry_price = normalize_number(position.get("entryPx"))
    side = "long" if size > 0 else "short"
    unrealized_pnl = normalize_number(position.get("unrealizedPnl"))
    return RuntimePosition(
        coin=str(position.get("coin", "UNKNOWN")),
        side=side,
        size=abs(size),
        entry_price=round(entry_price, 6),
        current_price=round(current_price, 6),
        pnl_pct=round(pnl_pct(entry_price, current_price, size), 4),
        unrealized_pnl=round(unrealized_pnl, 6),
        signal="watching",
    )


def detect_flow_reversal(coin: str, side: str, current_price: float) -> bool:
    history = PRICE_HISTORY[coin]
    history.append(current_price)
    if len(history) < SETTINGS.flow_window:
        return False

    start_price = history[0]
    if start_price <= 0:
        return False

    trend_pct = ((current_price - start_price) / start_price) * 100.0
    if side == "long":
        return trend_pct <= -(SETTINGS.flow_reversal_pct * 100.0)
    return trend_pct >= SETTINGS.flow_reversal_pct * 100.0


def update_favorable_extreme(coin: str, side: str, current_price: float) -> float:
    previous = FAVORABLE_EXTREMES.get(coin)
    if previous is None:
        FAVORABLE_EXTREMES[coin] = current_price
        return current_price

    if side == "long":
        FAVORABLE_EXTREMES[coin] = max(previous, current_price)
    else:
        FAVORABLE_EXTREMES[coin] = min(previous, current_price)
    return FAVORABLE_EXTREMES[coin]


def should_close_position(position: RuntimePosition, current_price: float) -> Optional[str]:
    pnl = position.pnl_pct / 100.0
    if pnl >= SETTINGS.take_profit_pct:
        return "take_profit"
    if pnl <= -SETTINGS.stop_loss_pct:
        return "stop_loss"

    extreme = update_favorable_extreme(position.coin, position.side, current_price)
    if position.side == "long":
        if current_price <= extreme * (1.0 - SETTINGS.trailing_stop_pct):
            return "trailing_stop"
    else:
        if current_price >= extreme * (1.0 + SETTINGS.trailing_stop_pct):
            return "trailing_stop"

    if detect_flow_reversal(position.coin, position.side, current_price):
        return "flow_reversal"

    return None


async def close_position(position: RuntimePosition, reason: str) -> Optional[Dict[str, Any]]:
    if EXCHANGE_CLIENT is None:
        return None

    now = time.monotonic()
    last_action = LAST_ACTION_AT.get(position.coin, 0.0)
    if now - last_action < SETTINGS.action_cooldown_seconds:
        return None

    try:
        LAST_ACTION_AT[position.coin] = now
        result = await asyncio.to_thread(EXCHANGE_CLIENT.market_close, position.coin, position.size)
        
        # Enregistrement en base de données
        try:
            conn = sqlite3.connect('/home/syhnes/TradeBot/database/trades.db')
            cursor = conn.cursor()
            cursor.execute('''
                INSERT INTO trades (coin, side, action, size, price, pnl, reason)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            ''', (position.coin, position.side, 'CLOSE', position.size, position.current_price, float(position.pnl_usd), reason))
            conn.commit()
            conn.close()
        except Exception as e:
            LOGGER.error(f"Erreur DB à la fermeture: {e}")

        alert = RuntimeAlert(
            coin=position.coin,
            reason=reason,
            message=f"Ordre market de clôture envoyé pour {position.coin} ({position.side}, size={position.size}).",
            timestamp=format_timestamp(),
        )
        async with STATE_LOCK:
            APP_STATE.last_alert = f"{position.coin}: {reason}"
            APP_STATE.alerts = [asdict(alert), *(APP_STATE.alerts or [])][:10]
        LOGGER.info("Market close sent for %s due to %s: %s", position.coin, reason, result)
        return result
    except Exception as exc:  # pragma: no cover - runtime safety
        LOGGER.exception("Failed to close position %s", position.coin)
        async with STATE_LOCK:
            APP_STATE.last_error = str(exc)
        return None


async def refresh_state() -> None:
    if INFO_CLIENT is None or SETTINGS.account_address is None:
        async with STATE_LOCK:
            APP_STATE.monitoring_status = "degraded"
            APP_STATE.last_checked_at = format_timestamp()
            APP_STATE.last_error = "Hyperliquid not configured: set HL_PRIVATE_KEY and HL_ACCOUNT_ADDRESS"
            APP_STATE.balance_usdc = 0.0
            APP_STATE.account_value = 0.0
            APP_STATE.total_unrealized_pnl = 0.0
            APP_STATE.positions = []
        return

    user_state = await asyncio.to_thread(INFO_CLIENT.user_state, SETTINGS.account_address)
    mids = await asyncio.to_thread(INFO_CLIENT.all_mids)

    balance_usdc = normalize_number(user_state.get("withdrawable"))
    cross_margin_summary = user_state.get("crossMarginSummary") or {}
    account_value = normalize_number(cross_margin_summary.get("accountValue"), balance_usdc)

    raw_positions = user_state.get("assetPositions", [])
    snapshots: List[Dict[str, Any]] = []
    total_unrealized_pnl = 0.0
    active_coins: set[str] = set()

    for raw_position in raw_positions:
        position_data = raw_position.get("position", {})
        size = normalize_number(position_data.get("szi"))
        if size == 0:
            continue

        coin = str(position_data.get("coin", "UNKNOWN"))
        if coin != "BTC":
            continue
        
        active_coins.add(coin)
        current_price = safe_mid_price(mids, coin, normalize_number(position_data.get("entryPx")))
        snapshot = build_position_snapshot(raw_position, current_price)
        total_unrealized_pnl += snapshot.unrealized_pnl

        reason = should_close_position(snapshot, current_price)
        if reason is not None:
            snapshot.signal = reason
            await close_position(snapshot, reason)
        snapshots.append(asdict(snapshot))

    async with STATE_LOCK:
        APP_STATE.monitoring_status = "running"
        APP_STATE.last_checked_at = format_timestamp()
        APP_STATE.last_error = None
        APP_STATE.balance_usdc = account_value # Utiliser la valeur totale du compte comme balance principale
        APP_STATE.account_value = balance_usdc  # Stocker le withdrawable en secondaire
        APP_STATE.total_unrealized_pnl = total_unrealized_pnl
        APP_STATE.positions = snapshots

    stale_coins = [coin for coin in list(PRICE_HISTORY.keys()) if coin not in active_coins]
    for coin in stale_coins:
        PRICE_HISTORY.pop(coin, None)
        FAVORABLE_EXTREMES.pop(coin, None)
        LAST_ACTION_AT.pop(coin, None)


async def monitor_loop() -> None:
    import time
    LOGGER.info("Monitoring loop (Hybride) started with interval %.2fs", SETTINGS.monitor_interval_seconds)
    while True:
        try:
            await refresh_state()
            
            # Sync strategy state into APP_STATE
            if WS_MONITOR is not None and "BTC" in WS_MONITOR.machines:
                machine = WS_MONITOR.machines["BTC"]
                async with STATE_LOCK:
                    APP_STATE.strategy_status = machine.state.name
                    APP_STATE.target_wall_price = machine.target_wall_price
                    APP_STATE.target_wall_size = machine.target_wall_size_usd
                    APP_STATE.recent_cvd = machine.calculate_recent_cvd(time.time())
                    
        except asyncio.CancelledError:
            raise
        except Exception as exc:  # pragma: no cover - runtime safety
            LOGGER.exception("Monitoring loop error")
            async with STATE_LOCK:
                APP_STATE.monitoring_status = "error"
                APP_STATE.last_error = str(exc)
                APP_STATE.last_checked_at = format_timestamp()
        await asyncio.sleep(SETTINGS.monitor_interval_seconds)


@asynccontextmanager
async def lifespan(app: FastAPI):
    global INFO_CLIENT, EXCHANGE_CLIENT, MONITOR_TASK, WS_MONITOR, RADAR_TASK
    try:
        INFO_CLIENT, EXCHANGE_CLIENT = create_clients()
    except Exception as exc:
        LOGGER.warning("Starting in degraded mode: %s", exc)
        INFO_CLIENT, EXCHANGE_CLIENT = None, None
    await refresh_state()
    
    # Start Strategy
    WS_MONITOR = WebsocketMonitor(["BTC"])
    WS_MONITOR.exchange_client = EXCHANGE_CLIENT
    WS_MONITOR.start()
    RADAR_TASK = asyncio.create_task(global_radar_loop(WS_MONITOR.machines))
    
    MONITOR_TASK = asyncio.create_task(monitor_loop())
    APP_STATE.monitoring_status = "running"
    try:
        yield
    finally:
        if MONITOR_TASK is not None:
            MONITOR_TASK.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await MONITOR_TASK
        if RADAR_TASK is not None:
            RADAR_TASK.cancel()


app = FastAPI(title="TradeBot Hyperliquid", lifespan=lifespan)
app.mount(f"{ROUTE_PREFIX}/static", StaticFiles(directory=str(BASE_DIR / "static")), name="static")


@app.middleware("http")
async def log_request_path(request: Request, call_next):
    LOGGER.info(
        "Incoming request path=%s root_path=%s forwarded_prefix=%s",
        request.url.path,
        request.scope.get("root_path", ""),
        request.headers.get("x-forwarded-prefix", ""),
    )
    return await call_next(request)


@app.get(f"{ROUTE_PREFIX}", response_class=HTMLResponse)
async def dashboard(request: Request):
    async with STATE_LOCK:
        snapshot = APP_STATE.as_dict()
    # Avoid Jinja2 environment cache key issues when snapshot contains nested dicts
    template_path = BASE_DIR / "templates" / "dashboard.html"
    template_src = template_path.read_text()
    template = TEMPLATES.env.from_string(template_src)
    rendered = template.render(request=request, snapshot=snapshot)
    return HTMLResponse(rendered)


@app.get(f"{ROUTE_PREFIX}/", include_in_schema=False)
async def dashboard_redirect():
    return RedirectResponse(url=ROUTE_PREFIX, status_code=307)


@app.get(f"{ROUTE_PREFIX}/api/state", name="dashboard_state")
async def dashboard_state() -> JSONResponse:
    async with STATE_LOCK:
        snapshot = APP_STATE.as_dict()
    return JSONResponse(snapshot)


@app.get(f"{ROUTE_PREFIX}/api/health", include_in_schema=False)
async def dashboard_health() -> JSONResponse:
    async with STATE_LOCK:
        snapshot = APP_STATE.as_dict()
    return JSONResponse({"status": snapshot["monitoring_status"], "last_checked_at": snapshot["last_checked_at"]})


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("main:app", host=SETTINGS.host, port=SETTINGS.port, reload=False)
