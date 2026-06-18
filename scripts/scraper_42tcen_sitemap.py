#!/usr/bin/env python3
"""
Scraper 42tcen.com přes sitemap.
Sitemaps jsou rozděleny po měsících s parametry date_start a date_end.

Instalace:
  pip install requests beautifulsoup4 lxml

Použití:
  python scraper_42tcen_sitemap.py
  python scraper_42tcen_sitemap.py --date-from 2025-01-01
  python scraper_42tcen_sitemap.py --output 42tcen.csv
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

SITEMAP_INDEX = "https://42tcen.com/sitemap_index.xml"
SOURCE        = "42tcen"
DATE_FROM     = datetime.datetime(2025, 1, 1, tzinfo=datetime.timezone.utc)

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    )
}

# Všechny sitemap URL od 2025-01 do aktuálního měsíce
SITEMAP_URLS = [
    "https://42tcen.com/sitemap_article.xml?date_start=20260401&date_end=20260422",
    "https://42tcen.com/sitemap_article.xml?date_start=20260301&date_end=20260331",
    "https://42tcen.com/sitemap_article.xml?date_start=20260201&date_end=20260228",
    "https://42tcen.com/sitemap_article.xml?date_start=20260101&date_end=20260131",
    "https://42tcen.com/sitemap_article.xml?date_start=20251201&date_end=20251231",
    "https://42tcen.com/sitemap_article.xml?date_start=20251101&date_end=20251130",
    "https://42tcen.com/sitemap_article.xml?date_start=20251001&date_end=20251031",
    "https://42tcen.com/sitemap_article.xml?date_start=20250901&date_end=20250930",
    "https://42tcen.com/sitemap_article.xml?date_start=20250801&date_end=20250831",
    "https://42tcen.com/sitemap_article.xml?date_start=20250701&date_end=20250731",
    "https://42tcen.com/sitemap_article.xml?date_start=20250601&date_end=20250630",
    "https://42tcen.com/sitemap_article.xml?date_start=20250501&date_end=20250531",
    "https://42tcen.com/sitemap_article.xml?date_start=20250401&date_end=20250430",
    "https://42tcen.com/sitemap_article.xml?date_start=20250301&date_end=20250331",
    "https://42tcen.com/sitemap_article.xml?date_start=20250201&date_end=20250228",
    "https://42tcen.com/sitemap_article.xml?date_start=20250101&date_end=20250131",
]

# ── Detekce domény z URL slugu ────────────────────────────────────────────────

DOMAIN_KEYWORDS = [
    ("POLITICS", [
        "vlada", "snemovna", "senat", "prezident", "ministr", "koalic",
        "opozic", "volby", "nato", "evropsk", "babis", "fiala", "trump",
        "premier", "parlament", "magyar", "orbán", "orban", "fico",
        "zahranicni", "domaci", "eu-", "ukraine", "ukrajna",
    ]),
    ("ECONOMY", [
        "ekonom", "finance", "burza", "inflac", "rozpocet", "koruna",
        "energi", "ceny", "ropa", "akcie", "investic", "firma", "dluh",
    ]),
    ("HEALTH", [
        "zdravi", "zdravot", "nemoc", "lekar", "vakcin", "pandemi", "covid",
    ]),
    ("CRIME", [
        "policie", "vrazd", "krimi", "soud", "rozsudek", "korupce",
        "teror", "utok", "podvod",
    ]),
    ("SOCIETY", [
        "migrac", "uprchl", "skola", "protest", "demonstrac", "dekret",
        "historie", "sudet",
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
    Dekóduje titulek z URL 42tcen.
    /entry/od-druzby-po-benesove-dekrety-co-znamena-peter-magyar-pre-slovensko
    → od druzby po benesove dekrety co znamena peter magyar pre slovensko
    """
    m = re.search(r"/entry/([^/?]+)$", url)
    if not m:
        return ""
    return m.group(1).replace("-", " ").strip()


def make_id(url: str) -> str:
    digest = hashlib.md5(url.encode()).hexdigest()[:8]
    return f"42tcen_{digest}"


def parse_lastmod(lastmod_str: str) -> datetime.datetime | None:
    try:
        return datetime.datetime.fromisoformat(
            lastmod_str.strip().replace("Z", "+00:00")
        )
    except Exception:
        return None


# ── Stažení sitemap souboru ──────────────────────────────────────────────────

def fetch_sitemap(url: str) -> str | None:
    try:
        r = requests.get(url, headers=HEADERS, timeout=30)
        if r.status_code == 200:
            return r.text
        else:
            print(f"HTTP {r.status_code}")
            return None
    except Exception as e:
        print(f"chyba: {e}")
        return None


# ── Parsování sitemap souboru ────────────────────────────────────────────────

def parse_sitemap(xml: str, date_from: datetime.datetime, scrape_ts: str) -> list:
    soup    = BeautifulSoup(xml, "xml")
    records = []

    for url_el in soup.find_all("url"):
        loc_el     = url_el.find("loc")
        lastmod_el = url_el.find("lastmod")

        if not loc_el:
            continue

        url = loc_el.get_text().strip()

        # Pouze /entry/ URL
        if "/entry/" not in url:
            continue

        # Přeskočit záznamy bez lastmod
        if not lastmod_el or not lastmod_el.get_text().strip():
            continue

        pub_date = parse_lastmod(lastmod_el.get_text())
        if not pub_date:
            continue

        # Přeskočit starší než date_from
        if pub_date < date_from:
            continue

        pub_str = pub_date.strftime("%Y-%m-%d")
        title   = slug_to_title(url)

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

def scrape(date_from: datetime.datetime, output: str) -> None:
    scrape_ts   = datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    all_records = []
    seen_urls   = set()

    print("=" * 54)
    print("  Scraper 42tcen.com — sitemap")
    print("=" * 54)
    print(f"  Scraping od:  {date_from.date()}")
    print(f"  Výstup:       {output}")
    print(f"  Počet sitemaps: {len(SITEMAP_URLS)}")
    print()

    for sitemap_url in SITEMAP_URLS:
        # Extrahuj datum rozsahu z URL pro popis
        m = re.search(r"date_start=(\d{8})", sitemap_url)
        label = m.group(1) if m else sitemap_url
        print(f"  Stahuji {label} ...", end=" ")

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
    parser = argparse.ArgumentParser(description="Scraper 42tcen.com přes sitemap")
    parser.add_argument(
        "--date-from", type=str, default="2025-01-01",
        help="Scraping zpětně do tohoto data RRRR-MM-DD (výchozí: 2025-01-01)",
    )
    parser.add_argument(
        "--output", type=str, default="42tcen_sitemap.csv",
        help="Název výstupního CSV (výchozí: 42tcen_sitemap.csv)",
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