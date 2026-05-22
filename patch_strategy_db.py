with open("/home/syhnes/TradeBot/sweep_strategy.py", "r") as f:
    code = f.read()

import_block = """import logging
from typing import Dict, Optional, List
import asyncio
import time
import sqlite3
"""

code = code.replace(
    'import logging\nfrom typing import Dict, Optional, List\nimport asyncio\nimport time',
    import_block
)

# On modifie execute_trade pour interagir avec le main.py via une callback ou enregistrer directement en DB
trade_block = """    def execute_trade(self):
        # Envoyer l'ordre au marché via SDK exchange
        logger.warning(f"🔫 >>> EXECUTION ORDRE SHORT {self.coin} AU MARCHE ! <<<")
        
        # Enregistrer le trade fictif pour le moment (en attendant le vrai cablage EXCHANGE_CLIENT)
        try:
            conn = sqlite3.connect('/home/syhnes/TradeBot/database/trades.db')
            cursor = conn.cursor()
            cursor.execute('''
                INSERT INTO trades (coin, side, action, size, price, reason)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', (self.coin, 'short', 'OPEN', 0.05, self.target_wall_price, 'SWEEP CONFIRMED'))
            conn.commit()
            conn.close()
        except Exception as e:
            logger.error(f"Erreur d'enregistrement DB: {e}")

        self.set_state(StrategyState.COOLDOWN, "Exécution terminée. Verrouillage COOLDOWN engagé.")
"""

code = code.replace(
    '    def execute_trade(self):\n        # Envoyer l\'ordre au marché via SDK exchange\n        logger.warning(f"🔫 >>> EXECUTION ORDRE SHORT {self.coin} AU MARCHE ! <<<")\n        self.set_state(StrategyState.COOLDOWN, "Exécution terminée. Verrouillage COOLDOWN engagé.")',
    trade_block
)

with open("/home/syhnes/TradeBot/sweep_strategy.py", "w") as f:
    f.write(code)
print("Sweep strategy patchée pour la DB")
