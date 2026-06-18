#!/usr/bin/env python3
"""
Scraper Novinky.cz přes sitemap.
Stahuje sitemap_articles_0.xml, _1.xml, ... dokud nenarazí na staré záznamy.

Instalace:
  pip install requests beautifulsoup4 lxml

Použití:
  python scraper_novinky_sitemap.py
  python scraper_novinky_sitemap.py --date-from 2025-01-01
  python scraper_novinky_sitemap.py --output novinky.csv
  python scraper_novinky_sitemap.py --max-files 6
"""

import csv
import datetime
import argparse
import hashlib
import sys
import time
import re

import requests
from bs4 import BeautifulSoup

# ── Konfigurace ──────────────────────────────────────────────────────────────

SITEMAP_BASE = "https://www.novinky.cz/sitemaps/sitemap_articles_{n}.xml"
SOURCE       = "Novinky"
DATE_FROM    = datetime.datetime(2025, 1, 1, tzinfo=datetime.timezone.utc)
START_N      = 0

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    )
}

# ── Mapování sekce → doména ──────────────────────────────────────────────────

SECTION_TO_DOMAIN = {
    "domaci":      "POLITICS",
    "zahranicni":  "POLITICS",
    "ekonomika":   "ECONOMY",
    "krimi":       "CRIME",
    "koktejl":     "OTHER",
    "kultura":     "OTHER",
    "sport":       "OTHER",
    "internet":    "OTHER",
    "cestovani":   "OTHER",
    "vtipy":       "OTHER",
    "bydleni":     "OTHER",
    "zdravi":      "HEALTH",
    "volby":       "POLITICS",
    "valka":       "POLITICS",
}


def detect_section(url: str) -> str:
    """
    Vytáhne sekci z URL Novinky.
    /clanek/zahranicni-evropa-ropovod-...-40574458  → zahranicni
    /clanek/domaci-babis-jedna-...-40574447         → domaci
    """
    m = re.search(r"/clanek/([a-z]+)", url)
    return m.group(1) if m else "other"


def detect_domain(section: str) -> str:
    return SECTION_TO_DOMAIN.get(section, "OTHER")


def slug_to_title(url: str) -> str:
    """
    Dekóduje titulek z URL slugu Novinky.
    /clanek/zahranicni-evropa-ropovod-druzba-neni-hracka-...-40574458
    → evropa ropovod druzba neni hracka ...
    """
    m = re.search(r"/clanek/([^/?]+)$", url)
    if not m:
        return ""
    slug = m.group(1)
    # Odstraň koncové číselné ID
    slug = re.sub(r"-\d+$", "", slug)
    # Odstraň sekci (první slovo před pomlčkou)
    known_sections = list(SECTION_TO_DOMAIN.keys()) + [
        "koktejl", "vtipy", "bydleni", "cestovani", "internet",
        "zdravi", "kultura", "sport", "volby", "valka",
    ]
    for sec in sorted(known_sections, key=len, reverse=True):
        if slug.startswith(sec + "-"):
            slug = slug[len(sec) + 1:]
            break
    return slug.replace("-", " ").strip()


def make_id(url: str) -> str:
    digest = hashlib.md5(url.encode()).hexdigest()[:8]
    return f"novinky_{digest}"


def parse_lastmod(lastmod_str: str) -> datetime.datetime | None:
    try:
        return datetime.datetime.fromisoformat(
            lastmod_str.strip().replace("Z", "+00:00")
        )
    except Exception:
        return None


# ── Stažení jednoho sitemap souboru ─────────────────────────────────────────

def fetch_sitemap(n: int) -> str | None:
    url = SITEMAP_BASE.format(n=n)
    try:
        r = requests.get(url, headers=HEADERS, timeout=15)
        if r.status_code == 200:
            return r.text
        elif r.status_code == 404:
            return None
        else:
            print(f"  [VAROVÁNÍ] HTTP {r.status_code} pro soubor _{n}")
            return None
    except Exception as e:
        print(f"  [CHYBA] Soubor _{n}: {e}")
        return None


# ── Parsování jednoho sitemap souboru ────────────────────────────────────────

