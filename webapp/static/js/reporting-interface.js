/**
 * Reporting Interface
 * Provides comprehensive report generation and management functionality
 */

class ReportingInterface {
    constructor(options = {}) {
        this.options = {
            container: '#reporting-container',
            generateUrl: '/api/reporting/generate',
            previewUrl: '/api/reporting/preview',
            downloadUrl: '/api/reporting/download',
            templatesUrl: '/api/reporting/templates',
            historyUrl: '/api/reporting/history',
            formatsUrl: '/api/reporting/formats',
            typesUrl: '/api/reporting/types',
            validateUrl: '/api/reporting/config/validate',
            ...options
        };

        this.reportFormats = [];
        this.reportTypes = [];
        this.templates = [];
        this.reportHistory = [];
        this.currentConfig = {};
        this.isGenerating = false;

        this.init();
    }

    init() {
        this.setupContainer();
        this.setupEventListeners();
        this.loadInitialData();
    }

    setupContainer() {
        this.container = document.querySelector(this.options.container);
        if (!this.container) {
            console.error('Reporting container not found');
            return;
        }

        this.container.innerHTML = this.getContainerHTML();
        this.reportForm = this.container.querySelector('#report-form');
    }

    getContainerHTML() {
        return `
            <div class="reporting-interface">
                <div class="reporting-header">
                    <h2 class="section-title">
                        <i class="fas fa-chart-bar"></i>
                        Training Reports
                    </h2>
                    <div class="header-actions">
                        <button class="btn btn-primary" id="new-report">
                            <i class="fas fa-plus"></i> New Report
                        </button>
                    </div>
                </div>

                <div class="reporting-content">
                    <div class="report-generator" id="report-generator" style="display: none;">
                        <form id="report-form" class="report-form">
                            <div class="form-section">
                                <h4>Basic Configuration</h4>
                                <div class="form-group">
                                    <label class="form-label" for="report-title">Report Title</label>
                                    <input type="text" id="report-title" class="form-input" required>
                                </div>
                                <div class="form-group">
                                    <label class="form-label" for="report-type">Report Type</label>
                                    <select id="report-type" class="form-select" required>
                                        <option value="">Select report type...</option>
                                    </select>
                                </div>
                                <div class="form-group">
                                    <label class="form-label" for="report-format">Output Format</label>
                                    <select id="report-format" class="form-select" required>
                                        <option value="">Select format...</option>
                                    </select>
                                </div>
                            </div>
                            
                            <div class="form-actions">
                                <button type="button" class="btn btn-secondary" id="preview-report">
                                    <i class="fas fa-eye"></i> Preview
                                </button>
                                <button type="submit" class="btn btn-primary" id="generate-report">
                                    <i class="fas fa-download"></i> Generate Report
                                </button>
                            </div>
                        </form>
                    </div>

                    <div class="reports-dashboard" id="reports-dashboard">
                        <div class="dashboard-section">
                            <h3>Recent Reports</h3>
                            <div class="reports-list" id="history-list">
                                <!-- Report history will be loaded here -->
                            </div>
                        </div>
                    </div>
                </div>

                <div class="loading-overlay" id="loading-overlay" style="display: none;">
                    <div class="loading-content">
                        <div class="spinner"></div>
                        <p id="loading-message">Generating report...</p>
                    </div>
                </div>
            </div>
        `;
    }

    setupEventListeners() {
        this.container.querySelector('#new-report')?.addEventListener('click', () => {
            this.showReportGenerator();
        });

        this.container.querySelector('#preview-report')?.addEventListener('click', () => {
            this.previewReport();
        });

        this.container.querySelector('#generate-report')?.addEventListener('click', () => {
            this.generateReport();
        });

        this.reportForm?.addEventListener('submit', (e) => {
            e.preventDefault();
            this.generateReport();
        });
    }

    async loadInitialData() {
        try {
            await this.loadReportFormats();
            await this.loadReportTypes();
            await this.loadReportHistory();
        } catch (error) {
            console.error('Error loading initial data:', error);
        }
    }

    async loadReportFormats() {
        try {
            const response = await fetch(this.options.formatsUrl);
            if (!response.ok) throw new Error('Failed to load formats');
            
            const data = await response.json();
            this.reportFormats = data.formats;
            
            const formatSelect = this.container.querySelector('#report-format');
            if (formatSelect) {
                formatSelect.innerHTML = '<option value="">Select format...</option>';
                this.reportFormats.forEach(format => {
                    const option = document.createElement('option');
                    option.value = format.value;
                    option.textContent = format.name;
                    formatSelect.appendChild(option);
                });
            }
        } catch (error) {
            console.error('Error loading report formats:', error);
        }
    }

