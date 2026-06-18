#!/usr/bin/env python3
"""
Scraper protiproud.info přes sitemap.
Jeden soubor: sitemap-posts.xml

Instalace:
  pip install requests beautifulsoup4 lxml

Použití:
  python scraper_protiproud_sitemap.py
  python scraper_protiproud_sitemap.py --date-from 2025-01-01
  python scraper_protiproud_sitemap.py --output protiproud.csv
"""

import csv
import datetime
import argparse
import hashlib
import sys
import re

import requests
from bs4 import BeautifulSoup

# ── Konfigurace ──────────────────────────────────────────────────────────────

SITEMAP_URL = "https://protiproud.info/sitemap-posts.xml"
SOURCE      = "Protiproud"
DATE_FROM   = datetime.datetime(2025, 1, 1, tzinfo=datetime.timezone.utc)

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
        "orban", "fico", "magyar", "brusel", "zahranicni", "domaci",
        "eu-", "ukraine", "ukrajna", "rusko", "zelenskyj", "putin",
        "parlament", "volen", "voleb",
    ]),
    ("ECONOMY", [
        "ekonom", "finance", "burza", "inflac", "rozpocet", "koruna",
        "energi", "ceny", "ropa", "akcie", "investic", "sankce", "dluh",
    ]),
    ("HEALTH", [
        "zdravi", "zdravot", "nemoc", "lekar", "vakcin", "pandemi",
        "covid", "mrna", "ockov",
    ]),
    ("CRIME", [
        "policie", "vrazd", "krimi", "soud", "korupce", "teror",
        "utok", "podvod", "gang", "mafia", "spionaz",
    ]),
    ("SOCIETY", [
        "migrac", "uprchl", "nelegalni", "migrant", "protest",
        "demonstrac", "cenzur", "propaganda", "dezinformac",
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
    /hysterie-kolem-poplatku-pro-verejnopravni-media-...
    → hysterie kolem poplatku pro verejnopravni media ...
    """
    slug = url.rstrip("/").split("/")[-1]
    return slug.replace("-", " ").strip()


def make_id(url: str) -> str:
    digest = hashlib.md5(url.encode()).hexdigest()[:8]
    return f"protiproud_{digest}"


def parse_lastmod(lastmod_str: str) -> datetime.datetime | None:
    try:
        # Formát může být "2026-04-22 16:44" nebo ISO
        s = lastmod_str.strip()
        # Zkus ISO formát
        try:
            return datetime.datetime.fromisoformat(s.replace("Z", "+00:00"))
        except Exception:
            pass
        # Zkus "YYYY-MM-DD HH:MM"
        return datetime.datetime.strptime(s, "%Y-%m-%d %H:%M").replace(
            tzinfo=datetime.timezone.utc
        )
    except Exception:
        return None


# ── Stažení a parsování ──────────────────────────────────────────────────────

def fetch_sitemap() -> str | None:
    try:
        r = requests.get(SITEMAP_URL, headers=HEADERS, timeout=30)
        if r.status_code == 200:
            return r.text
        else:
            print(f"  [CHYBA] HTTP {r.status_code}")
            return None
    except Exception as e:
        print(f"  [CHYBA] {e}")
        return None


def parse_sitemap(xml: str, date_from: datetime.datetime, scrape_ts: str) -> list:
    soup    = BeautifulSoup(xml, "xml")
    records = []

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
    scrape_ts = datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

    print("=" * 54)
    print("  Scraper Protiproud.info — sitemap")
    print("=" * 54)
    print(f"  Scraping od:  {date_from.date()}")
    print(f"  Výstup:       {output}")
    print()

    print(f"  Stahuji sitemap-posts.xml ...", end=" ")
    xml = fetch_sitemap()
    if xml is None:
        sys.exit(1)

    records = parse_sitemap(xml, date_from, scrape_ts)
    print(f"{len(records)} záznamů")

    # Statistiky
    from collections import Counter
    print(f"\n  Celkem záznamů: {len(records)}")

    domain_counts = Counter(r["domain"] for r in records)
    print("\n  Podle domény:")
    for domain, count in sorted(domain_counts.items(), key=lambda x: -x[1]):
        print(f"    {domain:<12} {count:>5}")

    # Uložení
    fieldnames = ["id", "text", "url", "source", "domain", "published", "scraped_at"]
    with open(output, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(records)

    print(f"\n✅ Uloženo {len(records)} záznamů → {output}")


# ── CLI ──────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="Scraper Protiproud.info přes sitemap")
    parser.add_argument(
        "--date-from", type=str, default="2025-01-01",
        help="Přeskočit záznamy starší než toto datum (výchozí: 2025-01-01)",
    )
    parser.add_argument(
        "--output", type=str, default="protiproud_sitemap.csv",
        help="Název výstupního CSV (výchozí: protiproud_sitemap.csv)",
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