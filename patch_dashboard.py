import re

with open("/home/syhnes/TradeBot/templates/dashboard.html", "r") as f:
    html = f.read()

if "Chart.js" not in html:
    html = html.replace("</title>", "</title>\n    <script src=\"https://cdn.jsdelivr.net/npm/chart.js\"></script>")

chart_html = """        <section class="positions-grid">
            <header>
                <h2>Performance du Bot (Trade PNL)</h2>
            </header>
            <div class="card" style="grid-column: 1 / -1; min-height: 300px; display: flex; align-items: center; justify-content: center;">
                <canvas id="pnlChart" style="width: 100%; height: 100%;"></canvas>
            </div>
            
            <div class="card" style="grid-column: 1 / -1; overflow-x: auto;">
                <table id="trades-table" width="100%" style="text-align: left; border-collapse: collapse;">
                    <thead>
                        <tr>
                            <th>Date</th>
                            <th>O/C</th>
                            <th>Coin</th>
                            <th>Side</th>
                            <th>Prix</th>
                            <th>PnL</th>
                            <th>Raison</th>
                        </tr>
                    </thead>
                    <tbody id="trades-body"></tbody>
                </table>
            </div>
        </section>
        
        <section class="positions-grid">"""

if "pnlChart" not in html:
    html = html.replace('        <section class="positions-grid">', chart_html, 1)

js_logic = """
        let pnlChart = null;

        async function updateChart() {
            try {
                const response = await fetch('/api/db_trades');
                if(!response.ok) return;
                const trades = await response.json();
                
                const tableBody = document.getElementById('trades-body');
                tableBody.innerHTML = '';
                
                let cumulativePnl = 0;
                const labels = [];
                const dataPoints = [];

                trades.forEach(t => {
                    if(t.action === 'CLOSE') {
                        cumulativePnl += t.pnl;
                    }
                    labels.push(t.timestamp.replace('Z','').split('.')[0]);
                    dataPoints.push(cumulativePnl);
                    
                    const tr = document.createElement('tr');
                    tr.style.borderBottom = "1px solid #333";
                    tr.innerHTML = `
                        <td style="padding: 5px;">${new Date(t.timestamp + 'Z').toLocaleString()}</td>
                        <td style="padding: 5px;"><span style="color: ${t.action === 'OPEN' ? 'orange' : 'cyan'};">${t.action}</span></td>
                        <td style="padding: 5px;">${t.coin}</td>
                        <td style="padding: 5px;">${t.side}</td>
                        <td style="padding: 5px;">${t.price}$</td>
                        <td style="padding: 5px; color: ${t.pnl < 0 ? 'var(--color-danger)' : (t.pnl > 0 ? 'var(--color-success)' : '#fff')};">${t.action === 'CLOSE' ? (t.pnl ? t.pnl.toFixed(2)+'$' : '0$') : '-'}</td>
                        <td style="padding: 5px;">${t.reason}</td>
                    `;
                    tableBody.appendChild(tr);
                });

                if(pnlChart) {
                    pnlChart.data.labels = labels;
                    pnlChart.data.datasets[0].data = dataPoints;
                    pnlChart.update();
                } else {
                    const ctx = document.getElementById('pnlChart').getContext('2d');
                    pnlChart = new Chart(ctx, {
                        type: 'line',
                        data: {
                            labels: labels,
                            datasets: [{
                                label: 'PnL Cumulé Bot ($)',
                                data: dataPoints,
                                borderColor: 'cyan',
                                backgroundColor: 'rgba(0, 255, 255, 0.1)',
                                fill: true,
                                tension: 0.1,
                                pointRadius: 2,
                            }]
                        },
                        options: {
                            responsive: true,
                            maintainAspectRatio: false,
                            scales: {
                                x: { grid: { color: '#333' }, ticks: { color: '#888' } },
                                y: { grid: { color: '#333' }, ticks: { color: '#888' } },
                            },
                            plugins: {
                                legend: { labels: { color: '#ccc' } }
                            }
                        }
                    });
                }
            } catch(e) {
                console.error("Erreur graphe:", e);
            }
        }
        
        setInterval(updateChart, 10000);
        updateChart();
"""

if "updateChart" not in html:
    html = html.replace('        setInterval(updateDashboard, 10000);', '        setInterval(updateDashboard, 10000);\n' + js_logic)

with open("/home/syhnes/TradeBot/templates/dashboard.html", "w") as f:
    f.write(html)
