"""
CCP-AT Comparison Engine - Web GUI Application
Flask-based web interface for comparing CCP and AT whitelists
"""

import os
import sys
import logging
import io
import uuid
import zipfile
from datetime import datetime
from flask import Flask, render_template, request, jsonify, send_file, session
from werkzeug.utils import secure_filename
import pandas as pd
import numpy as np
from compare_engine import ComparisonEngine, ValidationError

# ================================
# FLASK APP CONFIGURATION
# ================================

app = Flask(__name__)
app.secret_key = 'ccp_at_comparison_secret_key_2025'

# In-memory cache for comparison results (keyed by session ID)
RESULTS_CACHE = {}

# File upload configuration
UPLOAD_FOLDER = os.path.join(os.path.dirname(__file__), 'temp_uploads')
RESULTS_FOLDER = os.path.join(os.path.dirname(__file__), 'temp_results')
MAPPING_FILE = os.path.join(os.path.dirname(__file__), 'Column_Mapping.xlsx')
ALLOWED_EXTENSIONS = {'xlsx', 'xls'}
MAX_FILE_SIZE = 50 * 1024 * 1024  # 50MB max file size

os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(RESULTS_FOLDER, exist_ok=True)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['MAX_CONTENT_LENGTH'] = MAX_FILE_SIZE

