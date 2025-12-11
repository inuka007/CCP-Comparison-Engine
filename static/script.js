/* ================================
   CCP-AT Comparison Engine - JavaScript
   ================================ */

// ================================
// STATE MANAGEMENT
// ================================

let appState = {
    uploadedFiles: [],
    validationResult: null,
    comparisonResults: null,
    currentStep: 1
};

// ================================
// GLOBAL ELEMENT REFERENCES
// ================================

let uploadArea, fileInput, uploadBtn, clearFilesBtn, compareBtn, resetBtn;

// ================================
// DOM INITIALIZATION
// ================================

function initializeElements() {
    uploadArea = document.getElementById('uploadArea');
    fileInput = document.getElementById('fileInput');
    uploadBtn = document.getElementById('uploadBtn');
    clearFilesBtn = document.getElementById('clearFilesBtn');
    compareBtn = document.getElementById('compareBtn');
    resetBtn = document.getElementById('resetBtn');
    
    attachEventListeners();
}

function attachEventListeners() {
    // Upload area click
    uploadArea.addEventListener('click', () => fileInput.click());
    
    // File input change
    fileInput.addEventListener('change', handleFileSelect);
    
    // Drag and drop
    uploadArea.addEventListener('dragover', (e) => {
        e.preventDefault();
        uploadArea.classList.add('drag-over');
    });
    
    uploadArea.addEventListener('dragleave', () => {
        uploadArea.classList.remove('drag-over');
    });
    
    uploadArea.addEventListener('drop', (e) => {
        e.preventDefault();
        uploadArea.classList.remove('drag-over');
        const files = Array.from(e.dataTransfer.files);
        fileInput.files = createFileList(files);
        handleFileSelect();
    });
    
    // Upload button
    uploadBtn.addEventListener('click', uploadFiles);
    
    // Clear files button
    clearFilesBtn.addEventListener('click', clearFiles);
    
    // Compare button
    compareBtn.addEventListener('click', runComparison);
    
    // Reset button
    resetBtn.addEventListener('click', resetSession);
}

function clearFiles() {
    appState.uploadedFiles = [];
    document.getElementById('filesList').style.display = 'none';
    uploadBtn.disabled = true;
    clearFilesBtn.style.display = 'none';
    fileInput.value = '';
    document.getElementById('validationResults').style.display = 'none';
}

// ================================
// FILE SELECTION & UPLOAD
// ================================

function handleFileSelect() {
    const files = Array.from(fileInput.files);
    
    if (files.length === 0) {
        return;
    }
    
    appState.uploadedFiles = files;
    displaySelectedFiles(files);
    uploadBtn.disabled = false;
    clearFilesBtn.style.display = 'inline-block';
}

function displaySelectedFiles(files) {
    const filesContainer = document.getElementById('filesContainer');
    const filesList = document.getElementById('filesList');
    
    filesContainer.innerHTML = '';
    
    files.forEach((file, index) => {
        const fileItem = document.createElement('div');
        fileItem.className = 'file-item';
        fileItem.innerHTML = `
            <span>
                <i class="bi bi-file-earmark-spreadsheet"></i>
                <span class="file-name">${file.name}</span>
            </span>
            <span class="file-size">${(file.size / 1024).toFixed(2)} KB</span>
            <button type="button" class="btn-close" onclick="removeFile(${index})" aria-label="Remove"></button>
        `;
        filesContainer.appendChild(fileItem);
    });
    
    filesList.style.display = 'block';
}

function removeFile(index) {
    appState.uploadedFiles.splice(index, 1);
    
    if (appState.uploadedFiles.length === 0) {
        document.getElementById('filesList').style.display = 'none';
        uploadBtn.disabled = true;
        clearFilesBtn.style.display = 'none';
        fileInput.value = '';
    } else {
        displaySelectedFiles(appState.uploadedFiles);
    }
}

// ================================
// FILE UPLOAD API CALL
// ================================

