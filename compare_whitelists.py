import pandas as pd
import numpy as np
from datetime import datetime
import os
from pathlib import Path
import sys
import shutil

# Fix encoding for Windows console
if sys.stdout.encoding != 'utf-8':
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

print("\n======================================")
print("      CCP-AT COMPARISON ENGINE")
print("======================================\n")

# ================================
# CONFIG – Update file names here
# ================================
# Get the directory where this script is located
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))

# Input folder
INPUT_DIR = os.path.join(SCRIPT_DIR, "input_data")
OUTPUT_DIR = os.path.join(SCRIPT_DIR, "output_results")

# Create output directory if it doesn't exist
os.makedirs(OUTPUT_DIR, exist_ok=True)

FILE_CCP_SEC = os.path.join(INPUT_DIR, "CCP_Security_Whitelist.xlsx")
FILE_CCP_RULES = os.path.join(INPUT_DIR, "CCP_Market_Rules.xlsx")
FILE_AT = os.path.join(INPUT_DIR, "AT_Whitelist.xlsx")
FILE_MAPPING = os.path.join(INPUT_DIR, "Column_Mapping.xlsx")

# Final output locations - 3 separate Excel files + 1 report
OUTPUT_REQ1_FILE = os.path.join(OUTPUT_DIR, "01_Securities_In_CCP_Not_In_AT.xlsx")
OUTPUT_REQ2_FILE = os.path.join(OUTPUT_DIR, "02_Securities_In_AT_Not_In_CCP.xlsx")
OUTPUT_REQ3_FILE = os.path.join(OUTPUT_DIR, "03_Securities_Config_Mismatch.xlsx")
REPORT_FILE = os.path.join(OUTPUT_DIR, "00_Comparison_Report.xlsx")

# ================================
# COLUMN NORMALIZER
# ================================
def normalize_columns(df):
    """
    Normalize column names: strip whitespace, replace spaces with underscores,
    handle multiple underscores, and convert to lowercase.
    """
    df.columns = (
        df.columns.astype(str)
        .str.strip()
        .str.replace(r"\s+", "_", regex=True)
        .str.replace(r"__+", "_", regex=True)
        .str.lower()
    )
    return df

# ================================
# FUNCTION TO CONFIRM KEY COLUMNS EXIST
# ================================
def require_columns(df, required_cols, source_name):
    """
    Ensures that the normalized dataframe contains all required columns.
    Raises a clean error if any are missing.
    """
    missing = [col for col in required_cols if col not in df.columns]
    if missing:
        raise Exception(
            f"❌ ERROR: Missing columns {missing} in {source_name}. "
            f"Available columns: {list(df.columns)}"
        )
    return df

def require_exchange(df, source_name):
    """
    Ensures that the normalized dataframe contains column 'exchange'.
    Raises a clean error if missing.
    """
    if "exchange" not in df.columns:
        raise Exception(
            f"❌ ERROR: No column named 'Exchange' found in {source_name}. "
            f"Please ensure it appears exactly as 'Exchange' (case-ignored)."
        )
    return df

# ================================
# IDENTIFY SYMBOL/SECURITY ID COLUMN
# ================================
def get_symbol_column(df):
    """
    Detects the symbol/security ID column.
    Looks for common names: symbol, security_id, isin, cusip, etc.
    """
    common_names = ['symbol', 'security_id', 'isin', 'cusip', 'identifier', 'secid']
    for col in common_names:
        if col in df.columns:
            return col
    
    # If not found, raise error
    raise Exception(
        f"❌ ERROR: Could not identify symbol/security column. "
        f"Available columns: {list(df.columns)}. "
        f"Expected one of: {common_names}"
    )


# ================================
# LOAD FILES
# ================================
print("Loading spreadsheets...")

try:
    ccp_sec_raw = pd.read_excel(FILE_CCP_SEC)
    ccp_rules_raw = pd.read_excel(FILE_CCP_RULES)
    at_raw = pd.read_excel(FILE_AT)
    mapping_raw = pd.read_excel(FILE_MAPPING)
    print("✔ Loaded all files.\n")
except FileNotFoundError as e:
    print(f"❌ ERROR: Could not find file: {e}")
    exit(1)


# ================================
# NORMALIZE COLUMN NAMES
# ================================
print("Normalizing column names...")

ccp_sec = normalize_columns(ccp_sec_raw.copy())
ccp_rules = normalize_columns(ccp_rules_raw.copy())
at = normalize_columns(at_raw.copy())
mapping = normalize_columns(mapping_raw.copy())

print("✔ Normalized all column names.\n")


# ================================
# VALIDATE EXCHANGE EXISTS
# ================================
print("Validating that 'exchange' column exists...")

