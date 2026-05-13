class OrganizationsPage {
    constructor() {
        this.currentPage = 1;
        this.pageSize = 10;
        this.totalResults = 0;
        this.currentEditingId = null;
        this.currentDeleteId = null;
        this.init();
    }

    async init() {
        this.bindEvents();
        await this.loadOrganizations();
    }

    bindEvents() {
        const perPageSelect = document.querySelector('.per-page-select');
        if (perPageSelect) {
            perPageSelect.addEventListener('change', (e) => {
                this.pageSize = parseInt(e.target.value);
                this.currentPage = 1;
                this.loadOrganizations();
            });
        }

        const createBtn = document.getElementById('create-org-btn');
        if (createBtn) {
            createBtn.addEventListener('click', () => this.openCreateModal());
        }
    }

    async loadOrganizations() {
        try {
            this.showLoading();
            const result = await api.getOrganizations(this.currentPage, this.pageSize);
            this.totalResults = result.total || 0;
            this.updateTable(result.data || []);
            this.updatePagination();
            this.updateResultsCount();
        } catch (error) {
            console.error('Failed to load organizations:', error);
            Utils.showErrorMessage('Не удалось загрузить организации');
        } finally {
            this.hideLoading();
        }
    }

    updateTable(organizations) {
        const tbody = document.querySelector('.results-table tbody');
        if (!tbody) return;
        tbody.innerHTML = '';

        if (organizations.length === 0) {
            tbody.innerHTML = `<tr><td colspan="4" style="text-align:center;padding:40px;">Организации не найдены</td></tr>`;
            return;
        }

        organizations.forEach(org => {
            const tr = document.createElement('tr');
            const name = org.full_name || 'Без названия';
            const count = org.dissertations_count || 0;
            tr.innerHTML = `
                <td><a href="organization-detail.html?id=${org._key}" class="dissertation-title">${Utils.escapeHtml(name)}</a></td>
                <td>${count}</td>
                <td>
                    <div class="action-buttons-cell">
                        <button class="btn-edit" onclick="orgsPage.openEditModal('${org._key}')">✏️</button>
                        <button class="btn-delete" onclick="orgsPage.openDeleteModal('${org._key}', '${Utils.escapeHtml(name).replace(/'/g, "&#39;")}')">🗑️</button>
                    </div>
                </td>
            `;
            tbody.appendChild(tr);
        });
    }

    updatePagination() {
        const container = document.querySelector('.pagination');
        if (!container) return;
        const totalPages = Math.ceil(this.totalResults / this.pageSize);
        container.innerHTML = '';

        const prevBtn = document.createElement('button');
        prevBtn.className = `pagination-btn ${this.currentPage === 1 ? 'disabled' : ''}`;
        prevBtn.textContent = '←';
        prevBtn.addEventListener('click', () => {
            if (this.currentPage > 1) {
                this.currentPage--;
                this.loadOrganizations();
            }
        });
        container.appendChild(prevBtn);

        const maxVisible = 5;
        let start = Math.max(1, this.currentPage - Math.floor(maxVisible / 2));
        let end = Math.min(totalPages, start + maxVisible - 1);
        if (end - start + 1 < maxVisible) start = Math.max(1, end - maxVisible + 1);

        for (let i = start; i <= end; i++) {
            const btn = document.createElement('button');
            btn.className = `pagination-btn ${i === this.currentPage ? 'active' : ''}`;
            btn.textContent = i;
            btn.addEventListener('click', () => {
                this.currentPage = i;
                this.loadOrganizations();
            });
            container.appendChild(btn);
        }

        const nextBtn = document.createElement('button');
        nextBtn.className = `pagination-btn ${this.currentPage === totalPages ? 'disabled' : ''}`;
        nextBtn.textContent = '→';
        nextBtn.addEventListener('click', () => {
            if (this.currentPage < totalPages) {
                this.currentPage++;
                this.loadOrganizations();
            }
        });
        container.appendChild(nextBtn);
    }

    updateResultsCount() {
        const strong = document.querySelector('.results-count strong');
        if (strong) strong.textContent = this.totalResults.toLocaleString('ru-RU');
    }

    showLoading() {
        const tbody = document.querySelector('.results-table tbody');
        if (tbody) tbody.style.opacity = '0.5';
    }

    hideLoading() {
        const tbody = document.querySelector('.results-table tbody');
        if (tbody) tbody.style.opacity = '1';
    }

    openCreateModal() {
        this.currentEditingId = null;
        document.getElementById('org-modal-title').textContent = 'Создание организации';
        document.getElementById('org-form').reset();
        document.getElementById('org-modal').style.display = 'flex';
    }

    async openEditModal(orgId) {
        try {
            const org = await api.getOrganizationDetails(orgId);
            this.currentEditingId = orgId;
            document.getElementById('org-modal-title').textContent = 'Редактирование организации';
            const form = document.getElementById('org-form');
            form.querySelector('[name="full_name"]').value = org.full_name || '';
            document.getElementById('org-modal').style.display = 'flex';
        } catch (error) {
            console.error('Failed to load organization for editing:', error);
            Utils.showErrorMessage('Не удалось загрузить данные организации');
        }
    }

    async saveOrg() {
        const form = document.getElementById('org-form');
        const data = {
            full_name: form.querySelector('[name="full_name"]').value.trim()
        };
        if (!data.full_name) {
            Utils.showErrorMessage('Полное название обязательно');
            return;
        }
        try {
            if (this.currentEditingId) {
                await api.updateOrganization(this.currentEditingId, data);
                Utils.showMessage('Организация обновлена', 'success');
            } else {
                await api.createOrganization(data);
                Utils.showMessage('Организация создана', 'success');
            }
            this.closeOrgModal();
            await this.loadOrganizations();
        } catch (error) {
            console.error('Failed to save organization:', error);
            Utils.showErrorMessage('Не удалось сохранить организацию: ' + (error.message || ''));
        }
    }

    openDeleteModal(orgId, name) {
        this.currentDeleteId = orgId;
        document.getElementById('delete-org-name').textContent = name;
        document.getElementById('org-delete-modal').style.display = 'flex';
    }

    async confirmOrgDelete() {
        try {
            await api.deleteOrganization(this.currentDeleteId);
            Utils.showMessage('Организация удалена', 'success');
            this.closeOrgDeleteModal();
            await this.loadOrganizations();
        } catch (error) {
            console.error('Failed to delete organization:', error);
            Utils.showErrorMessage('Не удалось удалить организацию: ' + error.message);
        }
    }

    closeOrgModal() {
        document.getElementById('org-modal').style.display = 'none';
    }

    closeOrgDeleteModal() {
        document.getElementById('org-delete-modal').style.display = 'none';
        this.currentDeleteId = null;
    }
}

document.addEventListener('DOMContentLoaded', () => {
    window.orgsPage = new OrganizationsPage();
});

window.closeOrgModal = () => window.orgsPage.closeOrgModal();
window.closeOrgDeleteModal = () => window.orgsPage.closeOrgDeleteModal();
window.saveOrg = () => window.orgsPage.saveOrg();
window.confirmOrgDelete = () => window.orgsPage.confirmOrgDelete();
