import sqlite3

def init_db():
    conn = sqlite3.connect('/home/syhnes/TradeBot/database/trades.db')
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS trades (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
            coin TEXT,
            side TEXT,
            action TEXT,
            size FLOAT,
            price FLOAT,
            pnl FLOAT DEFAULT 0.0,
            reason TEXT
        )
    ''')
    conn.commit()
    conn.close()
    print("Base de données initialisée.")

if __name__ == '__main__':
    init_db()
