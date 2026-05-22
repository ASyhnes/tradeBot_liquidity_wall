# 📊 Tableau de Bord (Dashboard Front)

## Introduction Contextuelle
Interface web permettant à l'utilisateur de surveiller visuellement l'état du bot Hyperliquid en temps réel. Il offre une vision claire sur la santé financière du compte (PnL, balance) et l'état actuel de la stratégie algorithmique sans avoir à lire les logs de la console.

## Dépendances
- `main.py` : Fournit les données d'état via l'API FastAPI (`/api/state`).
- HTML, JavaScript vanille et `Chart.js` pour les graphiques.
- Base de données SQLite pour l'historique de performance.

## Documentation Technique

### 1. Métriques Macro / Micro
Affiche l'état d'esprit actuel de la logique du bot :
- **Mur Cible (Macro)** : Niveau de prix où se trouve un déséquilibre massif d'ordres en attente (détecté par le module radar).
- **CVD Récent (Micro)** : Momentum d'achat/vente à très court terme (5 minutes). Sert de gâchette.
- **Statut Stratégie** : Reflète la machine à état (STANDBY, ARMED, EXECUTION, COOLDOWN).

### 2. Indicateurs Financiers
Supervise le compte Hyperliquid réel :
- **Balance USDC** et **Valeur du Compte** : Les liquidités libres et la valeur totale estimée.
- **Positions Ouvertes** : Les trades actuellement en cours (bot et manuels).
- **PnL Latent** : Profil ou perte non réalisée des positions en cours.

### 3. Performance du Bot (Trade PNL)
- **Graphique (Chart.js)** : Trace visuellement l'évolution des gains générés par les actions automatiques du bot.
- **Historique SQLite** : Liste détaillée et immuable des actions d'ouverture et de fermeture, le gain associé, et la raison de clôture (ex: *Prise de profit*, *Stop_loss*).

### 4. Surveillance en Direct
Écoute continue des Websockets Hyperliquid pour rafraîchir en direct le prix d'entrée, le PnL en %, et le signal en cours pour chaque position active.

---
[[documentation_index|<- Retour à l'index]]