# ================================
# LOGGING CONFIGURATION
# ================================

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('app.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# ================================
# ALLOWED FILE EXTENSIONS CHECK
# ================================

def allowed_file(filename):
    """Check if file has allowed extension"""
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

# ================================
# ROUTES - HOME
# ================================

@app.route('/')
def home():
    """Render home page with file upload interface"""
    return render_template('index.html')

# ================================
# ROUTES - FILE UPLOAD & VALIDATION
# ================================

@app.route('/api/upload', methods=['POST'])
def upload_files():
    """Handle file upload and validation"""
    try:
        logger.info("Starting file upload process...")
        
        # Check if files are present in request
        if 'files' not in request.files:
            return jsonify({
                'success': False,
                'error': 'No files provided. Please upload all required files.',
                'type': 'missing_files'
            }), 400
        
        files = request.files.getlist('files')
        
        if not files or len(files) == 0:
            return jsonify({
                'success': False,
                'error': 'No files selected. Please select at least one file.',
                'type': 'no_selection'
            }), 400
        
        logger.info(f"Received {len(files)} files for upload")
        
        # Save uploaded files temporarily
        uploaded_file_paths = {}
        for file in files:
            if file.filename == '':
                logger.warning("Empty filename received")
                continue
            
            if not allowed_file(file.filename):
                logger.warning(f"Invalid file type: {file.filename}")
                return jsonify({
                    'success': False,
                    'error': f'Invalid file type: {file.filename}. Only .xlsx and .xls files are allowed.',
                    'type': 'invalid_format'
                }), 400
            
            filename = secure_filename(file.filename)
            filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            file.save(filepath)
            uploaded_file_paths[filename] = filepath
            logger.info(f"Saved file: {filename}")
        
        # Validate uploaded files
        validation_result = validate_uploaded_files(uploaded_file_paths)
        
        if not validation_result['success']:
            return jsonify(validation_result), 400
        
        # Store file paths in session for later processing
        session['uploaded_files'] = uploaded_file_paths
        session['validation_result'] = validation_result
        
        logger.info("Files uploaded and validated successfully")
        
        return jsonify({
            'success': True,
            'message': 'Files uploaded and validated successfully',
            'validation': validation_result
        }), 200
    
    except Exception as e:
        logger.error(f"Error during file upload: {str(e)}")
        return jsonify({
            'success': False,
            'error': f'Server error during upload: {str(e)}',
            'type': 'server_error'
        }), 500

# ================================
# FILE VALIDATION LOGIC
# ================================

def validate_uploaded_files(file_paths):
    """
    Validate uploaded Excel files for format and required columns
    
    Args:
        file_paths: Dictionary of filename -> filepath
    
    Returns:
        Dictionary with validation results
    """
    validation_results = {
        'success': True,
        'warnings': [],
        'errors': [],
        'files_status': {}
    }
    
    required_files = {
        'CCP_Security_Whitelist.xlsx': ['symbol', 'exchange'],
        'CCP_Market_Rules.xlsx': ['exchange'],
        'AT_Whitelist.xlsx': ['symbol', 'exchange']
    }
    
    uploaded_filenames = {os.path.basename(p).lower(): p for p in file_paths.values()}
    
    # Check for required files
    for required_file in required_files.keys():
        required_file_lower = required_file.lower()
        found = False
        
        for uploaded_file, filepath in file_paths.items():
            if uploaded_file.lower() == required_file_lower:
                found = True
                try:
                    # Read Excel file
                    df = pd.read_excel(filepath)
                    
                    # Normalize column names
                    df.columns = (
                        df.columns.astype(str)
                        .str.strip()
                        .str.replace(r"\s+", "_", regex=True)
                        .str.replace(r"__+", "_", regex=True)
                        .str.lower()
                    )
                    
                    # Check required columns
                    required_cols = required_files[required_file]
                    missing_cols = [col for col in required_cols if col not in df.columns]
                    
                    if missing_cols:
                        validation_results['errors'].append(
                            f"File '{required_file}' is missing required columns: {', '.join(missing_cols)}"
                        )
                        validation_results['success'] = False
                    
                    # Check for data
                    if len(df) == 0:
                        validation_results['warnings'].append(
                            f"File '{required_file}' is empty (no data rows)"
                        )
                    
                    # File-specific validations
                    if required_file == 'CCP_Security_Whitelist.xlsx':
                        if 'symbol' in df.columns and df['symbol'].isna().all():
                            validation_results['errors'].append(
                                f"File '{required_file}': Symbol column is empty"
                            )
                            validation_results['success'] = False
                    
                    validation_results['files_status'][required_file] = {
                        'status': 'valid',
                        'rows': len(df),
                        'columns': len(df.columns)
                    }
                    logger.info(f"Validated {required_file}: {len(df)} rows, {len(df.columns)} columns")
                    
                except Exception as e:
                    validation_results['errors'].append(
                        f"Error reading file '{required_file}': {str(e)}"
                    )
                    validation_results['success'] = False
                    validation_results['files_status'][required_file] = {
                        'status': 'error',
                        'error': str(e)
                    }
                    logger.error(f"Error validating {required_file}: {str(e)}")
                
                break
        
        if not found:
            validation_results['errors'].append(
                f"Required file missing: {required_file}"
            )
            validation_results['success'] = False
            validation_results['files_status'][required_file] = {
                'status': 'missing'
            }
            logger.warning(f"Required file not found: {required_file}")
    
    # Check if Column_Mapping.xlsx exists on backend
    if not os.path.isfile(MAPPING_FILE):
        validation_results['warnings'].append(
            "Column_Mapping.xlsx not found on server. Using default mapping behavior."
        )
        logger.warning("Column_Mapping.xlsx not found on server")
    else:
        validation_results['files_status']['Column_Mapping.xlsx'] = {
            'status': 'valid',
            'source': 'server'
        }
        logger.info("Column_Mapping.xlsx loaded from server")
    
    return validation_results

# ================================
# ROUTES - RUN COMPARISON
# ================================

@app.route('/api/compare', methods=['POST'])
def run_comparison():
    """Run the comparison analysis on uploaded files"""
    try:
        logger.info("Starting comparison analysis...")
        
        # Check if files were uploaded and validated
        if 'uploaded_files' not in session:
            return jsonify({
                'success': False,
                'error': 'No files in session. Please upload files first.',
                'type': 'no_files'
            }), 400
        
        uploaded_files = session['uploaded_files']
        
        # Add Column_Mapping.xlsx from backend if it exists
        if os.path.isfile(MAPPING_FILE):
            uploaded_files['Column_Mapping.xlsx'] = MAPPING_FILE
        
        # Initialize comparison engine
        engine = ComparisonEngine(uploaded_files)
        
        # Run comparison
        results = engine.compare()
        
        # Create a unique results ID for this session
        results_id = str(uuid.uuid4())
        session['results_id'] = results_id
        
        # Store results in memory cache (not in session to avoid serialization issues)
        RESULTS_CACHE[results_id] = {
            'requirement_1': results['requirement_1'],
            'requirement_2': results['requirement_2'],
            'requirement_3': results['requirement_3'],
            'statistics': results['statistics'],
            'timestamp': datetime.now().isoformat()
        }
        
        logger.info(f"Comparison completed: {results['statistics']}")
        
        return jsonify({
            'success': True,
            'message': 'Comparison completed successfully',
            'statistics': {k: (int(v) if isinstance(v, (int, float)) else str(v)) 
                          for k, v in results['statistics'].items()},
            'summary': {
                'requirement_1_count': len(results['requirement_1']),
                'requirement_2_count': len(results['requirement_2']),
                'requirement_3_count': len(results['requirement_3'])
            }
        }), 200
    
    except ValidationError as e:
        logger.error(f"Validation error during comparison: {str(e)}")
        return jsonify({
            'success': False,
            'error': f'Validation error: {str(e)}',
            'type': 'validation_error'
        }), 400
    
    except Exception as e:
        logger.error(f"Error during comparison: {str(e)}")
        logger.error(f"Traceback: {repr(e)}")
        return jsonify({
            'success': False,
            'error': f'Error during comparison: {str(e)}',
            'type': 'comparison_error'
        }), 500

# ================================
# ROUTES - GET RESULTS PREVIEW
# ================================

@app.route('/api/results', methods=['GET'])
def get_results():
    """Get comparison results for display in frontend"""
    try:
        if 'results_id' not in session or session['results_id'] not in RESULTS_CACHE:
            return jsonify({
                'success': False,
                'error': 'No results available. Please run comparison first.',
                'type': 'no_results'
            }), 400
        
        results = RESULTS_CACHE[session['results_id']]
        
        # Clean dataframes for JSON serialization
        def clean_value(val):
            """Convert pandas/numpy types to JSON-safe Python types"""
            if pd.isna(val):
                return None
            if isinstance(val, (pd.Timestamp, np.datetime64)):
                return str(val)
            if isinstance(val, (np.integer, np.floating)):
                return float(val) if isinstance(val, np.floating) else int(val)
            return str(val) if val is not None else None
        
        def clean_dataframe_for_json(df):
            """Clean dataframe for JSON serialization"""
            df_copy = df.fillna('')
            for col in df_copy.columns:
                df_copy[col] = df_copy[col].apply(clean_value)
            return df_copy.to_dict('records')
        
        req1_data = clean_dataframe_for_json(results['requirement_1'])
        req2_data = clean_dataframe_for_json(results['requirement_2'])
        req3_data = clean_dataframe_for_json(results['requirement_3'])
        
        # Return limited preview (first 100 rows per requirement)
        return jsonify({
            'success': True,
            'statistics': {k: (int(v) if isinstance(v, (int, float)) else str(v)) 
                          for k, v in results['statistics'].items()},
            'requirement_1': {
                'data': req1_data[:100],
                'total': len(req1_data),
                'preview': True if len(req1_data) > 100 else False
            },
            'requirement_2': {
                'data': req2_data[:100],
                'total': len(req2_data),
                'preview': True if len(req2_data) > 100 else False
            },
            'requirement_3': {
                'data': req3_data[:100],
                'total': len(req3_data),
                'preview': True if len(req3_data) > 100 else False
            }
        }), 200
    
    except Exception as e:
        logger.error(f"Error retrieving results: {str(e)}")
        return jsonify({
            'success': False,
            'error': f'Error retrieving results: {str(e)}',
            'type': 'server_error'
        }), 500

# ================================
# ROUTES - DOWNLOAD RESULTS
# ================================

@app.route('/api/download/<requirement>', methods=['GET'])
def download_results(requirement):
    """Download specific requirement results as Excel file"""
    try:
        if 'results_id' not in session or session['results_id'] not in RESULTS_CACHE:
            return jsonify({
                'success': False,
                'error': 'No results available. Please run comparison first.',
                'type': 'no_results'
            }), 400
        
        results = RESULTS_CACHE[session['results_id']]
        
        # Map requirement parameter to data
        requirement_map = {
            'req1': ('requirement_1', '01_Securities_In_CCP_Not_In_AT.xlsx'),
            'req2': ('requirement_2', '02_Securities_In_AT_Not_In_CCP.xlsx'),
            'req3': ('requirement_3', '03_Securities_Config_Mismatch.xlsx'),
            'report': ('report', '00_Comparison_Report.xlsx')
        }
        
        if requirement not in requirement_map:
            return jsonify({
                'success': False,
                'error': 'Invalid requirement specified',
                'type': 'invalid_param'
            }), 400
        
        req_key, filename = requirement_map[requirement]
        
        if req_key == 'report':
            # Generate summary report
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
                    results['statistics'].get('total_ccp', 0),
                    results['statistics'].get('total_at', 0),
                    results['statistics'].get('total_common', 0),
                    "",
                    len(results['requirement_1']),
                    f"{len(results['requirement_1'])} records",
                    "",
                    len(results['requirement_2']),
                    f"{len(results['requirement_2'])} records",
                    "",
                    len(results['requirement_3']),
                    f"{len(results['requirement_3'])} records",
                    "",
                    len(results['requirement_1']) + len(results['requirement_2']) + len(results['requirement_3']),
                    "",
                    results['timestamp']
                ]
            }
            df = pd.DataFrame(report_data)
        else:
            df = results[req_key]
        
        # Create Excel file in memory
        output = io.BytesIO()
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            # For Requirement 3, write AT and CCP sheets + a Diffs summary
            if req_key == 'requirement_3':
                # df contains combined rows with at_ and ccp_ prefixed columns
                # Write AT sheet
                at_cols = [c for c in df.columns if c.startswith('at_')]
                if at_cols:
                    df_at = df[at_cols].copy()
                    # remove prefix for readability
                    df_at.columns = [c.replace('at_', '') for c in df_at.columns]
                    df_at.to_excel(writer, sheet_name='AT', index=False)

                    # Auto-adjust AT widths
                    ws_at = writer.sheets['AT']
                    for column in ws_at.columns:
                        max_length = 0
                        column_letter = column[0].column_letter
                        for cell in column:
                            try:
                                if cell.value and len(str(cell.value)) > max_length:
                                    max_length = len(str(cell.value))
                            except:
                                pass
                        ws_at.column_dimensions[column_letter].width = max_length + 2

                # Write CCP sheet
                ccp_cols = [c for c in df.columns if c.startswith('ccp_')]
                if ccp_cols:
                    df_ccp = df[ccp_cols].copy()
                    df_ccp.columns = [c.replace('ccp_', '') for c in df_ccp.columns]
                    df_ccp.to_excel(writer, sheet_name='CCP', index=False)

                    # Auto-adjust CCP widths
                    ws_ccp = writer.sheets['CCP']
                    for column in ws_ccp.columns:
                        max_length = 0
                        column_letter = column[0].column_letter
                        for cell in column:
                            try:
                                if cell.value and len(str(cell.value)) > max_length:
                                    max_length = len(str(cell.value))
                            except:
                                pass
                        ws_ccp.column_dimensions[column_letter].width = max_length + 2

                # Write Diffs summary sheet
                diff_cols = [c for c in df.columns if c not in at_cols + ccp_cols]
                if diff_cols:
                    df_diffs = df[diff_cols].copy()
                    df_diffs.to_excel(writer, sheet_name='Diffs', index=False)

                    ws_d = writer.sheets['Diffs']
                    for column in ws_d.columns:
                        max_length = 0
                        column_letter = column[0].column_letter
                        for cell in column:
                            try:
                                if cell.value and len(str(cell.value)) > max_length:
                                    max_length = len(str(cell.value))
                            except:
                                pass
                        ws_d.column_dimensions[column_letter].width = max_length + 2
            else:
                df.to_excel(writer, sheet_name='Results', index=False)
                # Auto-adjust column widths for Results
                worksheet = writer.sheets['Results']
                for column in worksheet.columns:
                    max_length = 0
                    column_letter = column[0].column_letter
                    for cell in column:
                        try:
                            if len(str(cell.value)) > max_length:
                                max_length = len(str(cell.value))
                        except:
                            pass
                    adjusted_width = (max_length + 2)
                    worksheet.column_dimensions[column_letter].width = adjusted_width
        
        output.seek(0)
        
        logger.info(f"Downloaded {filename}")
        
        return send_file(
            output,
            mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
            as_attachment=True,
            download_name=filename
        )
    
    except Exception as e:
        logger.error(f"Error downloading results: {str(e)}")
        return jsonify({
            'success': False,
            'error': f'Error downloading results: {str(e)}',
            'type': 'download_error'
        }), 500

