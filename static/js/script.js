const canvas = document.getElementById('orbitCanvas');
const ctx = canvas.getContext('2d');

let width, height;
let logs = [];
let stats = {};

// Resize Canvas
function resize() {
    width = window.innerWidth;
    height = window.innerHeight;
    canvas.width = width;
    canvas.height = height;
}
window.addEventListener('resize', resize);
resize();

// Fetch Data
async function fetchData() {
    try {
        const [logsRes, statsRes] = await Promise.all([
            fetch('/logs'),
            fetch('/stats')
        ]);

        logs = await logsRes.json();
        stats = await statsRes.json();

        updateHUD();
    } catch (e) {
        console.error("Fetch failed", e);
    }
}

function updateHUD() {
    // Update Text Stats
    document.getElementById('total-logs').innerText = stats.total || 0;
    document.getElementById('last-sync').innerText = new Date().toLocaleTimeString();

    // Update Charts
    // Volume (Goal: 7/week?)
    const vol = stats.volume || 0;
    const volPct = Math.min((vol / 7) * 100, 100);
    updateChart('volume-chart', volPct, vol);

    // Streak (Goal: 4 weeks?)
    const streak = stats.streak || 0;
    const streakPct = Math.min((streak / 4) * 100, 100);
    updateChart('streak-chart', streakPct, streak);
}

function updateChart(id, percent, value) {
    const chart = document.getElementById(id);
    const circle = chart.querySelector('.circle');
    const text = chart.querySelector('.percentage');

    circle.setAttribute('stroke-dasharray', `${percent}, 100`);
    text.textContent = value;
}

// Animation Loop
let time = 0;

function draw() {
    ctx.fillStyle = '#05070a';
    ctx.fillRect(0, 0, width, height);

    const cx = width / 2;
    const cy = height / 2;

    // Draw Grid
    ctx.strokeStyle = 'rgba(255, 255, 255, 0.03)';
    ctx.lineWidth = 1;

    // Concentric Circles (Orbits)
    const rings = [100, 200, 300, 400];
    rings.forEach((r, i) => {
        ctx.beginPath();
        ctx.arc(cx, cy, r, 0, Math.PI * 2);
        ctx.stroke();

        // Rotating markers on rings
        const angle = time * (0.001 * (i % 2 ? 1 : -1)) + (i * 10);
        const mx = cx + Math.cos(angle) * r;
        const my = cy + Math.sin(angle) * r;

        ctx.fillStyle = 'rgba(255, 255, 255, 0.5)';
        ctx.beginPath();
        ctx.arc(mx, my, 2, 0, Math.PI * 2);
        ctx.fill();
    });

    // Draw Core
    ctx.shadowBlur = 20;
    ctx.shadowColor = '#ffffff';
    ctx.fillStyle = '#ffffff';
    ctx.beginPath();
    ctx.arc(cx, cy, 10, 0, Math.PI * 2);
    ctx.fill();
    ctx.shadowBlur = 0;

    // Draw Logs as Nodes
    // We map logs to positions based on time
    // Recent logs are closer to the center? Or further?
    // Let's make recent logs closer to center (Gravity)

    const now = new Date().getTime();
    const maxAge = 30 * 24 * 60 * 60 * 1000; // 30 days

    logs.forEach((ts, i) => {
        const date = new Date(ts).getTime();
        const age = now - date;

        if (age > maxAge) return; // Too old

        // Calculate radius based on age (Newer = Closer)
        // Min radius 50, Max radius 400
        const r = 50 + (age / maxAge) * 350;

        // Angle based on time of day? Or just spread out?
        // Let's use the timestamp to generate a deterministic angle
        const angle = (date % 86400000) / 86400000 * Math.PI * 2;

        // Add some slow rotation
        const rotation = time * 0.0005;
        const finalAngle = angle + rotation;

        const x = cx + Math.cos(finalAngle) * r;
        const y = cy + Math.sin(finalAngle) * r;

        // Draw Connection Line
        ctx.strokeStyle = 'rgba(255, 50, 50, 0.1)';
        ctx.beginPath();
        ctx.moveTo(cx, cy);
        ctx.lineTo(x, y);
        ctx.stroke();

        // Draw Node
        const isRecent = age < (24 * 60 * 60 * 1000); // Last 24h

        ctx.shadowBlur = isRecent ? 15 : 5;
        ctx.shadowColor = isRecent ? '#ff3333' : '#ffffff';
        ctx.fillStyle = isRecent ? '#ff3333' : '#ffffff';

        ctx.beginPath();
        ctx.arc(x, y, isRecent ? 4 : 2, 0, Math.PI * 2);
        ctx.fill();
        ctx.shadowBlur = 0;
    });

    time += 16;
    requestAnimationFrame(draw);
}

// Init
fetchData();
setInterval(fetchData, 30000); // Refresh every 30s
draw();
