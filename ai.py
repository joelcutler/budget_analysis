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
    raise ValueError(f"No matching column found for {candidates}")

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

    # Remove *codes that contain at least one digit
    desc = re.sub(r'\*\w*\d\w*', '', desc)

    # Remove remaining punctuation
    desc = re.sub(r'[^A-Z\s]', ' ', desc)

    # Collapse multiple spaces
    desc = re.sub(r'\s+', ' ', desc).strip()

    return desc

#--------------------------------------------------------------------------------------------------
def group_similar_descriptions(grouped, cutoff=0.85):
    """
    Merge similar normalized descriptions using fuzzy matching.
    """
    merged = {}
    for desc, stats in grouped.items():
        # Try to find a similar existing key
        match = get_close_matches(desc, merged.keys(), n=1, cutoff=cutoff)
        if match:
            key = match[0]
            merged[key]["count"] += stats["count"]
            merged[key]["total"] += stats["total"]
        else:
            merged[desc] = stats.copy()
    return merged

#--------------------------------------------------------------------------------------------------
def write_csv(output_file, grouped):
    """Write grouped summary to CSV."""
    os.makedirs(os.path.dirname(output_file), exist_ok=True)
    with open(output_file, "w", newline="", encoding="utf-8") as csvfile:
        writer = csv.writer(csvfile)
        writer.writerow(["Description", "Count", "Total", "Monthly Average"])
        for desc, stats in sorted(grouped.items(), key=lambda x: x[0]):
            if stats["count"] <= 1:
                continue  # only recurring
            avg_month = stats["total"] / 12
            writer.writerow([
                desc, 
                stats["count"], 
                f"${stats['total']:.2f}",       # format total as $X.XX
                f"${avg_month:.2f}"             # format avg per month as $X.XX
            ])
    print(f"✅ Wrote {output_file}")

#--------------------------------------------------------------------------------------------------
def process_account(account, path):
    transactions, headers = read_csv_dynamic(path)

    # Find columns dynamically
    desc_col = find_column(headers, ["desc"])
    amt_col = find_column(headers, ["amount", "amt"])

    grouped = defaultdict(lambda: {"count": 0, "total": 0.00})

    for row in transactions:
        desc_raw = row[desc_col].strip()
        try:
            amt = float(row[amt_col].replace(",", "").replace("$", ""))
        except:
            continue  # skip bad rows

        if amt >= 0:
            continue  # only include negative amounts
        amt = abs(amt)

        keyword = normalize_description(desc_raw)
        g = grouped[keyword]
        g["count"] += 1
        g["total"] += amt

    # Merge fuzzy matches
    merged = group_similar_descriptions(grouped)

    output_file = f"./output/{account}_summary.csv"
    write_csv(output_file, merged)

#--------------------------------------------------------------------------------------------------
def main(files):
    for account, path in files.items():
        if not os.path.exists(path):
            print(f"[WARN] {path} not found, skipping.")
            continue
        process_account(account, path)

#--------------------------------------------------------------------------------------------------
if __name__ == "__main__":
    files = {
    "Chase8296": "./input/Chase8296_Activity20240801_20250817_20250817.csv",
    "Chase2835": "./input/Chase2835_Activity20240801_20250817_20250817.csv",
    "Chase8967": "./input/Chase8967_Activity_20250817.csv"
    }

    main(files)