# ================================
# ROUTES - ZIP DOWNLOAD
# ================================

@app.route('/api/download-zip', methods=['GET'])
def download_zip():
    """Download all results as a ZIP bundle"""
    try:
        if 'results_id' not in session or session['results_id'] not in RESULTS_CACHE:
            return jsonify({
                'success': False,
                'error': 'No results available. Please run comparison first.',
                'type': 'no_results'
            }), 400
        
        results = RESULTS_CACHE[session['results_id']]
        
        # Create ZIP file in memory
        zip_buffer = io.BytesIO()
        
        with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zip_file:
            # Define all files to include
            files_to_zip = [
                ('requirement_1', 'requirement_1', '01_Securities_In_CCP_Not_In_AT.xlsx'),
                ('requirement_2', 'requirement_2', '02_Securities_In_AT_Not_In_CCP.xlsx'),
                ('requirement_3', 'requirement_3', '03_Securities_Config_Mismatch.xlsx'),
                ('report', 'report', '00_Comparison_Report.xlsx')
            ]
            
            for file_type, cache_key, filename in files_to_zip:
                # Generate individual file
                output = io.BytesIO()
                
                if cache_key == 'report':
                    # Generate summary report
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
                            results['statistics'].get('total_ccp', 0),
                            results['statistics'].get('total_at', 0),
                            results['statistics'].get('total_common', 0),
                            "",
                            len(results['requirement_1']),
                            f"{len(results['requirement_1'])} records",
                            "",
                            len(results['requirement_2']),
                            f"{len(results['requirement_2'])} records",
                            "",
                            len(results['requirement_3']),
                            f"{len(results['requirement_3'])} records",
                            "",
                            len(results['requirement_1']) + len(results['requirement_2']) + len(results['requirement_3']),
                            "",
                            results['timestamp']
                        ]
                    }
                    df = pd.DataFrame(report_data)
                else:
                    df = results[cache_key]
                
                # Write to BytesIO
                with pd.ExcelWriter(output, engine='openpyxl') as writer:
                    if cache_key == 'requirement_3':
                        # Write AT sheet
                        at_cols = [c for c in df.columns if c.startswith('at_')]
                        if at_cols:
                            df_at = df[at_cols].copy()
                            df_at.columns = [c.replace('at_', '') for c in df_at.columns]
                            df_at.to_excel(writer, sheet_name='AT', index=False)
                        
                        # Write CCP sheet
                        ccp_cols = [c for c in df.columns if c.startswith('ccp_')]
                        if ccp_cols:
                            df_ccp = df[ccp_cols].copy()
                            df_ccp.columns = [c.replace('ccp_', '') for c in df_ccp.columns]
                            df_ccp.to_excel(writer, sheet_name='CCP', index=False)
                        
                        # Write Diffs sheet
                        diff_cols = [c for c in df.columns if c not in at_cols + ccp_cols]
                        if diff_cols:
                            df_diffs = df[diff_cols].copy()
                            df_diffs.to_excel(writer, sheet_name='Diffs', index=False)
                    else:
                        df.to_excel(writer, sheet_name='Results', index=False)
                
                # Add file to ZIP
                output.seek(0)
                zip_file.writestr(filename, output.getvalue())
            
            # Add a README file
            readme_content = """CCP-AT Comparison Engine - Results Bundle
=============================================

This ZIP file contains all comparison results:

Files included:
- 00_Comparison_Report.xlsx: Summary report with overall statistics
- 01_Securities_In_CCP_Not_In_AT.xlsx: Securities that exist in CCP but not in AT
- 02_Securities_In_AT_Not_In_CCP.xlsx: Securities that exist in AT but not in CCP
- 03_Securities_Config_Mismatch.xlsx: Securities in both with configuration mismatches
  - AT Sheet: AT configuration values
  - CCP Sheet: CCP configuration values
  - Diffs Sheet: Summary of differences

Generated: {timestamp}
""".format(timestamp=results['timestamp'])
            
            zip_file.writestr('README.txt', readme_content)
        
        zip_buffer.seek(0)
        logger.info("Downloaded comparison results as ZIP bundle")
        
        return send_file(
            zip_buffer,
            mimetype='application/zip',
            as_attachment=True,
            download_name='CCP_AT_Comparison_Results.zip'
        )
    
    except Exception as e:
        logger.error(f"Error creating ZIP file: {str(e)}")
        return jsonify({
            'success': False,
            'error': f'Error creating ZIP file: {str(e)}',
            'type': 'zip_error'
        }), 500

