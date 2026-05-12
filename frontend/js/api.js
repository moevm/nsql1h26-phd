class ApiClient {
    constructor(baseUrl = '') {
        this.baseUrl = baseUrl;
    }

    async request(endpoint, options = {}) {
        const url = `${this.baseUrl}${endpoint}`;
        const config = {
            headers: {
                'Content-Type': 'application/json',
                ...options.headers,
            },
            ...options,
        };

        try {
            const response = await fetch(url, config);

            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }

            return await response.json();
        } catch (error) {
            console.error(`API request failed: ${endpoint}`, error);
            throw error;
        }
    }

    async get(endpoint) {
        return this.request(endpoint);
    }

    async post(endpoint, data) {
        return this.request(endpoint, {
            method: 'POST',
            body: JSON.stringify(data),
        });
    }

    async getDissertations(filters = {}, page = 1, pageSize = 10) {
        const params = new URLSearchParams({
            page: page.toString(),
            page_size: pageSize.toString(),
            ...filters
        });

        return this.get(`/api/dissertations?${params}`);
    }

    async getDissertationDetails(dissId) {
        return this.get(`/api/dissertations/${dissId}`);
    }

    async getStatistics() {
        const totalResult = await this.getDissertations({}, 1, 1);
        const total = totalResult.total || 0;

        const sampleData = await this.getDissertations({}, 1, Math.min(total, 1000));

        const uniqueAuthors = new Set();
        const uniqueOrgs = new Set();
        const uniqueSpecialties = new Set();

        sampleData.data?.forEach(diss => {
            if (diss.author_name) uniqueAuthors.add(diss.author_name);
            if (diss.organization_name) uniqueOrgs.add(diss.organization_name);
            if (diss.specialty_code) uniqueSpecialties.add(diss.specialty_code);
        });

        return {
            totalDissertations: total,
            totalAuthors: uniqueAuthors.size,
            totalOrganizations: uniqueOrgs.size,
            totalSpecialties: uniqueSpecialties.size
        };
    }

    async getDissertationsByYears() {
        const yearCounts = {};

        const firstResult = await this.getDissertations({}, 1, 1);
        const total = firstResult.total || 0;

        const pageSize = 500;
        const totalPages = Math.ceil(total / pageSize);

        for (let page = 1; page <= totalPages; page++) {
            const result = await this.getDissertations({}, page, pageSize);
            result.data?.forEach(diss => {
                if (diss.defense_date) {
                    const year = new Date(diss.defense_date).getFullYear();
                    if (year && year >= 2015 && year <= 2026) {
                        yearCounts[year] = (yearCounts[year] || 0) + 1;
                    }
                }
            });
        }

        const years = [];
        const counts = [];

        for (let year = 2015; year <= 2026; year++) {
            years.push(year);
            counts.push(yearCounts[year] || 0);
        }

        return { years, counts };
    }

    async exportDissertations(filters = {}, format = 'csv') {
        const params = new URLSearchParams();

        if (filters.id) {
            params.append('diss_id', filters.id);
        }

        params.append('export_format', format);

        const response = await fetch(`/api/dissertations/export?${params}`, {
            headers: {
                'Accept': format === 'csv' ? 'text/csv' : 'application/json'
            }
        });

        if (response.ok) {
            const blob = await response.blob();
            const url = window.URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.href = url;
            a.download = `dissertations_export.${format}`;
            document.body.appendChild(a);
            a.click();
            window.URL.revokeObjectURL(url);
            document.body.removeChild(a);
        } else {
            throw new Error(`Failed to export ${format}`);
        }
    }
}

const api = new ApiClient();