ccp_sec = require_exchange(ccp_sec, "CCP Security Whitelist")
ccp_rules = require_exchange(ccp_rules, "CCP Market Rules")
at = require_exchange(at, "AT Whitelist")

print("✔ All files contain 'exchange'.\n")


# ================================
# DETECT SYMBOL COLUMNS
# ================================
print("Detecting symbol/security ID columns...")

ccp_symbol_col = get_symbol_column(ccp_sec)
at_symbol_col = get_symbol_column(at)

print(f"✔ CCP symbol column: '{ccp_symbol_col}'")
print(f"✔ AT symbol column: '{at_symbol_col}'\n")


# ================================
# MERGE CCP SEC + CCP RULES
# ================================
print("Merging CCP Security + CCP Rules...")
print(f"   CCP Rules will be merged on 'exchange' (many-to-one relationship)")

ccp_combined = pd.merge(
    ccp_sec,
    ccp_rules,
    on="exchange",
    how="left",
    validate="m:1"   # many symbols to one exchange config
)

print(f"✔ CCP merged successfully. Combined shape: {ccp_combined.shape}\n")


# ================================
# CLEAN MAPPING FILE
# mapping: ccp_column | at_column
# ================================
print("Preparing mapping file...")

mapping = mapping.dropna(how="all")
mapping = mapping.fillna("")

# Normalize mapped names
mapping["ccp_column"] = mapping["ccp_column"].str.lower().str.strip()
mapping["at_column"] = mapping["at_column"].str.lower().str.strip()

# Display mappings
print("Column Mappings (CCP → AT):")
for _, row in mapping.iterrows():
    ccp_col = row["ccp_column"]
    at_col = row["at_column"]
    status = "(CCP-only field)" if at_col == "" else f"→ {at_col}"
    print(f"   {ccp_col} {status}")

print("✔ Mapping cleaned.\n")


# ================================
# CREATE COMPOSITE KEY FOR COMPARISON
# ================================
print("Creating composite keys for comparison...")

# For CCP: use symbol + exchange as unique identifier
ccp_combined["composite_key"] = (
    ccp_combined[ccp_symbol_col].astype(str) + "|" + 
    ccp_combined["exchange"].astype(str)
)

# For AT: use symbol + exchange as unique identifier
at["composite_key"] = (
    at[at_symbol_col].astype(str) + "|" + 
    at["exchange"].astype(str)
)

print(f"✔ CCP records: {len(ccp_combined)}")
print(f"✔ AT records: {len(at)}\n")


# ================================
# ALIGN CCP → AT STRUCTURE
# ================================
print("Aligning CCP columns according to mapping...")
print("   Note: CCP-only fields are marked with 'ccp_only_' prefix")
print("         These fields will NOT be used in config comparison\n")

# Start with the symbol and exchange (primary comparison keys)
aligned_ccp = pd.DataFrame()
aligned_ccp[at_symbol_col] = ccp_combined[ccp_symbol_col]
aligned_ccp["exchange"] = ccp_combined["exchange"]
aligned_ccp["composite_key"] = ccp_combined["composite_key"]

# Count CCP-only vs mapped columns
ccp_only_count = 0
mapped_count = 0

# Map columns according to mapping file
for _, row in mapping.iterrows():
    ccp_col = row["ccp_column"]
    at_col = row["at_column"]

    # If AT column is empty, this is a CCP-ONLY field (not in AT)
    # Store separately and EXCLUDE from comparison
    if at_col == "":
        ccp_only_count += 1
        if ccp_col in ccp_combined.columns:
            aligned_ccp[f"ccp_only_{ccp_col}"] = ccp_combined[ccp_col]
        else:
            aligned_ccp[f"ccp_only_{ccp_col}"] = np.nan
        continue

    # Normal CCP → AT mapping: rename CCP column to AT column name
    mapped_count += 1
    if ccp_col in ccp_combined.columns:
        aligned_ccp[at_col] = ccp_combined[ccp_col]
    else:
        aligned_ccp[at_col] = np.nan

print(f"✔ CCP aligned to AT structure.")
print(f"   Mapped columns (will be compared): {mapped_count}")
print(f"   CCP-only columns (excluded): {ccp_only_count}\n")


# ================================
# REQUIREMENT 1: SYMBOLS IN CCP BUT NOT IN AT
# ================================
print("REQUIREMENT 1: Identifying symbols in CCP but not in AT...")

ccp_keys = set(ccp_combined["composite_key"])
at_keys = set(at["composite_key"])

missing_in_at = ccp_keys - at_keys
requirement_1 = ccp_combined[ccp_combined["composite_key"].isin(missing_in_at)].copy()
requirement_1["action"] = "ADD to AT Asia Whitelist"