def parse_sitemap(xml: str, date_from: datetime.datetime, scrape_ts: str) -> tuple[list, bool]:
    soup    = BeautifulSoup(xml, "xml")
    records = []
    stop    = False

    for url_el in soup.find_all("url"):
        loc_el     = url_el.find("loc")
        lastmod_el = url_el.find("lastmod")

        if not loc_el:
            continue

        url     = loc_el.get_text().strip()
        section = detect_section(url)

        # Datum
        pub_date = None
        pub_str  = ""
        if lastmod_el:
            pub_date = parse_lastmod(lastmod_el.get_text())
            if pub_date:
                pub_str = pub_date.strftime("%Y-%m-%d")

        # Filtr podle data
        if pub_date is not None and pub_date < date_from:
            stop = True
            break

        title = slug_to_title(url)
        if not title:
            continue

        records.append({
            "id":        make_id(url),
            "text":      title,
            "url":       url,
            "source":    SOURCE,
            "domain":    detect_domain(section),
            "published": pub_str,
            "scraped_at": scrape_ts,
        })

    return records, stop


# ── Hlavní scraper ───────────────────────────────────────────────────────────

def scrape(date_from: datetime.datetime, output: str, max_files: int | None = None) -> None:
    scrape_ts   = datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    all_records = []
    seen_urls   = set()

    print("=" * 54)
    print("  Scraper Novinky.cz — sitemap")
    print("=" * 54)
    print(f"  Scraping od:  {date_from.date()}")
    print(f"  Výstup:       {output}")
    if max_files:
        print(f"  Max souborů:  {max_files} (_{START_N} až _{START_N + max_files - 1})")
    print()

    n = START_N
    files_done = 0

    while True:
        print(f"  Stahuji sitemap_articles_{n}.xml ...", end=" ")
        xml = fetch_sitemap(n)

        if xml is None:
            print("nenalezeno — konec")
            break

        records, stop = parse_sitemap(xml, date_from, scrape_ts)

        new = 0
        for r in records:
            if r["url"] not in seen_urls:
                seen_urls.add(r["url"])
                all_records.append(r)
                new += 1

        print(f"+{new} záznamů (celkem {len(all_records)})")

        if stop:
            print(f"  ✋ Nalezen článek starší než {date_from.date()} — zastavuji")
            break

        files_done += 1
        if max_files is not None and files_done >= max_files:
            print(f"  ℹ Dosažen limit {max_files} souborů — zastavuji")
            break

        n += 1
        time.sleep(0.5)

    # Statistiky
    from collections import Counter
    print(f"\n  Celkem unikátních záznamů: {len(all_records)}")

    domain_counts = Counter(r["domain"] for r in all_records)
    print("\n  Podle domény:")
    for domain, count in sorted(domain_counts.items(), key=lambda x: -x[1]):
        print(f"    {domain:<12} {count:>5}")

    section_counts = Counter(detect_section(r["url"]) for r in all_records)
    print("\n  Podle sekce:")
    for section, count in sorted(section_counts.items(), key=lambda x: -x[1]):
        print(f"    {section:<20} {count:>5}")

    # Uložení
    fieldnames = ["id", "text", "url", "source", "domain", "published", "scraped_at"]
    with open(output, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(all_records)

    print(f"\n✅ Uloženo {len(all_records)} záznamů → {output}")


# ── CLI ──────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="Scraper Novinky.cz přes sitemap")
    parser.add_argument(
        "--max-files", type=int, default=None,
        help="Maximální počet sitemap souborů (výchozí: všechny)",
    )
    parser.add_argument(
        "--sitemap-base", type=str,
        default="https://www.novinky.cz/sitemaps/sitemap_articles_{n}.xml",
        help="Šablona URL sitemapů — {n} se nahradí číslem",
    )
    parser.add_argument(
        "--date-from", type=str, default="2025-01-01",
        help="Scraping zpětně do tohoto data RRRR-MM-DD (výchozí: 2025-01-01)",
    )
    parser.add_argument(
        "--output", type=str, default="novinky_sitemap.csv",
        help="Název výstupního CSV (výchozí: novinky_sitemap.csv)",
    )
    args = parser.parse_args()

    global SITEMAP_BASE
    SITEMAP_BASE = args.sitemap_base

    try:
        date_from = datetime.datetime.strptime(args.date_from, "%Y-%m-%d").replace(
            tzinfo=datetime.timezone.utc
        )
    except ValueError:
        print(f"[CHYBA] Neplatné datum: {args.date_from}")
        sys.exit(1)

    scrape(date_from, args.output, args.max_files)


if __name__ == "__main__":
    main()