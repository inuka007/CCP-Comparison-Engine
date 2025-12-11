# Development Guide - CCP-AT Comparison Engine

## Project Structure

```
CCP-Comparison-Engine/
├── app.py                      # Flask web application (GUI)
├── compare_engine.py           # Core comparison logic (refactored from CLI)
├── compare_whitelists.py       # Legacy CLI version (command-line interface)
├── requirements.txt            # Python dependencies
├── templates/
│   └── index.html             # Web UI (Bootstrap 5 + vanilla JS)
├── static/
│   ├── script.js              # Frontend JavaScript
│   └── style.css              # Custom CSS styling
├── input_data/                # Input Excel files (for CLI version)
├── output_results/            # Output results folder
├── temp_uploads/              # Temporary uploaded files (auto-cleaned)
├── temp_results/              # Temporary result files (auto-cleaned)
├── README.md                  # User-facing documentation
├── QUICK_START.md             # Quick start guide
├── .gitignore                 # Git ignore rules
└── IMPROVEMENTS_SUMMARY.md    # Detailed improvements changelog
```

---

## Core Components

### 1. **app.py** (Flask Web Application)
**Purpose:** Provides web GUI interface for file upload, comparison, and download

**Key Features:**
- File upload and validation API endpoints
- Comparison execution engine interface
- Result caching and session management
- ZIP bundle download functionality
- CORS-ready structure

**Key Endpoints:**
- `GET /` - Render home page
- `POST /api/upload` - Upload and validate files
- `POST /api/compare` - Run comparison analysis
- `GET /api/download/{requirement}` - Download individual result file
- `GET /api/download-zip` - Download all results as ZIP

**Configuration:**
- `UPLOAD_FOLDER`: Temporary file storage
- `MAPPING_FILE`: Static Column_Mapping.xlsx path (backend-managed)
- `MAX_FILE_SIZE`: 50MB upload limit
- `RESULTS_CACHE`: In-memory result caching by session ID

### 2. **compare_engine.py** (Core Comparison Logic)
**Purpose:** Encapsulates all comparison logic in a reusable class

**Main Class: `ComparisonEngine`**
- **Initialization:** Loads file paths
- **compare():** Main workflow orchestrator
- **Private Methods:**
  - `_load_files()` - Read Excel files
  - `_normalize_columns()` - Standardize column names
  - `_validate_columns()` - Verify required columns
  - `_detect_symbol_columns()` - Auto-detect symbol/exchange columns
  - `_merge_ccp()` - Combine CCP Securities + Rules
  - `_prepare_mapping()` - Prepare column mapping
  - `_create_composite_keys()` - Create comparison keys
  - `_align_ccp_structure()` - Align to AT structure
  - `_run_requirements()` - Execute 4 comparison requirements
  - `_generate_statistics()` - Calculate result stats

**Custom Exceptions:**
- `ValidationError` - Raised on file validation failure
- `ComparisonError` - Raised on comparison logic failure

**Workflow:**
1. Load input files
2. Normalize and validate columns
3. Detect key columns (symbol, exchange)
4. Merge/prepare CCP data
5. Create composite keys
6. Run 4 requirements:
   - Req 1: Securities in CCP, not in AT
   - Req 2: Securities in AT, not in CCP
   - Req 3: Security configuration mismatches
   - Req 4: Rules comparison
7. Generate statistics and return results

### 3. **compare_whitelists.py** (Legacy CLI)
**Purpose:** Original command-line interface (kept for reference)

**Usage:**
```bash
python compare_whitelists.py
```

**Note:** This script contains the same logic as `compare_engine.py` but is not refactored into a class. Use for CLI execution or reference only.

### 4. **templates/index.html** (Web UI)
**Features:**
- Step-by-step UI workflow
- Real-time file validation
- Progress indicators
- Result export options (individual + ZIP bundle)
- Bootstrap 5 responsive design

**Key Sections:**
1. Step 1: File Upload & Validation
2. Step 2: Run Comparison
3. Step 3: Results & Downloads

### 5. **static/script.js** (Frontend Logic)
**Key Functions:**
- `handleFileSelect()` - Process selected files
- `uploadFiles()` - Submit files to backend
- `runComparison()` - Trigger comparison endpoint
- `downloadResults()` - Download individual or ZIP results
- `displayResults()` - Render results in UI

**State Management:**
- File selection tracking
- Upload progress feedback
- Comparison status updates
- Result caching

### 6. **static/style.css** (UI Styling)
**Features:**
- Modern card-based layout
- Smooth transitions and hover effects
- Alert styling with visual hierarchy
- Button state feedback
- Responsive grid design
- Bootstrap 5 integration

---

## Key Improvements (Version 1.1)

