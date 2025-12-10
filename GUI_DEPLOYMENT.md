# CCP-AT Comparison Engine - GUI Edition (v2.0)

## Overview

This is a web-based GUI for the CCP-AT Comparison Engine that allows users to:

1. **Upload Excel Files** - Upload the 4 required Excel files with drag-and-drop support
2. **Validate Files** - Automatic validation of file format, required columns, and data integrity
3. **Run Comparison** - Execute the comparison analysis between CCP and AT whitelists
4. **View Results** - Preview results in a responsive web interface with statistics
5. **Download Exports** - Download individual requirement results or summary reports as Excel files

## System Requirements

- **Python**: 3.8 or higher
- **Operating System**: Windows, macOS, or Linux
- **Browser**: Chrome, Firefox, Safari, or Edge (modern version)
- **Disk Space**: Minimum 100MB for application and temporary files

## Installation

### Step 1: Clone or Navigate to Project Directory

```bash
cd "c:\Users\InukaWeerasekara\Downloads\CCP AT Comparison Engine"
```

### Step 2: Ensure You're on the GUI Branch

```bash
git checkout gui
```

### Step 3: Create Virtual Environment (Recommended)

```bash
# Windows
python -m venv venv
venv\Scripts\activate

# macOS/Linux
python3 -m venv venv
source venv/bin/activate
```

### Step 4: Install Dependencies

```bash
pip install -r requirements.txt
```

## Running the Application

### Start the Web Server

```bash
python app.py
```

The application will start on `http://127.0.0.1:5000`

### Access in Browser

Open your web browser and navigate to:

```
http://localhost:5000
```

## Usage Guide

### Step 1: Upload Files

1. Click the upload area or drag-and-drop your Excel files
2. Ensure all 4 required files are selected:
   - `CCP_Security_Whitelist.xlsx`
   - `CCP_Market_Rules.xlsx`
   - `AT_Whitelist.xlsx`
   - `Column_Mapping.xlsx`
3. Click **Upload Files** button
4. System will validate files automatically

### Step 2: Run Comparison

1. Once files are validated, click **Run Comparison** button
2. Wait for processing to complete (may take 30-60 seconds depending on data size)
3. Progress indicator will show during processing

### Step 3: Review Results

The results page displays:

- **Summary Statistics**: Total records, matches, and action items
- **Requirement 1 Tab**: Securities in CCP but NOT in AT (918 records)
  - Action: ADD to AT Asia Whitelist
- **Requirement 2 Tab**: Securities in AT but NOT in CCP (4,467 records)
  - Action: REVIEW activity/positions - DELETE or ADD to Exception List
- **Requirement 3 Tab**: Config mismatches (0 records)
  - Action: UPDATE AT to match CCP & Setup Market Exception rule

### Step 4: Download Results

Each requirement has a **Download as Excel** button that exports:
- Full data set (not limited to preview)
- Formatted Excel file with auto-sized columns
- Includes action column for each row

Click **Download Summary Report** for overall statistics in Excel format.

## File Structure

```
CCP AT Comparison Engine/
├── app.py                          # Flask web application
├── compare_engine.py               # Core comparison logic module
├── compare_whitelists.py           # Original command-line script
├── requirements.txt                # Python dependencies
├── README.md                       # Project documentation
├── GUI_DEPLOYMENT.md              # This file
├── .gitignore                      # Git ignore rules
│
├── templates/
│   └── index.html                 # Main HTML interface
│
├── static/
│   ├── style.css                  # CSS styling
│   └── script.js                  # JavaScript functionality
│
├── input_data/                    # Input Excel files (CLI mode)
│   ├── CCP_Security_Whitelist.xlsx
│   ├── CCP_Market_Rules.xlsx
│   ├── AT_Whitelist.xlsx
│   └── Column_Mapping.xlsx
│
├── output_results/                # Output files (CLI mode)
│   ├── 00_Comparison_Report.xlsx
│   ├── 01_Securities_In_CCP_Not_In_AT.xlsx
│   ├── 02_Securities_In_AT_Not_In_CCP.xlsx
│   └── 03_Securities_Config_Mismatch.xlsx
│
└── temp_uploads/                  # Temporary uploaded files (auto-created)
    ├── CCP_Security_Whitelist.xlsx
    ├── CCP_Market_Rules.xlsx
    ├── AT_Whitelist.xlsx
    └── Column_Mapping.xlsx
```

## Features

### 1. Drag-and-Drop File Upload
- Click or drag files into the upload area
- Supports multiple file selection
- Visual feedback during drag-over state

### 2. File Validation
- Validates file format (Excel .xlsx/.xls)
- Checks for required columns:
  - CCP Security: symbol, exchange
  - CCP Market Rules: exchange
  - AT Whitelist: symbol, exchange
  - Column Mapping: ccp_column, at_column
- Verifies data presence (non-empty files)
- Displays detailed validation results

### 3. Smart Data Validation
- Normalizes column names automatically
- Detects and handles CCP-only fields
- Validates composite keys (symbol|exchange)
- Handles NaN and missing values safely

### 4. Interactive Results Display
- Tabbed interface for 3 requirements
- Real-time statistics dashboard
- Preview tables (first 100 rows)
- Badge counts for each requirement

