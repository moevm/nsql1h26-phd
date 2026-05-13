class DissertationDetailPage {
    constructor() {
        this.dissertationId = this.getDissertationIdFromUrl();
        if (!this.dissertationId) {
            this.showErrorMessage('ID диссертации не указан');
            return;
        }
        this.init();
    }

    getDissertationIdFromUrl() {
        const urlParams = new URLSearchParams(window.location.search);
        return urlParams.get('id');
    }

    async init() {
        await this.loadDissertationDetails();
        this.bindEvents();
    }

    bindEvents() {
        const fisButton = document.querySelector('.btn-primary');
        if (fisButton && fisButton.textContent.includes('ФИС ГНА')) {
            fisButton.addEventListener('click', () => {
                this.openFisGnaSite();
            });
        }

        document.querySelectorAll('.btn-export').forEach(button => {
            button.addEventListener('click', () => {
                this.exportMetadata(button);
            });
        });

        const similarButton = Array.from(document.querySelectorAll('.btn-primary')).find(
            btn => btn.textContent.includes('похожие')
        );
        if (similarButton) {
            similarButton.addEventListener('click', () => {
                this.findSimilarDissertations();
            });
        }

        document.querySelectorAll('.similar-item').forEach(item => {
            item.addEventListener('click', () => {
                this.goToSimilarDissertation(item);
            });
        });
    }

    async loadDissertationDetails() {
        try {
            const dissertation = await api.getDissertationDetails(this.dissertationId);
            this.currentDissertation = dissertation;
            this.updateDissertationDetails(dissertation);
        } catch (error) {
            console.error('Failed to load dissertation details:', error);
            this.showErrorMessage('Не удалось загрузить детали диссертации');
        }
    }

    updateDissertationDetails(dissertation) {
        const pageTitle = document.querySelector('.page-title');
        if (pageTitle && dissertation.title) {
            pageTitle.textContent = dissertation.title;
        }

        this.updateMetadata(dissertation);

        this.updateAbstractText(dissertation);

        this.updateStatusHistory(dissertation);
    }

    updateMetadata(dissertation) {
        const authorName = dissertation.author?.full_name || dissertation.author_name || 'Не указан';
        const authorKey = dissertation.author?._key || dissertation.author_id || '';
        const orgName = dissertation.organization?.full_name || dissertation.organization_name || 'Не указана';
        const orgKey = dissertation.organization?._key || dissertation.organization_id || '';
        const defenseDate = dissertation.defense_date ? new Date(dissertation.defense_date).toLocaleDateString('ru-RU') : 'Не указана';
        const councilCode = dissertation.defense_council_code || 'Не указан';
        const specialtyCode = dissertation.specialty_code || 'Не указана';
        const type = dissertation.type || 'ВАК';
        const created = dissertation.created_at ? new Date(dissertation.created_at).toLocaleDateString('ru-RU') : 'Не указана';
        const updated = dissertation.updated_at ? new Date(dissertation.updated_at).toLocaleDateString('ru-RU') : 'Не указана';

        const metadataFields = document.querySelectorAll('.metadata-field');
        metadataFields.forEach(field => {
            const label = field.querySelector('.metadata-label');
            const value = field.querySelector('.metadata-value');
            if (!label || !value) return;

            const labelText = label.textContent.trim();

            if (labelText === 'Автор:') {
                value.innerHTML = '';
                if (authorKey) {
                    const link = document.createElement('a');
                    link.href = `author-detail.html?id=${authorKey}`;
                    link.className = 'metadata-value link';
                    link.textContent = authorName;
                    value.appendChild(link);
                } else {
                    value.textContent = authorName;
                }
            } else if (labelText === 'Организация защиты:') {
                value.innerHTML = '';
                if (orgKey) {
                    const link = document.createElement('a');
                    link.href = `organization-detail.html?id=${orgKey}`;
                    link.className = 'metadata-value link';
                    link.textContent = orgName;
                    value.appendChild(link);
                } else {
                    value.textContent = orgName;
                }
            } else if (labelText === 'Дата защиты:') {
                value.textContent = defenseDate;
            } else if (labelText === 'Диссертационный совет:') {
                value.textContent = councilCode;
            } else if (labelText === 'Специальность:') {
                value.innerHTML = '';
                if (specialtyCode !== 'Не указана') {
                    const link = document.createElement('a');
                    link.href = `dissertation.html?specialty_code=${encodeURIComponent(specialtyCode)}`;
                    link.className = 'metadata-value link';
                    link.textContent = specialtyCode;
                    value.appendChild(link);
                } else {
                    value.textContent = specialtyCode;
                }
            } else if (labelText === 'Тип защиты:') {
                value.textContent = type;
            } else if (labelText === 'Добавлена:') {
                value.textContent = created;
            } else if (labelText === 'Обновлена:') {
                value.textContent = updated;
            }
        });
    }

    updateAbstractText(dissertation) {
        const abstractText = document.querySelector('.abstract-text');
        const content = dissertation.abstract_text || dissertation.file_content || '';

        if (abstractText && content) {
            abstractText.innerHTML = this.formatAbstractText(content);
        }
    }

    formatAbstractText(text) {
        const paragraphs = text.split('\n').filter(p => p.trim());

        return paragraphs.map(paragraph => {
            return paragraph + '<br><br>';
        }).join('');
    }

    updateStatusHistory(dissertation) {
        const statusHistorySection = Array.from(document.querySelectorAll('.detail-card')).find(
            card => card.querySelector('.detail-title')?.textContent.includes('История статусов')
        );

        if (!statusHistorySection) return;

        if (dissertation.processing_status && dissertation.updated_at) {
            const statusContent = statusHistorySection.querySelector('.detail-content');

            const statusRows = [
                {
                    status: this.getStatusInfo(dissertation.processing_status),
                    date: dissertation.updated_at,
                    description: this.getStatusDescription(dissertation.processing_status)
                }
            ];

            if (dissertation.created_at !== dissertation.updated_at) {
                statusRows.unshift({
                    status: { class: 'status-received', text: '📥 Получен' },
                    date: dissertation.created_at,
                    description: 'Документ добавлен в систему'
                });
            }

            statusContent.innerHTML = statusRows.map(row => `
                <div class="status-row">
                    <div><span class="status-badge ${row.status.class}">${row.status.text}</span></div>
                    <div>${new Date(row.date).toLocaleString('ru-RU')}</div>
                    <div>${row.description}</div>
                </div>
            `).join('');
        } else {
            statusHistorySection.style.display = 'none';
        }
    }

    getStatusInfo(status) {
        const statusMap = {
            'completed': { class: 'status-success', text: '✓ Обработан' },
            'processing': { class: 'status-progress', text: '⟳ В обработке' },
            'pending': { class: 'status-pending', text: '⏳ Ожидает' },
            'error': { class: 'status-error', text: '✗ Ошибка' }
        };
        return statusMap[status] || { class: 'status-received', text: '📥 Получен' };
    }

    getStatusDescription(status) {
        const descriptionMap = {
            'completed': 'Анализ текста завершен успешно',
            'processing': 'Выполняется семантический анализ',
            'pending': 'Ожидает начала обработки',
            'error': 'Ошибка при обработке документа'
        };
        return descriptionMap[status] || 'Статус неизвестен';
    }

    openFisGnaSite() {
        const fisButton = document.querySelector('.btn-primary');
        if (fisButton && this.currentDissertation?.vak_url) {
            window.open(this.currentDissertation.vak_url, '_blank');
        } else {
            this.showInfoMessage('Ссылка на ФИС ГНА недоступна');
        }
    }

    async exportMetadata(button) {
        try {
            const format = button.textContent.includes('CSV') ? 'csv' : 'json';
            await api.exportDissertations({ id: this.dissertationId }, format);
        } catch (error) {
            console.error('Export failed:', error);
            this.showErrorMessage('Ошибка экспорта метаданных');
        }
    }

    findSimilarDissertations() {
        const title = document.querySelector('.page-title')?.textContent;
        if (title) {
            const params = new URLSearchParams({ keywords: title.slice(0, 50) });
            window.location.href = `dissertation.html?${params.toString()}`;
        }
    }

    goToSimilarDissertation(element) {
        this.showInfoMessage('Переход к похожей диссертации в разработке');
    }

    showErrorMessage(message) {
        Utils.showErrorMessage(message);
    }

    showInfoMessage(message) {
        Utils.showInfoMessage(message);
    }
}

document.addEventListener('DOMContentLoaded', () => {
    new DissertationDetailPage();
});
