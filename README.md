# CCP-AT Comparison Engine

A Python-based tool with **Web GUI** to compare CCP (Client Clearing Protocol) and AT (Asia Trading) security whitelists and identify discrepancies.

## 📋 Overview

This tool combines two CCP data sheets and compares them against the AT whitelist to identify:
1. **Securities in CCP but not in AT** → Should be added to AT
2. **Securities in AT but not in CCP** → Should be reviewed for deletion or exception listing
3. **Securities in both with config mismatches** → Configuration settings need to be aligned
4. **Rules comparison** → Market rules alignment check

## 🌐 Web GUI (Recommended)

Modern web interface with real-time validation and easy file download.

**Start the server:**
```bash
python app.py
```

**Access:** http://127.0.0.1:5000

**Features:**
- Drag-and-drop file upload
- Real-time validation feedback
- Progress indicators
- Download results as individual files or ZIP bundle
- Mobile-responsive design
- Session-based result caching

## 💻 Command-Line Interface (Legacy)

For command-line execution, use the legacy script:

```bash
python compare_whitelists.py
```

---

## 📁 Project Structure

```
CCP AT Comparison Engine/
├── app.py                         ← Flask web application
├── compare_engine.py              ← Core comparison logic
├── compare_whitelists.py          ← Legacy CLI script
├── requirements.txt               ← Python dependencies
├── README.md                      ← User documentation
├── DEVELOPMENT.md                 ← Developer guide
├── QUICK_START.md                 ← Quick start guide
├── IMPROVEMENTS_SUMMARY.md        ← Changelog
├── templates/
│   └── index.html                 ← Web UI
├── static/
│   ├── script.js                  ← Frontend logic
│   └── style.css                  ← Styling
├── input_data/                    ← Input files (for CLI)
├── output_results/                ← Output files
├── temp_uploads/                  ← Temp upload storage
└── temp_results/                  ← Temp result storage
```

---

## 🚀 Quick Start

### Prerequisites
- Python 3.8+
- pip (Python package manager)

### Installation

1. **Install dependencies:**
```bash
pip install -r requirements.txt
```

Dependencies:
- Flask 3.0.0 (web framework)
- pandas 2.3.3 (data processing)
- openpyxl 3.1.5 (Excel handling)
- numpy 2.3.5 (numerical operations)
- Werkzeug 3.0.1 (WSGI utilities)

### Usage - Web GUI (Recommended)

1. **Start the server:**
```bash
python app.py
```

2. **Open in browser:**
Navigate to http://127.0.0.1:5000

3. **Upload files** (3 files required):
   - `AT_Whitelist.xlsx`
   - `CCP_Security_Whitelist.xlsx`
   - `CCP_Market_Rules.xlsx`
   - Note: Column_Mapping.xlsx is managed by the backend

4. **Run Comparison:**
Click "Run Comparison" button

5. **Download Results:**
- Download individual files (Requirement_1.xlsx, etc.)
- Download all as ZIP bundle

### Usage - Command-Line Interface

1. **Place input files** in `input_data/`:
   - `AT_Whitelist.xlsx`
   - `CCP_Security_Whitelist.xlsx`
   - `CCP_Market_Rules.xlsx`
   - `Column_Mapping.xlsx`

2. **Run the script:**
```bash
python compare_whitelists.py
```

3. **Check results** in `output_results/`

---

## 📊 Output Files

### Results Generated:
1. **Requirement_1.xlsx** - Securities in CCP, not in AT
2. **Requirement_2.xlsx** - Securities in AT, not in CCP
3. **Requirement_3.xlsx** - Configuration mismatches
4. **Requirement_4.xlsx** - Rules comparison

Each file includes:
- Detailed discrepancy records
- Matching criteria and metadata
- Summary statistics

### Result Statistics:
- Record counts per requirement
- Unique values per column
- Comparison timestamp
- File metadata

---

## 🔄 Comparison Workflow

1. **Load Files**: Read Excel files using openpyxl
2. **Normalize**: Standardize column names and whitespace
3. **Validate**: Check for required columns
4. **Detect**: Auto-detect symbol and exchange columns
5. **Merge**: Combine CCP Securities + Rules data
6. **Map**: Apply column mapping to align structures
7. **Create Keys**: Generate composite keys for comparison
8. **Compare**: Execute 4 comparison requirements
9. **Export**: Generate result Excel files

---

## ☁️ Deploy to PythonAnywhere (Free Tier)

Host this app for free on PythonAnywhere suitable for light internal usage.

