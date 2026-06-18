#!/usr/bin/env python3
import pandas as pd
import sys

path = "merged.csv" if len(sys.argv) < 2 else sys.argv[1]

print(f"Načítám {path} ...")
df = pd.read_csv(path)

print(f"\nCelkem záznamů: {len(df):,}")
print(f"\nPočet záznamů podle source:")
print("-" * 35)

counts = df["source"].value_counts()
for source, count in counts.items():
    pct = count / len(df) * 100
    print(f"  {source:<20} {count:>7,}  ({pct:.1f} %)")