import re

with open("/home/syhnes/TradeBot/sweep_strategy.py", "r") as f:
    code = f.read()

# Add exchange_client to evaluate_state
code = code.replace(
    'def evaluate_state(self, current_price: float, now: float):',
    'def evaluate_state(self, current_price: float, now: float, exchange_client=None):'
)

# Pass exchange_client to execute_trade
code = code.replace(
    'self.execute_trade()',
    'self.execute_trade(exchange_client)'
)

# Update execute_trade definition
code = code.replace(
    'def execute_trade(self):',
    'def execute_trade(self, exchange_client=None):'
)

# Update execute_trade body to actually make the order
execution_logic = """        # Envoyer l'ordre au marché via SDK exchange
        logger.warning(f"🔫 >>> EXECUTION ORDRE SHORT {self.coin} AU MARCHE ! <<<")
        
        trade_size = 0.01  # Taille du trade test: 0.01 BTC ~ 800 USD
        executed_px = self.target_wall_price
        
        if exchange_client:
            try:
                # is_buy = False pour SHORT
                logger.info(f"Envoi de l'ordre à HyperLiquid: market_open({self.coin}, is_buy=False, sz={trade_size})")
                res = exchange_client.market_open(self.coin, False, trade_size)
                logger.info(f"Réponse HyperLiquid: {res}")
            except Exception as e:
                logger.error(f"Erreur lors du passage d'ordre: {e}")
        else:
            logger.warning("Aucun client exchange fourni. Trade simulé uniquement.")

        # Enregistrer le trade
        try:"""

code = code.replace(
    '''        # Envoyer l'ordre au marché via SDK exchange
        logger.warning(f"🔫 >>> EXECUTION ORDRE SHORT {self.coin} AU MARCHE ! <<<")
        
        # Enregistrer le trade fictif pour le moment (en attendant le vrai cablage EXCHANGE_CLIENT)
        try:''',
    execution_logic
)

code = code.replace(
    '''0.05''',
    '''trade_size'''
)


# Add exchange_client to WebsocketMonitor
code = code.replace(
    'self.machines = {coin: StateMachine(coin) for coin in target_coins}',
    'self.machines = {coin: StateMachine(coin) for coin in target_coins}\n        self.exchange_client = None'
)

# Pass it in WebsocketMonitor
code = code.replace(
    'machine.evaluate_state(px, now)',
    'machine.evaluate_state(px, now, self.exchange_client)'
)

with open("/home/syhnes/TradeBot/sweep_strategy.py", "w") as f:
    f.write(code)

print("Patch strategy.py terminé")
