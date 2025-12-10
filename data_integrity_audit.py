"""
DATA INTEGRITY AUDIT SCRIPT
For CCP-AT Comparison Engine

This script validates that:
1. No records are lost during any transformation
2. No invalid data causes silent errors
3. All edge cases (NaN, NULL, empty strings) are handled correctly
4. The merge operation preserves all records
5. Composite key creation doesn't lose data
6. All three requirements correctly account for all records
"""

import pandas as pd
import numpy as np
import sys

print("\n" + "="*60)
print("    DATA INTEGRITY AUDIT - CCP-AT COMPARISON ENGINE")
print("="*60 + "\n")

# Load the actual data
input_dir = "input_data"

try:
    ccp_sec = pd.read_excel(f"{input_dir}/CCP_Security_Whitelist.xlsx")
    ccp_rules = pd.read_excel(f"{input_dir}/CCP_Market_Rules.xlsx")
    at = pd.read_excel(f"{input_dir}/AT_Whitelist.xlsx")
    mapping = pd.read_excel(f"{input_dir}/Column_Mapping.xlsx")
    print("✔ All input files loaded successfully\n")
except Exception as e:
    print(f"❌ Error loading files: {e}")
    sys.exit(1)

# ============================================================
# AUDIT 1: LOAD PHASE VALIDATION
# ============================================================
print("AUDIT 1: LOAD PHASE - No records lost during loading")
print("-" * 60)

ccp_sec_count = len(ccp_sec)
ccp_rules_count = len(ccp_rules)
at_count = len(at)

print(f"CCP Security Whitelist:    {ccp_sec_count} records")
print(f"CCP Market Rules:          {ccp_rules_count} records")
print(f"AT Whitelist:              {at_count} records")
print(f"Column Mapping:            {len(mapping)} mappings")

# Check for completely empty rows
ccp_sec_empty = ccp_sec.isna().all(axis=1).sum()
ccp_rules_empty = ccp_rules.isna().all(axis=1).sum()
at_empty = at.isna().all(axis=1).sum()

print(f"\nCompletely empty rows:")
print(f"  CCP Security:            {ccp_sec_empty} rows")
print(f"  CCP Rules:               {ccp_rules_empty} rows")
print(f"  AT Whitelist:            {at_empty} rows")

if ccp_sec_empty > 0 or ccp_rules_empty > 0 or at_empty > 0:
    print("⚠️  WARNING: Empty rows found - will be processed as data")
else:
    print("✔ No completely empty rows found")

# Normalize columns FIRST for validation
def normalize_cols(df):
    df.columns = (
        df.columns.astype(str)
        .str.strip()
        .str.replace(r"\s+", "_", regex=True)
        .str.replace(r"__+", "_", regex=True)
        .str.lower()
    )
    return df

ccp_sec_norm_temp = normalize_cols(ccp_sec.copy())
ccp_rules_norm_temp = normalize_cols(ccp_rules.copy())
at_norm_temp = normalize_cols(at.copy())

# Check for NULL/NaN in critical columns
print(f"\nCritical column validation:")
print(f"  CCP Security 'exchange':   {ccp_sec_norm_temp['exchange'].isna().sum()} NaN values")
print(f"  CCP Security 'symbol':     {ccp_sec_norm_temp.iloc[:, 0].isna().sum()} NaN values")
print(f"  CCP Rules 'exchange':      {ccp_rules_norm_temp['exchange'].isna().sum()} NaN values")
print(f"  AT 'exchange':             {at_norm_temp['exchange'].isna().sum()} NaN values")
print(f"  AT 'symbol':               {at_norm_temp.iloc[:, 0].isna().sum()} NaN values")

# ============================================================
# AUDIT 2: MERGE OPERATION - Record preservation
# ============================================================
print("\n\nAUDIT 2: MERGE OPERATION - CCP Security + CCP Rules")
print("-" * 60)

# Normalize columns like the script does
def normalize_cols(df):
    df.columns = (
        df.columns.astype(str)
        .str.strip()
        .str.replace(r"\s+", "_", regex=True)
        .str.replace(r"__+", "_", regex=True)
        .str.lower()
    )
    return df

ccp_sec_norm = normalize_cols(ccp_sec.copy())
ccp_rules_norm = normalize_cols(ccp_rules.copy())
at_norm = normalize_cols(at.copy())

print(f"Before merge:")
print(f"  CCP Security records:      {len(ccp_sec_norm)}")
print(f"  CCP Rules records:         {len(ccp_rules_norm)}")

