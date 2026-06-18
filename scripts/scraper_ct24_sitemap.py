#!/usr/bin/env python3
"""
Scraper ČT24 přes sitemap — bez Playwright, bez cookie banneru.
Stahuje sitemap_articles_1.xml, _2.xml, ... dokud nenarazí na staré záznamy.

Instalace:
  pip install requests beautifulsoup4

Použití:
  python scraper_ct24_sitemap.py
  python scraper_ct24_sitemap.py --date-from 2025-01-01
  python scraper_ct24_sitemap.py --output ct24.csv
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

SITEMAP_BASE = "https://ct24.ceskatelevize.cz/sitemaps/sitemap_articles_{n}.xml"
SOURCE       = "CT24"
BUCKET       = "NOT_MISLEADING"
DATE_FROM    = datetime.datetime(2025, 1, 1, tzinfo=datetime.timezone.utc)

# Žádné sekce se nepřeskakují — stahuje se vše
SKIP_SECTIONS: set = set()

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    )
}

# ── Mapování sekce z URL → doména ────────────────────────────────────────────

SECTION_TO_DOMAIN = {
    "domaci":    "POLITICS",
    "svet":      "POLITICS",
    "ekonomika": "ECONOMY",
    "krimi":     "CRIME",
    "veda":      "OTHER",
    "sport":     "OTHER",
    "kultura":   "OTHER",
    "media":     "OTHER",
    "regiony":   "SOCIETY",
}


def detect_section(url: str) -> str:
    """Vytáhne sekci z URL — druhý segment za /clanek/"""
    m = re.search(r"/clanek/([^/]+)/", url)
    return m.group(1) if m else "other"


def detect_domain(section: str) -> str:
    return SECTION_TO_DOMAIN.get(section, "OTHER")


def slug_to_title(url: str) -> str:
    """
    Dekóduje titulek z URL slugu.
    /clanek/svet/trump-americke-namornictvo-zautocilo-372559
    → Trump americke namornictvo zautocilo
    """
    m = re.search(r"/clanek/[^/]+/(.+?)(?:-\d+)?$", url)
    if not m:
        return ""
    slug = m.group(1)
    # Odstraní koncové číslo ID
    slug = re.sub(r"-\d+$", "", slug)
    return slug.replace("-", " ").strip()


def make_id(url: str) -> str:
    digest = hashlib.md5(url.encode()).hexdigest()[:8]
    return f"ct24_{digest}"


def parse_lastmod(lastmod_str: str) -> datetime.datetime | None:
    """Parsuje ISO datum z lastmod tagu."""
    try:
        return datetime.datetime.fromisoformat(
            lastmod_str.strip().replace("Z", "+00:00")
        )
    except Exception:
        return None


# ── Stažení jednoho sitemap souboru ─────────────────────────────────────────

def fetch_sitemap(n: int) -> str | None:
    """Stáhne sitemap soubor číslo n. Vrátí XML text nebo None."""
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
    """
    Parsuje XML sitemapy a vrátí (záznamy, stop).
    stop=True znamená že jsme narazili na článek starší než date_from.
    """
    soup    = BeautifulSoup(xml, "xml")
    records = []
    stop    = False

    for url_el in soup.find_all("url"):
        loc_el     = url_el.find("loc")
        lastmod_el = url_el.find("lastmod")

        if not loc_el:
            continue

        url      = loc_el.get_text().strip()
        section  = detect_section(url)

        # Přeskočit irelevantní sekce
        if section in SKIP_SECTIONS:
            continue

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
            "id":           make_id(url),
            "text":         title,
            "url":          url,
            "source":       SOURCE,
            "domain":       detect_domain(section),
            "published":    pub_str,
            "scraped_at":   scrape_ts,
        })

    return records, stop


# ── Hlavní scraper ───────────────────────────────────────────────────────────

def scrape(date_from: datetime.datetime, output: str, max_files: int | None = None) -> None:
    scrape_ts   = datetime.datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ")
    all_records = []
    seen_urls   = set()

    print("=" * 54)
    print("  Scraper ČT24 — sitemap")
    print("=" * 54)
    print(f"  Scraping od:  {date_from.date()}")
    print(f"  Výstup:       {output}")
    print()

    n = 1
    while True:
        print(f"  Stahuji sitemap_articles_{n}.xml ...", end=" ")
        xml = fetch_sitemap(n)

        if xml is None:
            print(f"nenalezeno — konec")
            break

        records, stop = parse_sitemap(xml, date_from, scrape_ts)

        # Deduplikace
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

        if max_files is not None and n >= max_files:
            print(f"  ℹ Dosažen limit {max_files} souborů — zastavuji")
            break

        n += 1
        time.sleep(0.5)  # ohleduplná pauza

    # Statistiky
    from collections import Counter
    print(f"\n  Celkem unikátních záznamů: {len(all_records)}")

    domain_counts = Counter(r["domain"] for r in all_records)
    print("\n  Podle domény:")
    for domain, count in sorted(domain_counts.items(), key=lambda x: -x[1]):
        print(f"    {domain:<12} {count:>5}")

    section_counts = Counter(
        re.search(r"/clanek/([^/]+)/", r["url"]).group(1)
        if re.search(r"/clanek/([^/]+)/", r["url"]) else "?"
        for r in all_records
    )
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
    parser = argparse.ArgumentParser(description="Scraper ČT24 přes sitemap")
    parser.add_argument(
        "--max-files", type=int, default=None,
        help="Maximální počet sitemap souborů ke stažení (výchozí: všechny)",
    )
    parser.add_argument(
        "--sitemap-base", type=str,
        default="https://ct24.ceskatelevize.cz/sitemaps/sitemap_articles_{n}.xml",
        help="Šablona URL sitemapů — {n} se nahradí číslem souboru",
    )
    parser.add_argument(
        "--date-from", type=str, default="2025-01-01",
        help="Scraping zpětně do tohoto data RRRR-MM-DD (výchozí: 2025-01-01)",
    )
    parser.add_argument(
        "--output", type=str, default="ct24_sitemap.csv",
        help="Název výstupního CSV (výchozí: ct24_sitemap.csv)",
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