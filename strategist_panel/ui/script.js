document.addEventListener('DOMContentLoaded', () => {
    // Configuration
    const CORE_WS_URL = "ws://localhost:8766"; // This must match the port in gem_bot_core/main.py for strategists
    const RECONNECT_INTERVAL_MS = 5000;

    // DOM Elements
    const statusEl = document.getElementById('connection-status');
    const lastSignalEl = document.getElementById('last-signal');
    const wapEl = document.getElementById('metric-wap');
    const spreadEl = document.getElementById('metric-spread');
    const imbalanceEl = document.getElementById('metric-imbalance');
    const logContainerEl = document.getElementById('log-container');

    function connect() {
        const ws = new WebSocket(CORE_WS_URL);

        ws.onopen = () => {
            updateConnectionStatus(true);
            addLogMessage('Connected to Gem.Bot Core.');
        };

        ws.onmessage = (event) => {
            try {
                const message = JSON.parse(event.data);
                updateUI(message);
                addLogMessage(`Received data: ${JSON.stringify(message)}`);
            } catch (error) {
                addLogMessage(`Error parsing message: ${error}`, 'error');
                console.error("Failed to parse incoming message:", event.data);
            }
        };

        ws.onclose = () => {
            updateConnectionStatus(false);
            addLogMessage(`Connection closed. Retrying in ${RECONNECT_INTERVAL_MS / 1000}s...`, 'error');
            setTimeout(connect, RECONNECT_INTERVAL_MS);
        };

        ws.onerror = (error) => {
            addLogMessage(`WebSocket error: ${error.message || 'Unknown error'}`, 'error');
            console.error("WebSocket Error:", error);
            ws.close(); // This will trigger the onclose event and reconnection logic
        };
    }

    function updateConnectionStatus(isConnected) {
        if (isConnected) {
            statusEl.textContent = 'CONNECTED';
            statusEl.className = 'status-connected';
        } else {
            statusEl.textContent = 'DISCONNECTED';
            statusEl.className = 'status-disconnected';
        }
    }

    function updateUI(data) {
        if (data.type !== 'core_update') return;

        const { features, prediction } = data;

        // Update main signal
        lastSignalEl.textContent = prediction;
        lastSignalEl.className = `signal-${prediction.toLowerCase()}`;

        // Update metrics
        wapEl.textContent = features.wap.toFixed(2);
        spreadEl.textContent = features.spread.toFixed(4);
        imbalanceEl.textContent = features.book_imbalance_5_levels.toFixed(4);
    }

    function addLogMessage(message, level = 'info') {
        const p = document.createElement('p');
        const timestamp = new Date().toLocaleTimeString();
        p.textContent = `[${timestamp}] ${message}`;

        if (level === 'error') {
            p.style.color = 'var(--status-disconnected-color)';
        }

        logContainerEl.appendChild(p);
        // Auto-scroll to the bottom
        logContainerEl.scrollTop = logContainerEl.scrollHeight;
    }

    // Initial connection attempt
    connect();
});