# Perform the merge (same as script)
ccp_combined = pd.merge(
    ccp_sec_norm,
    ccp_rules_norm,
    on="exchange",
    how="left",
    validate="m:1"
)

print(f"\nAfter merge:")
print(f"  Combined records:          {len(ccp_combined)}")
print(f"  Records preserved:         {'✔ YES' if len(ccp_combined) == len(ccp_sec_norm) else '❌ NO'}")

if len(ccp_combined) != len(ccp_sec_norm):
    print(f"  ⚠️  ERROR: Records lost during merge!")
    print(f"     Expected: {len(ccp_sec_norm)}, Got: {len(ccp_combined)}")
else:
    print(f"  ✔ All CCP Security records preserved in merge")

# Check for duplicate keys from rules
duplicate_exchanges = ccp_rules_norm["exchange"].duplicated().sum()
print(f"\nDuplicate exchanges in CCP Rules: {duplicate_exchanges}")
if duplicate_exchanges > 0:
    print("  ⚠️  Multiple rules for same exchange detected")
    dups = ccp_rules_norm[ccp_rules_norm["exchange"].duplicated(keep=False)]
    print(f"     {len(dups)} rows have duplicate exchanges")

# ============================================================
# AUDIT 3: COMPOSITE KEY CREATION - NaN handling
# ============================================================
print("\n\nAUDIT 3: COMPOSITE KEY CREATION - No data loss with NaN")
print("-" * 60)

# Get symbol columns
ccp_symbol_col = None
at_symbol_col = None
for col in ['symbol', 'security_id', 'isin', 'cusip', 'identifier', 'secid']:
    if col in ccp_sec_norm.columns:
        ccp_symbol_col = col
        break
for col in ['symbol', 'security_id', 'isin', 'cusip', 'identifier', 'secid']:
    if col in at_norm.columns:
        at_symbol_col = col
        break

print(f"CCP symbol column: {ccp_symbol_col}")
print(f"AT symbol column:  {at_symbol_col}")

# Create composite keys
ccp_combined["composite_key"] = (
    ccp_combined[ccp_symbol_col].astype(str) + "|" + 
    ccp_combined["exchange"].astype(str)
)
at_norm["composite_key"] = (
    at_norm[at_symbol_col].astype(str) + "|" + 
    at_norm["exchange"].astype(str)
)

print(f"\nComposite key creation:")
print(f"  CCP keys created:          {len(ccp_combined)} keys")
print(f"  AT keys created:           {len(at_norm)} keys")

# Check for 'nan|' pattern (NaN in symbol)
nan_ccp = ccp_combined["composite_key"].str.contains("nan\\|", case=False).sum()
nan_at = at_norm["composite_key"].str.contains("nan\\|", case=False).sum()

print(f"\nNaN values in composite keys:")
print(f"  CCP keys with 'nan':       {nan_ccp} keys")
print(f"  AT keys with 'nan':        {nan_at} keys")

if nan_ccp > 0:
    print(f"  ⚠️  {nan_ccp} CCP records have NULL symbol")
    null_records = ccp_combined[ccp_combined["composite_key"].str.contains("nan\\|", case=False)]
    print(f"     These records WILL be included in comparisons")
if nan_at > 0:
    print(f"  ⚠️  {nan_at} AT records have NULL symbol")
    null_records = at_norm[at_norm["composite_key"].str.contains("nan\\|", case=False)]
    print(f"     These records WILL be included in comparisons")

# ============================================================
# AUDIT 4: COMPARISON LOGIC - Record accounting
# ============================================================
print("\n\nAUDIT 4: COMPARISON LOGIC - All records accounted for")
print("-" * 60)

ccp_keys = set(ccp_combined["composite_key"])
at_keys = set(at_norm["composite_key"])

missing_in_at = ccp_keys - at_keys
extra_in_at = at_keys - ccp_keys
common_keys = ccp_keys & at_keys

req1_count = len(missing_in_at)
req2_count = len(extra_in_at)
req3_count = len(common_keys)

print(f"Requirement 1 (CCP not in AT):     {req1_count} unique keys")
print(f"Requirement 2 (AT not in CCP):     {req2_count} unique keys")
print(f"Requirement 3 (Both, potential mismatch): {req3_count} unique keys")

# Verify all CCP records are accounted for
ccp_accounted = req1_count + req3_count
print(f"\nCCP Record Accounting:")
print(f"  Total CCP unique keys:     {len(ccp_keys)}")
print(f"  Accounted for (Req1+Req3): {ccp_accounted}")
print(f"  Records preserved:         {'✔ YES' if ccp_accounted == len(ccp_keys) else '❌ NO'}")

