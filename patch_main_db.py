with open("/home/syhnes/TradeBot/main.py", "r") as f:
    code = f.read()

import_block = """import os
import time
import sqlite3
"""

code = code.replace(
    'import os\nimport time',
    import_block
)

# On modifie close_position pour enregistrer en base la fermeture de la position
close_patch = """        result = await asyncio.to_thread(EXCHANGE_CLIENT.market_close, position.coin, position.size)
        
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
"""

code = code.replace(
    '        result = await asyncio.to_thread(EXCHANGE_CLIENT.market_close, position.coin, position.size)',
    close_patch
)

with open("/home/syhnes/TradeBot/main.py", "w") as f:
    f.write(code)
print("Main patché pour la DB")
