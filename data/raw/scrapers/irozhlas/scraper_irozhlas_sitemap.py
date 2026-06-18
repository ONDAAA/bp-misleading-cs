#!/usr/bin/env python3
"""
Scraper iRozhlas.cz přes sitemap.
Datum se parsuje přímo z URL (např. _2603170903_zko → 2026-03-17).

Instalace:
  pip install requests beautifulsoup4 lxml

Použití:
  python scraper_irozhlas_sitemap.py
  python scraper_irozhlas_sitemap.py --date-from 2025-01-01
  python scraper_irozhlas_sitemap.py --output irozhlas.csv
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

SITEMAPS = [
    "https://www.irozhlas.cz/sites/default/files/irozhlas_feeds/sitemaps/sitemap-6.xml",
    "https://www.irozhlas.cz/sites/default/files/irozhlas_feeds/sitemaps/sitemap-7.xml",
]

SOURCE    = "iRozhlas"
DATE_FROM = datetime.datetime(2025, 1, 1, tzinfo=datetime.timezone.utc)

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    )
}

# ── Mapování sekce → doména ──────────────────────────────────────────────────

SECTION_TO_DOMAIN = {
    "zpravy-domov":   "POLITICS",
    "zpravy-svet":    "POLITICS",
    "ekonomika":      "ECONOMY",
    "zpravy-krimi":   "CRIME",
    "zdravi":         "HEALTH",
    "veda-technologie": "OTHER",
    "sport":          "OTHER",
    "kultura":        "OTHER",
    "zivotni-styl":   "OTHER",
    "regiony":        "SOCIETY",
    "komentare":      "OTHER",
}


def detect_section(url: str) -> str:
    """Vytáhne sekci z URL iRozhlas — první segment za doménou."""
    m = re.search(r"irozhlas\.cz/([^/]+)/", url)
    return m.group(1) if m else "other"


def detect_domain(section: str) -> str:
    return SECTION_TO_DOMAIN.get(section, "OTHER")


def parse_date_from_url(url: str) -> datetime.datetime | None:
    """
    Parsuje datum z konce URL iRozhlas.
    Vzor: _YYMMDDHHII_xxx
    Příklad: _2603170903_zko → 2026-03-17
    """
    m = re.search(r"_(\d{2})(\d{2})(\d{2})\d{4}_[a-z]+$", url)
    if not m:
        return None
    try:
        year  = 2000 + int(m.group(1))
        month = int(m.group(2))
        day   = int(m.group(3))
        return datetime.datetime(year, month, day, tzinfo=datetime.timezone.utc)
    except Exception:
        return None


def slug_to_title(url: str) -> str:
    """
    Dekóduje titulek z URL iRozhlas.
    /zpravy-domov/pripravy-vodni-nadrze-kryry-pokracuji_2603170903_zko
    → pripravy vodni nadrze kryry pokracuji
    """
    # Vezmi poslední segment URL
    slug = url.rstrip("/").split("/")[-1]
    # Odstraň datum a suffix: _YYMMDDHHII_xxx
    slug = re.sub(r"_\d{10}_[a-z]+$", "", slug)
    # Odstraň případné zbytky
    slug = re.sub(r"_\d+$", "", slug)
    return slug.replace("-", " ").strip()


def make_id(url: str) -> str:
    digest = hashlib.md5(url.encode()).hexdigest()[:8]
    return f"irozhlas_{digest}"


# ── Stažení sitemap souboru ──────────────────────────────────────────────────

def fetch_sitemap(url: str) -> str | None:
    for attempt in range(3):
        try:
            r = requests.get(url, headers=HEADERS, timeout=60)
            if r.status_code == 200:
                return r.text
            else:
                print(f"  [VAROVÁNÍ] HTTP {r.status_code}")
                return None
        except Exception as e:
            print(f"  [POKUS {attempt+1}/3] {e}")
            time.sleep(5)
    print("  [CHYBA] Nepodařilo se stáhnout po 3 pokusech")
    return None


# ── Parsování sitemap souboru ────────────────────────────────────────────────

def parse_sitemap(xml: str, date_from: datetime.datetime, scrape_ts: str) -> list:
    """
    Parsuje XML sitemapy iRozhlas.
    Datum se bere z URL, ne z lastmod (ten v XML není).
    Záznamy starší než date_from se přeskočí.
    """
    soup    = BeautifulSoup(xml, "xml")
    records = []

    for url_el in soup.find_all("url"):
        loc_el = url_el.find("loc")
        if not loc_el:
            continue

        url = loc_el.get_text().strip()

        # Datum z URL
        pub_date = parse_date_from_url(url)

        # Přeskočit záznamy bez rozpoznatelného data
        if pub_date is None:
            continue

        # Přeskočit záznamy starší než date_from
        if pub_date < date_from:
            continue

        pub_str = pub_date.strftime("%Y-%m-%d")
        section = detect_section(url)
        title   = slug_to_title(url)

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

    return records


# ── Hlavní scraper ───────────────────────────────────────────────────────────

def scrape(date_from: datetime.datetime, output: str) -> None:
    scrape_ts   = datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    all_records = []
    seen_urls   = set()

    print("=" * 54)
    print("  Scraper iRozhlas.cz — sitemap")
    print("=" * 54)
    print(f"  Scraping od:  {date_from.date()}")
    print(f"  Výstup:       {output}")
    print()

    for sitemap_url in SITEMAPS:
        print(f"  Stahuji: {sitemap_url.split('/')[-1]} ...", end=" ")
        xml = fetch_sitemap(sitemap_url)
        if xml is None:
            continue

        records = parse_sitemap(xml, date_from, scrape_ts)

        new = 0
        for r in records:
            if r["url"] not in seen_urls:
                seen_urls.add(r["url"])
                all_records.append(r)
                new += 1

        print(f"+{new} záznamů (celkem {len(all_records)})")
        time.sleep(0.5)

    # Statistiky
    from collections import Counter
    print(f"\n  Celkem unikátních záznamů: {len(all_records)}")

    domain_counts = Counter(r["domain"] for r in all_records)
    print("\n  Podle domény:")
    for domain, count in sorted(domain_counts.items(), key=lambda x: -x[1]):
        print(f"    {domain:<20} {count:>5}")

    section_counts = Counter(detect_section(r["url"]) for r in all_records)
    print("\n  Podle sekce:")
    for section, count in sorted(section_counts.items(), key=lambda x: -x[1]):
        print(f"    {section:<25} {count:>5}")

    # Uložení
    fieldnames = ["id", "text", "url", "source", "domain", "published", "scraped_at"]
    with open(output, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(all_records)

    print(f"\n✅ Uloženo {len(all_records)} záznamů → {output}")


# ── CLI ──────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="Scraper iRozhlas.cz přes sitemap")
    parser.add_argument(
        "--date-from", type=str, default="2025-01-01",
        help="Scraping zpětně do tohoto data RRRR-MM-DD (výchozí: 2025-01-01)",
    )
    parser.add_argument(
        "--output", type=str, default="irozhlas_sitemap.csv",
        help="Název výstupního CSV (výchozí: irozhlas_sitemap.csv)",
    )
    args = parser.parse_args()

    try:
        date_from = datetime.datetime.strptime(args.date_from, "%Y-%m-%d").replace(
            tzinfo=datetime.timezone.utc
        )
    except ValueError:
        print(f"[CHYBA] Neplatné datum: {args.date_from}")
        sys.exit(1)

    scrape(date_from, args.output)


if __name__ == "__main__":
    main()