print(f"✔ Found {len(requirement_1)} symbols in CCP but not in AT\n")


# ================================
# REQUIREMENT 2: SYMBOLS IN AT BUT NOT IN CCP
# ================================
print("REQUIREMENT 2: Identifying symbols in AT but not in CCP...")

extra_in_at = at_keys - ccp_keys
requirement_2 = at[at["composite_key"].isin(extra_in_at)].copy()
requirement_2["action"] = "REVIEW: Check activity/positions - DELETE or ADD to Exception List"

# Keep only essential columns to reduce file size
cols_to_keep = [at_symbol_col, "exchange", "action"] + [col for col in requirement_2.columns if col in at.columns]
cols_to_keep = list(dict.fromkeys(cols_to_keep))  # Remove duplicates
requirement_2 = requirement_2[[col for col in cols_to_keep if col in requirement_2.columns]]

print(f"✔ Found {len(requirement_2)} symbols in AT but not in CCP\n")


# ================================
# REQUIREMENT 3: CONFIG MISMATCHES (In both CCP and AT)
# ================================
print("REQUIREMENT 3: Identifying config mismatches...")
print("   Comparison basis: symbol + exchange (composite key)")
print("   Comparing ONLY mapped columns (CCP-only fields are excluded)\n")

common_keys = ccp_keys & at_keys
requirement_3_list = []

# Get ONLY mapped columns for comparison (EXCLUDES CCP-only fields where AT column is empty)
# This ensures we only compare fields that exist in BOTH systems
mapped_cols = mapping[mapping["at_column"] != ""][["ccp_column", "at_column"]].values
ccp_only_fields = mapping[mapping["at_column"] == ""]["ccp_column"].tolist()

print(f"   Total records with symbol+exchange in both CCP & AT: {len(common_keys)}")
print(f"   Mapped columns to compare: {len(mapped_cols)}")
print(f"   CCP-only columns (EXCLUDED): {len(ccp_only_fields)}")
if ccp_only_fields:
    print(f"   CCP-only fields excluded: {', '.join(ccp_only_fields[:3])}" + ("..." if len(ccp_only_fields) > 3 else ""))
print("   Processing comparisons...\n")

# Convert to sets for faster lookup
ccp_by_key = {key: ccp_combined[ccp_combined["composite_key"] == key].iloc[0] for key in common_keys}
at_by_key = {key: at[at["composite_key"] == key].iloc[0] for key in common_keys}

for key in common_keys:
    ccp_row = ccp_by_key[key]
    at_row = at_by_key[key]
    
    mismatches = []
    
    # Check only mapped columns for mismatches
    for ccp_col, at_col in mapped_cols:
        # Check if both columns exist
        if ccp_col in ccp_row.index and at_col in at_row.index:
            ccp_val = ccp_row[ccp_col]
            at_val = at_row[at_col]
            
            # Handle NaN comparisons
            if pd.isna(ccp_val) and pd.isna(at_val):
                continue
            elif pd.isna(ccp_val) or pd.isna(at_val):
                mismatches.append(f"{at_col} (CCP: {ccp_val}, AT: {at_val})")
            elif str(ccp_val).lower() != str(at_val).lower():
                mismatches.append(f"{at_col} (CCP: {ccp_val}, AT: {at_val})")
    
    if mismatches:
        requirement_3_list.append({
            "composite_key": key,
            at_symbol_col: ccp_row[ccp_symbol_col],
            "exchange": ccp_row["exchange"],
            "mismatched_fields": "; ".join(mismatches),
            "action": "UPDATE AT to match CCP and SETUP Market Exception rule in CCP"
        })

requirement_3 = pd.DataFrame(requirement_3_list)
print(f"✔ Found {len(requirement_3)} symbols with config mismatches\n")


# ================================
# GENERATE STATISTICS REPORT
# ================================
print("\n======================================")
print("        COMPARISON STATISTICS")
print("======================================\n")

total_ccp = len(ccp_combined)
total_at = len(at)
total_common = len(common_keys)

