# 🧠 Stratégie Hybride Macro/Micro

## Introduction Contextuelle
C'est le "cerveau" algorithmique du bot. Le module est chargé de guetter le bon alignement des planètes entre un niveau de prix structurel (Macro) et le momentum d'ordre immédiat (Micro) pour déclencher une prise de position optimale sur Hyperliquid (Liquidity Sweep).

## Dépendances
- `hyperliquid` SDK : Pour écouter les trades (Micro) et passer des ordres (EXECUTION).
- `binance_radar.py` : Pour recevoir les cibles Macro.
- SQLite (`database/trades.db`) : Pour enregistrer l'entrée d'une position.

## Documentation Technique

### 1. La Machine à État (`StateMachine`)
Gère le cycle de vie de la stratégie en fonction des informations du marché.
- **STANDBY** (En attente) : Le prix du marché est encore trop loin du Mur Cible. Le bot reste passif et attend une opportunité.
- **ARMED** (Armé) : Le prix entre dans la zone d'impact du Mur Cible (`ARM_THRESHOLD_PCT`). Le bot scrute le CVD à la milliseconde près.
- **EXECUTION** (Action) : Le prix transperce le mur ET le CVD montre un épuisement inverse (Divergence négative pour un SHORT sur résistance, Divergence positive pour un LONG sur support). Un trade Market est déclenché dans la bonne direction.
- **COOLDOWN** (Repos) : Période de sécurité (`COOLDOWN_MINUTES`) après une exécution pour éviter le sur-trading.

### 2. Le CVD (Cumulative Volume Delta)
Calculé en temps réel via la classe `WebsocketMonitor`. Ce monitor écoute chaque trade Hyperliquid (`px`, `sz`, `side`) et maintient un historique (`recent_trades`). La fonction `calculate_recent_cvd()` somme le volume agressif pour repérer les divergences massives.

### 3. Passage d'Ordre
Quand l'état passe en `EXECUTION`, le script ordonne à l'API Hyperliquid d'ouvrir une position (`market_open()`), en spécifiant s'il s'agit d'un achat (LONG) ou d'une vente (SHORT) en fonction du type de mur percuté, puis l'inscrit dans la base de données de traçabilité SQLite.

---
[[documentation_index|<- Retour à l'index]]
