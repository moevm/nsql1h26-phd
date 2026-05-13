class AuthorsPage {
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
        await this.loadAuthors();
    }

    bindEvents() {
        const perPageSelect = document.querySelector('.per-page-select');
        if (perPageSelect) {
            perPageSelect.addEventListener('change', (e) => {
                this.pageSize = parseInt(e.target.value);
                this.currentPage = 1;
                this.loadAuthors();
            });
        }

        const createBtn = document.getElementById('create-author-btn');
        if (createBtn) {
            createBtn.addEventListener('click', () => this.openCreateModal());
        }
    }

    async loadAuthors() {
        try {
            this.showLoading();
            const result = await api.getAuthors(this.currentPage, this.pageSize);
            this.totalResults = result.total || 0;
            this.updateTable(result.data || []);
            this.updatePagination();
            this.updateResultsCount();
        } catch (error) {
            console.error('Failed to load authors:', error);
            Utils.showErrorMessage('Не удалось загрузить авторов');
        } finally {
            this.hideLoading();
        }
    }

    updateTable(authors) {
        const tbody = document.querySelector('.results-table tbody');
        if (!tbody) return;
        tbody.innerHTML = '';

        if (authors.length === 0) {
            tbody.innerHTML = `<tr><td colspan="3" style="text-align:center;padding:40px;">Авторы не найдены</td></tr>`;
            return;
        }

        authors.forEach(author => {
            const tr = document.createElement('tr');
            const name = author.full_name || 'Без имени';
            const count = author.dissertations_count || 0;
            tr.innerHTML = `
                <td><a href="author-detail.html?id=${author._key}" class="dissertation-title">${Utils.escapeHtml(name)}</a></td>
                <td>${count}</td>
                <td>
                    <div class="action-buttons-cell">
                        <button class="btn-edit" onclick="authorsPage.openEditModal('${author._key}')">✏️</button>
                        <button class="btn-delete" onclick="authorsPage.openDeleteModal('${author._key}', '${Utils.escapeHtml(name).replace(/'/g, "&#39;")}')">🗑️</button>
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
                this.loadAuthors();
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
                this.loadAuthors();
            });
            container.appendChild(btn);
        }

        const nextBtn = document.createElement('button');
        nextBtn.className = `pagination-btn ${this.currentPage === totalPages ? 'disabled' : ''}`;
        nextBtn.textContent = '→';
        nextBtn.addEventListener('click', () => {
            if (this.currentPage < totalPages) {
                this.currentPage++;
                this.loadAuthors();
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
        document.getElementById('author-modal-title').textContent = 'Создание автора';
        document.getElementById('author-form').reset();
        document.getElementById('author-modal').style.display = 'flex';
    }

    async openEditModal(authorId) {
        try {
            const author = await api.getAuthorDetails(authorId);
            this.currentEditingId = authorId;
            document.getElementById('author-modal-title').textContent = 'Редактирование автора';
            document.getElementById('author-form').querySelector('[name="full_name"]').value = author.full_name || '';
            document.getElementById('author-modal').style.display = 'flex';
        } catch (error) {
            console.error('Failed to load author for editing:', error);
            Utils.showErrorMessage('Не удалось загрузить данные автора');
        }
    }

    async saveAuthor() {
        const form = document.getElementById('author-form');
        const fullName = form.querySelector('[name="full_name"]').value.trim();
        if (!fullName) {
            Utils.showErrorMessage('ФИО автора обязательно');
            return;
        }
        try {
            if (this.currentEditingId) {
                await api.updateAuthor(this.currentEditingId, { full_name: fullName });
                Utils.showMessage('Автор обновлён', 'success');
            } else {
                await api.createAuthor({ full_name: fullName });
                Utils.showMessage('Автор создан', 'success');
            }
            this.closeAuthorModal();
            await this.loadAuthors();
        } catch (error) {
            console.error('Failed to save author:', error);
            Utils.showErrorMessage('Не удалось сохранить автора: ' + (error.message || ''));
        }
    }

    openDeleteModal(authorId, name) {
        this.currentDeleteId = authorId;
        document.getElementById('delete-author-name').textContent = name;
        document.getElementById('author-delete-modal').style.display = 'flex';
    }

    async confirmAuthorDelete() {
        try {
            await api.deleteAuthor(this.currentDeleteId);
            Utils.showMessage('Автор удалён', 'success');
            this.closeAuthorDeleteModal();
            await this.loadAuthors();
        } catch (error) {
            console.error('Failed to delete author:', error);
            Utils.showErrorMessage('Не удалось удалить автора: ' + error.message);
        }
    }

    closeAuthorModal() {
        document.getElementById('author-modal').style.display = 'none';
    }

    closeAuthorDeleteModal() {
        document.getElementById('author-delete-modal').style.display = 'none';
        this.currentDeleteId = null;
    }
}

document.addEventListener('DOMContentLoaded', () => {
    window.authorsPage = new AuthorsPage();
});

window.closeAuthorModal = () => window.authorsPage.closeAuthorModal();
window.closeAuthorDeleteModal = () => window.authorsPage.closeAuthorDeleteModal();
window.saveAuthor = () => window.authorsPage.saveAuthor();
window.confirmAuthorDelete = () => window.authorsPage.confirmAuthorDelete();
