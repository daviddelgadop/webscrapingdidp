import os
import time
import pathlib
import requests
import json
import re

from dotenv import load_dotenv
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager
from bs4 import BeautifulSoup

#  Configuration générale

load_dotenv()

URL = os.getenv("URL", "https://coinmarketcap.com/")
USER_AGENT = os.getenv("USER_AGENT", "Mozilla/5.0 (compatible; PythonScraper/1.0)")
SAVE_DIR = os.getenv("SAVE_DIR", "out")
WAIT_TIME = int(os.getenv("WAIT_TIME", "5"))
WAIT_TIME_MAX = int(os.getenv("WAIT_TIME_MAX", "15"))

pathlib.Path(SAVE_DIR).mkdir(parents=True, exist_ok=True)

# Variables de fichiers

HTML_SANS_HEADERS = os.path.join(SAVE_DIR, "coinmarketcap_sans_headers.html")
HTML_AVEC_HEADERS = os.path.join(SAVE_DIR, "coinmarketcap_avec_headers.html")
HTML_AVEC_SELENIUM = os.path.join(SAVE_DIR, "coinmarketcap_avec_selenium.html")
HTML_COMBINE = os.path.join(SAVE_DIR, "coinmarketcap_combined.html")
HTML_DETAIL = os.path.join(SAVE_DIR, "coinmarketcap_detail.html")
JSON_DETAIL = os.path.join(SAVE_DIR, "cryptos_detail.json")

# Expressions régulières
MONEY_RE = re.compile(r'\$[\s0-9\.,]+[A-Za-z]*')
PCT_RE = re.compile(r'[-+]?(\d+(\.\d+)?)\s?%')


# Fonctions utilitaires
# Convertir une chaîne monétaire ("$1.23B") en nombre (float)
def parse_money(value):
    if not value:
        return None
    clean = value.replace('$', '').replace(',', '').strip().upper()
    multiplier = 1.0
    if clean.endswith('T'):
        multiplier = 1e12
        clean = clean[:-1]
    elif clean.endswith('B'):
        multiplier = 1e9
        clean = clean[:-1]
    elif clean.endswith('M'):
        multiplier = 1e6
        clean = clean[:-1]
    elif clean.endswith('K'):
        multiplier = 1e3
        clean = clean[:-1]
    try:
        return float(clean) * multiplier
    except ValueError:
        return None

# Sauvegarder la réponse HTML
def sauvegarder_reponse(content: str, filepath: str, status_code: int):
    with open(filepath, "w", encoding="utf-8") as f:
        f.write(content or "")
    print(f"Réponse sauvegardée ({status_code}) -> {filepath}")

# Nettoyer les espaces
def _clean_text(s):
    return re.sub(r'\s+', ' ', s or '').strip()

# Recherche la valeur de Market Cap, FDV, Volume, etc
def _find_stats_value(soup, label_regex, fallback_label=None, numeric=False):
    label_pattern = re.compile(label_regex, re.I)
    fallback_pattern = re.compile(fallback_label, re.I) if fallback_label else None

    for box in soup.select("div.StatsInfoBox_base__kP2xM"):
        dt = box.find("dt")
        if not dt:
            continue
        label_text = dt.get_text(" ", strip=True)
        if label_pattern.search(label_text) or (fallback_pattern and fallback_pattern.search(label_text)):
            dd = box.find("dd")
            if not dd:
                continue
            text_dd = dd.get_text(" ", strip=True)
            money = MONEY_RE.search(text_dd)
            pct = PCT_RE.search(text_dd)
            if not money:
                span_money = dd.find("span", string=MONEY_RE)
                if span_money:
                    money = MONEY_RE.search(span_money.get_text(strip=True))
            if not pct:
                pct_node = dd.find(attrs={"data-role": "percentage-value"}) or dd.find(string=PCT_RE)
                if pct_node:
                    pct_txt = getattr(pct_node, "get_text", lambda *a, **k: str(pct_node))()
                    pct = PCT_RE.search(pct_txt)
            money_val = money.group(0) if money else None
            pct_val = pct.group(0) if pct else None
            if numeric:
                money_val = parse_money(money_val)
            return money_val, pct_val
    return None, None