async function uploadFiles() {
    if (appState.uploadedFiles.length === 0) {
        showAlert('error', 'Please select files first');
        return;
    }
    
    uploadBtn.disabled = true;
    uploadBtn.innerHTML = '<span class="spinner-border spinner-border-sm me-2"></span>Uploading...';
    
    const formData = new FormData();
    appState.uploadedFiles.forEach(file => {
        formData.append('files', file);
    });
    
    try {
        console.log('✓ Uploading files:', appState.uploadedFiles.map(f => f.name));
        
        const response = await fetch('/api/upload', {
            method: 'POST',
            body: formData
        });
        
        const data = await response.json();
        console.log('✓ Upload response:', data);
        
        if (response.ok) {
            appState.validationResult = data.validation;
            displayValidationResults(data.validation);
            
            // Show success state
            uploadBtn.disabled = true;
            uploadBtn.classList.add('btn-success');
            uploadBtn.classList.remove('btn-primary');
            uploadBtn.innerHTML = '<i class="bi bi-check-circle"></i> Files Uploaded & Validated ✓';
            clearFilesBtn.disabled = true;
            
            showAlert('success', 'Files uploaded and validated successfully!');
            
            // Move to step 2
            document.getElementById('step1').style.opacity = '0.8';
            document.getElementById('step1').style.pointerEvents = 'none';
            document.getElementById('step2').style.display = 'block';
            appState.currentStep = 2;
        } else {
            showAlert('error', data.error || 'Upload failed');
            uploadBtn.disabled = false;
            uploadBtn.innerHTML = '<i class="bi bi-upload"></i> Upload Files';
        }
    } catch (error) {
        console.error('✗ Error uploading files:', error);
        showAlert('error', 'Error uploading files: ' + error.message);
        uploadBtn.disabled = false;
        uploadBtn.innerHTML = '<i class="bi bi-upload"></i> Upload Files';
    }
}

// ================================
// VALIDATION RESULTS DISPLAY
// ================================

function displayValidationResults(validation) {
    const validationContent = document.getElementById('validationContent');
    const validationResults = document.getElementById('validationResults');
    
    validationContent.innerHTML = '';
    
    // Check for errors
    if (validation.errors && validation.errors.length > 0) {
        validation.errors.forEach(error => {
            const errorDiv = document.createElement('div');
            errorDiv.className = 'validation-check error';
            errorDiv.innerHTML = `<i class="bi bi-x-circle-fill"></i><span>${error}</span>`;
            validationContent.appendChild(errorDiv);
        });
    }
    
    // Check for warnings
    if (validation.warnings && validation.warnings.length > 0) {
        validation.warnings.forEach(warning => {
            const warningDiv = document.createElement('div');
            warningDiv.className = 'validation-check warning';
            warningDiv.innerHTML = `<i class="bi bi-exclamation-triangle-fill"></i><span>${warning}</span>`;
            validationContent.appendChild(warningDiv);
        });
    }
    
    // Display file status
    if (validation.files_status) {
        Object.entries(validation.files_status).forEach(([filename, status]) => {
            const statusDiv = document.createElement('div');
            
            if (status.status === 'valid') {
                statusDiv.className = 'validation-check valid';
                statusDiv.innerHTML = `
                    <i class="bi bi-check-circle-fill"></i>
                    <span><strong>${filename}</strong> - ${status.rows} rows, ${status.columns} columns</span>
                `;
                updateChecklist(filename, true);
            } else if (status.status === 'error') {
                statusDiv.className = 'validation-check error';
                statusDiv.innerHTML = `
                    <i class="bi bi-x-circle-fill"></i>
                    <span><strong>${filename}</strong> - Error: ${status.error}</span>
                `;
            } else if (status.status === 'missing') {
                statusDiv.className = 'validation-check error';
                statusDiv.innerHTML = `
                    <i class="bi bi-x-circle-fill"></i>
                    <span><strong>${filename}</strong> - File not found</span>
                `;
            }
            
            validationContent.appendChild(statusDiv);
        });
    }
    
    validationResults.style.display = 'block';
}

function updateChecklist(filename, valid) {
    const checkboxMap = {
        'CCP_Security_Whitelist.xlsx': 'check1',
        'CCP_Market_Rules.xlsx': 'check2',
        'AT_Whitelist.xlsx': 'check3'
    };
    
    if (checkboxMap[filename]) {
        document.getElementById(checkboxMap[filename]).checked = valid;
    }
}

// ================================
// COMPARISON EXECUTION
// ================================

