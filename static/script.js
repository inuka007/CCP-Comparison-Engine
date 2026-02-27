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

// ================================
// UI HELPERS
// ================================

function show(el) { el.style.display = 'block'; }
function hide(el) { el.style.display = 'none'; }

function setButtonLoading(button, isLoading, text) {
    if (isLoading) {
        button.dataset.originalText = button.innerHTML;
        button.innerHTML = text;
        button.disabled = true;
        button.classList.add('processing');
    } else {
        button.innerHTML = button.dataset.originalText || button.innerHTML;
        button.disabled = false;
        button.classList.remove('processing');
    }
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
    
    setButtonLoading(uploadBtn, true, '<span class="spinner-border spinner-border-sm me-2"></span>Uploading...');
    
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
            setButtonLoading(uploadBtn, false);
            uploadBtn.innerHTML = '<i class="bi bi-upload"></i> Upload Files';
        }
    } catch (error) {
        console.error('✗ Error uploading files:', error);
        showAlert('error', 'Error uploading files: ' + error.message);
        setButtonLoading(uploadBtn, false);
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
    
    setButtonLoading(compareBtn, true, '<i class="bi bi-hourglass-split"></i> Processing... Please wait');
    const processingSpinner = document.getElementById('processingSpinner');
    show(processingSpinner);
    
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
            show(document.getElementById('step3'));
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
        setButtonLoading(compareBtn, false);
        compareBtn.innerHTML = '<i class="bi bi-play-circle"></i> Run Comparison';
        hide(processingSpinner);
    }
}

// ================================
// FETCH AND DISPLAY RESULTS
// ================================

let summaryChart = null;

