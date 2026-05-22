# TradeBot - Liquidity Wall 📈

TradeBot est un daemon Python automatisé qui applique une stratégie de trading algorithmique **Hybride Macro/Micro**. Conçu pour interagir avec l'exchange décentralisé **Hyperliquid**, ce bot combine une analyse des marchés globaux et un suivi précis des flux pour prendre des décisions d'entrées en position.

## 🚀 Fonctionnalités Principales

- **Radar Macro (Murs de Liquidité)** : Scrape et analyse les carnets d'ordres sur Binance Futures pour identifier les zones majeures de liquidité ("Liquidity Walls").
- **Déclencheur Micro (CVD)** : Utilise l'indicateur CVD (Cumulative Volume Delta) comme signal de confirmation (Micro) pour déclencher ses positions sur Hyperliquid.
- **Tableau de Bord Intégré** : Interface web FastAPI pour surveiller les métriques en temps réel, gérer l'environnement du bot et visualiser les performances.
- **Suivi des Performances (PnL)** : Base de données SQLite locale (`database/trades.db`) permettant de garder une trace asynchrone des performances et des trades exécutés.
- **Machine à État Autonome** : Gère automatiquement le cycle de vie de la stratégie : `STANDBY` > `ARMED` > `EXECUTION` > `COOLDOWN`.

## 🏗️ Architecture du Projet

* **`main.py`** : Orchestrateur principal et serveur Web (FastAPI). Gère le cycle de vie des positions et fournit l'interface de contrôle.
* **`sweep_strategy.py`** : Cœur de la logique de trading. Croise les données macro (liquidité) et micro (CVD) pour passer les ordres sur Hyperliquid.
* **`binance_radar.py`** : Scanner macro analysant les Orderbooks de Binance.
* **`templates/` & `static/`** : Fichiers du tableau de bord frontend (HTML, JS, CSS, Chart.js).
* **`documentation/`** : Contient une documentation détaillée par module (`documentation_index.md`).

## 🛠️ Installation et Lancement

1. **Cloner le dépôt**
   ```bash
   git clone https://github.com/ASyhnes/tradeBot_liquidity_wall.git
   cd tradeBot_liquidity_wall
   ```

2. **Configuration de l'environnement virtuel et des dépendances**
   ```bash
   python -m venv .venv
   source .venv/bin/activate  # Sous Windows : .venv\Scripts\activate
   pip install -r requirements.txt
   ```

3. **Variables d'Environnement**
   * Copiez le fichier d'exemple pour créer votre configuration :
     ```bash
     cp .env.example .env
     ```
   * Éditez `.env` et ajoutez vos clés API.

4. **Lancement du Bot**
   ```bash
   python main.py
   ```
   *Le bot démarrera son service en arrière-plan et le dashboard sera accessible localement via le port configuré dans le serveur web.*

## 📚 Documentation
Pour plus de détails techniques, consultez le dossier `documentation/` et son [Index](documentation/documentation_index.md).

---
*Avertissement : Ce logiciel est fourni à des fins éducatives et de recherche. Le trading algorithmique comporte des risques financiers importants.*
