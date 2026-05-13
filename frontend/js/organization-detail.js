class OrganizationDetailPage {
    constructor() {
        this.orgId = new URLSearchParams(window.location.search).get('id');
        if (!this.orgId) { Utils.showErrorMessage('ID организации не указан'); return; }
        this.currentPage = 1;
        this.pageSize = 10;
        this.filters = {};
        this.init();
    }

    async init() {
        await this.loadOrganizationDetails();
        await this.loadDissertations();
        this.bindEvents();
    }

    bindEvents() {
        document.querySelector('.org-pagination')?.addEventListener('click', e => {
            const btn = e.target.closest('button'); if (!btn) return;
            if (btn.classList.contains('pagination-arrow')) {
                btn.textContent.includes('←') ? this.prevPage() : this.nextPage();
            } else if (btn.classList.contains('pagination-page')) {
                this.goToPage(parseInt(btn.textContent));
            }
        });
        document.querySelector('.search-input')?.addEventListener('keypress', e => {
            if (e.key === 'Enter') {
                this.filters.search = e.target.value.trim();
                this.currentPage = 1;
                this.loadDissertations();
            }
        });
        document.querySelector('.search-select:first-of-type')?.addEventListener('change', e => {
            this.filters.year = e.target.value === 'Все годы' ? null : e.target.value;
            this.currentPage = 1; this.loadDissertations();
        });
        document.querySelector('.search-select:last-of-type')?.addEventListener('change', e => {
            this.filters.specialty = e.target.value === 'Все специальности' ? null : e.target.value;
            this.currentPage = 1; this.loadDissertations();
        });
    }

    async loadOrganizationDetails() {
        try {
            const org = await api.getOrganizationDetails(this.orgId);
            document.querySelector('.org-name').textContent = org.full_name || '—';
            document.querySelector('.stat-square-number').textContent = org.dissertations_count || 0;
        } catch (e) { Utils.showErrorMessage('Ошибка загрузки данных организации'); }
    }

    async loadDissertations() {
        try {
            const result = await api.getOrganizationDissertations(
                this.orgId, this.currentPage, this.pageSize, this.filters
            );
            this.total = result.total;
            this.renderTable(result.data);
            this.updatePagination();
            this.updateInfo();
        } catch (e) { 
            Utils.showErrorMessage('Ошибка загрузки диссертаций');
        }
    }

    renderTable(data) {
        const tbody = document.querySelector('.org-table tbody');
        tbody.innerHTML = '';
        if (!data?.length) { tbody.innerHTML = '<tr><td colspan="4">Нет диссертаций</td></tr>'; return; }
        data.forEach(diss => {
            const tr = document.createElement('tr');
            const defenseDate = diss.defense_date ? new Date(diss.defense_date).toLocaleDateString('ru-RU') : '—';
            tr.innerHTML = `
                <td><a href="dissertation-detail.html?id=${diss._key}" class="org-diss-link">${Utils.escapeHtml(diss.title||'—')}</a></td>
                <td>${Utils.escapeHtml(diss.author_name||'—')}</td>
                <td>${defenseDate}</td>
                <td><a href="dissertation.html?specialty_code=${encodeURIComponent(diss.specialty_code || '')}" class="org-diss-link">${Utils.escapeHtml(diss.specialty_code || '—')}</a></td>
            `;
            tbody.appendChild(tr);
        });
    }

    updatePagination() {
        const container = document.querySelector('.pagination-controls');
        if (!container) return;
        const totalPages = Math.ceil(this.total / this.pageSize) || 1;
        container.innerHTML = '';
        const add = (text, cls, disabled=false) => {
            const b = document.createElement('button');
            b.className = cls; b.textContent = text; b.disabled = disabled;
            container.appendChild(b);
        };
        add('←', 'pagination-arrow', this.currentPage === 1);
        for (let i = Math.max(1, this.currentPage-2); i <= Math.min(totalPages, this.currentPage+2); i++)
            add(i, `pagination-page${i===this.currentPage ? ' active' : ''}`);
        add('→', 'pagination-arrow', this.currentPage === totalPages);
    }

    updateInfo() {
        const info = document.querySelector('.pagination-info');
        if (info) info.textContent = `Показано ${(this.currentPage-1)*this.pageSize+1}-${Math.min(this.currentPage*this.pageSize, this.total)} из ${this.total}`;
    }

    prevPage() { if (this.currentPage > 1) { this.currentPage--; this.loadDissertations(); } }
    nextPage() { if (this.currentPage < Math.ceil(this.total/this.pageSize)) { this.currentPage++; this.loadDissertations(); } }
    goToPage(p) { if (p && p !== this.currentPage) { this.currentPage = p; this.loadDissertations(); } }
}

document.addEventListener('DOMContentLoaded', () => new OrganizationDetailPage());
