document.addEventListener('DOMContentLoaded', () => {
    fetchMetrics();
});

const chatHistory = document.getElementById('chatHistory');
const chatForm = document.getElementById('chatForm');
const userInput = document.getElementById('userInput');
const sendBtn = document.getElementById('sendBtn');
const suggestionsContainer = document.getElementById('suggestionsContainer');
const headerMetrics = document.getElementById('headerMetrics');

const roleSelect = document.getElementById('roleSelect');
const zoneSelect = document.getElementById('zoneSelect');
const bdoSelect = document.getElementById('bdoSelect');
const apiKeyInput = document.getElementById('apiKeyInput');

// Populate BDOs helper
function populateBDOs(zone) {
    bdoSelect.innerHTML = '<option value="">Select BDO...</option>';
    if(!zone) return;
    const prefix = zone.charAt(0); // E, W, N, S
    for(let i=1; i<=20; i++) {
        let num = i < 10 ? '0'+i : i;
        let bdoName = `${prefix}_BDO_${num}`;
        bdoSelect.innerHTML += `<option value="${bdoName}">${bdoName}</option>`;
    }
}

function handleRoleChange() {
    const role = roleSelect.value;
    const chipContainer = document.querySelector('.suggestion-chips');
    
    // Reset Views
    zoneSelect.style.display = 'none';
    bdoSelect.style.display = 'none';
    zoneSelect.value = "";
    bdoSelect.value = "";
    
    if (role === 'National Sales Manager') {
        chipContainer.innerHTML = `
            <button onclick="submitSuggested('Which zone is performing best?')">Which zone is performing best?</button>
            <button onclick="submitSuggested('What is the national collection percentage?')">National collection %?</button>
            <button onclick="submitSuggested('Show me top active coverage zones.')">Active dealer coverage</button>
        `;
    } else if (role === 'Zonal Sales Manager') {
        zoneSelect.style.display = 'inline-block';
        chipContainer.innerHTML = `
            <button onclick="submitSuggested('Which BDO is underperforming?')">Which BDO is underperforming?</button>
            <button onclick="submitSuggested('Show me high risk collections in my zone')">Collection risks</button>
            <button onclick="submitSuggested('Which BDO has most pending dispatches?')">Pending dispatches</button>
        `;
    } else if (role === 'BDO') {
        zoneSelect.style.display = 'inline-block';
        bdoSelect.style.display = 'inline-block';
        chipContainer.innerHTML = `
            <button onclick="submitSuggested('Give me my 5 daily actions')">Give me my 5 daily actions</button>
            <button onclick="submitSuggested('Which of my saudas are expiring soon?')">Expiring saudas</button>
            <button onclick="submitSuggested('Which dealers need collection follow-up today?')">Pending collection</button>
        `;
    }
    fetchMetrics();
}

function handleZoneChange() {
    if(roleSelect.value === 'BDO') {
        populateBDOs(zoneSelect.value);
    }
    fetchMetrics();
}

async function fetchMetrics() {
    try {
        const role = roleSelect.value;
        const zone = zoneSelect.value;
        const bdo = bdoSelect.value;
        
        let url = `/api/metrics?role=${encodeURIComponent(role)}&zone=${encodeURIComponent(zone)}&bdo=${encodeURIComponent(bdo)}`;
        
        const response = await fetch(url);
        const data = await response.json();
        
        let revenueCr = (data.total_revenue / 10000000).toFixed(2);
        let riskL = (data.total_outstanding / 100000).toFixed(2);
        let dormantPct = ((data.dormant_count / data.total_dealers) * 100).toFixed(1);

        headerMetrics.innerHTML = `
            <div class="metric-card">
                <span class="metric-label">Total Dealers</span>
                <span class="metric-value">${data.total_dealers}</span>
            </div>
            <div class="metric-card">
                <span class="metric-label">Gross Revenue</span>
                <span class="metric-value">₹${revenueCr} Cr</span>
            </div>
            <div class="metric-card">
                <span class="metric-label">Risk Exposure</span>
                <span class="metric-value">₹${riskL} L</span>
            </div>
            <div class="metric-card">
                <span class="metric-label">Critical Dormancy</span>
                <span class="metric-value">${data.dormant_count} <span style="font-size: 0.9rem; color: #94a3b8;">(${dormantPct}%)</span></span>
            </div>
        `;
    } catch (e) {
        console.error("Failed to load metrics", e);
    }
}

