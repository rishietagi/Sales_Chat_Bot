document.addEventListener('DOMContentLoaded', () => {
    fetchBDOs();
});

const chatHistory = document.getElementById('chatHistory');
const chatForm = document.getElementById('chatForm');
const userInput = document.getElementById('userInput');
const sendBtn = document.getElementById('sendBtn');
const suggestionsContainer = document.getElementById('suggestionsContainer');
const headerMetrics = document.getElementById('headerMetrics');
const bdoSelect = document.getElementById('bdoSelect');
const apiKeyInput = document.getElementById('apiKeyInput');
const modelSelect = document.getElementById('modelSelect');
const refreshModelsBtn = document.getElementById('refreshModelsBtn');

async function fetchBDOs() {
    try {
        const response = await fetch('/api/bdos');
        const data = await response.json();
        bdoSelect.innerHTML = '<option value="">Select BDO...</option>';
        if (data.bdos) {
            data.bdos.forEach(bdo => {
                bdoSelect.innerHTML += `<option value="${bdo}">${bdo}</option>`;
            });
        }
    } catch (e) {
        console.error("Failed to load BDOs", e);
    }
}

async function fetchGeminiModels() {
    const apiKey = apiKeyInput.value.trim();
    if (!apiKey) {
        alert("Please enter your API Key first to fetch models.");
        return;
    }
    
    refreshModelsBtn.textContent = "Fetching...";
    refreshModelsBtn.disabled = true;

    try {
        const response = await fetch(`/api/models/gemini?api_key=${encodeURIComponent(apiKey)}`);
        const data = await response.json();
        
        if (data.error) {
            alert("Error fetching models: " + data.error);
            refreshModelsBtn.textContent = "Fetch Available Models";
            refreshModelsBtn.disabled = false;
            return;
        }

        modelSelect.innerHTML = '';
        if (data.models && data.models.length > 0) {
            data.models.forEach(m => {
                const opt = document.createElement('option');
                opt.value = m.name.replace('models/', '');
                opt.textContent = m.display;
                if (opt.value === 'gemini-1.5-flash') opt.selected = true;
                modelSelect.appendChild(opt);
            });
        } else {
            modelSelect.innerHTML = '<option value="gemini-1.5-flash">No models found</option>';
        }
    } catch (e) {
        console.error("Failed to load models", e);
        alert("Failed to reach server for models.");
    } finally {
        refreshModelsBtn.textContent = "Fetch Available Models";
        refreshModelsBtn.disabled = false;
    }
}

function formatCurrency(amount) {
    if (!amount) return "₹0";
    if (amount >= 10000000) {
        return `₹${(amount / 10000000).toFixed(2)} Cr`;
    } else if (amount >= 100000) {
        return `₹${(amount / 100000).toFixed(2)} L`;
    } else {
        return `₹${Math.floor(amount).toLocaleString('en-IN')}`;
    }
}

async function fetchMetrics() {
    const bdo = bdoSelect.value;
    if (!bdo) {
        headerMetrics.innerHTML = '';
        return;
    }
    
    try {
        const response = await fetch(`/api/metrics?bdo=${encodeURIComponent(bdo)}`);
        const data = await response.json();
        
        if (data.error) {
            console.error(data.error);
            return;
        }

        headerMetrics.innerHTML = `
            <div class="metric-card">
                <span class="metric-label">Total Dealers</span>
                <span class="metric-value">${data.total_dealers || 0}</span>
            </div>
            <div class="metric-card">
                <span class="metric-label">Active Dealers</span>
                <span class="metric-value">${data.active_dealers || 0}</span>
            </div>
            <div class="metric-card">
                <span class="metric-label">Contracts (Active / Total)</span>
                <span class="metric-value">${data.active_contracts || 0} / ${data.total_contracts || 0}</span>
            </div>
            <div class="metric-card">
                <span class="metric-label">Booked Revenue</span>
                <span class="metric-value">${formatCurrency(data.total_booked_revenue)}</span>
            </div>
            <div class="metric-card">
                <span class="metric-label">Received Revenue</span>
                <span class="metric-value">${formatCurrency(data.total_received_revenue)}</span>
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
    const wrapper = document.createElement('div');
    wrapper.className = 'message-wrapper ai-wrapper';
    
    const avatar = document.createElement('img');
    avatar.src = '/static/icon.jpeg';
    avatar.className = 'chat-avatar';
    
    const msgDiv = document.createElement('div');
    msgDiv.className = 'message ai';
    
    // Parse Markdown
    msgDiv.innerHTML = marked.parse(markdownText);
    
    // Build Data Table if exists
    if (tableData && tableData.length > 0) {
        const tableWrapper = document.createElement('div');
        tableWrapper.className = 'data-table-wrapper';
        
        const table = document.createElement('table');
        
        // Headers
        const thead = document.createElement('thead');
        const hRow = document.createElement('tr');
        
        // Filter keys to show relevant info
        const allKeys = Object.keys(tableData[0]);
        const keys = allKeys.filter(k => 
            ['dealer_name', 'material_desc', 'pending_qty', 'contract_valid_to', 'basic_rate', 'oil_type', 'delivery_date', 'priority', 'type'].includes(k)
        );
        
        if (keys.length > 0) {
            hRow.innerHTML = keys.map(k => `<th>${k.replace(/_/g, ' ').toUpperCase()}</th>`).join('');
            thead.appendChild(hRow);
            table.appendChild(thead);
            
            // Body
            const tbody = document.createElement('tbody');
            tableData.forEach(row => {
                const tr = document.createElement('tr');
                let cells = '';
                keys.forEach(k => {
                    let val = row[k];
                    if (k === 'basic_rate') val = "₹" + val.toLocaleString('en-IN');
                    if (k === 'contract_valid_to' || k === 'delivery_date') {
                        if (val && val !== 'Unknown') val = new Date(val).toLocaleDateString();
                    }
                    cells += `<td>${val}</td>`;
                });
                tr.innerHTML = cells;
                tbody.appendChild(tr);
            });
            table.appendChild(tbody);
            tableWrapper.appendChild(table);
            msgDiv.appendChild(tableWrapper);
        }
    }
    
    wrapper.appendChild(avatar);
    wrapper.appendChild(msgDiv);
    
    chatHistory.appendChild(wrapper);
    chatHistory.scrollTop = chatHistory.scrollHeight;
}

function showTypingIndicator() {
    const wrapper = document.createElement('div');
    wrapper.className = 'message-wrapper ai-wrapper';
    wrapper.id = 'typingIndicator';
    
    const avatar = document.createElement('img');
    avatar.src = '/static/icon.jpeg';
    avatar.className = 'chat-avatar';
    
    const loader = document.createElement('div');
    loader.className = 'typing-indicator';
    loader.innerHTML = `
        <div class="typing-dot"></div>
        <div class="typing-dot"></div>
        <div class="typing-dot"></div>
    `;
    
    wrapper.appendChild(avatar);
    wrapper.appendChild(loader);
    
    chatHistory.appendChild(wrapper);
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
        alert("Please enter an API Key first!");
        return;
    }
    
    const bdo = bdoSelect.value;
    if (!bdo) {
        alert("Please select a BDO first!");
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
            bdo: bdo,
            model: modelSelect.value
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

userInput.addEventListener('keydown', function(e) {
    if (e.key === 'Enter' && !e.shiftKey) {
        e.preventDefault();
        chatForm.dispatchEvent(new Event('submit', { cancelable: true }));
    }
});

chatForm.addEventListener('submit', handleQuerySubmit);
refreshModelsBtn.addEventListener('click', fetchGeminiModels);
