/* Dashboard polling and chart rendering */

const STRATEGY_PARAMS = {
    ema_sma_crossover: [
        { key: "ema_period", label: "EMA Period", default: 10 },
        { key: "sma_period", label: "SMA Period", default: 20 },
    ],
    rsi: [
        { key: "period", label: "RSI Period", default: 14 },
        { key: "overbought", label: "Overbought", default: 70 },
        { key: "oversold", label: "Oversold", default: 30 },
    ],
    combined: [
        { key: "ema_period", label: "EMA Period", default: 10 },
        { key: "sma_period", label: "SMA Period", default: 20 },
        { key: "rsi_period", label: "RSI Period", default: 14 },
        { key: "rsi_overbought", label: "Overbought", default: 70 },
        { key: "rsi_oversold", label: "Oversold", default: 30 },
    ],
};

const PLOTLY_LAYOUT = {
    paper_bgcolor: "#1a1a2e",
    plot_bgcolor: "#16213e",
    font: { color: "#e0e0e0", size: 11 },
    margin: { t: 20, b: 40, l: 60, r: 20 },
    xaxis: { gridcolor: "#2a2a4e", rangeslider: { visible: false } },
    yaxis: { gridcolor: "#2a2a4e" },
    legend: { bgcolor: "rgba(0,0,0,0)", font: { size: 10 } },
};

let currentChartPair = null;
let chartInitialized = false;
let equityInitialized = false;

// ==================== POLLING ====================

async function fetchJSON(url) {
    const resp = await fetch(url);
    return resp.json();
}

async function fetchPortfolio() {
    try {
        const data = await fetchJSON("/api/portfolio");
        document.getElementById("total-value").textContent = "$" + data.total_value.toFixed(2);
        document.getElementById("cash-balance").textContent = "$" + data.cash_balance.toFixed(2);

        const pnlEl = document.getElementById("total-pnl");
        pnlEl.textContent = "$" + data.total_pnl.toFixed(2);
        pnlEl.className = "card-value " + (data.total_pnl >= 0 ? "positive" : "negative");

        const pctEl = document.getElementById("total-pnl-pct");
        pctEl.textContent = data.total_pnl_pct.toFixed(2) + "%";
        pctEl.className = "card-value " + (data.total_pnl_pct >= 0 ? "positive" : "negative");
    } catch (e) {
        console.error("Portfolio fetch error:", e);
    }
}

async function fetchPrices() {
    try {
        const data = await fetchJSON("/api/prices");
        const ticker = document.getElementById("price-ticker");
        ticker.innerHTML = "";
        for (const [symbol, price] of Object.entries(data)) {
            ticker.innerHTML += `
                <div class="ticker-item">
                    <div class="ticker-symbol">${symbol}</div>
                    <div class="ticker-price">$${price.toFixed(2)}</div>
                </div>`;
        }

        // Populate chart pair selector if empty
        const select = document.getElementById("chart-pair-select");
        if (select.options.length === 0) {
            for (const symbol of Object.keys(data)) {
                const opt = document.createElement("option");
                opt.value = symbol;
                opt.textContent = symbol;
                select.appendChild(opt);
            }
            if (!currentChartPair && select.options.length > 0) {
                currentChartPair = select.options[0].value;
                updateChart();
            }
        }
    } catch (e) {
        console.error("Prices fetch error:", e);
    }
}

async function fetchPositions() {
    try {
        const data = await fetchJSON("/api/positions");
        const tbody = document.querySelector("#positions-table tbody");
        const empty = document.getElementById("no-positions");
        tbody.innerHTML = "";

        if (data.length === 0) {
            empty.style.display = "block";
            return;
        }
        empty.style.display = "none";

        for (const p of data) {
            const pnlClass = p.unrealized_pnl >= 0 ? "positive" : "negative";
            tbody.innerHTML += `<tr>
                <td>${p.symbol}</td>
                <td>${p.side}</td>
                <td>${p.quantity.toFixed(6)}</td>
                <td>$${p.entry_price.toFixed(4)}</td>
                <td>$${p.current_price.toFixed(4)}</td>
                <td class="${pnlClass}">$${p.unrealized_pnl.toFixed(2)}</td>
                <td>${p.stop_loss_price ? "$" + p.stop_loss_price.toFixed(4) : "-"}</td>
                <td>${p.take_profit_price ? "$" + p.take_profit_price.toFixed(4) : "-"}</td>
                <td>${formatTime(p.opened_at)}</td>
            </tr>`;
        }
    } catch (e) {
        console.error("Positions fetch error:", e);
    }
}

