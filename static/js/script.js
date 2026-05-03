const REFRESH_INTERVAL_MS = 60000;
const ANIMATION_DURATION_MS = 400;
const TOAST_DURATION_MS = 2000;
const DELETE_CONFIRM_TIMEOUT_MS = 3000;
const DAYS_PER_WEEK = 7;
const MS_PER_DAY = 24 * 60 * 60 * 1000;
const MS_PER_WEEK = DAYS_PER_WEEK * MS_PER_DAY;
const DECIMAL_RADIX = 10;
const MONTHS_IN_YEAR = 12;

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

// Binary heatmap: done (1) or not done (0)
function countToLevel(count) {
    return count > 0 ? 1 : 0;
}

// Animate a stat number counting up/down
function animateValue(el, newVal) {
    const startVal = parseInt(el.innerText, DECIMAL_RADIX) || 0;
    if (startVal === newVal) return;
    const startTime = performance.now();
    function step(now) {
        const progress = Math.min((now - startTime) / ANIMATION_DURATION_MS, 1);
        const eased = 1 - Math.pow(1 - progress, 3); // ease-out cubic
        el.innerText = Math.round(startVal + (newVal - startVal) * eased);
        if (progress < 1) requestAnimationFrame(step);
    }
    requestAnimationFrame(step);
}

// Toast notification
let _toastTimeout = null;
function showToast(message) {
    const toast = document.getElementById('toast');
    toast.textContent = message;
    toast.classList.add('visible');
    clearTimeout(_toastTimeout);
    _toastTimeout = setTimeout(() => toast.classList.remove('visible'), TOAST_DURATION_MS);
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

    // 3. Update Cards with animation
    animateValue(document.getElementById('week-count'), stats.volume ?? 0);
    animateValue(document.getElementById('streak-count'), stats.streak ?? 0);
    animateValue(document.getElementById('total-count'), stats.total ?? 0);

    // 4. Week-over-week trend
    updateWeekTrend(dailyCounts);

    // 5. Best streak
    updateBestStreak(dailyCounts);

    // 6. Render Heatmap
    renderHeatmap(dailyCounts);
}

// Show whether the habit has been done this week
function updateWeekTrend(dailyCounts) {
    const trendEl = document.getElementById('week-trend');
    if (!trendEl) return;
    const today = new Date();
    let doneThisWeek = false;
    for (let dayOffset = 0; dayOffset < DAYS_PER_WEEK; dayOffset++) {
        const date = new Date(today);
        date.setDate(date.getDate() - dayOffset);
        const key = date.toISOString().split('T')[0];
        if ((dailyCounts[key] ?? 0) > 0) { doneThisWeek = true; break; }
    }
    if (doneThisWeek) {
        trendEl.textContent = '\u2713';
        trendEl.className = 'trend-up';
    } else {
        trendEl.textContent = '';
        trendEl.className = 'trend-neutral';
    }
}

// Compute best weekly streak from daily counts
function updateBestStreak(dailyCounts) {
    const subtextEl = document.getElementById('streak-subtext');
    if (!subtextEl) return;
    const dates = Object.keys(dailyCounts);
    if (dates.length === 0) {
        subtextEl.textContent = 'Current Streak';
        return;
    }
    // Get unique ISO weeks that had activity, keyed by Monday's date
    const activeWeeks = new Set();
    for (const dateStr of dates) {
        const date = new Date(dateStr + 'T00:00:00');
        const dayIndex = date.getDay();
        const monday = new Date(date);
        monday.setDate(date.getDate() - ((dayIndex + 6) % DAYS_PER_WEEK));
        activeWeeks.add(monday.toISOString().split('T')[0]);
    }
    // Sort week start dates and find longest consecutive run (7-day gaps)
    const sorted = Array.from(activeWeeks).sort();
    let best = 1;
    let current = 1;
    for (let i = 1; i < sorted.length; i++) {
        const prev = new Date(sorted[i - 1] + 'T00:00:00');
        const curr = new Date(sorted[i] + 'T00:00:00');
        const diffDays = (curr - prev) / MS_PER_DAY;
        if (diffDays === DAYS_PER_WEEK) {
            current++;
            if (current > best) best = current;
        } else {
            current = 1;
        }
    }
    subtextEl.textContent = 'Current Streak \u00B7 Best: ' + best + 'w';
}

