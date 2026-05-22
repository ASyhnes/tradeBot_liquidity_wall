# ⚙️ Service Principal et Orchestrateur

## Introduction Contextuelle
Le `main.py` est le cœur battant de l'application TradeBot. C'est le point d'entrée qui relie l'interface Web (FastAPI), la communication avec Hyperliquid (SDK), la stratégie asynchrone en arrière-plan, et la gestion du cycle de vie des positions (Take Profit / Stop Loss).

## Dépendances
- `fastapi` et `uvicorn` : Serveur Web.
- `hyperliquid` (Exchange et Info clients).
- `sweep_strategy` : La boucle de stratégie et le Websocket Monitor.
- Base de données SQLite (`database/trades.db`).

## Documentation Technique

### 1. Gestion d'État et de Configuration
- Charge les variables d'environnement (clés API, configurations de risques) via `.env`.
- Maintient un état d'exécution partagé `APP_STATE` (Classe `RuntimeState`) synchronisé grâce à un lock asynchrone (`STATE_LOCK`). Cela permet à l'interface web de lire les infos sans bloquer la stratégie.

### 2. Boucle de Surveillance (`monitor_loop`)
S'exécute à intervalles réguliers (ex: toutes les 10s).
- Elle interroge l'API Hyperliquid (solde USDC, PnL total).
- Scanne les positions actuellement ouvertes sur Hyperliquid.
- Injecte l'état du module de stratégie dans l'état global.

### 3. Gestion de Risque et Clôture (Risk Management)
Si une position est ouverte, le module vérifie constamment des conditions critiques :
- **Take Profit / Stop Loss** (Pourcentage fixe).
- **Trailing Stop** : Réajuste dynamiquement le stop loss en fonction d'un extremum enregistré (`FAVORABLE_EXTREMES`).
- **Flow Reversal** : Détection d'un renversement rapide de momentum défavorable.
Si une condition est remplie, `close_position` est appelé pour envoyer un ordre de fermeture au marché.

### 4. Interface Web (API Routes)
Sert le contenu statique (HTML/CSS) pour l'utilisateur, et expose une route `/api/state` qui transmet l'objet `APP_STATE` sous format JSON au client web.

---
[[documentation_index|<- Retour à l'index]]
