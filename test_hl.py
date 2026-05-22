from hyperliquid.info import Info
from hyperliquid.utils import constants
import json
import os
from dotenv import load_dotenv

load_dotenv("/home/syhnes/TradeBot/.env")
info = Info(constants.MAINNET_API_URL)
user_state = info.user_state(os.getenv("HL_ACCOUNT_ADDRESS"))
# print(json.dumps(user_state, indent=2))
print("WITHDRAWABLE:", user_state.get("withdrawable"))
print("MARGIN_SUMMARY:", json.dumps(user_state.get("marginSummary", {}), indent=2))
print("CROSS_MARGIN:", json.dumps(user_state.get("crossMarginSummary", {}), indent=2))
