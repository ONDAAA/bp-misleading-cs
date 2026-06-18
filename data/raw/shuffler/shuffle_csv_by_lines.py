"""
Interleaved randomizace CSV souboru pro Label Studio.

Vstup:
    CSV s řádky uspořádanými po blocích kategorií (např. 160 NOT, 160 POT, 80 MIS).
    Jakákoliv struktura sloupců — skript pracuje s celými řádky, ne s konkrétními poli.

Výstup:
    Nový CSV s promíchaným pořadím záznamů.
    Žádné 3+ záznamy ze stejné kategorie nejdou za sebou.

Použití:
    python3 shuffle_csv_by_lines.py vstup.csv vystup.csv

    nebo (s explicitními velikostmi bloků):
    python3 shuffle_csv_by_lines.py vstup.csv vystup.csv 160,160,80

Reprodukovatelnost: random_state=42
"""

import sys
import csv
import random
import os

# === KONFIGURACE ===
RANDOM_STATE = 42
MAX_CONSECUTIVE = 2  # max 2 záznamy ze stejné kategorie za sebou


def interleaved_shuffle_by_groups(rows, group_sizes, max_consecutive=2, seed=42):
    """
    Promíchá záznamy mezi skupinami tak, aby žádné 3+ ze stejné skupiny
    nešly za sebou.
    
    Args:
        rows: seznam řádků (list of dicts/lists)
        group_sizes: seznam velikostí skupin (např. [160, 160, 80])
        max_consecutive: max kolik záznamů ze stejné skupiny může jít za sebou
        seed: random seed pro reprodukovatelnost
    
    Returns:
        Promíchaný seznam řádků.
    """
    rng = random.Random(seed)
    
    # Rozdělit řádky do skupin podle pořadí
    groups = []
    start = 0
    for i, size in enumerate(group_sizes):
        group = rows[start:start + size]
        # Náhodně promíchat uvnitř skupiny
        rng.shuffle(group)
        groups.append({"id": i, "records": group})
        start += size
    
    # Sestavit výsledek
    result = []
    last_group_id = None
    consecutive_count = 0
    
    while any(len(g["records"]) > 0 for g in groups):
        # Kandidáti: skupiny, které mají záznamy a nepřesáhly by max_consecutive
        candidates = []
        for g in groups:
            if len(g["records"]) == 0:
                continue
            if g["id"] == last_group_id and consecutive_count >= max_consecutive:
                continue
            candidates.append(g)
        
        # Fallback: pokud žádná skupina neprošla filtrem, vezmu všechny neprázdné
        if not candidates:
            candidates = [g for g in groups if len(g["records"]) > 0]
        
        # Vážený výběr — preferuju skupiny s víc zbývajícími záznamy
        weights = [len(g["records"]) for g in candidates]
        total = sum(weights)
        r = rng.uniform(0, total)
        cum = 0
        chosen = candidates[0]
        for g, w in zip(candidates, weights):
            cum += w
            if r <= cum:
                chosen = g
                break
        
        # Vezmu první záznam z vybrané skupiny
        record = chosen["records"].pop(0)
        result.append(record)
        
        # Update tracking
        if chosen["id"] == last_group_id:
            consecutive_count += 1
        else:
            consecutive_count = 1
            last_group_id = chosen["id"]
    
    return result


def check_max_run(rows, group_assignments):
    """Vrátí maximální délku sekvence stejné skupiny za sebou."""
    if not rows:
        return 0
    max_run = 1
    current_run = 1
    for i in range(1, len(rows)):
        if group_assignments[i] == group_assignments[i - 1]:
            current_run += 1
            max_run = max(max_run, current_run)
        else:
            current_run = 1
    return max_run


def main():
    # === Parsování argumentů ===
    if len(sys.argv) < 3:
        print("Použití: python3 shuffle_csv_by_lines.py vstup.csv vystup.csv [velikosti_bloků]")
        print("Příklad: python3 shuffle_csv_by_lines.py data.csv data_shuffled.csv 160,160,80")
        print()
        print("Pokud nezadáš velikosti bloků, skript se zeptá.")
        sys.exit(1)
    
    input_path = sys.argv[1]
    output_path = sys.argv[2]
    
    if not os.path.exists(input_path):
        print(f"❌ Soubor '{input_path}' nenalezen.")
        sys.exit(1)
    
    # === Načtení CSV ===
    print(f"📂 Načítám {input_path}...")
    with open(input_path, "r", encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f)
        fieldnames = reader.fieldnames
        rows = list(reader)
    
    print(f"   Načteno {len(rows)} řádků.")
    print(f"   Sloupce: {fieldnames}")
    
    # === Velikosti skupin ===
    if len(sys.argv) >= 4:
        group_sizes = [int(x) for x in sys.argv[3].split(",")]
    else:
        print()
        print("Zadej velikosti bloků oddělené čárkou (např. '160,160,80'):")
        user_input = input("   Velikosti: ").strip()
        group_sizes = [int(x) for x in user_input.split(",")]
    
    # Validace
    total_expected = sum(group_sizes)
    if total_expected != len(rows):
        print(f"❌ Součet velikostí ({total_expected}) neodpovídá počtu řádků ({len(rows)}).")
        sys.exit(1)
    
    print(f"✓ Skupiny: {group_sizes} (celkem {total_expected})")
    
    # === Promíchat ===
    print()
    print(f"🔀 Promíchávám (max {MAX_CONSECUTIVE} za sebou, random_state={RANDOM_STATE})...")
    
    # Pamatuju si, do které skupiny každý řádek patřil (pro statistiku)
    group_membership_orig = []
    for i, size in enumerate(group_sizes):
        group_membership_orig.extend([i] * size)
    
    # Před randomizací: dictionary řádek → původní skupina
    row_to_group = {id(row): group_membership_orig[i] for i, row in enumerate(rows)}
    
    # Promíchat
    shuffled = interleaved_shuffle_by_groups(rows, group_sizes,
                                              max_consecutive=MAX_CONSECUTIVE,
                                              seed=RANDOM_STATE)
    
    # Nová skupinová příslušnost po randomizaci
    group_after = [row_to_group[id(row)] for row in shuffled]
    
    max_run = check_max_run(shuffled, group_after)
    print(f"   ✓ Promícháno. Nejdelší sekvence stejné skupiny: {max_run}")
    print(f"   Prvních 20 záznamů (skupina): {group_after[:20]}")
    
    # Statistika rovnoměrnosti po blocích 50
    print()
    print("📊 Distribuce po blocích 50 záznamů:")
    block_size = 50
    for i in range(0, len(shuffled), block_size):
        block = group_after[i:i + block_size]
        counts = {g: block.count(g) for g in range(len(group_sizes))}
        counts_str = ", ".join([f"G{g}={c}" for g, c in counts.items()])
        print(f"   {i:4d}-{i + block_size - 1:4d}: {counts_str}")
    
    # === Uložit ===
    print()
    print(f"💾 Ukládám do {output_path}...")
    with open(output_path, "w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(shuffled)
    
    print(f"   ✓ Uloženo {len(shuffled)} řádků.")
    print()
    print("✅ Hotovo. Soubor je připraven k importu do Label Studio.")
    print(f"   Pro BP: 'Pořadí záznamů bylo randomizováno s ohledem na rovnoměrnost")
    print(f"   distribuce kategorií (max {MAX_CONSECUTIVE} stejné kategorie za sebou)")
    print(f"   s random_state={RANDOM_STATE} pro reprodukovatelnost.'")


if __name__ == "__main__":
    main()