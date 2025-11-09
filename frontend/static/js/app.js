// SMC Trading Bot Dashboard JavaScript

const API_BASE = 'http://localhost:5000/api';

// Initialize dashboard
document.addEventListener('DOMContentLoaded', function() {
    initializeDashboard();
    setupEventListeners();
    startDataUpdates();
});

// Initialize dashboard components
function initializeDashboard() {
    updateStatus();
    updateTrades();
    updateParameters();
}

// Setup event listeners
function setupEventListeners() {
    // Control buttons
    document.getElementById('start-bot-btn').addEventListener('click', startBot);
    document.getElementById('stop-bot-btn').addEventListener('click', stopBot);
    document.getElementById('switch-env-btn').addEventListener('click', switchEnvironment);
}

// Start periodic data updates
function startDataUpdates() {
    // Update status every 3 seconds
    setInterval(updateStatus, 3000);

    // Update trades every 10 seconds
    setInterval(updateTrades, 10000);

    // Update parameters every 30 seconds
    setInterval(updateParameters, 30000);
}

// API call wrapper
async function apiCall(endpoint, options = {}) {
    try {
        const response = await fetch(`${API_BASE}${endpoint}`, options);
        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }
        return await response.json();
    } catch (error) {
        console.error(`API call failed: ${endpoint}`, error);
        return null;
    }
}

// Update bot status
async function updateStatus() {
    const status = await apiCall('/status');
    if (!status) return;

    // Update status indicator
    const statusDot = document.getElementById('bot-status-dot');
    const statusText = document.getElementById('bot-status-text');

    if (status.running) {
        statusDot.className = 'status-dot running';
        statusText.textContent = 'Running';
    } else {
        statusDot.className = 'status-dot stopped';
        statusText.textContent = 'Stopped';
    }

    // Update environment badge
    const envBadge = document.getElementById('environment-badge');
    envBadge.textContent = status.environment.toUpperCase();
    envBadge.className = `badge ${status.environment}`;

    // Update metrics
    document.getElementById('total-pnl').textContent = `$${status.total_pnl.toFixed(2)}`;
    document.getElementById('win-rate').textContent = `${(status.win_rate * 100).toFixed(1)}%`;
    document.getElementById('open-trades').textContent = status.open_trades;
    document.getElementById('account-balance').textContent = `$${status.account_balance.toLocaleString()}`;
}

// Update trades display
async function updateTrades() {
    const trades = await apiCall('/trades');
    if (!trades) return;

    // Update open trades
    updateOpenTradesTable(trades.open_trades);

    // Update recent trades
    updateRecentTradesTable(trades.closed_trades);
}

// Update open trades table
function updateOpenTradesTable(openTrades) {
    const container = document.getElementById('open-trades-table');

    if (!openTrades || openTrades.length === 0) {
        container.innerHTML = '<p class="no-data">No open trades</p>';
        return;
    }

    let html = `
        <table class="trade-table">
            <thead>
                <tr>
                    <th>Symbol</th>
                    <th>Side</th>
                    <th>Entry Price</th>
                    <th>Size</th>
                    <th>P&L</th>
                    <th>Actions</th>
                </tr>
            </thead>
            <tbody>
    `;

    openTrades.forEach(trade => {
        const pnlClass = trade.pnl >= 0 ? 'pnl-positive' : 'pnl-negative';
        const pnlText = trade.pnl >= 0 ? `+$${trade.pnl.toFixed(2)}` : `$${trade.pnl.toFixed(2)}`;

        html += `
            <tr>
                <td>${trade.symbol}</td>
                <td>${trade.side}</td>
                <td>$${trade.entry_price.toFixed(2)}</td>
                <td>${trade.size}</td>
                <td class="${pnlClass}">${pnlText}</td>
                <td>
                    <button class="btn btn-danger btn-sm" onclick="closeTrade('${trade.id}')">
                        Close
                    </button>
                </td>
            </tr>
        `;
    });

    html += `
            </tbody>
        </table>
    `;

    container.innerHTML = html;
}

