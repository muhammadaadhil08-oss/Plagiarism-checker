document.addEventListener("DOMContentLoaded", function() {
    // File upload and text area listeners for new_check
    const docUpload = document.getElementById('documentUpload');
    const scanButton = document.getElementById('scanButton');
    const scannerInput = document.getElementById('hiddenScannerInput');
    const btnBrowse = document.getElementById('btnBrowse');
    const wordCountLabel = document.getElementById('wordCountLabel');

    if (scannerInput && wordCountLabel) {
        scannerInput.addEventListener('input', function() {
            const text = this.value;
            const words = text.trim() ? text.trim().split(/\s+/).length : 0;
            const chars = text.length;
            wordCountLabel.innerText = `${words} words, ${chars} characters`;
        });
    }

    if (docUpload && scannerInput) {
        docUpload.addEventListener('change', function(e) {
            const file = e.target.files[0];
            if (!file) return;

            const reader = new FileReader();
            reader.onload = function(evt) {
                scannerInput.value = evt.target.result;
                // update word count
                const evtText = evt.target.result;
                const words = evtText.trim() ? evtText.trim().split(/\s+/).length : 0;
                const chars = evtText.length;
                if (wordCountLabel) wordCountLabel.innerText = `${words} words, ${chars} characters`;
                
                if (btnBrowse) {
                    btnBrowse.innerText = "Selected: " + file.name;
                }
                if (scanButton) scanButton.disabled = false;
            };
            reader.readAsText(file);
        });
    }
});

function triggerScan() {
    const text = document.getElementById('hiddenScannerInput').value;
    if (!text || text.trim().split(/\s+/).length < 15) {
        alert("Please provide at least 15 words to scan.");
        return;
    }

    const overlay = document.getElementById('scanOverlay');
    const scanButton = document.getElementById('scanButton');
    const btnBrowse = document.getElementById('btnBrowse');
    
    // Extract filename if uploaded, else default
    let filename = "Pasted Text";
    if (btnBrowse && btnBrowse.innerText.includes("Selected: ")) {
        filename = btnBrowse.innerText.replace("Selected: ", "").trim();
    }

    if (scanButton) scanButton.disabled = true;
    if (overlay) overlay.style.display = "block";

    // Capture user's local time for accurate history display
    const localNow = new Date();
    const localDate = localNow.toLocaleDateString('en-US', { month: 'long', day: 'numeric', year: 'numeric' });
    const localTime = localNow.toLocaleTimeString('en-US', { hour: '2-digit', minute: '2-digit', hour12: true });

    // Call the Plagiarism API
    fetch('/plagiarism', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        },
        body: JSON.stringify({ 
            text: text, 
            filename: filename,
            local_date: localDate,
            local_time: localTime 
        })
    })
    .then(response => response.json())
    .then(data => {
        if (scanButton) scanButton.disabled = false;
        if (overlay) overlay.style.display = "none";
        renderResult(data);
    })
    .catch((error) => {
        alert("Plagiarism Scan Error: " + error.message);
        if (scanButton) scanButton.disabled = false;
        if (overlay) overlay.style.display = "none";
    });
}

