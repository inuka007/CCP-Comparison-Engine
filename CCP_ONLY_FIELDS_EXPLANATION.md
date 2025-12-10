# CCP-Only Fields Handling - Technical Documentation

## Overview

The comparison engine is designed to handle fields that exist in CCP (Client Clearing Protocol) but NOT in AT (Asia Trading). These are called **CCP-only fields** and are handled safely without throwing errors.

## How CCP-Only Fields Are Handled

### 1. **Identification Phase**
- Read the `Column_Mapping.xlsx` file
- Fields where the **AT column is EMPTY** are classified as "CCP-only"
- These are fields that have a CCP column name but no corresponding AT column

Example from the mapping file:
```
CCP Column                          AT Column
─────────────────────────────────────────────────
buy restricted                      [EMPTY]     ← CCP-only
sell restricted                     [EMPTY]     ← CCP-only
min qty alwd for auto cls scheduler [EMPTY]     ← CCP-only
```

### 2. **Comparison Basis**
The comparison ALWAYS uses these PRIMARY KEYS:
- **Symbol** (e.g., "AAPL")
- **Exchange** (e.g., "NASDAQ")

These form a **composite key**: `symbol|exchange` (e.g., "AAPL|NASDAQ")

**CCP-only fields are NEVER used for comparison** - they are completely excluded.

### 3. **Processing Logic**

#### Step A: Column Alignment
```python
# CCP-only fields are prefixed with 'ccp_only_' during alignment
# Example: buy restricted → ccp_only_buy_restricted
# These are stored but NOT used in any comparison logic
```

#### Step B: Config Mismatch Detection
```python
# Only MAPPED columns are compared
# Formula: Mapped columns = All mapping rows WHERE at_column IS NOT EMPTY

# CCP-only columns are excluded from this calculation:
mapped_cols = mapping[mapping["at_column"] != ""][["ccp_column", "at_column"]].values

# Result: Only fields that exist in BOTH CCP and AT are compared
```

#### Step C: Output Files

**Requirement 1: Securities in CCP but NOT in AT**
- Includes all CCP columns (with CCP-only fields)
- No error - CCP-only fields are simply part of the data

**Requirement 2: Securities in AT but NOT in CCP**
- Only AT columns are included
- CCP-only fields are not relevant

**Requirement 3: Config Mismatches**
- Only compares MAPPED columns (fields in both systems)
- CCP-only fields are completely ignored
- No config mismatch will be reported for CCP-only fields

---

## Example Scenario

### Input Data
**Column_Mapping.xlsx:**
```
CCP Column                    AT Column
────────────────────────────────────────────
minimum order value      →    minimum order value    [MAPPED]
buy restricted           →    [EMPTY]                [CCP-ONLY]
sell restricted          →    [EMPTY]                [CCP-ONLY]
max notional             →    max notional           [MAPPED]
```

**CCP Security Whitelist:**
```
symbol  exchange  minimum order value  buy restricted  sell restricted  max notional
AAPL    NASDAQ    100                  True           False            5000000
GOOGL   NYSE      50                   False          True             10000000
```

**AT Whitelist:**
```
symbol  exchange  minimum order value  max notional
AAPL    NASDAQ    100                  5000000
MSFT    NASDAQ    25                   3000000
```

### Comparison Output

**Requirement 1 (CCP not in AT): 1 record**
```
symbol  exchange  minimum order value  buy restricted  sell restricted  max notional  action
GOOGL   NYSE      50                   False          True             10000000      ADD to AT
```
✅ CCP-only fields (`buy restricted`, `sell restricted`) included without error

**Requirement 3 (Config Mismatches): 0 records**
```
Comparison Details:
  - Records in both: AAPL|NASDAQ
  - Mapped columns compared: 2 (minimum order value, max notional)
  - CCP-only fields ignored: 2 (buy restricted, sell restricted)
  - Mismatches found: 0 (both systems match on mapped fields)
```
✅ CCP-only fields never cause mismatch errors

---

## Key Points

✅ **No Errors** - CCP-only fields never cause exceptions  
✅ **Smart Comparison** - Only compares fields that exist in BOTH systems  
✅ **Clean Output** - CCP-only fields included in outputs but marked with prefix  
✅ **Transparent Logic** - Logs clearly show which fields are excluded  
✅ **Primary Key Based** - Comparison always uses symbol + exchange  

---

## How to Verify

Look at the script output during execution:

```
Aligning CCP columns according to mapping...
   Note: CCP-only fields are marked with 'ccp_only_' prefix
         These fields will NOT be used in config comparison

✔ CCP aligned to AT structure.
   Mapped columns (will be compared): 32
   CCP-only columns (excluded): 3
```

This shows:
- **32 columns** will be used for config comparison (mapped)
- **3 columns** are CCP-only and will be excluded

---

## Technical Implementation

```python
# Line 299-300 in compare_whitelists.py
# ONLY get mapped columns (excludes CCP-only)
mapped_cols = mapping[mapping["at_column"] != ""][["ccp_column", "at_column"]].values

# This ensures the loop at lines 307-320 only compares:
# - Fields that exist in CCP column list
# - AND have a corresponding AT column
# - CCP-only fields are automatically excluded
```

---

## Summary

The code is **production-ready** and handles CCP-only fields gracefully:
1. ✅ Identifies CCP-only fields (empty AT column in mapping)
2. ✅ Stores them separately with `ccp_only_` prefix
3. ✅ Excludes them from all comparisons
4. ✅ Includes them in output files (when CCP data is exported)
5. ✅ Never throws errors

**No changes needed - this is working as designed!**
