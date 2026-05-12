class AuthorDetailPage {
    constructor() {
        this.authorId = new URLSearchParams(window.location.search).get('id');
        if (!this.authorId) {
            Utils.showErrorMessage('ID автора не указан');
            return;
        }
        this.init();
    }

    async init() {
        await this.loadAuthorDetails();
    }

    async loadAuthorDetails() {
        try {
            const author = await api.getAuthorDetails(this.authorId);
            this.renderAuthor(author);
        } catch (e) {
            Utils.showErrorMessage('Ошибка загрузки данных автора');
        }
    }

    renderAuthor(author) {
        document.querySelector('.profile-name').textContent = author.full_name || 'Без имени';
        const dissertations = author.dissertations || [];
        document.querySelector('.stat-number').textContent = dissertations.length;

        const tbody = document.querySelector('.dissertations-table tbody');
        tbody.innerHTML = '';
        if (dissertations.length === 0) {
            tbody.innerHTML = '<tr><td colspan="3">Диссертации не найдены</td></tr>';
            return;
        }

        dissertations.forEach(diss => {
            const tr = document.createElement('tr');
            const title = diss.title || 'Без названия';
            const year = diss.defense_date ? new Date(diss.defense_date).getFullYear() : '—';
            const org = diss.organization_name || '—';
            tr.innerHTML = `
                <td><a href="dissertation-detail.html?id=${diss._key}" class="dissertation-link">${Utils.escapeHtml(title)}</a></td>
                <td>${year}</td>
                <td>${Utils.escapeHtml(org)}</td>
            `;
            tbody.appendChild(tr);
        });
    }
}

document.addEventListener('DOMContentLoaded', () => new AuthorDetailPage());