print(f"Total CCP Records:                    {total_ccp}")
print(f"Total AT Records:                     {total_at}")
print(f"Records in Both (No Action):          {total_common}")
print(f"\nACTION REQUIRED:")
print(f"  Requirement 1 (Add to AT):          {len(requirement_1)} records")
print(f"  Requirement 2 (Review in AT):       {len(requirement_2)} records")
print(f"  Requirement 3 (Config Mismatch):    {len(requirement_3)} records")
print(f"\nTotal Records Needing Action:         {len(requirement_1) + len(requirement_2) + len(requirement_3)}")
print(f"Timestamp:                            {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
print("======================================\n")


# ================================
# WRITE REQUIREMENT 1 OUTPUT
# ================================
print(f"Writing Requirement 1 (CCP not in AT)...")

try:
    # Prepare Req1 with all CCP columns
    req1_output = requirement_1.copy()
    req1_output["action"] = "ADD to AT Asia Whitelist"
    
    with pd.ExcelWriter(OUTPUT_REQ1_FILE, engine="openpyxl") as writer:
        req1_output.to_excel(writer, sheet_name="CCP_Not_In_AT", index=False)
    
    print(f"✔ Requirement 1 saved to: {OUTPUT_REQ1_FILE}")
except Exception as e:
    print(f"❌ Error writing Requirement 1: {e}\n")


# ================================
# WRITE REQUIREMENT 2 OUTPUT
# ================================
print(f"Writing Requirement 2 (AT not in CCP)...")

try:
    # Prepare Req2 with AT columns
    req2_output = requirement_2.copy()
    req2_output["action"] = "REVIEW: Check activity/positions - DELETE or ADD to Exception List"
    
    with pd.ExcelWriter(OUTPUT_REQ2_FILE, engine="openpyxl") as writer:
        req2_output.to_excel(writer, sheet_name="AT_Not_In_CCP", index=False)
    
    print(f"✔ Requirement 2 saved to: {OUTPUT_REQ2_FILE}")
except Exception as e:
    print(f"❌ Error writing Requirement 2: {e}\n")


# ================================
# WRITE REQUIREMENT 3 OUTPUT
# ================================
print(f"Writing Requirement 3 (Config Mismatches)...")

try:
    # Prepare Req3
    if len(requirement_3) > 0:
        req3_output = requirement_3.copy()
    else:
        req3_output = pd.DataFrame(columns=[at_symbol_col, "exchange", "mismatched_fields", "action"])
    
    with pd.ExcelWriter(OUTPUT_REQ3_FILE, engine="openpyxl") as writer:
        req3_output.to_excel(writer, sheet_name="Config_Mismatch", index=False)
    
    print(f"✔ Requirement 3 saved to: {OUTPUT_REQ3_FILE}")
except Exception as e:
    print(f"❌ Error writing Requirement 3: {e}\n")


# ================================
# WRITE SUMMARY REPORT
# ================================
print(f"\nWriting Comparison Summary Report...")

report_data = {
    "Metric": [
        "Total CCP Records (Merged)",
        "Total AT Records",
        "Records in Both (No Action Required)",
        "",
        "REQUIREMENT 1: Securities in CCP but NOT in AT",
        "  → Action: ADD to AT Asia Whitelist",
        "",
        "REQUIREMENT 2: Securities in AT but NOT in CCP",
        "  → Action: REVIEW activity/positions - DELETE or ADD to Exception List",
        "",
        "REQUIREMENT 3: Securities in BOTH with Config Mismatch",
        "  → Action: UPDATE AT to match CCP & Setup Market Exception rule",
        "",
        "TOTAL Records Requiring Action",
        "",
        "Report Generated"
    ],
    "Count/Value": [
        total_ccp,
        total_at,
        total_common,
        "",
        len(requirement_1),
        f"{len(requirement_1)} records",
        "",
        len(requirement_2),
        f"{len(requirement_2)} records",
        "",
        len(requirement_3),
        f"{len(requirement_3)} records",
        "",
        len(requirement_1) + len(requirement_2) + len(requirement_3),
        "",
        datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    ]
}

report_df = pd.DataFrame(report_data)

try:
    with pd.ExcelWriter(REPORT_FILE, engine="openpyxl") as writer:
        report_df.to_excel(writer, sheet_name="Summary", index=False)
    
    print(f"✔ Summary report saved to: {REPORT_FILE}\n")
except Exception as e:
    print(f"❌ Error writing REPORT_FILE: {e}\n")

print("\n======================================")
print("✔ PROCESS COMPLETED SUCCESSFULLY")
print("======================================\n")
print("📁 OUTPUT FILES GENERATED:\n")
print(f"  1. {OUTPUT_REQ1_FILE}")
print(f"     → {len(requirement_1)} securities in CCP but NOT in AT\n")
print(f"  2. {OUTPUT_REQ2_FILE}")
print(f"     → {len(requirement_2)} securities in AT but NOT in CCP\n")
print(f"  3. {OUTPUT_REQ3_FILE}")
print(f"     → {len(requirement_3)} securities with config mismatches\n")
print(f"  📊 {REPORT_FILE}")
print(f"     → Summary report with all statistics\n")
print("======================================\n")
