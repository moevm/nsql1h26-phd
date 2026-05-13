class DissertationPage {
    constructor() {
        this.currentPage = 1;
        this.pageSize = 10;
        this.totalResults = 0;
        this.currentFilters = {};
        this.init();
    }

    async init() {
        this.bindEvents();
        await this.loadInitialData();
    }

    bindEvents() {
        const applyFiltersBtn = document.querySelector('.btn-primary');
        if (applyFiltersBtn) {
            applyFiltersBtn.addEventListener('click', () => this.applyFilters());
        }

        const createBtn = document.getElementById('create-dissertation-btn');
        if (createBtn) {
            createBtn.addEventListener('click', () => this.openCreateModal());
        }

        const resetFiltersBtn = document.querySelector('.btn-secondary');
        if (resetFiltersBtn) {
            resetFiltersBtn.addEventListener('click', () => this.resetFilters());
        }

        const exportBtn = document.querySelector('.btn-export');
        if (exportBtn) {
            exportBtn.addEventListener('click', () => this.exportResults());
        }

        const perPageSelect = document.querySelector('.per-page-select');
        if (perPageSelect) {
            perPageSelect.addEventListener('change', (e) => {
                this.pageSize = parseInt(e.target.value);
                this.currentPage = 1;
                this.loadDissertations();
            });
        }

        this.bindPaginationEvents();

        const filterInputs = document.querySelectorAll('.filter-input');
        filterInputs.forEach(input => {
            input.addEventListener('keypress', (e) => {
                if (e.key === 'Enter') {
                    this.applyFilters();
                }
            });
        });

        const statusSelect = document.querySelector('.filter-select');
        const statusDisplay = document.getElementById('status-display');
        const statusDropdown = document.querySelector('.status-dropdown');

        if (statusSelect && statusDisplay && statusDropdown) {
            statusSelect.addEventListener('click', (e) => {
                e.stopPropagation();
                statusDropdown.style.display = statusDropdown.style.display === 'none' ? 'block' : 'none';
            });

            document.addEventListener('click', () => {
                statusDropdown.style.display = 'none';
            });

            statusDropdown.addEventListener('click', (e) => {
                e.stopPropagation();
            });

            document.querySelectorAll('.status-option').forEach(option => {
                option.addEventListener('click', () => {
                    const value = option.dataset.value;
                    const text = option.textContent;
                    statusDisplay.textContent = text;
                    statusDisplay.dataset.value = value;
                    statusDropdown.style.display = 'none';
                });
            });

            statusDropdown.addEventListener('mouseenter', (e) => {
                e.target.style.backgroundColor = '#f3f4f6';
            });

            statusDropdown.addEventListener('mouseleave', (e) => {
                e.target.style.backgroundColor = '';
            });
        }
    }

    bindPaginationEvents() {
        const paginationButtons = document.querySelectorAll('.pagination-btn');
        paginationButtons.forEach(btn => {
            btn.addEventListener('click', () => {
                const text = btn.textContent.trim();
                if (text === '←') {
                    if (this.currentPage > 1) {
                        this.currentPage--;
                        this.loadDissertations();
                    }
                } else if (text === '→') {
                    const totalPages = Math.ceil(this.totalResults / this.pageSize);
                    if (this.currentPage < totalPages) {
                        this.currentPage++;
                        this.loadDissertations();
                    }
                } else {
                    const page = parseInt(text);
                    if (page && page !== this.currentPage) {
                        this.currentPage = page;
                        this.loadDissertations();
                    }
                }
            });
        });
    }

    async loadInitialData() {
        const urlParams = new URLSearchParams(window.location.search);

        if (urlParams.toString()) {
            this.currentFilters = {};
            urlParams.forEach((value, key) => {
                if (value) this.currentFilters[key] = value;
            });
            this.populateFiltersFromUrl();
        }

        await this.loadDissertations();
    }

    populateFiltersFromUrl() {
        const yearFrom = this.currentFilters.year_from;
        const yearTo = this.currentFilters.year_to;
        const organization = this.currentFilters.organization;
        const specialty = this.currentFilters.specialty_code;
        const author = this.currentFilters.author_name;
        const keywords = this.currentFilters.keywords;
        const status = this.currentFilters.processing_status;

        if (yearFrom) {
            const yearFromInput = document.querySelector('.date-range input:first-child');
            if (yearFromInput) yearFromInput.value = yearFrom;
        }
        if (yearTo) {
            const yearToInput = document.querySelector('.date-range input:last-child');
            if (yearToInput) yearToInput.value = yearTo;
        }
        if (organization) {
            const orgInput = document.querySelectorAll('.filter-input')[2];
            if (orgInput) orgInput.value = organization;
        }
        if (specialty) {
            const specialtyInput = document.querySelectorAll('.filter-input')[3];
            if (specialtyInput) specialtyInput.value = specialty;
        }
        if (author) {
            const authorInput = document.querySelectorAll('.filter-input')[4];
            if (authorInput) authorInput.value = author;
        }
        if (keywords) {
            const keywordsInput = document.querySelectorAll('.filter-input')[5];
            if (keywordsInput) keywordsInput.value = keywords;
        }
        if (status) {
            const statusDisplay = document.getElementById('status-display');
            if (statusDisplay) {
                statusDisplay.textContent = this.getStatusText(status);
                statusDisplay.dataset.value = status;
            }
        }
    }

    getStatusText(status) {
        const statusMap = {
            'pending': 'В обработке',
            'processing': 'Обрабатывается',
            'completed': 'Завершено',
            'error': 'Ошибка'
        };
        return statusMap[status] || 'Любой';
    }

    async applyFilters() {
        this.currentFilters = this.getFiltersFromForm();
        this.currentPage = 1;
        await this.loadDissertations();
    }

    resetFilters() {
        const filterInputs = document.querySelectorAll('.filter-input');
        filterInputs.forEach(input => input.value = '');

        const statusDisplay = document.getElementById('status-display');
        if (statusDisplay) {
            statusDisplay.textContent = 'Любой';
            statusDisplay.dataset.value = '';
        }

        const checkboxes = document.querySelectorAll('.checkbox-group input');
        checkboxes.forEach(checkbox => checkbox.checked = false);

        this.currentFilters = {};
        this.currentPage = 1;
        this.loadDissertations();
    }

    getFiltersFromForm() {
        const filters = {};

        const yearFrom = document.querySelector('.date-range input:first-child')?.value;
        const yearTo = document.querySelector('.date-range input:last-child')?.value;
        const organization = document.querySelectorAll('.filter-input')[2]?.value;
        const specialty = document.querySelectorAll('.filter-input')[3]?.value;
        const author = document.querySelectorAll('.filter-input')[4]?.value;
        const keywords = document.querySelectorAll('.filter-input')[5]?.value;

        if (yearFrom) filters.year_from = parseInt(yearFrom);
        if (yearTo) filters.year_to = parseInt(yearTo);
        if (organization) filters.organization = organization;
        if (specialty) filters.specialty_code = specialty;
        if (author) filters.author_name = author;
        if (keywords) filters.keywords = keywords;

        const statusValue = document.getElementById('status-display')?.dataset.value;
        if (statusValue) {
            filters.processing_status = statusValue;
        }

        return filters;
    }

    getStatusValue(text) {
        const statusMap = {
            'В обработке': 'pending',
            'Обрабатывается': 'processing',
            'Завершено': 'completed',
            'Ошибка': 'error'
        };
        return statusMap[text] || '';
    }

    async loadDissertations() {
        try {
            this.showLoading();

            const result = await api.getDissertations(
                this.currentFilters,
                this.currentPage,
                this.pageSize
            );

            this.totalResults = result.total || 0;
            this.updateResults(result.data || []);
            this.updatePagination();
            this.updateResultsCount();

        } catch (error) {
            console.error('Failed to load dissertations:', error);
            this.showError('Не удалось загрузить диссертации. Попробуйте позже.');
        } finally {
            this.hideLoading();
        }
    }

    updateResults(dissertations) {
        const tbody = document.querySelector('.results-table tbody');
        if (!tbody) return;

        tbody.innerHTML = '';

        if (dissertations.length === 0) {
            tbody.innerHTML = `
                <tr>
                    <td colspan="6" style="text-align: center; padding: 40px; color: #6b7280;">
                        Диссертации не найдены. Попробуйте изменить параметры поиска.
                    </td>
                </tr>
            `;
            return;
        }

        dissertations.forEach(diss => {
            const row = this.createDissertationRow(diss);
            tbody.appendChild(row);
        });
    }

    createDissertationRow(dissertation) {
        const tr = document.createElement('tr');

        const title = dissertation.title || 'Без названия';
        const author = dissertation.author_name || 'Неизвестный автор';
        const defenseDate = dissertation.defense_date ? new Date(dissertation.defense_date).toLocaleDateString('ru-RU') : 'Неизвестна';
        const organization = dissertation.organization_name || 'Неизвестна';
        const specialty = dissertation.specialty_code || 'Не указана';

        tr.innerHTML = `
            <td><a href="dissertation-detail.html?id=${dissertation._key}" class="dissertation-title">${this.escapeHtml(title)}</a></td>
            <td class="author-name">${this.escapeHtml(author)}</td>
            <td class="year-value">${defenseDate}</td>
            <td class="org-name">${this.escapeHtml(organization)}</td>
            <td class="spec-name">${this.escapeHtml(specialty)}</td>
            <td>
                <div class="action-buttons-cell">
                    <button class="btn-edit" onclick="dissertationPage.openEditModal('${dissertation._key}')">
                        ✏️
                    </button>
                    <button class="btn-delete" onclick="dissertationPage.openDeleteModal('${dissertation._key}', '${this.escapeHtml(title)}')">
                        🗑️
                    </button>
                </div>
            </td>
        `;

        return tr;
    }

    openCreateModal() {
        this.currentEditingId = null;
        document.getElementById('modal-title').textContent = 'Создание диссертации';
        document.getElementById('dissertation-form').reset();
        document.getElementById('dissertation-modal').style.display = 'flex';
    }

    async openEditModal(dissId) {
        try {
            const dissertation = await api.getDissertationDetails(dissId);
            this.currentEditingId = dissId;

            document.getElementById('modal-title').textContent = 'Редактирование диссертации';
            this.populateDissertationForm(dissertation);
            document.getElementById('dissertation-modal').style.display = 'flex';
        } catch (error) {
            console.error('Failed to load dissertation for editing:', error);
            this.showError('Не удалось загрузить диссертацию для редактирования');
        }
    }

    populateDissertationForm(dissertation) {
        const form = document.getElementById('dissertation-form');

        form.querySelector('[name="title"]').value = dissertation.title || '';
        form.querySelector('[name="defense_date"]').value = dissertation.defense_date || '';
        form.querySelector('[name="specialty_code"]').value = dissertation.specialty_code || '';
        form.querySelector('[name="type"]').value = dissertation.type || 'Кандидатская';
        form.querySelector('[name="science_branch"]').value = dissertation.science_branch || '';
        form.querySelector('[name="defense_council_code"]').value = dissertation.defense_council_code || '';
        form.querySelector('[name="vak_url"]').value = dissertation.vak_url || '';
        form.querySelector('[name="organization_advert_url"]').value = dissertation.organization_advert_url || '';

        const authorName = dissertation.author?.full_name || dissertation.author_name || '';
        form.querySelector('[name="author_name"]').value = authorName;

        const orgName = dissertation.organization?.full_name || dissertation.organization_name || '';
        form.querySelector('[name="organization_name"]').value = orgName;
    }

    async saveDissertation() {
        try {
            const formData = this.getFormDataFromForm();

            const requiredFields = ['title', 'author_name', 'defense_date', 'organization_name', 'specialty_code', 'vak_url'];
            const missingFields = requiredFields.filter(field => !formData[field] || formData[field].trim() === '');

            if (missingFields.length > 0) {
                this.showError('Заполните все обязательные поля: ' + missingFields.map(field => {
                    const fieldNames = {
                        'title': 'Название',
                        'author_name': 'Автор',
                        'defense_date': 'Дата защиты',
                        'organization_name': 'Организация',
                        'specialty_code': 'Код специальности',
                        'vak_url': 'URL ВАК'
                    };
                    return fieldNames[field] || field;
                }).join(', '));
                return;
            }

            if (this.currentEditingId) {
                await api.updateDissertation(this.currentEditingId, formData);
                this.showSuccess('Диссертация успешно обновлена');
            } else {
                await api.createDissertation(formData);
                this.showSuccess('Диссертация успешно создана');
            }

            this.closeDissertationModal();
            await this.loadDissertations();
        } catch (error) {
            console.error('Failed to save dissertation:', error);
            this.showError('Не удалось сохранить диссертацию: ' + (error.message || 'Произошла ошибка'));
        }
    }

    getFormDataFromForm() {
        const form = document.getElementById('dissertation-form');
        const formData = new FormData(form);
        const data = {};

        for (let [key, value] of formData.entries()) {
            data[key] = value;
        }

        return data;
    }

    openDeleteModal(dissId, title) {
        this.currentDeleteId = dissId;
        document.getElementById('delete-dissertation-title').textContent = title;
        document.getElementById('delete-modal').style.display = 'flex';
    }

    async confirmDelete() {
        try {
            await api.deleteDissertation(this.currentDeleteId);
            this.showSuccess('Диссертация успешно удалена');
            this.closeDeleteModal();
            await this.loadDissertations();
        } catch (error) {
            console.error('Failed to delete dissertation:', error);
            this.showError('Не удалось удалить диссертацию: ' + error.message);
        }
    }

    closeDissertationModal() {
        document.getElementById('dissertation-modal').style.display = 'none';
    }

    closeDeleteModal() {
        document.getElementById('delete-modal').style.display = 'none';
        this.currentDeleteId = null;
    }

    updatePagination() {
        const paginationContainer = document.querySelector('.pagination');
        if (!paginationContainer) return;

        const totalPages = Math.ceil(this.totalResults / this.pageSize);
        const currentPage = this.currentPage;

        paginationContainer.innerHTML = '';

        const prevBtn = document.createElement('button');
        prevBtn.className = `pagination-btn ${currentPage === 1 ? 'disabled' : ''}`;
        prevBtn.textContent = '←';
        prevBtn.addEventListener('click', () => {
            if (currentPage > 1) {
                this.currentPage--;
                this.loadDissertations();
            }
        });
        paginationContainer.appendChild(prevBtn);

        const maxVisiblePages = 5;
        let startPage = Math.max(1, currentPage - Math.floor(maxVisiblePages / 2));
        let endPage = Math.min(totalPages, startPage + maxVisiblePages - 1);

        if (endPage - startPage + 1 < maxVisiblePages) {
            startPage = Math.max(1, endPage - maxVisiblePages + 1);
        }

        for (let i = startPage; i <= endPage; i++) {
            const pageBtn = document.createElement('button');
            pageBtn.className = `pagination-btn ${i === currentPage ? 'active' : ''}`;
            pageBtn.textContent = i;
            pageBtn.addEventListener('click', () => {
                this.currentPage = i;
                this.loadDissertations();
            });
            paginationContainer.appendChild(pageBtn);
        }

        const nextBtn = document.createElement('button');
        nextBtn.className = `pagination-btn ${currentPage === totalPages ? 'disabled' : ''}`;
        nextBtn.textContent = '→';
        nextBtn.addEventListener('click', () => {
            if (currentPage < totalPages) {
                this.currentPage++;
                this.loadDissertations();
            }
        });
        paginationContainer.appendChild(nextBtn);
    }

    updateResultsCount() {
        const resultsCount = document.querySelector('.results-count strong');
        if (resultsCount) {
            resultsCount.textContent = this.totalResults.toLocaleString('ru-RU');
        }
    }

    async exportResults() {
        try {
            this.showExportLoading();

            await api.exportDissertations(this.currentFilters, 'csv');
            this.showSuccess('Экспорт успешно выполнен');

        } catch (error) {
            console.error('Export failed:', error);
            this.showError('Не удалось выполнить экспорт. Попробуйте позже.');
        } finally {
            this.hideExportLoading();
        }
    }


    showLoading() {
        const tbody = document.querySelector('.results-table tbody');
        if (tbody) {
            tbody.style.opacity = '0.5';
        }
    }

    hideLoading() {
        const tbody = document.querySelector('.results-table tbody');
        if (tbody) {
            tbody.style.opacity = '1';
        }
    }

    showExportLoading() {
        const exportBtn = document.querySelector('.btn-export');
        if (exportBtn) {
            exportBtn.disabled = true;
            exportBtn.textContent = 'Экспорт...';
        }
    }

    hideExportLoading() {
        const exportBtn = document.querySelector('.btn-export');
        if (exportBtn) {
            exportBtn.disabled = false;
            exportBtn.innerHTML = `
                <svg width="14" height="14" viewBox="0 0 14 14" fill="white">
                    <path d="M7 1v8M4 8l3 3 3-3"/>
                    <path d="M1 11h12v2H1z"/>
                </svg>
                Экспорт результатов
            `;
        }
    }

    showError(message) {
        Utils.showErrorMessage(message);
    }

    showSuccess(message) {
        Utils.showMessage(message, 'success');
    }

    escapeHtml(text) {
        return Utils.escapeHtml(text);
    }
}

document.addEventListener('DOMContentLoaded', () => {
    window.dissertationPage = new DissertationPage();
});

window.closeDissertationModal = function() {
    window.dissertationPage.closeDissertationModal();
};

window.closeDeleteModal = function() {
    window.dissertationPage.closeDeleteModal();
};

window.saveDissertation = function() {
    window.dissertationPage.saveDissertation();
};

window.confirmDelete = function() {
    window.dissertationPage.confirmDelete();
};