function submitSuggested(query) {
    userInput.value = query;
    handleQuerySubmit(new Event('submit'));
}

function appendUserMessage(text) {
    if(suggestionsContainer) suggestionsContainer.style.display = 'none';
    const msgDiv = document.createElement('div');
    msgDiv.className = 'message user';
    msgDiv.textContent = text;
    chatHistory.appendChild(msgDiv);
    chatHistory.scrollTop = chatHistory.scrollHeight;
}

function appendAIMessage(markdownText, tableData) {
    const msgDiv = document.createElement('div');
    msgDiv.className = 'message ai';
    
    // Parse Markdown
    msgDiv.innerHTML = marked.parse(markdownText);
    
    // Build Data Table if exists
    if (tableData && tableData.length > 0) {
        const wrapper = document.createElement('div');
        wrapper.className = 'data-table-wrapper';
        
        const table = document.createElement('table');
        
        // Headers
        const thead = document.createElement('thead');
        const hRow = document.createElement('tr');
        const keys = Object.keys(tableData[0]).filter(k => !['actions', 'priority_score'].includes(k)); // Customize visible columns
        
        hRow.innerHTML = `<th>Priority</th>` + keys.map(k => `<th>${k}</th>`).join('');
        thead.appendChild(hRow);
        table.appendChild(thead);
        
        // Body
        const tbody = document.createElement('tbody');
        tableData.forEach(row => {
            const tr = document.createElement('tr');
            let cells = `<td>${row['priority_score'].toFixed(0)}</td>`;
            keys.forEach(k => {
                let val = row[k];
                if (typeof val === 'number' && (k.includes('revenue') || k.includes('amount') || k.includes('value'))) {
                    val = "₹ " + val.toLocaleString('en-IN');
                }
                cells += `<td>${val}</td>`;
            });
            tr.innerHTML = cells;
            tbody.appendChild(tr);
        });
        table.appendChild(tbody);
        wrapper.appendChild(table);
        msgDiv.appendChild(wrapper);
    }
    
    chatHistory.appendChild(msgDiv);
    chatHistory.scrollTop = chatHistory.scrollHeight;
}

function showTypingIndicator() {
    const loader = document.createElement('div');
    loader.className = 'typing-indicator';
    loader.id = 'typingIndicator';
    loader.innerHTML = `
        <div class="typing-dot"></div>
        <div class="typing-dot"></div>
        <div class="typing-dot"></div>
    `;
    chatHistory.appendChild(loader);
    chatHistory.scrollTop = chatHistory.scrollHeight;
}

function hideTypingIndicator() {
    const loader = document.getElementById('typingIndicator');
    if(loader) loader.remove();
}

async function handleQuerySubmit(e) {
    e.preventDefault();
    
    const apiKey = apiKeyInput.value.trim();
    if (!apiKey) {
        alert("Please enter a Groq API Key first!");
        return;
    }
    
    const query = userInput.value.trim();
    if (!query) return;

    appendUserMessage(query);
    userInput.value = '';
    sendBtn.disabled = true;
    showTypingIndicator();

    try {
        const payload = {
            query: query,
            api_key: apiKey,
            role: roleSelect.value,
            zone: zoneSelect.value,
            bdo: bdoSelect.value
        };
        
        const response = await fetch('/api/chat', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(payload)
        });
        
        const data = await response.json();
        hideTypingIndicator();
        
        if(data.error) {
            appendAIMessage(`**Error:** ${data.error}`);
        } else {
            appendAIMessage(data.explanation, data.data);
        }
    } catch (e) {
        hideTypingIndicator();
        appendAIMessage(`**Connection Error:** Could not reach the server.`);
    } finally {
        sendBtn.disabled = false;
        userInput.focus();
    }
}

chatForm.addEventListener('submit', handleQuerySubmit);