async function fetchTrades() {
    try {
        const data = await fetchJSON("/api/trades?limit=50");
        const tbody = document.querySelector("#trades-table tbody");
        const empty = document.getElementById("no-trades");
        tbody.innerHTML = "";

        if (data.length === 0) {
            empty.style.display = "block";
            return;
        }
        empty.style.display = "none";

        for (const t of data) {
            const pnlClass = t.pnl >= 0 ? "positive" : "negative";
            tbody.innerHTML += `<tr>
                <td>${t.symbol}</td>
                <td>${t.side}</td>
                <td>$${t.entry_price.toFixed(4)}</td>
                <td>$${t.exit_price.toFixed(4)}</td>
                <td>${t.quantity.toFixed(6)}</td>
                <td class="${pnlClass}">$${t.pnl.toFixed(2)}</td>
                <td class="${pnlClass}">${t.pnl_pct.toFixed(2)}%</td>
                <td>$${t.fees.toFixed(4)}</td>
                <td>${t.strategy_name}</td>
                <td>${formatDuration(t.duration_minutes)}</td>
            </tr>`;
        }
    } catch (e) {
        console.error("Trades fetch error:", e);
    }
}

async function fetchOrders() {
    try {
        const data = await fetchJSON("/api/orders?limit=30");
        const tbody = document.querySelector("#orders-table tbody");
        const empty = document.getElementById("no-orders");
        tbody.innerHTML = "";

        if (data.length === 0) {
            empty.style.display = "block";
            return;
        }
        empty.style.display = "none";

        for (const o of data) {
            const statusClass = o.status === "filled" ? "positive" : o.status === "cancelled" ? "negative" : "";
            tbody.innerHTML += `<tr>
                <td>#${o.id}</td>
                <td>${o.symbol}</td>
                <td>${o.side}</td>
                <td>${o.order_type}</td>
                <td>${o.quantity.toFixed(6)}</td>
                <td>${o.filled_price ? "$" + o.filled_price.toFixed(4) : (o.price ? "$" + o.price.toFixed(4) : "-")}</td>
                <td class="${statusClass}">${o.status}</td>
                <td>$${o.fee.toFixed(4)}</td>
                <td>${formatTime(o.created_at)}</td>
            </tr>`;
        }
    } catch (e) {
        console.error("Orders fetch error:", e);
    }
}

async function fetchPerformance() {
    try {
        const data = await fetchJSON("/api/performance");
        document.getElementById("metric-total-trades").textContent = data.total_trades;
        document.getElementById("metric-win-rate").textContent = data.win_rate.toFixed(1) + "%";
        document.getElementById("metric-avg-pnl").textContent = "$" + data.avg_pnl.toFixed(2);
        document.getElementById("metric-best-trade").textContent = "$" + data.best_trade.toFixed(2);
        document.getElementById("metric-worst-trade").textContent = "$" + data.worst_trade.toFixed(2);
        document.getElementById("metric-total-fees").textContent = "$" + data.total_fees.toFixed(2);

        // Equity curve
        if (data.equity_curve && data.equity_curve.length > 0) {
            const trace = {
                x: data.equity_curve.map(p => p.timestamp),
                y: data.equity_curve.map(p => p.value),
                type: "scatter",
                mode: "lines",
                line: { color: "#00d4aa", width: 2 },
                fill: "tozeroy",
                fillcolor: "rgba(0, 212, 170, 0.1)",
            };
            const layout = {
                ...PLOTLY_LAYOUT,
                yaxis: { ...PLOTLY_LAYOUT.yaxis, title: "Portfolio Value ($)" },
            };
            if (!equityInitialized) {
                Plotly.newPlot("equity-chart", [trace], layout, { responsive: true });
                equityInitialized = true;
            } else {
                Plotly.react("equity-chart", [trace], layout);
            }
        }
    } catch (e) {
        console.error("Performance fetch error:", e);
    }
}

async function fetchLogs() {
    try {
        const data = await fetchJSON("/api/logs?count=50");
        const viewer = document.getElementById("log-viewer");
        viewer.innerHTML = data.logs
            .map(log => `<div class="log-entry">${escapeHtml(log)}</div>`)
            .join("");
        viewer.scrollTop = viewer.scrollHeight;
    } catch (e) {
        console.error("Logs fetch error:", e);
    }
}

async function fetchEngineStatus() {
    try {
        const data = await fetchJSON("/api/engine/status");
        const badge = document.getElementById("engine-status");
        badge.textContent = data.running ? "Running" : "Stopped";
        badge.className = "status-badge " + (data.running ? "online" : "offline");

        document.getElementById("strategy-name").textContent = data.strategy;
        document.getElementById("timeframe-badge").textContent = data.timeframe;
    } catch (e) {
        console.error("Engine status fetch error:", e);
    }
}