# Récuperer les lignes <tr> d’un tableau
def get_all_tr(soup: BeautifulSoup):
    tbody = soup.find('tbody')
    if not tbody:
        return []
    trs = tbody.find_all('tr', recursive=False) or tbody.find_all('tr')
    print(f"{len(trs)} lignes <tr> détectées.")
    return trs

# Extraire le lien des cryptomonnaies des balises <tr>
def get_href(tr_tag: BeautifulSoup) -> str | None:
    for a in tr_tag.find_all("a", href=True):
        href = a["href"]
        if re.match(r"^/currencies/[^/]+/?$", href):
            return href
    return None


# Fonctions de scraping

# Scraping de la page sans headers
def scraping_sans_headers(url: str) -> str | None:
    print("Scraping sans headers...")
    session = requests.Session()
    try:
        response = session.get(url, timeout=15)
        response.encoding = response.apparent_encoding
        sauvegarder_reponse(response.text, HTML_SANS_HEADERS, response.status_code)
        return response.text
    except requests.RequestException as e:
        print(f"Erreur scraping_sans_headers : {e}")
    finally:
        session.close()
    return None

# Scraping de la page avec headers
def scraping_avec_headers(url: str) -> str | None:
    print("Scraping avec headers...")
    headers = {"User-Agent": USER_AGENT}
    session = requests.Session()
    try:
        response = session.get(url, headers=headers, timeout=15)
        response.encoding = response.apparent_encoding
        sauvegarder_reponse(response.text, HTML_AVEC_HEADERS, response.status_code)
        return response.text
    except requests.RequestException as e:
        print(f"Erreur scraping_avec_headers : {e}")
    finally:
        session.close()
    return None

# Scraping de la page avec Selenium
def scraping_avec_selenium(url: str, wait: int = 30) -> str | None:
    print("Scraping avec Selenium (avec attente du tableau)...")
    options = Options()
    options.add_argument("--headless=new")
    options.add_argument("--disable-gpu")
    options.add_argument("--no-sandbox")
    options.add_argument("--log-level=3")
    driver = None
    try:
        driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)
        driver.get(url)
        WebDriverWait(driver, wait).until(EC.presence_of_element_located((By.TAG_NAME, "tbody")))
        html = driver.page_source
        sauvegarder_reponse(html, HTML_AVEC_SELENIUM, 200)
        return html
    except Exception as e:
        print(f"Erreur scraping_avec_selenium : {e}")
    finally:
        if driver:
            try:
                driver.quit()
            except Exception:
                pass
    return None


# Création de fichiers