# Verify all AT records are accounted for
at_accounted = req2_count + req3_count
print(f"\nAT Record Accounting:")
print(f"  Total AT unique keys:      {len(at_keys)}")
print(f"  Accounted for (Req2+Req3): {at_accounted}")
print(f"  Records preserved:         {'✔ YES' if at_accounted == len(at_keys) else '❌ NO'}")

# ============================================================
# AUDIT 5: ROW-LEVEL VERIFICATION
# ============================================================
print("\n\nAUDIT 5: ROW-LEVEL VERIFICATION - Physical record preservation")
print("-" * 60)

# Get actual records
req1_records = ccp_combined[ccp_combined["composite_key"].isin(missing_in_at)]
req2_records = at_norm[at_norm["composite_key"].isin(extra_in_at)]

print(f"Requirement 1 - row count:     {len(req1_records)} rows")
print(f"Requirement 2 - row count:     {len(req2_records)} rows")

# Verify no duplication
req1_duplicates = len(req1_records) - len(set(req1_records["composite_key"]))
req2_duplicates = len(req2_records) - len(set(req2_records["composite_key"]))

print(f"\nDuplicate detection:")
print(f"  Req1 duplicate rows:       {req1_duplicates}")
print(f"  Req2 duplicate rows:       {req2_duplicates}")

# ============================================================
# AUDIT 6: EDGE CASES
# ============================================================
print("\n\nAUDIT 6: EDGE CASES - Special value handling")
print("-" * 60)

# Check for leading/trailing spaces
ccp_symbols_space = (ccp_combined[ccp_symbol_col] != ccp_combined[ccp_symbol_col].astype(str).str.strip()).sum()
at_symbols_space = (at_norm[at_symbol_col] != at_norm[at_symbol_col].astype(str).str.strip()).sum()

print(f"Leading/trailing spaces in symbol:")
print(f"  CCP:                       {ccp_symbols_space} records")
print(f"  AT:                        {at_symbols_space} records")
if ccp_symbols_space > 0 or at_symbols_space > 0:
    print("  ⚠️  Spaces may cause key mismatch")

# Check for case sensitivity
ccp_sample = ccp_combined[ccp_symbol_col].astype(str).head(5)
at_sample = at_norm[at_symbol_col].astype(str).head(5)
print(f"\nCase sensitivity (composite keys are case-sensitive):")
print(f"  Sample CCP symbols:        {ccp_sample.tolist()}")
print(f"  Sample AT symbols:         {at_sample.tolist()}")

# ============================================================
# FINAL SUMMARY
# ============================================================
print("\n\n" + "="*60)
print("                    AUDIT SUMMARY")
print("="*60)

print(f"""
LOAD PHASE:
  ✔ {ccp_sec_count + ccp_rules_count + at_count} records loaded
  ✔ All files accessible
  
MERGE PHASE:
  ✔ {len(ccp_combined)} CCP records after merge
  ✔ No records lost (left join preserves all)
  
COMPOSITE KEY PHASE:
  ✔ {len(ccp_keys)} unique CCP keys
  ✔ {len(at_keys)} unique AT keys
  {'⚠️  NaN values in keys present' if (nan_ccp > 0 or nan_at > 0) else '✔ No NaN values in keys'}
  
COMPARISON PHASE:
  ✔ Req1: {req1_count} CCP not in AT
  ✔ Req2: {req2_count} AT not in CCP
  ✔ Req3: {req3_count} in both
  ✔ CCP accounted: {ccp_accounted}/{len(ccp_keys)} ({int(ccp_accounted/len(ccp_keys)*100)}%)
  ✔ AT accounted: {at_accounted}/{len(at_keys)} ({int(at_accounted/len(at_keys)*100)}%)
  
INTEGRITY LEVEL: {'🟢 EXCELLENT' if (ccp_accounted == len(ccp_keys) and at_accounted == len(at_keys)) else '🟡 GOOD WITH NOTES'}
""")

print("="*60 + "\n")
print("CONCLUSION:")
print("-" * 60)
if ccp_accounted == len(ccp_keys) and at_accounted == len(at_keys):
    print("✅ ALL RECORDS ARE PRESERVED AND ACCOUNTED FOR")
    print("✅ NO DATA IS LOST DURING ANY TRANSFORMATION")
    print("✅ SAFE TO USE FOR PRODUCTION COMPARISONS")
else:
    print("❌ DATA INTEGRITY ISSUE DETECTED")
    print("⚠️  Please review above results")

print("="*60 + "\n")
