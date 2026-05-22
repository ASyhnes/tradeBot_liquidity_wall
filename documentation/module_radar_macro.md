# 📡 Radar Macro (Binance)

## Introduction Contextuelle
Ce module interroge continuellement le marché disposant de la plus forte liquidité mondiale (Binance Futures) pour identifier les "Murs Institutionnels". Ces zones de fortes résistances/supports agissent comme des aimants pour le prix et servent de zones cibles pour le bot.

## Dépendances
- Bibliothèque `aiohttp` : Appels asynchrones performants.
- API Binance Futures (`fapi.binance.com`).

## Documentation Technique

### 1. Fonctionnement du Fetch (`fetch_largest_wall`)
Le script appelle l'endpoint `/fapi/v1/depth` (Orderbook/L2) de manière asynchrone, en réclamant la profondeur maximale autorisée en un seul call sans websocket (`limit=1000`).

### 2. Analyse des Murs
- Il balaye le côté `asks` (Vendeurs / Résistance) et le côté `bids` (Acheteurs / Support).
- Il calcule le "Poids en USD" (Prix x Quantité).
- Si le poids d'un mur dépasse le seuil défini `min_wall_usd` (par exemple 2M$), il est sélectionné.

### 3. Retour de données
La fonction retourne un dictionnaire contenant le type (`ASK` pour Résistance ou `BID` pour Support), le prix exact du mur, et sa taille en dollars. Ces données sont ensuite injectées dans la machine à état de la stratégie hybride pour lui indiquer s'il devra préparer un LONG ou un SHORT.

---
[[documentation_index|<- Retour à l'index]]
