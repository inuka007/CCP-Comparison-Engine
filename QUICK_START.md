# Quick Start Guide - CCP-AT Comparison Engine GUI

## 🚀 Get Started in 3 Steps

### Step 1: Navigate to Project Directory
```bash
cd "c:\Users\InukaWeerasekara\Downloads\CCP AT Comparison Engine"
```

### Step 2: Verify You're on GUI Branch
```bash
git checkout gui
```

### Step 3: Start the Application
```bash
python app.py
```

**Output should show:**
```
 * Running on http://127.0.0.1:5000
 * Press CTRL+C to quit
```

### Step 4: Open in Browser
```
http://localhost:5000
```

---

## 📋 What You'll See

### Step 1: Upload Excel Files
- Drag and drop your 4 Excel files into the upload area
- Or click to browse and select files
- Visual checklist confirms all files are recognized

### Step 2: Run Comparison
- Click "Run Comparison" button
- Wait for processing (30-60 seconds depending on data size)
- See progress spinner during processing

### Step 3: View Results
- **Statistics Dashboard** shows summary counts
- **Three Tabs** for each requirement:
  - Tab 1: Securities in CCP but NOT in AT (918 records)
  - Tab 2: Securities in AT but NOT in CCP (4,467 records)
  - Tab 3: Config mismatches (0 records)

### Step 4: Download Results
- Download individual Excel files for each requirement
- Download summary report
- Click "Start Over" to run another comparison

---

## 🎯 Key Features

✅ **Drag-and-Drop Upload** - Easy file selection
✅ **Real-Time Validation** - Checks file format and columns
✅ **Progress Indicators** - Shows what's happening
✅ **Interactive Tables** - Preview results with sorting
✅ **Excel Export** - Download properly formatted files
✅ **Mobile Responsive** - Works on tablets and phones
✅ **Error Messages** - Clear feedback on issues

---

## 🛠️ Troubleshooting

### "Module not found: Flask"
```bash
pip install -r requirements.txt
```

### "Port 5000 already in use"
Edit `app.py` line 72:
```python
app.run(debug=True, host='127.0.0.1', port=5001)  # Change to 5001
```

### "Files won't upload"
- Check file size (max 50MB)
- Ensure .xlsx or .xls format
- Try clearing browser cache

---

## 📚 Required Excel Files

Place these 4 files in the `input_data/` folder (for CLI mode) or upload via GUI:

1. **CCP_Security_Whitelist.xlsx** - Contains symbol, exchange, and config
2. **CCP_Market_Rules.xlsx** - Contains exchange-specific rules
3. **AT_Whitelist.xlsx** - Contains AT symbols and configuration
4. **Column_Mapping.xlsx** - Maps CCP columns to AT columns

---

## 🔄 Bi-Weekly Workflow

1. Receive updated Excel files
2. Open http://localhost:5000 in browser
3. Upload the 4 files
4. Click "Run Comparison"
5. Review results in each tab
6. Download Excel files as needed
7. Share with relevant teams
8. Click "Start Over" for next run

---

## 📊 Output Files

When you download results, you get:

- **01_Securities_In_CCP_Not_In_AT.xlsx** - 918 records to ADD
- **02_Securities_In_AT_Not_In_CCP.xlsx** - 4,467 records to REVIEW
- **03_Securities_Config_Mismatch.xlsx** - 0 mismatches to UPDATE
- **00_Comparison_Report.xlsx** - Summary statistics

---

## 🎓 Understanding the Results

### Requirement 1: CCP ∩ ¬AT
Securities that exist in CCP but NOT in AT
- **Action**: ADD these securities to AT Asia Whitelist
- **Example**: New CCP securities not yet in AT system

### Requirement 2: AT ∩ ¬CCP
Securities that exist in AT but NOT in CCP
- **Action**: REVIEW activity/positions - DELETE or ADD to Exception List
- **Example**: Securities in AT that CCP doesn't trade

### Requirement 3: Config Mismatches
Securities in both systems with different configurations
- **Action**: UPDATE AT to match CCP or SETUP Market Exception rule
- **Example**: Different commission rates, status flags, etc.

---

## 💾 File Management

### Temporary Files
- Uploaded files stored in `temp_uploads/` folder
- Automatically deleted when you click "Start Over"
- Safe to manually delete if needed

### Output Files (CLI Mode)
- Generated in `output_results/` folder when using CLI
- GUI downloads directly to your Downloads folder

### Logs
- Application logs saved to `app.log`
- Useful for troubleshooting issues

---

## 🔗 Useful Links

- **GitHub**: https://github.com/inuka007/CCP-Comparison-Engine
- **Full Documentation**: See GUI_DEPLOYMENT.md
- **Original Script**: compare_whitelists.py (command-line version)

---

## 🎉 You're Ready!

The GUI is now ready to use. Just run:
```bash
python app.py
```

Then open http://localhost:5000 in your browser!

For detailed documentation, see **GUI_DEPLOYMENT.md**

---

**Version**: 2.0 (GUI Edition)
**Last Updated**: December 10, 2025
**Status**: Production Ready ✅
