// Fetch Data
async function fetchData() {
    try {
        const [logsRes, statsRes] = await Promise.all([
            fetch('/logs'),
            fetch('/stats')
        ]);

        const logs = await logsRes.json();
        const stats = await statsRes.json();

        renderDashboard(logs, stats);
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
    const today = new Date().toISOString().split('T')[0];
    const todayCount = dailyCounts[today] || 0;

    document.getElementById('today-count').innerText = todayCount;
    document.getElementById('streak-count').innerText = stats.streak || 0;
    document.getElementById('total-count').innerText = stats.total || 0;

    // 4. Render Heatmap
    renderHeatmap(dailyCounts);
}

function renderHeatmap(dailyCounts) {
    const container = document.getElementById('heatmap');
    container.innerHTML = '';
    container.className = 'heatmap-year'; // Switch to flex container

    const now = new Date();
    const currentYear = now.getFullYear();

    // Iterate through months 0-11
    for (let month = 0; month < 12; month++) {
        // Create Month Block
        const monthBlock = document.createElement('div');
        monthBlock.className = 'month-block';

        // Label
        const monthLabel = document.createElement('div');
        monthLabel.className = 'month-label';
        const date = new Date(currentYear, month, 1);
        monthLabel.innerText = date.toLocaleString('default', { month: 'short' });
        monthBlock.appendChild(monthLabel);

        // Grid
        const monthGrid = document.createElement('div');
        monthGrid.className = 'month-grid';

        // Calculate days in month and start day
        const daysInMonth = new Date(currentYear, month + 1, 0).getDate();
        const startDay = new Date(currentYear, month, 1).getDay(); // 0=Sun

        // Add empty cells for padding
        for (let i = 0; i < startDay; i++) {
            const empty = document.createElement('div');
            empty.className = 'day-cell empty';
            monthGrid.appendChild(empty);
        }

        // Add days
        for (let day = 1; day <= daysInMonth; day++) {
            // Format YYYY-MM-DD
            // Note: Month is 0-indexed, so +1. Pad with 0.
            const m = String(month + 1).padStart(2, '0');
            const d = String(day).padStart(2, '0');
            const dateStr = `${currentYear}-${m}-${d}`;

            const count = dailyCounts[dateStr] || 0;

            const cell = document.createElement('div');
            cell.className = 'day-cell';

            // Determine Level (Binary)
            let level = 0;
            if (count > 0) level = 1;

            cell.setAttribute('data-level', level);
            cell.title = `${dateStr}: ${count} logs`;

            monthGrid.appendChild(cell);
        }

        monthBlock.appendChild(monthGrid);
        container.appendChild(monthBlock);
    }
}

// Init
fetchData();
setInterval(fetchData, 60000); // Refresh every minute