async function fetchAndDisplayResults() {
    try {
        console.log('✓ Fetching /api/results');
        const response = await fetch('/api/results');
        const data = await response.json();
        
        console.log('✓ Results data received:', data);
        
        if (response.ok) {
            displayOverallStats(data.statistics);
            displayRequirementDetails(data);
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
// DISPLAY OVERALL STATISTICS WITH CHART
// ================================

function displayOverallStats(stats) {
    // Update stat boxes
    document.getElementById('stat-ccp').textContent = stats.total_ccp.toLocaleString();
    document.getElementById('stat-at').textContent = stats.total_at.toLocaleString();
    document.getElementById('stat-common').textContent = stats.total_common.toLocaleString();
    document.getElementById('stat-action').textContent = stats.total_action_required.toLocaleString();
    
    // Create chart
    const ctx = document.getElementById('summaryChart').getContext('2d');
    
    // Destroy existing chart if any
    if (summaryChart) {
        summaryChart.destroy();
    }
    
    summaryChart = new Chart(ctx, {
        type: 'doughnut',
        data: {
            labels: ['Matched Records', 'Req1: CCP→AT', 'Req2: AT→CCP', 'Req3: Mismatch'],
            datasets: [{
                data: [
                    stats.total_common,
                    stats.requirement_1_count,
                    stats.requirement_2_count,
                    stats.requirement_3_count
                ],
                backgroundColor: [
                    'rgba(34, 197, 94, 0.8)',   // green
                    'rgba(220, 38, 38, 0.8)',   // red
                    'rgba(245, 158, 11, 0.8)',  // yellow
                    'rgba(14, 165, 233, 0.8)'   // blue
                ],
                borderColor: [
                    'rgb(34, 197, 94)',
                    'rgb(220, 38, 38)',
                    'rgb(245, 158, 11)',
                    'rgb(14, 165, 233)'
                ],
                borderWidth: 2
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: {
                    position: 'bottom',
                    labels: {
                        padding: 15,
                        font: {
                            size: 11
                        }
                    }
                },
                tooltip: {
                    callbacks: {
                        label: function(context) {
                            const label = context.label || '';
                            const value = context.parsed || 0;
                            const total = context.dataset.data.reduce((a, b) => a + b, 0);
                            const percentage = ((value / total) * 100).toFixed(1);
                            return `${label}: ${value.toLocaleString()} (${percentage}%)`;
                        }
                    }
                }
            }
        }
    });
    
    document.getElementById('overallStats').style.display = 'block';
}

// ================================
// DISPLAY REQUIREMENT DETAILS
// ================================

function displayRequirementDetails(data) {
    const stats = data.statistics;
    
    // Update requirement counts
    document.getElementById('req1-count').textContent = stats.requirement_1_count.toLocaleString();
    document.getElementById('req2-count').textContent = stats.requirement_2_count.toLocaleString();
    document.getElementById('req3-count').textContent = stats.requirement_3_count.toLocaleString();
    
    // Log summary data for debugging
    console.log('Req1 summary:', data.requirement_1.summary);
    console.log('Req2 summary:', data.requirement_2.summary);
    console.log('Req3 summary:', data.requirement_3.summary);
    
    // Display summary tables
    displayReq1Summary(data.requirement_1.summary);
    displayReq2Summary(data.requirement_2.summary);
    displayReq3Summary(data.requirement_3.summary);
    
    document.getElementById('requirementDetails').style.display = 'block';
}

function displayReq1Summary(summaryData) {
    const table = document.getElementById('req1-summary-table');
    
    console.log('displayReq1Summary called with:', summaryData);
    
    if (!summaryData || summaryData.length === 0) {
        table.innerHTML = '<thead class="table-light"><tr><th colspan="2" class="text-center">No summary data available</th></tr></thead><tbody></tbody>';
        return;
    }
    
    // Req1 Summary: Segment Name | CCP # Securities
    let html = '<thead class="table-light"><tr>';
    html += '<th>Segment Name</th>';
    html += '<th class="text-end">CCP # Securities</th>';
    html += '</tr></thead><tbody>';
    
    summaryData.forEach(row => {
        const segmentName = row['Segment Name'] || row['segment_name'] || '';
        const ccpCount = row['CCP # Securities'] || row['ccp_securities'] || '';
        const isTotal = String(segmentName).toLowerCase().includes('total');
        
        html += `<tr${isTotal ? ' class="table-secondary fw-bold"' : ''}>`;
        html += `<td>${segmentName}</td>`;
        html += `<td class="text-end">${ccpCount}</td>`;
        html += '</tr>';
    });
    
    html += '</tbody>';
    table.innerHTML = html;
}

function displayReq2Summary(summaryData) {
    const table = document.getElementById('req2-summary-table');
    
    console.log('displayReq2Summary called with:', summaryData);
    
    if (!summaryData || summaryData.length === 0) {
        table.innerHTML = '<thead class="table-light"><tr><th colspan="4" class="text-center">No summary data available</th></tr></thead><tbody></tbody>';
        return;
    }
    
    // Req2 Summary: Region | Total Records | Comparable Records | Uncomparable Records
    let html = '<thead class="table-light"><tr>';
    html += '<th>Region</th>';
    html += '<th class="text-end">Total Records</th>';
    html += '<th class="text-end">Comparable Records</th>';
    html += '<th class="text-end">Uncomparable Records</th>';
    html += '</tr></thead><tbody>';
    
    summaryData.forEach(row => {
        const region = row['Region'] || row['region'] || '';
        const totalRecords = row['In AT not CCP'] || row['in_at_not_ccp'] || '';
        const comparableRecords = row['Exist in Product DB'] || row['exist_in_product_db'] || '';
        const uncomparableRecords = row['Do not exist in DB'] || row['do_not_exist_in_db'] || '';
        const isTotal = String(region).toLowerCase().includes('total');
        
        html += `<tr${isTotal ? ' class="table-secondary fw-bold"' : ''}>`;
        html += `<td>${region}</td>`;
        html += `<td class="text-end">${totalRecords}</td>`;
        html += `<td class="text-end">${comparableRecords}</td>`;
        html += `<td class="text-end">${uncomparableRecords}</td>`;
        html += '</tr>';
    });
    
    html += '</tbody>';
    table.innerHTML = html;
}

function displayReq3Summary(summaryData) {
    const table = document.getElementById('req3-summary-table');
    
    console.log('displayReq3Summary called with:', summaryData);
    
    if (!summaryData || summaryData.length === 0) {
        table.innerHTML = '<thead class="table-light"><tr><th colspan="2" class="text-center">No summary data available</th></tr></thead><tbody></tbody>';
        return;
    }
    
    // Req3 Summary: Pivot table with column headers as rows and exchanges as columns
    // First, extract all unique exchanges/columns
    const firstRow = summaryData[0];
    const columns = Object.keys(firstRow);
    
    // Assuming first column is the row label (Column Header)
    const rowLabelKey = columns[0];
    const exchangeColumns = columns.slice(1); // Rest are exchanges
    
    let html = '<thead class="table-light"><tr>';
    html += `<th>${rowLabelKey}</th>`;
    exchangeColumns.forEach(col => {
        html += `<th class="text-end">${col}</th>`;
    });
    html += '</tr></thead><tbody>';
    
    summaryData.forEach(row => {
        const rowLabel = row[rowLabelKey] || '';
        const isTotal = String(rowLabel).toLowerCase().includes('total');
        
        html += `<tr${isTotal ? ' class="table-secondary fw-bold"' : ''}>`;
        html += `<td>${rowLabel}</td>`;
        
        exchangeColumns.forEach(col => {
            const value = row[col] !== null && row[col] !== undefined ? row[col] : '';
            html += `<td class="text-end">${value}</td>`;
        });
        
        html += '</tr>';
    });
    
    html += '</tbody>';
    table.innerHTML = html;
}

function displayReq1Segments(req1Data) {
    const segmentList = document.getElementById('req1-segment-list');
    
    if (!req1Data || !req1Data.data || req1Data.data.length === 0) {
        segmentList.innerHTML = '<div class="text-muted small">No data available</div>';
        return;
    }
    
    // Count by segment (look for segment-related columns)
    const segments = {};
    req1Data.data.forEach(row => {
        const segment = row.segment_name || 'Unknown';
        segments[segment] = (segments[segment] || 0) + 1;
    });
    
    let html = '';
    Object.entries(segments).sort((a, b) => b[1] - a[1]).slice(0, 5).forEach(([segment, count]) => {
        html += `<div class="d-flex justify-content-between mb-1">
            <span>${segment}</span>
            <strong>${count}</strong>
        </div>`;
    });
    
    segmentList.innerHTML = html || '<div class="text-muted small">No segment data</div>';
}

function displayReq2Regions(req2Data) {
    const regionList = document.getElementById('req2-region-list');
    
    if (!req2Data || !req2Data.data || req2Data.data.length === 0) {
        regionList.innerHTML = '<div class="text-muted small">No data available</div>';
        return;
    }
    
    // Count by exchange/region
    const regions = {};
    req2Data.data.forEach(row => {
        const exchange = row.exchange || 'Unknown';
        regions[exchange] = (regions[exchange] || 0) + 1;
    });
    
    let html = '';
    Object.entries(regions).sort((a, b) => b[1] - a[1]).forEach(([exchange, count]) => {
        html += `<div class="d-flex justify-content-between mb-1">
            <span>${exchange}</span>
            <strong>${count}</strong>
        </div>`;
    });
    
    regionList.innerHTML = html || '<div class="text-muted small">No region data</div>';
}

function displayReq3Mismatches(req3Data) {
    const fieldList = document.getElementById('req3-field-list');
    
    if (!req3Data || !req3Data.data || req3Data.data.length === 0) {
        fieldList.innerHTML = '<div class="text-muted small">No data available</div>';
        return;
    }
    
    // Count mismatched fields
    const fields = {};
    req3Data.data.forEach(row => {
        const mismatchFields = row.mismatched_fields || '';
        if (mismatchFields) {
            mismatchFields.split(',').forEach(field => {
                const trimmed = field.trim();
                if (trimmed) {
                    fields[trimmed] = (fields[trimmed] || 0) + 1;
                }
            });
        }
    });
    
    let html = '';
    Object.entries(fields).sort((a, b) => b[1] - a[1]).slice(0, 5).forEach(([field, count]) => {
        html += `<div class="d-flex justify-content-between mb-1">
            <span class="text-truncate" style="max-width: 150px;">${field}</span>
            <strong>${count}</strong>
        </div>`;
    });
    
    fieldList.innerHTML = html || '<div class="text-muted small">No mismatch data</div>';
}

// ================================
// DISPLAY STATISTICS (Legacy - keeping for compatibility)
// ================================

function displayStatistics(stats) {
    document.getElementById('stat-ccp').textContent = stats.total_ccp.toLocaleString();
    document.getElementById('stat-at').textContent = stats.total_at.toLocaleString();
    document.getElementById('stat-common').textContent = stats.total_common.toLocaleString();
    document.getElementById('stat-action').textContent = stats.total_action_required.toLocaleString();
}

// ================================
// DISPLAY SUMMARY CARDS (Legacy - keeping for compatibility)
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
                'report': '00_Comparison_Report.xlsx',
                'combined': 'CCP_Combined_and_AT_Whitelist.xlsx'
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
            show(document.getElementById('step1'));
            document.getElementById('step1').style.opacity = '1';
            document.getElementById('step1').style.pointerEvents = 'auto';
            hide(document.getElementById('step2'));
            document.getElementById('step2').style.opacity = '1';
            document.getElementById('step2').style.pointerEvents = 'auto';
            hide(document.getElementById('step3'));
            document.getElementById('step3').style.opacity = '1';
            document.getElementById('step3').style.pointerEvents = 'auto';
            
            // Reset file inputs
            fileInput.value = '';
            hide(document.getElementById('filesList'));
            hide(document.getElementById('validationResults'));
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
    show(document.getElementById('step1'));
    hide(document.getElementById('step2'));
    hide(document.getElementById('step3'));
    
    console.log('✓ All event listeners attached');
});
