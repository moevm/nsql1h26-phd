class MainPage {
    constructor() {
        this.init();
    }

    async init() {
        this.bindEvents();
        await this.loadStatistics();
        await this.loadRecentDissertations();
        await this.loadYearChart();
    }

    bindEvents() {
        const searchInput = document.querySelector('.search-bar input');
        if (searchInput) {
            searchInput.addEventListener('keypress', (e) => {
                if (e.key === 'Enter') {
                    this.handleSearch();
                }
            });
        }

        document.querySelectorAll('.quick-link').forEach(link => {
            link.addEventListener('click', (e) => {
                e.preventDefault();
                const linkText = link.querySelector('.quick-link-text')?.textContent.trim();

                switch (linkText) {
                    case 'Новый поиск':
                        window.location.href = 'dissertation.html';
                        break;
                }
            });
        });

        document.querySelectorAll('.dissertation-item').forEach(item => {
            item.addEventListener('click', () => {
                const title = item.querySelector('.dissertation-title');
                if (title) {
                    this.searchByTitle(title.textContent.trim());
                }
            });
        });
    }

    async loadStatistics() {
        try {
            const stats = await api.getStatistics();
            this.updateStatistics(stats);
        } catch (error) {
            console.error('Failed to load statistics:', error);
            this.showErrorMessage('Не удалось загрузить статистику');
        }
    }

    updateStatistics(stats) {
        const statCards = {
            'Всего диссертаций': stats.totalDissertations,
            'Авторов': stats.totalAuthors,
            'Организаций': stats.totalOrganizations,
            'Специальностей': stats.totalSpecialties
        };

        document.querySelectorAll('.stat-card').forEach(card => {
            const label = card.querySelector('.stat-label');
            const value = card.querySelector('.stat-value');

            if (label && value) {
                const labelText = label.textContent.trim();
                if (statCards[labelText] !== undefined) {
                    value.textContent = this.formatNumber(statCards[labelText]);
                }
            }
        });
    }

    async loadRecentDissertations() {
        try {
            const result = await api.getDissertations({}, 1, 5);
            this.updateRecentDissertations(result.data || []);
        } catch (error) {
            console.error('Failed to load recent dissertations:', error);
            this.showErrorMessage('Не удалось загрузить последние диссертации');
        }
    }

    updateRecentDissertations(dissertations) {
        const list = document.querySelector('.dissertation-list');
        if (!list) return;

        list.innerHTML = '';

        if (dissertations.length === 0) {
            list.innerHTML = '<li class="dissertation-item"><div>Диссертаций не найдено</div></li>';
            return;
        }

        dissertations.forEach(diss => {
            const item = this.createDissertationItem(diss);
            list.appendChild(item);
        });
    }

    createDissertationItem(dissertation) {
        const li = document.createElement('li');
        li.className = 'dissertation-item';

        const title = dissertation.title || 'Без названия';
        const author = dissertation.author_name || 'Неизвестный автор';
        const year = dissertation.defense_date ? new Date(dissertation.defense_date).getFullYear() : 'Неизвестный год';

        li.innerHTML = `
            <div>
                <div class="dissertation-title">${this.escapeHtml(title)}</div>
                <div class="dissertation-meta">${this.escapeHtml(author)} • ${year}</div>
            </div>
            <span>→</span>
        `;

        li.addEventListener('click', () => {
            this.openDissertationDetails(dissertation._key);
        });

        return li;
    }

    async handleSearch() {
        const searchInput = document.querySelector('.search-bar input');
        const query = searchInput.value.trim();

        if (!query) {
            return;
        }

        try {
            const result = await api.getDissertations({ keywords: query }, 1, 10);

            if (result.data && result.data.length > 0) {
                const params = new URLSearchParams({ keywords: query });
                window.location.href = `dissertation.html?${params.toString()}`;
            } else {
                this.showInfoMessage('По вашему запросу ничего не найдено');
            }
        } catch (error) {
            console.error('Search failed:', error);
            this.showErrorMessage('Ошибка выполнения поиска. Попробуйте позже.');
        }
    }

    searchByTitle(title) {
        const searchInput = document.querySelector('.search-bar input');
        if (searchInput) {
            searchInput.value = title;
            this.handleSearch();
        }
    }


    openDissertationDetails(dissId) {
        window.location.href = `dissertation-detail.html?id=${dissId}`;
    }

    async loadYearChart() {
        try {
            const { years, counts } = await api.getDissertationsByYears();
            this.updateYearChart(years, counts);
        } catch (error) {
            console.error('Failed to load year chart:', error);
        }
    }

    updateYearChart(years, counts) {
        const container = document.querySelector('.chart-container');
        if (!container) {
            console.error('Chart container not found');
            return;
        }

        const maxValue = Math.max(...counts, 1);
        const barContainer = container.querySelector('.chart-bars');
        const labelContainer = container.querySelector('.chart-labels');

        if (!barContainer || !labelContainer) {
            console.error('Chart containers not found');
            return;
        }

        barContainer.innerHTML = '';
        labelContainer.innerHTML = '';

        const filteredYears = years.filter((year, index) => counts[index] > 0);
        const filteredCounts = counts.filter(count => count > 0);

        filteredCounts.forEach((count, index) => {
            const bar = document.createElement('div');
            bar.className = 'chart-bar';
            const height = (count / maxValue) * 200;
            bar.style.height = `${height}px`;
            bar.title = `${count} диссертаций`;
            barContainer.appendChild(bar);
        });

        const step = Math.max(1, Math.floor(filteredYears.length / 5));
        filteredYears.forEach((year, index) => {
            if (index % step === 0 || index === filteredYears.length - 1) {
                const label = document.createElement('span');
                label.textContent = year;
                labelContainer.appendChild(label);
            }
        });
    }

    formatNumber(num) {
        if (num >= 1000000) {
            return (num / 1000000).toFixed(1) + 'M';
        } else if (num >= 1000) {
            return (num / 1000).toFixed(1) + 'K';
        }
        return num.toString();
    }

    escapeHtml(text) {
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    }

    showErrorMessage(message) {
        this.showMessage(message, 'error');
    }

    showInfoMessage(message) {
        this.showMessage(message, 'info');
    }

    showMessage(message, type = 'info') {
        const existingMessages = document.querySelectorAll('.message-toast');
        existingMessages.forEach(msg => msg.remove());

        const messageDiv = document.createElement('div');
        messageDiv.className = `message-toast message-${type}`;
        messageDiv.textContent = message;

        Object.assign(messageDiv.style, {
            position: 'fixed',
            top: '20px',
            right: '20px',
            padding: '12px 20px',
            borderRadius: '8px',
            color: 'white',
            fontWeight: '500',
            zIndex: '1000',
            maxWidth: '300px',
            wordWrap: 'break-word',
            backgroundColor: type === 'error' ? '#ef4444' : '#3b82f6',
            boxShadow: '0 4px 6px rgba(0, 0, 0, 0.1)',
            transform: 'translateX(0)',
            transition: 'transform 0.3s ease'
        });

        document.body.appendChild(messageDiv);

        setTimeout(() => {
            messageDiv.style.transform = 'translateX(0)';
        }, 10);

        setTimeout(() => {
            messageDiv.style.transform = 'translateX(400px)';
            setTimeout(() => {
                if (messageDiv.parentNode) {
                    messageDiv.parentNode.removeChild(messageDiv);
                }
            }, 300);
        }, 3000);
    }
}

document.addEventListener('DOMContentLoaded', () => {
    new MainPage();
});
