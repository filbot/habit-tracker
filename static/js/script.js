// Fetch Data — single endpoint to avoid redundant DB reads
async function fetchData() {
    try {
        const res = await fetch('/dashboard');
        const data = await res.json();
        renderDashboard(data.logs, data.stats);
    } catch (e) {
        console.error("Fetch failed", e);
    }
}

function renderDashboard(logs, stats) {
    // 1. Update Header Date
    const options = { weekday: 'long', year: 'numeric', month: 'long', day: 'numeric' };
    document.getElementById('current-date').innerText = new Date().toLocaleDateString('en-US', options);

    // 2. Process Logs into Daily Counts
    const dailyCounts = {};
    logs.forEach(ts => {
        const date = ts.split('T')[0]; // YYYY-MM-DD
        dailyCounts[date] = (dailyCounts[date] || 0) + 1;
    });

    // 3. Update Cards
    document.getElementById('week-count').innerText = stats.volume || 0;
    document.getElementById('streak-count').innerText = stats.streak || 0;
    document.getElementById('total-count').innerText = stats.total || 0;

    // 4. Render Heatmap
    renderHeatmap(dailyCounts);
}

let _prevCounts = null;
let _heatmapBuilt = false;

function renderHeatmap(dailyCounts) {
    const container = document.getElementById('heatmap');
    const now = new Date();
    const currentYear = now.getFullYear();

    // Full rebuild only on first render
    if (!_heatmapBuilt) {
        container.innerHTML = '';
        container.className = 'heatmap-year';

        for (let month = 0; month < 12; month++) {
            const monthBlock = document.createElement('div');
            monthBlock.className = 'month-block';

            const monthLabel = document.createElement('div');
            monthLabel.className = 'month-label';
            const date = new Date(currentYear, month, 1);
            monthLabel.innerText = date.toLocaleString('default', { month: 'short' });
            monthBlock.appendChild(monthLabel);

            const monthGrid = document.createElement('div');
            monthGrid.className = 'month-grid';

            const daysInMonth = new Date(currentYear, month + 1, 0).getDate();
            const startDay = new Date(currentYear, month, 1).getDay();

            for (let i = 0; i < startDay; i++) {
                const empty = document.createElement('div');
                empty.className = 'day-cell empty';
                monthGrid.appendChild(empty);
            }

            for (let day = 1; day <= daysInMonth; day++) {
                const m = String(month + 1).padStart(2, '0');
                const d = String(day).padStart(2, '0');
                const dateStr = `${currentYear}-${m}-${d}`;

                const count = dailyCounts[dateStr] || 0;
                const cell = document.createElement('div');
                cell.className = 'day-cell';
                cell.setAttribute('data-date', dateStr);
                cell.setAttribute('data-level', count > 0 ? 1 : 0);
                cell.title = `${dateStr}: ${count} logs`;

                monthGrid.appendChild(cell);
            }

            monthBlock.appendChild(monthGrid);
            container.appendChild(monthBlock);
        }
        _heatmapBuilt = true;
        _prevCounts = dailyCounts;
        return;
    }

    // Differential update — only touch cells whose count changed
    for (let month = 0; month < 12; month++) {
        const daysInMonth = new Date(currentYear, month + 1, 0).getDate();
        for (let day = 1; day <= daysInMonth; day++) {
            const m = String(month + 1).padStart(2, '0');
            const d = String(day).padStart(2, '0');
            const dateStr = `${currentYear}-${m}-${d}`;

            const newCount = dailyCounts[dateStr] || 0;
            const oldCount = (_prevCounts && _prevCounts[dateStr]) || 0;

            if (newCount !== oldCount) {
                const cell = container.querySelector(`[data-date="${dateStr}"]`);
                if (cell) {
                    cell.setAttribute('data-level', newCount > 0 ? 1 : 0);
                    cell.title = `${dateStr}: ${newCount} logs`;
                }
            }
        }
    }
    _prevCounts = dailyCounts;
}

// Init
fetchData();
setInterval(fetchData, 60000); // Refresh every minute