async function runComparison() {
    console.log('✓ Run Comparison button clicked');
    console.log('✓ Current appState:', appState);
    console.log('✓ Making POST request to /api/compare');
    
    compareBtn.disabled = true;
    compareBtn.innerHTML = '<i class="bi bi-hourglass-split"></i> Processing... Please wait (this may take 30-60 seconds)';
    
    const processingSpinner = document.getElementById('processingSpinner');
    processingSpinner.style.display = 'block';
    
    try {
        const response = await fetch('/api/compare', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            }
        });
        
        console.log('✓ Response received with status:', response.status);
        const data = await response.json();
        console.log('✓ Response data:', data);
        
        if (response.ok) {
            console.log('✓ Comparison successful');
            appState.comparisonResults = data;
            
            console.log('✓ Fetching detailed results...');
            // Fetch and display results
            await fetchAndDisplayResults();
            
            showAlert('success', 'Comparison completed successfully! ✓');
            
            console.log('✓ Displaying step 3 results');
            // Move to step 3
            document.getElementById('step2').style.opacity = '0.8';
            document.getElementById('step2').style.pointerEvents = 'none';
            document.getElementById('step3').style.display = 'block';
            appState.currentStep = 3;
            
            // Scroll to results
            setTimeout(() => {
                document.getElementById('step3').scrollIntoView({ behavior: 'smooth' });
            }, 300);
        } else {
            console.error('✗ Comparison error - Server returned error:', response.status, data);
            showAlert('error', data.error || 'Comparison failed. Error: ' + response.status);
        }
    } catch (error) {
        console.error('✗ Error running comparison:', error);
        console.error('✗ Error details:', error.stack);
        showAlert('error', 'Error running comparison: ' + error.message);
    } finally {
        compareBtn.disabled = false;
        compareBtn.innerHTML = '<i class="bi bi-play-circle"></i> Run Comparison';
        processingSpinner.style.display = 'none';
    }
}

// ================================
// FETCH AND DISPLAY RESULTS
// ================================

async function fetchAndDisplayResults() {
    try {
        console.log('✓ Fetching /api/results');
        const response = await fetch('/api/results');
        const data = await response.json();
        
        console.log('✓ Results data received:', data);
        
        if (response.ok) {
            displayStatistics(data.statistics);
            displaySummaryCards(data.statistics);
            showDownloadPanel();
        } else {
            showAlert('error', 'Error fetching results: ' + data.error);
        }
    } catch (error) {
        console.error('✗ Error fetching results:', error);
        showAlert('error', 'Error fetching results: ' + error.message);
    }
}

// ================================
// DISPLAY STATISTICS
// ================================

function displayStatistics(stats) {
    document.getElementById('stat-ccp').textContent = stats.total_ccp.toLocaleString();
    document.getElementById('stat-at').textContent = stats.total_at.toLocaleString();
    document.getElementById('stat-common').textContent = stats.total_common.toLocaleString();
    document.getElementById('stat-action').textContent = stats.total_action_required.toLocaleString();
    
    document.getElementById('statisticsDashboard').style.display = 'block';
}

// ================================
// DISPLAY SUMMARY CARDS
// ================================

function displaySummaryCards(stats) {
    document.getElementById('req1-count').textContent = stats.requirement_1_count.toLocaleString();
    document.getElementById('req2-count').textContent = stats.requirement_2_count.toLocaleString();
    document.getElementById('req3-count').textContent = stats.requirement_3_count.toLocaleString();
    
    document.getElementById('req1-file-count').textContent = stats.requirement_1_count.toLocaleString() + ' records';
    document.getElementById('req2-file-count').textContent = stats.requirement_2_count.toLocaleString() + ' records';
    document.getElementById('req3-file-count').textContent = stats.requirement_3_count.toLocaleString() + ' records';
    
    document.getElementById('comparisonSummary').style.display = 'block';
}

// ================================
// SHOW DOWNLOAD PANEL
// ================================

function showDownloadPanel() {
    document.getElementById('downloadPanel').style.display = 'block';
}

// ================================
// DOWNLOAD RESULTS
// ================================