# ================================
# ROUTES - RESET SESSION
# ================================

@app.route('/api/reset', methods=['POST'])
def reset_session():
    """Reset session and clear uploaded files"""
    try:
        # Clear session
        session.clear()
        
        # Clean up temporary files
        for file in os.listdir(app.config['UPLOAD_FOLDER']):
            file_path = os.path.join(app.config['UPLOAD_FOLDER'], file)
            try:
                if os.path.isfile(file_path):
                    os.unlink(file_path)
            except Exception as e:
                logger.warning(f"Could not delete {file_path}: {str(e)}")
        
        logger.info("Session reset and temporary files cleared")
        
        return jsonify({
            'success': True,
            'message': 'Session reset successfully'
        }), 200
    
    except Exception as e:
        logger.error(f"Error resetting session: {str(e)}")
        return jsonify({
            'success': False,
            'error': f'Error resetting session: {str(e)}',
            'type': 'reset_error'
        }), 500

# ================================
# ERROR HANDLERS
# ================================

@app.errorhandler(413)
def request_entity_too_large(error):
    """Handle file too large error"""
    return jsonify({
        'success': False,
        'error': f'File too large. Maximum size is {MAX_FILE_SIZE / (1024*1024):.0f}MB',
        'type': 'file_too_large'
    }), 413

@app.errorhandler(404)
def not_found(error):
    """Handle 404 errors"""
    return jsonify({
        'success': False,
        'error': 'Endpoint not found',
        'type': 'not_found'
    }), 404

@app.errorhandler(500)
def internal_error(error):
    """Handle 500 errors"""
    logger.error(f"Internal server error: {str(error)}")
    return jsonify({
        'success': False,
        'error': 'Internal server error',
        'type': 'server_error'
    }), 500

# ================================
# MAIN
# ================================

if __name__ == '__main__':
    logger.info("Starting CCP-AT Comparison Engine GUI...")
    app.run(debug=True, host='127.0.0.1', port=5000)
