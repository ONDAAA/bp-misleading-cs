#!/usr/bin/env python3
"""
Scraper cz24.news přes WordPress sitemap.
Stahuje wp-sitemap-posts-post-40.xml až wp-sitemap-posts-post-61.xml.

Instalace:
  pip install requests beautifulsoup4 lxml

Použití:
  python scraper_cz24_sitemap.py
  python scraper_cz24_sitemap.py --date-from 2025-01-01
  python scraper_cz24_sitemap.py --output cz24.csv
  python scraper_cz24_sitemap.py --start 40 --end 61
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

SITEMAP_BASE = "https://cz24.news/wp-sitemap-posts-post-{n}.xml"
SOURCE       = "cz24news"
DATE_FROM    = datetime.datetime(2025, 1, 1, tzinfo=datetime.timezone.utc)
START_N      = 44
END_N        = 61

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    )
}

# ── Detekce domény z URL slugu ────────────────────────────────────────────────

DOMAIN_KEYWORDS = [
    ("POLITICS", [
        "vlada", "snemovna", "senat", "prezident", "ministr", "koalic",
        "opozic", "volby", "nato", "evropsk", "babis", "fiala", "trump",
        "biden", "zahranicni", "domaci", "eu-", "ukraine", "ukrajna",
        "rusko", "zelenskyj", "putin", "parlament",
    ]),
    ("ECONOMY", [
        "ekonom", "finance", "burza", "inflac", "rozpocet", "koruna",
        "energi", "ceny", "ropa", "akcie", "investic", "sankce",
    ]),
    ("HEALTH", [
        "zdravi", "zdravot", "nemoc", "lekar", "vakcin", "pandemi",
        "covid", "mrna",
    ]),
    ("CRIME", [
        "policie", "vrazd", "krimi", "soud", "korupce", "teror",
        "utok", "podvod", "gang", "mafia",
    ]),
    ("SOCIETY", [
        "migrac", "uprchl", "nelegalni", "migrant", "protest",
        "demonstrac", "cenzur", "propaganda",
    ]),
]


def detect_domain(url: str) -> str:
    url_lower = url.lower()
    for domain, keywords in DOMAIN_KEYWORDS:
        for kw in keywords:
            if kw in url_lower:
                return domain
    return "OTHER"


def slug_to_title(url: str) -> str:
    """
    Dekóduje titulek z URL cz24.news.
    /od-demokracie-ke-gestapu-trumpovy-ice-jednotky-...
    → od demokracie ke gestapu trumpovy ice jednotky ...
    """
    slug = url.rstrip("/").split("/")[-1]
    return slug.replace("-", " ").strip()


def make_id(url: str) -> str:
    digest = hashlib.md5(url.encode()).hexdigest()[:8]
    return f"cz24_{digest}"


def parse_lastmod(lastmod_str: str) -> datetime.datetime | None:
    try:
        return datetime.datetime.fromisoformat(
            lastmod_str.strip().replace("Z", "+00:00")
        )
    except Exception:
        return None


# ── Stažení sitemap souboru ──────────────────────────────────────────────────

def fetch_sitemap(n: int) -> str | None:
    url = SITEMAP_BASE.format(n=n)
    try:
        r = requests.get(url, headers=HEADERS, timeout=30)
        if r.status_code == 200:
            return r.text
        elif r.status_code == 404:
            return None
        else:
            print(f"HTTP {r.status_code}")
            return None
    except Exception as e:
        print(f"chyba: {e}")
        return None


# ── Parsování sitemap souboru ────────────────────────────────────────────────

def parse_sitemap(xml: str, date_from: datetime.datetime, scrape_ts: str) -> tuple[list, bool]:
    soup    = BeautifulSoup(xml, "xml")
    records = []
    stop    = False

    for url_el in soup.find_all("url"):
        loc_el     = url_el.find("loc")
        lastmod_el = url_el.find("lastmod")

        if not loc_el:
            continue

        url = loc_el.get_text().strip()

        # Přeskočit záznamy bez lastmod
        if not lastmod_el or not lastmod_el.get_text().strip():
            continue

        pub_date = parse_lastmod(lastmod_el.get_text())
        if not pub_date:
            continue

        pub_str = pub_date.strftime("%Y-%m-%d")

        # Přeskočit starší než date_from
        if pub_date < date_from:
            continue

        title = slug_to_title(url)
        if not title:
            continue

        records.append({
            "id":        make_id(url),
            "text":      title,
            "url":       url,
            "source":    SOURCE,
            "domain":    detect_domain(url),
            "published": pub_str,
            "scraped_at": scrape_ts,
        })

    return records


# ── Hlavní scraper ───────────────────────────────────────────────────────────

def scrape(date_from: datetime.datetime, output: str, start_n: int, end_n: int) -> None:
    scrape_ts   = datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    all_records = []
    seen_urls   = set()

    print("=" * 54)
    print("  Scraper cz24.news — sitemap")
    print("=" * 54)
    print(f"  Scraping od:  {date_from.date()}")
    print(f"  Soubory:      {start_n} až {end_n}")
    print(f"  Výstup:       {output}")
    print()

    for n in range(start_n, end_n + 1):
        print(f"  Stahuji wp-sitemap-posts-post-{n}.xml ...", end=" ")
        xml = fetch_sitemap(n)

        if xml is None:
            print("nenalezeno — přeskakuji")
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
        print(f"    {domain:<12} {count:>5}")

    # Uložení
    fieldnames = ["id", "text", "url", "source", "domain", "published", "scraped_at"]
    with open(output, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(all_records)

    print(f"\n✅ Uloženo {len(all_records)} záznamů → {output}")


# ── CLI ──────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="Scraper cz24.news přes sitemap")
    parser.add_argument(
        "--start", type=int, default=START_N,
        help=f"První číslo souboru (výchozí: {START_N})",
    )
    parser.add_argument(
        "--end", type=int, default=END_N,
        help=f"Poslední číslo souboru (výchozí: {END_N})",
    )
    parser.add_argument(
        "--date-from", type=str, default="2025-01-01",
        help="Přeskočit záznamy starší než toto datum RRRR-MM-DD (výchozí: 2025-01-01)",
    )
    parser.add_argument(
        "--output", type=str, default="cz24_sitemap.csv",
        help="Název výstupního CSV (výchozí: cz24_sitemap.csv)",
    )
    args = parser.parse_args()

    try:
        date_from = datetime.datetime.strptime(args.date_from, "%Y-%m-%d").replace(
            tzinfo=datetime.timezone.utc
        )
    except ValueError:
        print(f"[CHYBA] Neplatné datum: {args.date_from}")
        sys.exit(1)

    scrape(date_from, args.output, args.start, args.end)


if __name__ == "__main__":
    main()