### Task 1: Static Column Mapping
- Removed requirement to upload Column_Mapping.xlsx
- `MAPPING_FILE` constant loads from backend
- Automatic injection into comparison engine

### Task 2: Upload Button Feedback
- Success state with checkmark icon
- Button disabled after successful upload
- Color change from blue (primary) to green (success)

### Task 3: ZIP Bundle Download
- New `/api/download-zip` endpoint
- Creates ZIP with all 4 Excel files + README.txt
- Prominent UI button for easy access

### Task 4: CSS Refinements
- Enhanced button styling (hover, active, disabled states)
- Alert border-left styling for better visual hierarchy
- Form check improvements
- Responsive design maintained

### Task 5: Code Optimization
- Removed debug logging
- Optimized imports (removed unused `Path`)
- PEP8 compliance
- Consistent code structure

---

## Running the Application

### Web GUI (Recommended)
```bash
python app.py
# Navigate to http://127.0.0.1:5000
```

### Command-Line Interface
```bash
python compare_whitelists.py
```

---

## Data Flow

### Web GUI Flow
```
User Upload Files (3)
      ↓
/api/upload (validation)
      ↓
/api/compare (execute engine)
      ↓
Results cached in RESULTS_CACHE
      ↓
/api/download-* (download results)
```

### Comparison Engine Flow
```
File Paths Dict
      ↓
Load Excel Files
      ↓
Normalize & Validate Columns
      ↓
Detect Symbol Columns
      ↓
Merge CCP Data
      ↓
Create Composite Keys
      ↓
Run 4 Requirements
      ↓
Generate Statistics
      ↓
Return Results Dict
```

---

## Dependencies

```
Flask==3.0.0
pandas==2.3.3
openpyxl==3.1.5
numpy==2.3.5
Werkzeug==3.0.1
```

Install with:
```bash
pip install -r requirements.txt
```

---

## Logging

**Locations:**
- Console output (StreamHandler)
- `app.log` file (FileHandler)

**Log Levels:**
- `INFO` - Workflow milestones
- `WARNING` - Non-critical issues
- `ERROR` - Critical failures

**View Logs:**
```bash
tail -f app.log          # Unix/Linux/Mac
Get-Content app.log -Tail 10  # Windows PowerShell
```

---

## Testing & Validation

### Test File Requirements
- **AT_Whitelist.xlsx** - AT whitelist data
- **CCP_Security_Whitelist.xlsx** - CCP securities
- **CCP_Market_Rules.xlsx** - CCP rules
- **Column_Mapping.xlsx** - Column mappings (backend-managed, optional upload)

### Expected Outputs
1. `Requirement_1.xlsx` - CCP securities not in AT
2. `Requirement_2.xlsx` - AT securities not in CCP
3. `Requirement_3.xlsx` - Configuration mismatches
4. `Requirement_4.xlsx` - Rules comparison

### Result Statistics
Each output includes:
- Record count
- Unique values per column
- Timestamp
- Comparison metadata

---

## Git Workflow

### Current Branch: `gui`

**Recent Changes:**
- [v1.1] Added 5 major improvements (static mapping, upload feedback, ZIP download, CSS refinements, code optimization)
- [v1.0] Initial web GUI release with full comparison logic

### Commit & Push
```bash
git add .
git commit -m "Improvements: static mapping, upload feedback, ZIP download, UI refinement"
git push origin gui
```

---

## Troubleshooting

### Common Issues

**Port 5000 already in use:**
```bash
# Windows
netstat -ano | findstr :5000
taskkill /PID <PID> /F

# Linux/Mac
lsof -ti:5000 | xargs kill -9
```

**File encoding issues:**
- Ensure Excel files are UTF-8 compatible
- Use openpyxl for proper Excel handling

**Memory issues with large files:**
- Increase `MAX_FILE_SIZE` in app.py if needed
- Consider chunked processing for very large datasets

**Missing Column_Mapping.xlsx:**
- Place file in project root directory
- Ensure `MAPPING_FILE` path is correct in app.py

---

## Performance Considerations

- **Result Caching:** Uses in-memory dictionary (RESULTS_CACHE) keyed by session
- **File Upload:** Stored in `temp_uploads/` and auto-cleaned after processing
- **ZIP Generation:** Uses BytesIO for in-memory compression
- **DataFrame Operations:** Optimized with pandas vectorization

---

## Future Enhancements

- [ ] Database persistence for results history
- [ ] Drag-and-drop file upload
- [ ] Progress bar for long-running comparisons
- [ ] CSV export option
- [ ] Dark mode theme
- [ ] Role-based access control
- [ ] Scheduled/automated comparisons
- [ ] Webhook notifications

---

**Last Updated:** 2025-12-11  
**Version:** 1.1  
**Status:** Production Ready