function renderResult(data) {
    if (data.error) {
        alert("Scan Failed: " + data.error);
        return;
    }

    // Determine plagiarism level
    const plagScore = data.history_item ? data.history_item.plagiarism_score : (data.web_score || 0);
    const aiScore = data.history_item ? data.history_item.ai_score : (data.ai_score || 0);
    // We will adapt the UI badges to represent Plagiarism Uniqueness instead
    
    let colorClass, badgeClass, badgeText, iconBg, iconContent;
    if (plagScore > 40) {
        // High plagiarism
        colorClass = "red-val";
        badgeClass = "badge-red";
        badgeText = "Plagiarism Detected";
        iconBg = "red-icon";
        iconContent = '<svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"></path><polyline points="14 2 14 8 20 8"></polyline><line x1="16" y1="13" x2="8" y2="13"></line><line x1="16" y1="17" x2="8" y2="17"></line><polyline points="10 9 9 9 8 9"></polyline></svg>';
    } else if (plagScore > 10) {
        // Mixed
        colorClass = "orange-val";
        badgeClass = "badge-orange";
        badgeText = "Slightly Matched";
        iconBg = "orange-icon";
        iconContent = '<svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"></path><polyline points="14 2 14 8 20 8"></polyline></svg>';
    } else {
        // Human/Unique
        colorClass = "green-val";
        badgeClass = "badge-green";
        badgeText = "Unique Content";
        iconBg = "green-icon";
        iconContent = '<svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"></path><polyline points="14 2 14 8 20 8"></polyline></svg>';
    }

    // Append to action-center dynamically in new_check.html
    let resultContainer = document.getElementById('scanResultArea');
    if (!resultContainer) {
        resultContainer = document.createElement('div');
        resultContainer.id = 'scanResultArea';
        resultContainer.style.marginTop = '30px';
        resultContainer.style.width = '100%';
        resultContainer.style.maxWidth = '800px';
        const actionCenter = document.querySelector('.action-center');
        if (actionCenter) {
            actionCenter.appendChild(resultContainer);
        } else {
            document.body.appendChild(resultContainer);
        }
    }

    resultContainer.innerHTML = `
        <div class="check-item" style="text-align: left;">
            <div class="check-icon ${iconBg}">
                ${iconContent}
            </div>
            <div class="check-info">
                <h4>Analysis Result</h4>
                <span class="time">Just Scanned</span>
                <span class="badge ${badgeClass}">${badgeText}</span>
            </div>
            <div class="check-score" style="margin-right: 25px;">
                <span class="score-label">AI Score</span>
                <span class="score-val orange-val" style="font-size: 1.4rem;">${aiScore}%</span>
            </div>
            <div class="check-score">
                <span class="score-label">Plagiarism</span>
                <span class="score-val ${colorClass}" style="font-size: 1.4rem;">${plagScore}%</span>
                <span class="sub-score" style="display:block; margin-top:4px;">Unique: ${100 - plagScore}%</span>
            </div>
        </div>
    `;

    // Reset inputs
    const hiddenInput = document.getElementById('hiddenScannerInput');
    if (hiddenInput) hiddenInput.value = "";
    
    if (document.getElementById('wordCountLabel')) {
        document.getElementById('wordCountLabel').innerText = "0 words, 0 characters";
    }
    if (document.getElementById('btnBrowse')) {
        document.getElementById('btnBrowse').innerHTML = '<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" style="margin-right:6px; vertical-align:middle;"><path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"></path><polyline points="17 8 12 3 7 8"></polyline><line x1="12" y1="3" x2="12" y2="15"></line></svg> Browse Files';
    }
    const docUploadInputs = document.getElementById('documentUpload');
    if (docUploadInputs) docUploadInputs.value = "";
}

// History Page Interactions
function deleteHistoryItem(btn, itemId) {
    if(!itemId) return; // Prevent deleting nothing
    
    if(confirm("Are you sure you want to delete this analysis record?")) {
        fetch(`/api/history/${itemId}`, {
            method: 'DELETE'
        })
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                const item = document.getElementById('item-' + itemId);
                if (item) {
                    item.style.transition = 'opacity 0.3s ease';
                    item.style.opacity = '0';
                    setTimeout(() => {
                        item.remove();
                        // Optional: Could reload here to recalculate stats at top
                        location.reload(); 
                    }, 300);
                }
            } else {
                alert("Failed to delete item.");
            }
        })
        .catch(err => {
            console.error(err);
            alert("Error deleting the record.");
        });
    }
}

let viewDocController = null;

function closeModal() {
    const viewModal = document.getElementById('viewModal');
    if (viewModal) {
        viewModal.style.display = 'none';
        // Abort any pending fetch
        if (viewDocController) {
            viewDocController.abort();
            viewDocController = null;
        }
    }
}

