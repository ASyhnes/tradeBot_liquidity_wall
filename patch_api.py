with open("/home/syhnes/TradeBot/main.py", "r") as f:
    code = f.read()

api_route = """@app.get("/api/db_trades")
async def get_db_trades():
    try:
        conn = sqlite3.connect('/home/syhnes/TradeBot/database/trades.db')
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM trades ORDER BY timestamp ASC")
        rows = cursor.fetchall()
        conn.close()
        return JSONResponse([dict(row) for row in rows])
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)

@app.get("/api/state")"""

code = code.replace('@app.get("/api/state")', api_route)

with open("/home/syhnes/TradeBot/main.py", "w") as f:
    f.write(code)
print("API patchée")
