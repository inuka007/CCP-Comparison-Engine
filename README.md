# CCP-AT Comparison Engine

A Python-based tool to compare CCP (Client Clearing Protocol) and AT (Asia Trading) security whitelists and identify discrepancies.

## 📋 Overview

This tool combines two CCP data sheets and compares them against the AT whitelist to identify:
1. **Securities in CCP but not in AT** → Should be added to AT
2. **Securities in AT but not in CCP** → Should be reviewed for deletion or exception listing
3. **Securities in both with config mismatches** → Configuration settings need to be aligned

## 📁 Project Structure

```
CCP AT Comparison Engine/
├── compare_whitelists.py          ← Main Python script
├── .gitignore                     ← Git ignore rules
├── README.md                      ← This file
├── input_data/                    ← INPUT FILES (Replace with new data for each run)
│   ├── CCP_Security_Whitelist.xlsx
│   ├── CCP_Market_Rules.xlsx
│   ├── AT_Whitelist.xlsx
│   └── Column_Mapping.xlsx
└── output_results/                ← OUTPUT FILES (Generated automatically)
    ├── 00_Comparison_Report.xlsx  ← Summary statistics
    ├── 01_Securities_In_CCP_Not_In_AT.xlsx
    ├── 02_Securities_In_AT_Not_In_CCP.xlsx
    └── 03_Securities_Config_Mismatch.xlsx
```

## 🚀 Quick Start

### Prerequisites
- Python 3.7+
- pandas
- numpy
- openpyxl

### Installation
```bash
pip install pandas numpy openpyxl
```

### Usage

1. **Place input files** in the `input_data/` folder:
   - `CCP_Security_Whitelist.xlsx`
   - `CCP_Market_Rules.xlsx`
   - `AT_Whitelist.xlsx`
   - `Column_Mapping.xlsx`

2. **Run the script**:
   ```bash
   python compare_whitelists.py
   ```

3. **Review results** in `output_results/` folder

## 📊 Output Files

### 00_Comparison_Report.xlsx
Summary statistics including:
- Total CCP Records
- Total AT Records
- Count of records needing action per requirement

### 01_Securities_In_CCP_Not_In_AT.xlsx
Securities that exist in CCP but not in AT (should be added)

### 02_Securities_In_AT_Not_In_CCP.xlsx
Securities that exist in AT but not in CCP (should be reviewed)

### 03_Securities_Config_Mismatch.xlsx
Securities in both systems with configuration mismatches

## 🔄 Workflow

1. **Combine CCP Data**: Merges CCP Security Whitelist + CCP Market Rules on `exchange` field
2. **Normalize Columns**: Handles case sensitivity and spacing variations
3. **Map Columns**: Uses Column_Mapping file to align CCP → AT structure
4. **Compare**: Performs 3-way comparison
5. **Generate Reports**: Creates 4 Excel output files

## 🛠️ Key Features

✅ **Case-Insensitive Matching** - Handles column name variations  
✅ **Composite Key Identification** - Uses symbol + exchange for unique identification  
✅ **CCP Data Merging** - Correctly merges Security Whitelist with Market Rules  
✅ **Column Mapping** - Supports field name differences between CCP and AT  
✅ **Batch Processing** - Efficient processing of large datasets  
✅ **Detailed Reporting** - Clear statistics and actionable insights  

## 📝 Column Mapping

The `Column_Mapping.xlsx` file maps CCP column names to AT column names:

| CCP Column | AT Column | Status |
|-----------|-----------|--------|
| minimum ord value | minimum order value | Mapped |
| buy restricted | | CCP-only |
| sell restricted | | CCP-only |
| ... | ... | ... |

## ⚙️ Configuration

All configuration is in the script's CONFIG section:
- `INPUT_DIR`: Location of input files
- `OUTPUT_DIR`: Location for output files
- File names are auto-detected from the folders

## 🔍 Troubleshooting

### Missing Column Error
Ensure all input files have the required columns with proper naming.

### Permission Denied Error
Close any open Excel files that are being processed.

### No Records Found
Verify that the composite key (symbol + exchange) is correctly identified.

## 📞 Support

For issues or questions, please contact your system administrator.

## 📄 License

Internal use only.

---

**Last Updated**: December 5, 2025  
**Version**: 1.0