function viewDocument(itemId, title) {
    const modalTitle = document.getElementById('modalTitle');
    const viewModal = document.getElementById('viewModal');
    const contentViewer = document.getElementById('modalContentViewer');
    
    if (modalTitle && viewModal && contentViewer) {
        modalTitle.innerText = "Viewing: " + title;
        contentViewer.innerText = "Fetching content...";
        viewModal.style.display = 'flex';
        
        // Cancel previous request if any
        if (viewDocController) viewDocController.abort();
        viewDocController = new AbortController();
        
        fetch(`/api/history/${itemId}`, { signal: viewDocController.signal })
            .then(res => res.json())
            .then(data => {
                if(data.text) {
                    contentViewer.innerText = data.text;
                } else {
                    contentViewer.innerText = "Could not load document text.";
                }
                viewDocController = null;
            })
            .catch(err => {
                if (err.name === 'AbortError') {
                    console.log('Fetch aborted');
                } else {
                    contentViewer.innerText = "Error loading content.";
                    console.error(err);
                }
                viewDocController = null;
            });
    } else {
        alert("Viewing document: " + title);
    }
}

// History Search and Filtering
document.addEventListener("DOMContentLoaded", function() {
    const searchInput = document.querySelector('.expanded-search input');
    const historyList = document.getElementById('historyChecksList');
    
    // Date Range Filtering
    const dateFrom = document.getElementById('dateFrom');
    const dateTo = document.getElementById('dateTo');
    const filterBtn = document.querySelector('.btn-filter:first-of-type'); // Moved this declaration up

    function applyFilters() {
        if (!historyList) return; // Guard for non-history pages
        const searchTerm = (searchInput ? searchInput.value.toLowerCase() : "");
        const statusFilter = (filterBtn ? filterBtn.getAttribute('data-filter') || 'all' : 'all');
        const fromVal = dateFrom ? dateFrom.value : "";
        const toVal = dateTo ? dateTo.value : "";

        const items = historyList.querySelectorAll('.check-item');
        
        items.forEach(item => {
            const title = item.querySelector('.doc-title').innerText.toLowerCase();
            const badge = item.querySelector('.badge').innerText.toLowerCase();
            const itemDate = item.getAttribute('data-date'); // e.g., "2026-03-15"

            let show = true;

            // Search Filter
            if (searchTerm && !title.includes(searchTerm)) show = false;

            // Status Filter
            if (statusFilter !== 'all') {
                if (statusFilter === 'ai' && !badge.includes('ai')) show = false;
                if (statusFilter === 'human' && !badge.includes('human')) show = false;
                if (statusFilter === 'mixed' && !badge.includes('mixed')) show = false;
            }

            // Date Range Filter
            if (itemDate) {
                if (fromVal && itemDate < fromVal) show = false;
                if (toVal && itemDate > toVal) show = false;
            }

            item.style.display = show ? 'flex' : 'none';
        });
    }

    if (searchInput) {
        searchInput.addEventListener('input', applyFilters);
    }

    if (filterBtn) {
        filterBtn.addEventListener('click', function() {
            const currentFilter = filterBtn.getAttribute('data-filter') || 'all';
            let nextFilter, filterText;
            
            if (currentFilter === 'all') { nextFilter = 'ai'; filterText = 'Filter: AI'; }
            else if (currentFilter === 'ai') { nextFilter = 'human'; filterText = 'Filter: Human'; }
            else if (currentFilter === 'human') { nextFilter = 'mixed'; filterText = 'Filter: Mixed'; }
            else { nextFilter = 'all'; filterText = 'Filter'; }
            
            filterBtn.setAttribute('data-filter', nextFilter);
            filterBtn.innerHTML = `<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polygon points="22 3 2 3 10 12.46 10 19 14 21 14 12.46 22 3"></polygon></svg> ${filterText}`;
            
            applyFilters();
        });
    }

    if (dateFrom) dateFrom.addEventListener('change', applyFilters);
    if (dateTo) dateTo.addEventListener('change', applyFilters);
});
