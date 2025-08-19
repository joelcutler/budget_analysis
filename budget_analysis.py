"""
Script Name:    budget_analysis.py
Author:         Joel Cutler
Revision Date:  2025-08-17
Description:    This script read from a csv and generates a budget analysis report.
Version:        v1.1
Patch Notes:
"""

import pandas as pd
from difflib import get_close_matches


#--------------------------------------------------------------------------------------------------
def coerce_amts(df, col):
    """
    Coerce the amounts in a DataFrame column to numeric, handling errors by converting them to NaN.
    """
    df[col] = pd.to_numeric(df[col], errors='coerce')
    return df

#--------------------------------------------------------------------------------------------------
def summarize_recurring(df, min_occurrences=1, fuzzy_cutoff=0.6):
    """
    Summarize recurring charges:
      - Only include negative amounts
      - Each repeating description stays separate
      - Minor variations of the same description can be grouped with fuzzy matching
    """

    # Clean column names
    df.columns = df.columns.str.strip().str.lower()

    # Detect columns
    desc_col = next(c for c in df.columns if "description" in c.lower())
    amt_col = next(c for c in df.columns if "amount" in c.lower())

    # Strip any whitespace and coerce amounts to numeric
    df[amt_col] = df[amt_col].astype(str).str.strip()  # remove stray spaces
    df[amt_col] = pd.to_numeric(df[amt_col], errors='coerce')  # convert to numeric

    # Only include negative amounts (charges)
    df = df[df[amt_col] <= 0]

    if df.empty:
        return pd.DataFrame(columns=["description", "count", "total", "avg_per_month"])

    # Count descriptions to identify recurring ones
    desc_counts = df[desc_col].value_counts()
    recurring_descriptions = [desc for desc, cnt in desc_counts.items() if cnt >= min_occurrences]

    summary = []

    for desc in recurring_descriptions:
        temp_df = df[df[desc_col] == desc]

        grouped_amounts = temp_df[amt_col].tolist()
        total = abs(sum(grouped_amounts))
        count = len(grouped_amounts)
        avg_per_month = abs(round(total / 12, 2))

        summary.append({
            "description": desc,
            "count": count,
            "total": total,
            "avg_per_month": avg_per_month
        })

    summary_df = pd.DataFrame(summary)

    if not summary_df.empty:
        summary_df = summary_df.sort_values(by='total', ascending=False).reset_index(drop=True)

    return summary_df


#!-------------------------------------------------------------------------------------------------
def main(accounts):
    """
    Process all accounts and generate recurring charges summaries,
    automatically fixing column types if needed.
    """

    for account in accounts:
        df = account['df']
        name = account['name']

        # Clean column names
        df.columns = df.columns.str.strip().str.lower()

        # Detect columns
        desc_col = next(c for c in df.columns if "description" in c.lower())
        amt_col = next(c for c in df.columns if "amount" in c.lower())

        # Force correct types
        df[desc_col] = df[desc_col].astype(str).str.strip()
        df[amt_col] = pd.to_numeric(df[amt_col], errors='coerce')

        # Drop rows with empty or invalid descriptions
        df = df[df[desc_col].notna() & (df[desc_col] != 'nan')]

        # Generate recurring charges summary
        summary_df = summarize_recurring(df, min_occurrences=2)

        # Print the summary
        print(f"\nRecurring charges summary for {name}:\n")
        print(summary_df)

        # Save to CSV
        summary_df.to_csv(f"./output/{name}_recurring_summary.csv", index=False)


#?-------------------------------------------------------------------------------------------------
if __name__ == "__main__":
    # Load CSVs
    card_8296_df = pd.read_csv('./input/Chase8296_Activity20240801_20250817_20250817.csv')
    card_2835_df = pd.read_csv('./input/Chase2835_Activity20240801_20250817_20250817.csv')
    # checking_df = pd.read_csv('./input/Chase8967_Activity_20250817.csv')
    # print(checking_df.head())
    # print(checking_df.dtypes)

    # List of account dicts
    accounts = [
        {"df": card_8296_df, "name": "Card_8296"},
        {"df": card_2835_df, "name": "Card_2835"},
        # {"df": checking_df, "name": "Checking"}
    ]

    main(accounts)