1. Create a free account at pythonanywhere.com and open a Bash console.
2. Clone and install dependencies:

```bash
git clone https://github.com/inuka007/CCP-Comparison-Engine.git
cd CCP-Comparison-Engine
pip3.10 install --user -r requirements.txt
```

3. In the Web tab:
- Set “Source code” to your repo folder path.
- Point WSGI to this repo’s `wsgi.py`.
- Select Python 3.10 (or the version matching your `pip3.10`).

`wsgi.py` content (already included):

```python
import os
import sys
PROJECT_PATH = os.path.dirname(__file__)
if PROJECT_PATH not in sys.path:
   sys.path.append(PROJECT_PATH)
os.environ.setdefault('FLASK_ENV', 'production')
from app import app as application
```

4. Reload your app from the Web tab and open the provided subdomain.

Notes:
- Uploads/results are stored under `temp_uploads/` and `temp_results/` in your project folder.
- Free tier CPU is limited; keep files modest (UI enforces 50MB per file).
- If imports fail, verify the Web tab Python version and that dependencies were installed for that interpreter.


## ✨ Key Features

### Web GUI Features:
- ✅ File upload with real-time validation
- ✅ Progress indicators
- ✅ Individual file downloads
- ✅ ZIP bundle download option
- ✅ Mobile-responsive design
- ✅ Bootstrap 5 styling
- ✅ Session-based caching

### Comparison Features:
- ✅ Automatic column normalization
- ✅ Flexible symbol/exchange detection
- ✅ Column mapping for data alignment
- ✅ Configurable comparison keys
- ✅ Comprehensive mismatch detection
- ✅ Detailed result statistics

---

## 🛠️ Configuration

### Web Server (app.py)
```python
UPLOAD_FOLDER = 'temp_uploads'      # Temporary upload storage
MAPPING_FILE = 'Column_Mapping.xlsx' # Backend-managed mapping
MAX_FILE_SIZE = 50 * 1024 * 1024    # 50MB upload limit
ALLOWED_EXTENSIONS = {'xlsx', 'xls'} # Supported formats
```

### Comparison Engine (compare_engine.py)
Key configuration points:
- Column normalization rules
- Symbol column detection logic
- Composite key generation
- Comparison thresholds

---

## 📝 Input File Requirements

### AT_Whitelist.xlsx
- Must include symbol/security identifier column
- Should have exchange or similar grouping column
- Additional columns for configuration comparison

### CCP_Security_Whitelist.xlsx
- Security/symbol identifier column
- Exchange or market information
- Configuration data matching AT format

### CCP_Market_Rules.xlsx
- Rule identifiers and descriptions
- Exchange information
- Rule configuration data

### Column_Mapping.xlsx (Backend-Managed)
Maps column names from CCP format to AT format:
- ccp_column: Original CCP column name
- at_column: Target AT column name

---

## 🐛 Troubleshooting

### Port 5000 in use
```bash
# Windows
netstat -ano | findstr :5000
taskkill /PID <PID> /F

# Linux/Mac
lsof -ti:5000 | xargs kill -9
```

### File upload fails
- Check file format (must be .xlsx or .xls)
- Verify file size < 50MB
- Ensure file is not corrupted

### Column mismatch errors
- Verify Column_Mapping.xlsx includes required columns
- Check for extra spaces in column names
- Ensure file encoding is UTF-8

### Large file performance
- Consider splitting large datasets
- Increase timeout in production deployment
- Use chunked processing for very large files

---

## 📚 Documentation

- **QUICK_START.md** - Step-by-step quick start guide
- **DEVELOPMENT.md** - Developer documentation and architecture
- **IMPROVEMENTS_SUMMARY.md** - Detailed changelog of improvements

---

## 🔐 Security Notes

- Session keys are used for result isolation
- Temporary files are auto-cleaned after download
- File upload validation checks extensions and size
- No authentication layer (add in production)

---

## 📊 Version History

### v1.1 (Current)
- Web GUI improvements
- Static Column_Mapping backend loading
- Upload button success feedback
- ZIP bundle download
- CSS refinements
- Code optimization

### v1.0
- Initial release
- Web GUI with file upload
- Full comparison engine
- Result export

---

## 📞 Support

For issues or questions:
1. Check DEVELOPMENT.md for technical details
2. Review QUICK_START.md for usage examples
3. Check app.log for error messages

---

**Last Updated:** 2025-12-11  
**Current Version:** 1.1  
**Status:** Production Ready  
**Repository:** https://github.com/inuka007/CCP-Comparison-Engine (branch: gui)
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
