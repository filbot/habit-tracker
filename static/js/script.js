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
    const grid = document.getElementById('heatmap');
    grid.innerHTML = '';

    // Generate last 365 days
    const today = new Date();
    const oneYearAgo = new Date();
    oneYearAgo.setDate(today.getDate() - 365);

    // Adjust start date to align with Sunday?
    // For simplicity, let's just show last 52 weeks (364 days)
    // Find the Sunday 52 weeks ago
    const startDate = new Date(today);
    startDate.setDate(today.getDate() - 364);
    while (startDate.getDay() !== 0) {
        startDate.setDate(startDate.getDate() - 1);
    }

    const endDate = new Date();

    let currentDate = new Date(startDate);

    while (currentDate <= endDate) {
        const dateStr = currentDate.toISOString().split('T')[0];
        const count = dailyCounts[dateStr] || 0;

        const cell = document.createElement('div');
        cell.className = 'day-cell';

        // Determine Level (Binary)
        let level = 0;
        if (count > 0) level = 1;

        cell.setAttribute('data-level', level);
        cell.title = `${dateStr}: ${count} logs`;

        grid.appendChild(cell);

        // Next Day
        currentDate.setDate(currentDate.getDate() + 1);
    }
}

// Init
fetchData();
setInterval(fetchData, 60000); // Refresh every minute
