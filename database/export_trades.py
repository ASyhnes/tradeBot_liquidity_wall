import sqlite3
import csv
import json
import os

def export_data():
    db_path = '/home/syhnes/TradeBot/database/trades.db'
    if not os.path.exists(db_path):
        print("La base de données n'existe pas encore.")
        return
        
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM trades ORDER BY timestamp ASC")
    rows = cursor.fetchall()
    
    # Export CSV
    with open('/home/syhnes/TradeBot/database/trades_export.csv', 'w', newline='') as f:
        writer = csv.writer(f)
        writer.writerow(['ID', 'Date', 'Type d\'ordre', 'Coin', 'Taille', 'Prix', 'PNL ($)', 'Raison'])
        for r in rows:
            writer.writerow([r['id'], r['timestamp'], r['action'], r['coin'], r['size'], r['price'], r['pnl'], r['reason']])
            
    # Export JSON
    with open('/home/syhnes/TradeBot/database/trades_export.json', 'w') as f:
        json.dump([dict(r) for r in rows], f, indent=4)
        
    print(f"Export terminé : {len(rows)} trades extraits.")
    conn.close()

if __name__ == '__main__':
    export_data()
