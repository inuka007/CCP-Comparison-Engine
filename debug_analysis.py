"""Debug script to analyze AT and CCP duplicate composite keys"""
import pandas as pd
import os

upload_dir = 'temp_uploads'
at_file = None
ccp_file = None
for f in os.listdir(upload_dir):
    fl = f.lower()
    if 'at_whitelist' in fl:
        at_file = os.path.join(upload_dir, f)
    if 'ccp_security' in fl:
        ccp_file = os.path.join(upload_dir, f)

print(f"AT file: {at_file}")
print(f"CCP file: {ccp_file}")

# Load and normalize AT
at = pd.read_excel(at_file)
at.columns = (at.columns.astype(str).str.strip()
              .str.replace(r"\s+", "_", regex=True)
              .str.replace(r"__+", "_", regex=True)
              .str.lower())

sym_col = None
for c in ['symbol', 'security_id', 'isin', 'cusip', 'identifier', 'secid']:
    if c in at.columns:
        sym_col = c
        break

print(f"\nAT symbol col: {sym_col}")
print(f"AT total rows: {len(at)}")

at['composite_key'] = (at[sym_col].astype(str).str.strip().str.upper() + '|' + 
                       at['exchange'].astype(str).str.strip().str.upper())

unique_at = at['composite_key'].nunique()
print(f"AT unique composite keys: {unique_at}")
print(f"AT duplicate rows (extra): {len(at) - unique_at}")

# Show duplicate details
dup_mask = at.duplicated(subset=['composite_key'], keep=False)
dups = at[dup_mask].sort_values('composite_key')
print(f"\nTotal rows involved in duplicate groups: {len(dups)}")
dup_key_count = dups['composite_key'].nunique()
print(f"Number of duplicate key groups: {dup_key_count}")

dup_counts = at[dup_mask].groupby('composite_key').size().sort_values(ascending=False)
print(f"\nTop 30 duplicate keys (key: count):")
for key, count in dup_counts.head(30).items():
    print(f"  {key}: {count} rows")

print(f"\nDuplicate count distribution (rows per key):")
print(dup_counts.value_counts().sort_index().to_string())

# Now check if any duplicate rows differ
print(f"\n{'='*60}")
print("Checking if AT duplicate rows are truly identical...")
diff_count = 0
for key in dup_counts.index[:10]:
    group = at[at['composite_key'] == key]
    # Check if all rows in group are identical (excluding composite_key)
    cols_to_check = [c for c in group.columns if c != 'composite_key']
    first_row = group.iloc[0][cols_to_check]
    for i in range(1, len(group)):
        other_row = group.iloc[i][cols_to_check]
        diffs = []
        for col in cols_to_check:
            v1 = str(first_row[col]) if pd.notna(first_row[col]) else ''
            v2 = str(other_row[col]) if pd.notna(other_row[col]) else ''
            if v1 != v2:
                diffs.append(f"{col}: [{v1}] vs [{v2}]")
        if diffs:
            diff_count += 1
            print(f"\n  {key} - row 0 vs row {i} DIFFER:")
            for d in diffs[:5]:
                print(f"    {d}")
        else:
            print(f"  {key} - row 0 vs row {i}: IDENTICAL")

# Also check CCP
print(f"\n{'='*60}")
print("Loading CCP Security Whitelist...")
ccp = pd.read_excel(ccp_file)
ccp.columns = (ccp.columns.astype(str).str.strip()
               .str.replace(r"\s+", "_", regex=True)
               .str.replace(r"__+", "_", regex=True)
               .str.lower())

ccp_sym = None
for c in ['symbol', 'security_id', 'isin', 'cusip', 'identifier', 'secid']:
    if c in ccp.columns:
        ccp_sym = c
        break

ccp['composite_key'] = (ccp[ccp_sym].astype(str).str.strip().str.upper() + '|' +
                        ccp['exchange'].astype(str).str.strip().str.upper())

print(f"CCP total rows: {len(ccp)}")
print(f"CCP unique composite keys: {ccp['composite_key'].nunique()}")
print(f"CCP duplicate rows: {len(ccp) - ccp['composite_key'].nunique()}")

ccp_keys = set(ccp['composite_key'])
at_keys = set(at['composite_key'])
print(f"\nSet analysis:")
print(f"  CCP unique keys: {len(ccp_keys)}")
print(f"  AT unique keys: {len(at_keys)}")
print(f"  Common (intersection): {len(ccp_keys & at_keys)}")
print(f"  CCP only (Req1): {len(ccp_keys - at_keys)}")
print(f"  AT only (Req2): {len(at_keys - ccp_keys)}")