# Scraping de plusieurs pages avec Selenium
def scraping_selenium_multi_pages(
    url: str,
    target_total: int = 1000,
    combined_filename: str = HTML_COMBINE,
    wait: int = 15
) -> str | None:
    print(f"\nScraping multi-pages jusqu’à {target_total} cryptos...")

    options = Options()
    # options.add_argument("--headless=new")
    options.add_argument("--disable-gpu")
    options.add_argument("--no-sandbox")
    options.add_argument("--window-size=1920,1080")
    options.add_argument("--log-level=3")
    options.add_argument("--disable-blink-features=AutomationControlled")

    driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)
    wait_driver = WebDriverWait(driver, wait)
    combined_html_parts = []
    total_loaded = 0
    current_page = 1

    try:
        driver.get(url)

        while total_loaded < target_total:
            wait_driver.until(EC.presence_of_element_located((By.TAG_NAME, "tbody")))
            time.sleep(2)

            print(f"Chargement complet de la page {current_page} (scroll continu)...")
            max_wait = 60
            elapsed = 0
            scroll_pause = 2
            last_rows = 0

            while elapsed < max_wait:
                driver.execute_script("window.scrollBy(0, document.body.scrollHeight);")
                time.sleep(scroll_pause)
                driver.execute_script("window.scrollBy(0, -200);")
                time.sleep(scroll_pause)
                rows = driver.find_elements(By.CSS_SELECTOR, "tbody tr")
                if len(rows) == last_rows:
                    break
                last_rows = len(rows)
                elapsed += scroll_pause * 2

            time.sleep(2)
            html = driver.page_source
            nb_rows = len(driver.find_elements(By.CSS_SELECTOR, "tbody tr"))
            total_loaded += nb_rows

            # Création d’un commentaire HTML de suivi
            comment = f"<!-- Page {current_page} | {nb_rows} lignes extraites -->\n"
            section = f"<section data-page='{current_page}'>\n{comment}\n{html}\n</section>"
            combined_html_parts.append(section)

            print(f"Page {current_page} sauvegardée ({nb_rows} lignes, total cumulé : {total_loaded})")

            if total_loaded >= target_total:
                break

            next_buttons = driver.find_elements(By.CSS_SELECTOR, "ul.pagination li.next a[href]")
            if not next_buttons:
                print("Aucun bouton 'Next page' trouvé, arrêt.")
                break
            next_url = next_buttons[0].get_attribute("href")
            if not next_url:
                print("Lien suivant vide, arrêt.")
                break

            current_page += 1
            driver.get(next_url)
            time.sleep(3)

        # Sauvegarde du HTML combiné
        with open(combined_filename, "w", encoding="utf-8") as f:
            f.write("\n".join(combined_html_parts))

        print(f"Scraping terminé. Fichier combiné : {combined_filename} ({len(combined_html_parts)} pages)")
        return combined_filename

    except Exception as e:
        print(f"Erreur scraping_selenium_multi_pages : {type(e).__name__} - {e}")
        return None

    finally:
        try:
            driver.quit()
        except Exception:
            pass


# Créer le fichier des détails de chaque crypto
def creer_html_detail(base_html_file: str, max_cryptos: int = 50) -> str:
    print(f"Création du fichier de détails pour {max_cryptos} cryptos...")

    if not os.path.exists(base_html_file):
        print(f"Le fichier {base_html_file} est manquant.")
        return ""

    with open(base_html_file, "r", encoding="utf-8") as f:
        soup = BeautifulSoup(f, "html.parser")

    rows = []
    sections = soup.find_all("section", attrs={"data-page": True})
    if sections:
        for sec in sections:
            rows.extend(get_all_tr(sec))
    else:
        rows = get_all_tr(soup)

    if max_cryptos:
        rows = rows[:max_cryptos]

    combined_parts = []

    session = requests.Session()
    session.headers.update({"User-Agent": USER_AGENT})

    for i, tr in enumerate(rows, start=1):
        href = get_href(tr)
        if not href:
            continue
        full_url = URL.rstrip("/") + href

        try:
            r = session.get(full_url, timeout=15)
            r.raise_for_status()
            html = r.text
            combined_parts.append(
                f"<section data-crypto='{href.strip('/').split('/')[-1]}'>\n"
                f"<!-- {full_url} -->\n{html}\n</section>\n"
            )
            print(f"{i}. {href} sauvegardée ({len(html)} caractères)")
            time.sleep(1.5)
        except Exception as e:
            print(f"Erreur sur {full_url} : {e}")

    session.close()

    with open(HTML_DETAIL, "w", encoding="utf-8") as f:
        f.write("\n".join(combined_parts))

    print(f"\nFichier combiné créé : {HTML_DETAIL} ({len(combined_parts)} sections)")
    return HTML_DETAIL


