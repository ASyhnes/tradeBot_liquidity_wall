with open("/home/syhnes/TradeBot/main.py", "r") as f:
    code = f.read()

# On remplace l'affectation de APP_STATE.balance_usdc pour afficher la valeur totale par défaut
code = code.replace(
    'APP_STATE.balance_usdc = balance_usdc',
    'APP_STATE.balance_usdc = account_value # Utiliser la valeur totale du compte comme balance principale'
)
code = code.replace(
    'APP_STATE.account_value = account_value',
    'APP_STATE.account_value = balance_usdc  # Stocker le withdrawable en secondaire'
)

with open("/home/syhnes/TradeBot/main.py", "w") as f:
    f.write(code)
print("Patch appliqué")