async function downloadResults(requirement) {
    try {
        // Determine endpoint and filename
        let endpoint, filename;
        
        if (requirement === 'zip') {
            endpoint = 'download-zip';
            filename = 'CCP_AT_Comparison_Results.zip';
        } else {
            endpoint = `download/${requirement}`;
            const filenameMap = {
                'req1': '01_Securities_In_CCP_Not_In_AT.xlsx',
                'req2': '02_Securities_In_AT_Not_In_CCP.xlsx',
                'req3': '03_Securities_Config_Mismatch.xlsx',
                'report': '00_Comparison_Report.xlsx'
            };
            filename = filenameMap[requirement] || 'download.xlsx';
        }
        
        const response = await fetch(`/api/${endpoint}`);
        
        if (response.ok) {
            const blob = await response.blob();
            const url = window.URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.href = url;
            a.download = filename;
            document.body.appendChild(a);
            a.click();
            window.URL.revokeObjectURL(url);
            document.body.removeChild(a);
            
            showAlert('success', `Downloaded: ${filename}`);
        } else {
            showAlert('error', 'Error downloading file');
        }
    } catch (error) {
        console.error('Error downloading results:', error);
        showAlert('error', 'Error downloading file: ' + error.message);
    }
}

// ================================
// RESET SESSION
// ================================

async function resetSession() {
    if (!confirm('Are you sure you want to start over? All uploaded data will be cleared.')) {
        return;
    }
    
    try {
        const response = await fetch('/api/reset', {
            method: 'POST'
        });
        
        if (response.ok) {
            // Reset UI
            appState = {
                uploadedFiles: [],
                validationResult: null,
                comparisonResults: null,
                currentStep: 1
            };
            
            // Hide all steps except step 1
            document.getElementById('step1').style.display = 'block';
            document.getElementById('step1').style.opacity = '1';
            document.getElementById('step1').style.pointerEvents = 'auto';
            document.getElementById('step2').style.display = 'none';
            document.getElementById('step2').style.opacity = '1';
            document.getElementById('step2').style.pointerEvents = 'auto';
            document.getElementById('step3').style.display = 'none';
            document.getElementById('step3').style.opacity = '1';
            document.getElementById('step3').style.pointerEvents = 'auto';
            
            // Reset file inputs
            fileInput.value = '';
            document.getElementById('filesList').style.display = 'none';
            document.getElementById('validationResults').style.display = 'none';
            uploadBtn.disabled = true;
            clearFilesBtn.style.display = 'none';
            
            // Reset checklists
            document.getElementById('check1').checked = false;
            document.getElementById('check2').checked = false;
            document.getElementById('check3').checked = false;
            
            showAlert('success', 'Session reset. Ready for new upload.');
            
            // Scroll to top
            window.scrollTo({ top: 0, behavior: 'smooth' });
        } else {
            showAlert('error', 'Error resetting session');
        }
    } catch (error) {
        console.error('Error resetting session:', error);
        showAlert('error', 'Error resetting session: ' + error.message);
    }
}

// ================================
// ALERT NOTIFICATIONS
// ================================

function showAlert(type, message) {
    const alertContainer = document.getElementById('alertContainer');
    
    const alertDiv = document.createElement('div');
    alertDiv.className = `alert alert-${type} alert-dismissible fade show`;
    alertDiv.setAttribute('role', 'alert');
    alertDiv.innerHTML = `
        ${message}
        <button type="button" class="btn-close" data-bs-dismiss="alert" aria-label="Close"></button>
    `;
    
    alertContainer.appendChild(alertDiv);
    
    // Auto-dismiss after 5 seconds
    setTimeout(() => {
        alertDiv.remove();
    }, 5000);
}

// ================================
// FILE LIST POLYFILL
// ================================

function createFileList(files) {
    const dt = new DataTransfer();
    files.forEach(file => dt.items.add(file));
    return dt.files;
}

// ================================
// INITIALIZATION
// ================================

document.addEventListener('DOMContentLoaded', () => {
    console.log('✓ CCP-AT Comparison Engine GUI loaded successfully');
    
    // Initialize all elements and attach listeners
    initializeElements();
    
    // Ensure step 1 is visible
    document.getElementById('step1').style.display = 'block';
    document.getElementById('step2').style.display = 'none';
    document.getElementById('step3').style.display = 'none';
    
    console.log('✓ All event listeners attached');
});