# Extraire les infos d’une crypto
def get_info_crypto(soup: BeautifulSoup) -> dict:
    name = None
    symbol = None
    name_tag = soup.find("span", attrs={"data-role": "coin-name"})
    symbol_tag = soup.find("span", attrs={"data-role": "coin-symbol"})
    if name_tag:
        name = name_tag.get("title") or name_tag.get_text(strip=True)
    if symbol_tag:
        symbol = symbol_tag.get_text(strip=True)
    if not name:
        for tag in soup.find_all("script", type="application/ld+json"):
            try:
                data = json.loads(tag.string or "")
                objs = data if isinstance(data, list) else [data]
                for o in objs:
                    if isinstance(o, dict) and o.get("name"):
                        name = _clean_text(o["name"])
                        break
                if name:
                    break
            except Exception:
                pass
    if not name:
        h1 = soup.find("h1")
        if h1:
            t = _clean_text(h1.get_text(" ", strip=True))
            if t:
                name = re.sub(r"\bprice\b", "", t, flags=re.I).strip()
    if not name:
        title = soup.find("title")
        if title:
            t = _clean_text(title.get_text())
            name = re.split(r"\s+price\b", t, flags=re.I)[0].strip() if t else None

    price = None
    node = soup.select_one('span[data-test="text-cdp-price-display"]')
    if node:
        price = MONEY_RE.search(node.get_text(" ", strip=True))
        price = price.group(0) if price else node.get_text(" ", strip=True)

    if not price:
        pv = soup.find(attrs={"data-testid": "price-value"})
        if pv:
            m = MONEY_RE.search(pv.get_text(" ", strip=True))
            price = m.group(0) if m else pv.get_text(" ", strip=True)

    if not price:
        pv2 = soup.find("div", class_=re.compile(r"priceValue", re.I))
        if pv2:
            m = MONEY_RE.search(pv2.get_text(" ", strip=True))
            price = m.group(0) if m else pv2.get_text(" ", strip=True)

    market_cap, _ = _find_stats_value(soup, r"Market\s*Cap", fallback_label="Market")
    fdv, _ = _find_stats_value(soup, r"\bFDV\b", fallback_label="Fully Diluted")
    volume, _ = _find_stats_value(soup, r"Volume\s*\(24h\)", fallback_label="Volume")

    market_cap_val = parse_money(market_cap)
    fdv_val = parse_money(fdv)
    ratio = None
    if market_cap_val and fdv_val and fdv_val != 0:
        ratio = market_cap_val / fdv_val

    return {
        "name": name,
        "symbol": symbol,
        "price": price,
        "market_cap": market_cap,
        "stats": {
            "fdv": fdv,
            "volume": volume,
            "ratio": ratio
        }
    }

# Créer le fichier JSON avec les details des cryptos
def creer_json_detail(detail_html_file: str) -> str:
    print(f"Extraction des infos depuis {detail_html_file}...")
    with open(detail_html_file, "r", encoding="utf-8") as f:
        soup = BeautifulSoup(f, "html.parser")

    sections = soup.find_all("section", attrs={"data-crypto": True})
    results = []
    for i, sec in enumerate(sections, start=1):
        name_attr = sec["data-crypto"]
        sub_soup = BeautifulSoup(sec.decode_contents(), "html.parser")
        info = get_info_crypto(sub_soup)
        if info:
            results.append(info)
            print(f"{i}. {info.get('name', name_attr)} extrait")

    with open(JSON_DETAIL, "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2)

    print(f"\n{len(results)} cryptos extraites et sauvegardées dans {JSON_DETAIL}")
    return JSON_DETAIL


# Filtrer les cryptos selon le ratio
def filtrer_cryptos_par_ratio(input_json_path: str, seuil_ratio: float) -> str:
    if not os.path.exists(input_json_path):
        print(f"Le fichier {input_json_path} est introuvable.")
        return ""

    with open(input_json_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    filtered = [
        crypto for crypto in data
        if crypto.get("stats", {}).get("ratio") is not None
        and isinstance(crypto["stats"]["ratio"], (int, float))
        and crypto["stats"]["ratio"] < seuil_ratio
    ]

    output_json_path = os.path.splitext(input_json_path)[0] + f"_ratio_filter_{seuil_ratio}.json"

    with open(output_json_path, "w", encoding="utf-8") as f:
        json.dump(filtered, f, ensure_ascii=False, indent=2)

    print(f"{len(filtered)} cryptos enregistrées dans {output_json_path}")
    return output_json_path