let _prevCounts = null;
let _heatmapBuilt = false;

function formatDateKey(year, monthIndex, day) {
    const m = String(monthIndex + 1).padStart(2, '0');
    const d = String(day).padStart(2, '0');
    return `${year}-${m}-${d}`;
}

function buildAriaLabel(dateStr, count) {
    const dateObj = new Date(dateStr + 'T00:00:00');
    const formatted = dateObj.toLocaleDateString('en-US', { month: 'long', day: 'numeric' });
    return `${formatted}: ${count} log${count !== 1 ? 's' : ''}`;
}

function createDayCell(dateStr, count) {
    const cell = document.createElement('div');
    cell.className = 'day-cell';
    cell.setAttribute('data-date', dateStr);
    cell.setAttribute('data-level', countToLevel(count));
    cell.title = `${dateStr}: ${count} logs`;
    cell.setAttribute('role', 'gridcell');
    cell.setAttribute('tabindex', '0');
    cell.setAttribute('aria-label', buildAriaLabel(dateStr, count));

    cell.addEventListener('click', () => openDayDialog(dateStr));
    cell.addEventListener('keydown', (e) => {
        if (e.key === 'Enter' || e.key === ' ') {
            e.preventDefault();
            openDayDialog(dateStr);
        }
    });
    return cell;
}

function buildMonthBlock(year, monthIndex, dailyCounts) {
    const monthBlock = document.createElement('div');
    monthBlock.className = 'month-block';

    const monthLabel = document.createElement('div');
    monthLabel.className = 'month-label';
    monthLabel.innerText = new Date(year, monthIndex, 1).toLocaleString('default', { month: 'short' });
    monthBlock.appendChild(monthLabel);

    const monthGrid = document.createElement('div');
    monthGrid.className = 'month-grid';

    const daysInMonth = new Date(year, monthIndex + 1, 0).getDate();
    const startDay = new Date(year, monthIndex, 1).getDay();

    for (let i = 0; i < startDay; i++) {
        const empty = document.createElement('div');
        empty.className = 'day-cell empty';
        monthGrid.appendChild(empty);
    }
    for (let day = 1; day <= daysInMonth; day++) {
        const dateStr = formatDateKey(year, monthIndex, day);
        const count = dailyCounts[dateStr] ?? 0;
        monthGrid.appendChild(createDayCell(dateStr, count));
    }

    monthBlock.appendChild(monthGrid);
    return monthBlock;
}

function buildHeatmap(container, year, dailyCounts) {
    container.innerHTML = '';
    container.className = 'heatmap-year';
    for (let month = 0; month < MONTHS_IN_YEAR; month++) {
        container.appendChild(buildMonthBlock(year, month, dailyCounts));
    }
}

function updateChangedCells(container, year, dailyCounts, prevCounts) {
    for (let month = 0; month < MONTHS_IN_YEAR; month++) {
        const daysInMonth = new Date(year, month + 1, 0).getDate();
        for (let day = 1; day <= daysInMonth; day++) {
            const dateStr = formatDateKey(year, month, day);
            const newCount = dailyCounts[dateStr] ?? 0;
            const oldCount = (prevCounts && prevCounts[dateStr]) ?? 0;
            if (newCount === oldCount) continue;

            const cell = container.querySelector(`[data-date="${dateStr}"]`);
            if (!cell) continue;

            cell.setAttribute('data-level', countToLevel(newCount));
            cell.title = `${dateStr}: ${newCount} logs`;
            cell.setAttribute('aria-label', buildAriaLabel(dateStr, newCount));
            cell.classList.add('updated');
            setTimeout(() => cell.classList.remove('updated'), ANIMATION_DURATION_MS);
        }
    }
}

function renderHeatmap(dailyCounts) {
    const container = document.getElementById('heatmap');
    const currentYear = new Date().getFullYear();

    if (!_heatmapBuilt) {
        buildHeatmap(container, currentYear, dailyCounts);
        _heatmapBuilt = true;
    } else {
        updateChangedCells(container, currentYear, dailyCounts, _prevCounts);
    }
    _prevCounts = dailyCounts;
}

