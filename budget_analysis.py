import csv
import os
import re
from collections import defaultdict
from difflib import get_close_matches

#--------------------------------------------------------------------------------------------------
def read_csv_dynamic(file_path):
    """Read CSV into list of dicts."""
    with open(file_path, newline="", encoding="utf-8-sig") as csvfile:
        reader = csv.DictReader(csvfile)
        return list(reader), reader.fieldnames

#--------------------------------------------------------------------------------------------------
def find_column(headers, candidates):
    """Find the first header that matches candidate keywords."""
    for h in headers:
        for c in candidates:
            if c in h.lower():
                return h
    return None  # return None if not found

#--------------------------------------------------------------------------------------------------
def normalize_description(desc):
    """
    Normalize descriptions to create grouping keywords:
      - Uppercase
      - Remove *codes that contain numbers
      - Keep *codes that are only letters
      - Remove other punctuation
      - Collapse extra spaces
    """
    desc = desc.upper()
    desc = re.sub(r'\*\w*\d\w*', '', desc)  # Remove *codes with numbers
    desc = re.sub(r'[^A-Z\s]', ' ', desc)   # Remove punctuation
    desc = re.sub(r'\s+', ' ', desc).strip()
    return desc

#--------------------------------------------------------------------------------------------------
def group_similar_descriptions(grouped, cutoff=0.85):
    """
    Merge similar normalized descriptions using fuzzy matching.
    """
    merged = {}
    for desc, stats in grouped.items():
        match = get_close_matches(desc, merged.keys(), n=1, cutoff=cutoff)
        if match:
            key = match[0]
            merged[key]["count"] += stats["count"]
            merged[key]["total"] += stats["total"]
            # Merge categories: keep first non-empty or "N/A"
            if merged[key]["category"] == "N/A" and stats["category"] != "N/A":
                merged[key]["category"] = stats["category"]
        else:
            merged[desc] = stats.copy()
    return merged

#--------------------------------------------------------------------------------------------------
def write_csv(output_file, grouped):
    """Write grouped summary to CSV."""
    os.makedirs(os.path.dirname(output_file), exist_ok=True)
    with open(output_file, "w", newline="", encoding="utf-8") as csvfile:
        writer = csv.writer(csvfile)
        writer.writerow(["Description", "Category", "Count", "Total", "Monthly Average"])
        for desc, stats in sorted(grouped.items(), key=lambda x: x[0]):
            if stats["count"] <= 1:
                continue
            avg_month = stats["total"] / 12
            writer.writerow([
                desc,
                stats["category"],
                stats["count"],
                f"${stats['total']:.2f}",
                f"${avg_month:.2f}"
            ])
    print(f"✅ Wrote {output_file}")

#--------------------------------------------------------------------------------------------------
def process_account(account, path):
    transactions, headers = read_csv_dynamic(path)
    desc_col = find_column(headers, ["desc"])
    amt_col = find_column(headers, ["amount", "amt"])
    cat_col = find_column(headers, ["category", "cat"]) or "N/A"

    grouped = defaultdict(lambda: {"count": 0, "total": 0.00, "category": "N/A"})

    for row in transactions:
        desc_raw = row[desc_col].strip()
        try:
            amt = float(row[amt_col].replace(",", "").replace("$", ""))
        except:
            continue
        if amt >= 0:
            continue
        amt = abs(amt)

        # Determine category if available
        category = row[cat_col].strip() if cat_col != "N/A" and row.get(cat_col) else "N/A"

        keyword = normalize_description(desc_raw)
        g = grouped[keyword]
        g["count"] += 1
        g["total"] += amt
        if g["category"] == "N/A":
            g["category"] = category

    merged = group_similar_descriptions(grouped)
    output_file = f"./output/{account}_summary.csv"
    write_csv(output_file, merged)

    # Return rows for combined CSV
    rows = []
    for desc, stats in merged.items():
        if stats["count"] <= 1:
            continue
        avg_month = stats["total"] / 12
        rows.append([desc, stats["category"], stats["count"], stats["total"], avg_month])
    return rows

#--------------------------------------------------------------------------------------------------
def merge_rows(rows, cutoff=0.85):
    """Merge combined rows using fuzzy matching to avoid duplicates across accounts."""
    grouped = {}
    for desc, category, count, total, avg in rows:
        if desc not in grouped:
            grouped[desc] = {"count": count, "total": total, "category": category}
        else:
            grouped[desc]["count"] += count
            grouped[desc]["total"] += total
            if grouped[desc]["category"] == "N/A" and category != "N/A":
                grouped[desc]["category"] = category

    return group_similar_descriptions(grouped, cutoff=cutoff)

#--------------------------------------------------------------------------------------------------
def main(files):
    all_rows = []

    for account, path in files.items():
        if not os.path.exists(path):
            print(f"[WARN] {path} not found, skipping.")
            continue
        account_rows = process_account(account, path)
        all_rows.extend(account_rows)

    # Merge duplicates across accounts
    merged_all = merge_rows(all_rows)

    # Sort by description
    sorted_all = dict(sorted(merged_all.items(), key=lambda x: x[0]))

    # Write combined CSV
    combined_file = "./output/all_accounts_summary.csv"
    write_csv(combined_file, sorted_all)

#--------------------------------------------------------------------------------------------------
if __name__ == "__main__":
    files = {
        "Chase7035": "./input/Chase7035_Activity20230819_20250819_20250819.CSV",
        "Chase8296": "./input/Chase8296_Activity20240801_20250817_20250817.csv",
        "Chase2835": "./input/Chase2835_Activity20240801_20250817_20250817.csv",
        "Chase8967": "./input/Chase8967_Activity_20250817.csv"
    }

    main(files)
