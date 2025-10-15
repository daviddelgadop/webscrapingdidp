# Scraper CoinMarketCap (Python + Selenium)

Ce projet permet d’extraire automatiquement des données de **[CoinMarketCap](https://coinmarketcap.com/)**.  
Il combine un scraping multi-pages avec **Selenium**, la récupération des détails individuels de chaque cryptomonnaie, et l’exportation en **JSON**, avec une option de filtrage selon un ratio (Market Cap / FDV).

**IA M1** 

**David DELGADO** 


---

## Fonctionnalités principales

- **Scraping multi-pages** avec Selenium 
- **Extraction des informations détaillées** 
- **Génération des fichiers HTML et JSON**
- **Filtrage des cryptomonnaies** selon un seuil de ratio 

---

## Structure du projet

```
.
├── main.py                 # Point d’entrée principal
├── scraping_crypto.py      # Fonctions de scraping 
├── .env                    # Variables d’environnement
├── out/                    # Dossier de sortie pour les fichiers
└── requirements.txt        # Dépendances Python
```

---

## Fichier de configuration `.env`

- `URL` → Adresse de base à scraper  
- `USER_AGENT` → Identifiant du navigateur simulé  
- `SAVE_DIR` → Dossier de sortie  
- `WAIT_TIME` / `WAIT_TIME_MAX` → Délais d’attente Selenium  

---

## Utilisation

### 1. Installation des dépendances
```bash
pip install -r requirements.txt
```

### 2. Lancer le script principal
```bash
python main.py
```

---

## Paramètres principaux (dans `main.py`)

```python
NB_URLS_A_EXTRAIRE = 300        # Nombre total de cryptos à lister
NB_CRYPTOS_A_EXPORTER = 300     # Nombre de cryptos à extraire en détail
FILTER_RATIO = 0.3              # Seuil de filtrage 
```

---

## Fichiers générés

Les fichiers sont créés dans le dossier défini par `SAVE_DIR` (par défaut : `out/`).

| Fichier                                  | Description |
|------------------------------------------|-------------|
| `coinmarketcap_combined.html`            | HTML combiné de plusieurs pages de liste |
| `coinmarketcap_detail.html`              | HTML détaillé pour les cryptomonnaies sélectionnées |
| `cryptos_detail.json`                    | Données JSON des cryptomonnaies extraites |
| `cryptos_detail_ratio_filter_SEUIL.json` | Fichier filtré selon un seuil de ratio |

---

## Notes 

- Selenium scrolle automatiquement la page jusqu’à atteindre le nombre souhaité de cryptos (`NB_URLS_A_EXTRAIRE`).  
- Chaque page détaillée est ensuite récupérée via requêtes HTTP individuelles.  
- Pour le débogage, désactive le mode `--headless` dans la fonction `scraping_selenium_multi_pages()`.

---

## Exemple de sortie JSON

```json
{
  "name": "Bitcoin",
  "symbol": "BTC",
  "price": "$111,220.79",
  "market_cap": "$2.21T",
  "stats": {
    "fdv": "$2.33T",
    "volume": "$72.67B",
    "ratio": 0.9484978540772532
  }
}
```

---

## Dépendances

Voir `requirements.txt` pour la liste complète des dépendances nécessaires.

---