// ==================== CHART ====================

async function updateChart() {
    const select = document.getElementById("chart-pair-select");
    currentChartPair = select.value;
    if (!currentChartPair) return;

    try {
        const data = await fetchJSON("/api/chart/" + encodeURIComponent(currentChartPair));
        if (data.error) return;

        const candlestick = {
            x: data.timestamps,
            open: data.open,
            high: data.high,
            low: data.low,
            close: data.close,
            type: "candlestick",
            name: currentChartPair,
            increasing: { line: { color: "#00d4aa" } },
            decreasing: { line: { color: "#ff4757" } },
        };

        const traces = [candlestick];

        // Add indicator overlays
        const indicators = data.indicators || {};
        const colors = ["#ffa502", "#3742fa", "#ff6b81", "#70a1ff"];
        let colorIdx = 0;
        for (const [name, values] of Object.entries(indicators)) {
            traces.push({
                x: data.timestamps,
                y: values,
                type: "scatter",
                mode: "lines",
                name: name.toUpperCase(),
                line: { color: colors[colorIdx % colors.length], width: 1.5 },
            });
            colorIdx++;
        }

        const layout = {
            ...PLOTLY_LAYOUT,
            yaxis: { ...PLOTLY_LAYOUT.yaxis, title: "Price ($)" },
        };

        if (!chartInitialized) {
            Plotly.newPlot("price-chart", traces, layout, { responsive: true });
            chartInitialized = true;
        } else {
            Plotly.react("price-chart", traces, layout);
        }
    } catch (e) {
        console.error("Chart fetch error:", e);
    }
}

// ==================== STRATEGY CONTROLS ====================

document.getElementById("strategy-select").addEventListener("change", function () {
    updateStrategyParams(this.value);
});

function updateStrategyParams(strategy) {
    const params = STRATEGY_PARAMS[strategy] || [];
    const container = document.getElementById("strategy-params");
    container.innerHTML = params
        .map(
            (p) => `<div class="param-row">
            <label>${p.label}</label>
            <input type="number" id="param-${p.key}" value="${p.default}">
        </div>`
        )
        .join("");
}

async function applyStrategy() {
    const strategy = document.getElementById("strategy-select").value;
    const params = {};
    (STRATEGY_PARAMS[strategy] || []).forEach((p) => {
        const el = document.getElementById("param-" + p.key);
        if (el) params[p.key] = parseFloat(el.value);
    });

    try {
        const resp = await fetch("/api/strategy", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ name: strategy, params: params }),
        });
        const data = await resp.json();
        if (data.status === "ok") {
            fetchEngineStatus();
        } else {
            alert("Error: " + (data.error || "Unknown"));
        }
    } catch (e) {
        alert("Error applying strategy: " + e.message);
    }
}

// Load current strategy params on startup
async function loadCurrentStrategy() {
    try {
        const data = await fetchJSON("/api/strategy");
        const select = document.getElementById("strategy-select");
        select.value = data.name;
        updateStrategyParams(data.name);

        // Fill in current param values
        const config = data.config || {};
        for (const [key, value] of Object.entries(config)) {
            const el = document.getElementById("param-" + key);
            if (el) el.value = value;
        }
    } catch (e) {
        console.error("Strategy fetch error:", e);
    }
}

// ==================== UTILITIES ====================

function formatTime(isoStr) {
    if (!isoStr) return "-";
    const d = new Date(isoStr);
    return d.toLocaleString();
}

function formatDuration(minutes) {
    if (minutes < 60) return minutes + "m";
    const h = Math.floor(minutes / 60);
    const m = minutes % 60;
    if (h < 24) return h + "h " + m + "m";
    const d = Math.floor(h / 24);
    return d + "d " + (h % 24) + "h";
}

function escapeHtml(str) {
    const div = document.createElement("div");
    div.textContent = str;
    return div.innerHTML;
}

// ==================== INIT ====================

async function pollAll() {
    await Promise.all([
        fetchPortfolio(),
        fetchPrices(),
        fetchPositions(),
        fetchTrades(),
        fetchOrders(),
        fetchPerformance(),
        fetchLogs(),
        fetchEngineStatus(),
    ]);

    if (currentChartPair) {
        updateChart();
    }
}

// Initial load
loadCurrentStrategy();
updateStrategyParams("ema_sma_crossover");
pollAll();

// Start polling
setInterval(pollAll, POLLING_INTERVAL);