    async loadReportTypes() {
        try {
            const response = await fetch(this.options.typesUrl);
            if (!response.ok) throw new Error('Failed to load types');
            
            const data = await response.json();
            this.reportTypes = data.types;
            
            const typeSelect = this.container.querySelector('#report-type');
            if (typeSelect) {
                typeSelect.innerHTML = '<option value="">Select report type...</option>';
                this.reportTypes.forEach(type => {
                    const option = document.createElement('option');
                    option.value = type.value;
                    option.textContent = type.name;
                    typeSelect.appendChild(option);
                });
            }
        } catch (error) {
            console.error('Error loading report types:', error);
        }
    }

    async loadReportHistory() {
        try {
            const response = await fetch(this.options.historyUrl);
            if (!response.ok) throw new Error('Failed to load history');
            
            const data = await response.json();
            this.reportHistory = data.reports;
            this.renderReportHistory();
        } catch (error) {
            console.error('Error loading report history:', error);
        }
    }

    renderReportHistory() {
        const historyList = this.container.querySelector('#history-list');
        if (!historyList) return;
        
        if (this.reportHistory.length === 0) {
            historyList.innerHTML = '<p>No reports generated yet</p>';
            return;
        }
        
        historyList.innerHTML = '';
        this.reportHistory.slice(0, 5).forEach(report => {
            const reportItem = document.createElement('div');
            reportItem.className = 'report-item';
            reportItem.innerHTML = `
                <div class="report-info">
                    <div class="report-title">${report.title}</div>
                    <div class="report-meta">
                        <span class="format-badge">${report.format.toUpperCase()}</span>
                        <span class="date">${this.formatDate(report.generated_at)}</span>
                    </div>
                </div>
            `;
            historyList.appendChild(reportItem);
        });
    }

    showReportGenerator() {
        this.container.querySelector('#reports-dashboard').style.display = 'none';
        this.container.querySelector('#report-generator').style.display = 'block';
    }

    hideReportGenerator() {
        this.container.querySelector('#reports-dashboard').style.display = 'block';
        this.container.querySelector('#report-generator').style.display = 'none';
    }

    async previewReport() {
        try {
            const config = this.getFormConfig();
            this.showLoading('Generating preview...');
            
            const response = await fetch(this.options.previewUrl, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': this.getCSRFToken()
                },
                body: JSON.stringify(config)
            });
            
            if (!response.ok) {
                const error = await response.json();
                throw new Error(error.error || 'Failed to generate preview');
            }
            
            const data = await response.json();
            
            // Show preview in new window
            const newWindow = window.open('', '_blank');
            newWindow.document.write(data.preview.content);
            newWindow.document.close();
            
        } catch (error) {
            console.error('Error generating preview:', error);
            this.showError(error.message);
        } finally {
            this.hideLoading();
        }
    }

    async generateReport() {
        try {
            const config = this.getFormConfig();
            this.showLoading('Generating report...');
            
            const response = await fetch(this.options.generateUrl, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': this.getCSRFToken()
                },
                body: JSON.stringify(config)
            });
            
            if (!response.ok) {
                const error = await response.json();
                throw new Error(error.error || 'Failed to generate report');
            }
            
            const data = await response.json();
            
            if (data.report.download_url) {
                window.open(data.report.download_url, '_blank');
            } else if (data.report.content) {
                const newWindow = window.open('', '_blank');
                newWindow.document.write(data.report.content);
                newWindow.document.close();
            }
            
            this.showSuccess('Report generated successfully!');
            this.loadReportHistory();
            this.hideReportGenerator();
            
        } catch (error) {
            console.error('Error generating report:', error);
            this.showError(error.message);
        } finally {
            this.hideLoading();
        }
    }

    getFormConfig() {
        const form = this.reportForm;
        return {
            title: form.querySelector('#report-title').value,
            report_type: form.querySelector('#report-type').value,
            format: form.querySelector('#report-format').value,
            include_charts: true,
            include_metrics: true
        };
    }

    formatDate(dateString) {
        const date = new Date(dateString);
        return date.toLocaleDateString();
    }

    getCSRFToken() {
        return document.querySelector('meta[name="csrf-token"]')?.getAttribute('content') || '';
    }

    showLoading(message = 'Loading...') {
        const overlay = this.container.querySelector('#loading-overlay');
        const messageEl = this.container.querySelector('#loading-message');
        
        if (overlay && messageEl) {
            messageEl.textContent = message;
            overlay.style.display = 'flex';
        }
    }

    hideLoading() {
        const overlay = this.container.querySelector('#loading-overlay');
        if (overlay) {
            overlay.style.display = 'none';
        }
    }

    showError(message) {
        console.error(message);
        alert(message);
    }

    showSuccess(message) {
        console.log(message);
        alert(message);
    }
}

// Initialize the reporting interface
let reportingInterface;
document.addEventListener('DOMContentLoaded', () => {
    const container = document.querySelector('#reporting-container');
    if (container) {
        reportingInterface = new ReportingInterface();
    }
});