// Update recent trades table
function updateRecentTradesTable(closedTrades) {
    const container = document.getElementById('recent-trades-table');

    if (!closedTrades || closedTrades.length === 0) {
        container.innerHTML = '<p class="no-data">No recent trades</p>';
        return;
    }

    let html = `
        <table class="trade-table">
            <thead>
                <tr>
                    <th>Symbol</th>
                    <th>Side</th>
                    <th>Entry</th>
                    <th>Exit</th>
                    <th>P&L</th>
                    <th>Status</th>
                </tr>
            </thead>
            <tbody>
    `;

    closedTrades.slice(0, 10).forEach(trade => {  // Show last 10 trades
        const pnlClass = trade.pnl >= 0 ? 'pnl-positive' : 'pnl-negative';
        const pnlText = trade.pnl >= 0 ? `+$${trade.pnl.toFixed(2)}` : `$${trade.pnl.toFixed(2)}`;

        html += `
            <tr>
                <td>${trade.symbol}</td>
                <td>${trade.side}</td>
                <td>$${trade.entry_price.toFixed(2)}</td>
                <td>$${trade.exit_price ? trade.exit_price.toFixed(2) : 'N/A'}</td>
                <td class="${pnlClass}">${pnlText}</td>
                <td><span class="status-badge status-closed">CLOSED</span></td>
            </tr>
        `;
    });

    html += `
            </tbody>
        </table>
    `;

    container.innerHTML = html;
}

// Update parameters display
async function updateParameters() {
    const params = await apiCall('/parameters');
    if (!params) return;

    // Update risk parameters
    updateRiskParameters(params.risk);

    // Update trading parameters
    updateTradingParameters(params.trading);
}

// Update risk parameters display
function updateRiskParameters(risk) {
    const container = document.getElementById('risk-params');

    let html = '';
    for (const [key, value] of Object.entries(risk)) {
        const displayKey = key.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase());
        const displayValue = typeof value === 'number' && value < 1 ?
            `${(value * 100).toFixed(1)}%` : value;

        html += `
            <div class="parameter-item">
                <span class="parameter-label">${displayKey}</span>
                <span class="parameter-value">${displayValue}</span>
            </div>
        `;
    }

    container.innerHTML = html;
}

// Update trading parameters display
function updateTradingParameters(trading) {
    const container = document.getElementById('trading-params');

    let html = '';
    for (const [key, value] of Object.entries(trading)) {
        const displayKey = key.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase());
        const displayValue = Array.isArray(value) ? value.join(', ') : value;

        html += `
            <div class="parameter-item">
                <span class="parameter-label">${displayKey}</span>
                <span class="parameter-value">${displayValue}</span>
            </div>
        `;
    }

    container.innerHTML = html;
}

// Control functions
async function startBot() {
    const result = await apiCall('/control/start', { method: 'POST' });
    if (result) {
        alert('Bot started successfully!');
        updateStatus();
    } else {
        alert('Failed to start bot');
    }
}

async function stopBot() {
    const result = await apiCall('/control/stop', { method: 'POST' });
    if (result) {
        alert('Bot stopped successfully!');
        updateStatus();
    } else {
        alert('Failed to stop bot');
    }
}

async function switchEnvironment() {
    const currentEnv = document.getElementById('environment-badge').textContent.toLowerCase();
    const newEnv = currentEnv === 'testnet' ? 'live' : 'testnet';

    const confirmMsg = `Are you sure you want to switch to ${newEnv.toUpperCase()}? This will restart the bot.`;
    if (!confirm(confirmMsg)) return;

    const result = await apiCall('/control/environment', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ environment: newEnv })
    });

    if (result) {
        alert(`Switched to ${newEnv.toUpperCase()} successfully!`);
        updateStatus();
    } else {
        alert('Failed to switch environment');
    }
}

async function closeTrade(tradeId) {
    if (!confirm('Are you sure you want to close this trade?')) return;

    const result = await apiCall(`/trades/close/${tradeId}`, { method: 'POST' });
    if (result) {
        alert('Trade closed successfully!');
        updateTrades();
    } else {
        alert('Failed to close trade');
    }
}