### 5. Excel Export
- Download individual requirement results
- Download summary report
- Auto-formatted columns
- Proper cell widths for readability

### 6. User-Friendly Interface
- Bootstrap 5 responsive design
- Mobile-friendly layout
- Step-by-step workflow
- Clear action indicators
- Informative alerts and notifications

### 7. Session Management
- Session-based file handling
- Automatic cleanup of temporary files
- Reset functionality to start over

## API Endpoints

### Upload Files
```
POST /api/upload
Body: multipart/form-data (files)
Response: { success, validation, errors, warnings }
```

### Run Comparison
```
POST /api/compare
Response: { success, statistics, summary }
```

### Get Results
```
GET /api/results
Response: { success, statistics, requirement_1, requirement_2, requirement_3 }
```

### Download Results
```
GET /api/download/<requirement>
Params: req1, req2, req3, report
Response: Binary Excel file
```

### Reset Session
```
POST /api/reset
Response: { success, message }
```

## Troubleshooting

### Issue: "Port 5000 already in use"
**Solution**: Change port in `app.py`:
```python
app.run(debug=True, host='127.0.0.1', port=5001)  # Change 5000 to 5001
```

### Issue: "Module not found: Flask"
**Solution**: Install dependencies:
```bash
pip install -r requirements.txt
```

### Issue: "Files not uploading"
**Solution**: 
- Check file size (max 50MB)
- Ensure files are in Excel format (.xlsx or .xls)
- Try refreshing the browser

### Issue: "Comparison takes too long"
**Solution**:
- Large files (10,000+ rows) may take 30-60 seconds
- This is normal behavior
- Processing time depends on data size and system resources

### Issue: "Column not found error"
**Solution**:
- Verify Column_Mapping.xlsx is correct
- Ensure all required columns exist in source files
- Check for hidden characters or extra spaces in column names

## Advanced Configuration

### Change Upload Folder Location
Edit `app.py`:
```python
UPLOAD_FOLDER = '/custom/path/for/uploads'
```

### Increase File Size Limit
Edit `app.py`:
```python
MAX_FILE_SIZE = 100 * 1024 * 1024  # 100MB
```

### Enable Production Mode
Edit `app.py`:
```python
app.run(debug=False, host='0.0.0.0', port=5000)
```

### Enable HTTPS
Use a reverse proxy like Nginx or Apache, or use:
```python
from flask_talisman import Talisman
Talisman(app)
```

## Performance Tips

1. **Use SSD Storage**: Faster file I/O for uploads
2. **Optimize Data Size**: Remove unnecessary columns before uploading
3. **Close Unused Tabs**: Reduces browser memory usage
4. **Clear Cache**: Periodically delete temp_uploads folder
5. **Monitor System Resources**: Ensure sufficient RAM and disk space

## Bi-Weekly Usage Workflow

1. Receive updated Excel files from CCP and AT teams
2. Open application in browser: `http://localhost:5000`
3. Upload the 4 Excel files
4. Click "Run Comparison"
5. Review results in each tab
6. Download individual Excel files
7. Share results with relevant teams
8. Click "Start Over" for next comparison

## Logging and Debugging

Logs are saved to `app.log` in the project directory.

To enable debug mode:
```python
logging.basicConfig(level=logging.DEBUG)
```

To view logs:
```bash
tail -f app.log
```

## Support and Maintenance

### Regular Maintenance Tasks

1. **Clean Temporary Files**:
   ```bash
   rm -r temp_uploads/*
   ```

2. **Check Log Size** (if > 100MB):
   ```bash
   rm app.log
   ```

3. **Update Dependencies**:
   ```bash
   pip install --upgrade -r requirements.txt
   ```

### Git Management

To switch between branches:
```bash
git checkout gui          # Switch to GUI
git checkout QA           # Switch to QA
git checkout main         # Switch to main
```

To push GUI changes:
```bash
git push origin gui
```

## Additional Features

### Built-in Features
✅ Drag-and-drop file upload
✅ Real-time validation
✅ Progress indicators
✅ Responsive design
✅ Excel export with formatting
✅ Session management
✅ Error handling and logging
✅ Statistics dashboard
✅ Tabbed results display
✅ Auto cleanup of temp files

### Possible Future Enhancements
- 📋 Scheduled/automated comparisons
- 📊 Advanced filtering and search
- 📈 Comparison history tracking
- 🔔 Email notifications
- 🔐 User authentication
- 📱 Mobile app version
- 🌐 Multi-language support
- 🎨 Dark theme option

## Version History

### v2.0 (Current)
- Web-based GUI with Flask
- Responsive Bootstrap 5 interface
- Real-time file validation
- Interactive results display
- Excel export functionality
- Session-based file handling

### v1.0 (Command-line)
- Core comparison logic
- Command-line interface
- Batch processing support
- Original implementation

## Contact and Support

For issues or questions, please:
1. Check the troubleshooting section
2. Review logs in `app.log`
3. Visit: https://github.com/inuka007/CCP-Comparison-Engine

## License

This application is proprietary. All rights reserved.

---

**Last Updated**: December 10, 2025
**Maintained By**: CCP-AT Team
**Repository**: https://github.com/inuka007/CCP-Comparison-Engine