// Day Dialog
let _dialogCurrentDate = null;
let _dialogTriggerCell = null;

async function openDayDialog(dateStr) {
    const dayDialog = document.getElementById('day-dialog');
    const dialogDate = document.getElementById('dialog-date');
    const dialogLogList = document.getElementById('dialog-log-list');
    _dialogCurrentDate = dateStr;
    _dialogTriggerCell = document.querySelector(`[data-date="${dateStr}"]`);
    const display = new Date(dateStr + 'T00:00:00').toLocaleDateString('en-US', {
        weekday: 'long', year: 'numeric', month: 'long', day: 'numeric'
    });
    dialogDate.textContent = display;
    dialogLogList.innerHTML = '';
    if (typeof dayDialog.showModal === 'function') {
        dayDialog.showModal();
    } else {
        dayDialog.setAttribute('open', '');
    }
    await refreshLogList(dateStr);
    // Focus the add-log button for accessibility
    document.getElementById('dialog-add-log').focus();
}

async function refreshLogList(dateStr) {
    try {
        const res = await fetch(`/logs/${dateStr}`);
        const logs = await res.json();
        renderLogList(logs);
    } catch (e) {
        console.error("Failed to fetch logs for date", e);
    }
}

function renderLogList(logs) {
    const dialogLogList = document.getElementById('dialog-log-list');
    dialogLogList.innerHTML = '';
    if (logs.length === 0) {
        const empty = document.createElement('div');
        empty.className = 'dialog-empty';
        empty.textContent = 'No logs for this day';
        dialogLogList.appendChild(empty);
        return;
    }
    logs.forEach(log => {
        const entry = document.createElement('div');
        entry.className = 'log-entry';

        const time = document.createElement('span');
        time.className = 'log-entry-time';
        const ts = new Date(log.timestamp);
        time.textContent = ts.toLocaleTimeString('en-US', { hour: '2-digit', minute: '2-digit', second: '2-digit' });

        const delBtn = document.createElement('button');
        delBtn.className = 'log-delete-btn';
        delBtn.textContent = 'Delete';

        let confirmTimer = null;
        delBtn.addEventListener('click', () => {
            if (delBtn.classList.contains('confirming')) {
                clearTimeout(confirmTimer);
                deleteLog(log.id);
            } else {
                delBtn.classList.add('confirming');
                delBtn.textContent = 'Sure?';
                confirmTimer = setTimeout(() => {
                    delBtn.classList.remove('confirming');
                    delBtn.textContent = 'Delete';
                }, DELETE_CONFIRM_TIMEOUT_MS);
            }
        });

        entry.appendChild(time);
        entry.appendChild(delBtn);
        dialogLogList.appendChild(entry);
    });
}

async function deleteLog(logId) {
    try {
        await fetch(`/log/${logId}`, { method: 'DELETE' });
        showToast('Log deleted');
        await refreshLogList(_dialogCurrentDate);
        fetchData();
    } catch (e) {
        console.error("Failed to delete log", e);
        showToast('Something went wrong');
    }
}

document.getElementById('dialog-add-log').addEventListener('click', async () => {
    if (!_dialogCurrentDate) return;
    try {
        await fetch('/log', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ timestamp: _dialogCurrentDate + 'T12:00:00' })
        });
        showToast('Log added');
        await refreshLogList(_dialogCurrentDate);
        fetchData();
    } catch (e) {
        console.error("Failed to add log", e);
        showToast('Something went wrong');
    }
});

// Close on backdrop click + return focus
const dayDialog = document.getElementById('day-dialog');
dayDialog.addEventListener('click', (e) => {
    if (e.target === e.currentTarget) {
        e.currentTarget.close();
    }
});

dayDialog.addEventListener('close', () => {
    if (_dialogTriggerCell) {
        _dialogTriggerCell.focus();
        _dialogTriggerCell = null;
    }
});

// Init
fetchData();
setInterval(fetchData, REFRESH_INTERVAL_MS);
