import os
from dotenv import load_dotenv
import pathlib
from scraping_crypto import (
    scraping_sans_headers,
    scraping_selenium_multi_pages,
    scraping_avec_headers,
    creer_html_detail,
    creer_json_detail,
    filtrer_cryptos_par_ratio
)

load_dotenv()

URL = os.getenv("URL", "https://coinmarketcap.com/")
USER_AGENT = os.getenv("USER_AGENT", "Mozilla/5.0 (compatible; PythonScraper/1.0)")
SAVE_DIR = os.getenv("SAVE_DIR", "out")
WAIT_TIME = int(os.getenv("WAIT_TIME", "5"))
WAIT_TIME_MAX = int(os.getenv("WAIT_TIME_MAX", "15"))

NB_URLS_A_EXTRAIRE = 300
NB_CRYPTOS_A_EXPORTER = 300

FILTER_RATIO = 0.3

pathlib.Path(SAVE_DIR).mkdir(parents=True, exist_ok=True)

if __name__ == "__main__":

    print(f"\nScraping {URL}\n")

    # 0 - Autres méthodes possibles
    # html_scraping_sans_headers = scraping_sans_headers(URL)
    # html_scraping_avec_headers = scraping_avec_headers(URL)
    # html_scraping_avec_selenium = scraping_avec_selenium(URL)

    # 1 - Lire le site et obtenir la liste d’URLs d’un nombre déterminé de cryptomonnaies
    general_html_file = scraping_selenium_multi_pages(
        url=URL,
        target_total=NB_URLS_A_EXTRAIRE
    )

    # 2 - Créer le fichier avec les détails d’un nombre déterminé de cryptomonnaies
    #general_html_file = os.path.join(SAVE_DIR, "coinmarketcap_combined.html")
    detail_html_file = creer_html_detail(general_html_file, max_cryptos=NB_CRYPTOS_A_EXPORTER)

    # 3 - Extraire les détails de chaque cryptomonnaie et les sauvegarder dans un fichier JSON
    #detail_html_file = os.path.join(SAVE_DIR, "coinmarketcap_detail.html")
    detail_json_file = creer_json_detail(detail_html_file)

    filtrer_cryptos_par_ratio(detail_json_file, FILTER_RATIO)
