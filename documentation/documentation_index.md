# 🗺️ Index de la Documentation

**Objectif du Projet** : TradeBot est un daemon Python automatisé s'assurant d'appliquer la stratégie "Hybride Macro/Micro" sur l'exchange décentralisé Hyperliquid. Le bot se base sur des Murs de Liquidité (Macro) issus de Binance et le CVD (Micro) pour déclencher ses entrées de positions. Il intègre également un suivi de performance (PnL) asynchrone stocké en base de données SQLite et un tableau de bord web.

## 🏗️ Architecture Globale

`/home/syhnes/TradeBot`
- **Main / Web Service** (`main.py`) : Interface web FastAPI pour surveiller les métriques, configuration de l'environnement, et gestion des fermetures automatiques.
- **Logique Stratégique** (`sweep_strategy.py`) : La tâche de fond (machine à état) qui croise CVD, cible de liquidité, et passage d'ordres sur Hyperliquid.
- **Radar Macro** (`binance_radar.py`) : Scraper de carnets d'ordres pour détecter les gros murs de liquidité.
- **Dashboard** : Fichiers HTML/JS pour visualiser les résultats.
- **Base de données** : SQLite local (`database/trades.db`) pour la persistance locale des trades.

## 📚 Index des Modules

- [[module_dashboard_front]] : Le tableau de bord Web (HTML/JS/Chart.js) et les indicateurs financiers.
- [[module_strategie_hybride]] : La logique interne (STANDBY / ARMED / EXECUTION / COOLDOWN) et la gestion du CVD.
- [[module_radar_macro]] : Le scanner des Orderbooks sur Binance Futures (Macro).
- [[module_main_service]] : L'orchestrateur principal, le serveur web, et le gestionnaire de cycle de vie des positions.

---
*Généré suivant le standard Agent-Ready (MemPalace)*
