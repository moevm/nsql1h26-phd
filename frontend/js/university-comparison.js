class UniversityComparisonPage {
    constructor() {
        this.chart = null;
        this.currentData = [];
        this.init();
    }

    init() {
        this.bindEvents();
        this.loadData(null, null);
    }

    bindEvents() {
        document.getElementById('show-all-btn').addEventListener('click', () => {
            document.getElementById('year-from').value = '';
            document.getElementById('year-to').value = '';
            this.loadData(null, null);
        });

        document.getElementById('apply-period-btn').addEventListener('click', () => {
            const from = document.getElementById('year-from').value;
            const to = document.getElementById('year-to').value;
            this.loadData(from || null, to || null);
        });
    }

    async loadData(yearFrom, yearTo) {
        try {
            Utils.showInfoMessage('Загрузка данных...');
            const data = await api.getOrganizationsComparison(yearFrom, yearTo, 10);
            this.currentData = data || [];
            this.renderTable();
            this.renderChart();
        } catch (e) {
            console.error(e);
            Utils.showErrorMessage('Ошибка загрузки данных сравнения');
        }
    }

    renderChart() {
        const canvas = document.getElementById('org-pie-chart');
        if (!canvas) {
            console.warn('Canvas element not found');
            return;
        }
        if (typeof Chart === 'undefined') {
            console.warn('Chart.js not loaded');
            return;
        }
        if (this.chart) {
            this.chart.destroy();
        }
        if (!this.currentData.length) return;

        const labels = this.currentData.map(item => item.organization_name);
        const counts = this.currentData.map(item => item.count);

        try {
            this.chart = new Chart(canvas.getContext('2d'), {
                type: 'pie',
                data: {
                    labels: labels,
                    datasets: [{
                        data: counts,
                        backgroundColor: [
                            '#2563EB', '#10B981', '#F59E0B', '#EF4444', '#8B5CF6',
                            '#EC4899', '#06B6D4', '#F97316', '#84CC16', '#6366F1'
                        ],
                    }]
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    plugins: {
                        legend: {
                            position: 'bottom',
                            labels: {
                                font: { size: 12 }
                            }
                        }
                    }
                }
            });
        } catch (err) {
            console.error('Chart rendering error:', err);
            Utils.showErrorMessage('Ошибка отрисовки диаграммы');
        }
    }

    renderTable() {
        const tbody = document.getElementById('top10-table-body');
        if (!tbody) return;
        tbody.innerHTML = '';
        if (!this.currentData.length) {
            tbody.innerHTML = '<tr><td colspan="3">Нет данных</td></tr>';
            return;
        }
        this.currentData.forEach((item, index) => {
            const tr = document.createElement('tr');
            tr.innerHTML = `
                <td>${index + 1}</td>
                <td><a href="organization-detail.html?id=${item.organization_key}" class="dissertation-title">${Utils.escapeHtml(item.organization_name)}</a></td>
                <td>${item.count}</td>
            `;
            tbody.appendChild(tr);
        });
    }
}

document.addEventListener('DOMContentLoaded', () => new UniversityComparisonPage());
