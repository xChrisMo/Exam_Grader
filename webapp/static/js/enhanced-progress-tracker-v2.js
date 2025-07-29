/**
 * Enhanced Progress Tracker v2
 * Requirements: 1.5, 2.4, 2.5, 6.7
 */

class EnhancedProgressTrackerV2 {
    constructor(options = {}) {
        this.options = {
            container: '#training-progress-section',
            jobsUrl: '/api/llm-training/jobs',
            refreshInterval: 2000,
            ...options
        };

        this.jobs = new Map();
        this.activeJobs = new Set();
        this.refreshTimer = null;
        this.isLoading = false;

        this.init();
    }

    init() {
        this.setupContainer();
        this.setupEventListeners();
        this.loadJobs();
        this.startRealTimeUpdates();
    }

    setupContainer() {
        this.container = document.querySelector(this.options.container);
        if (!this.container) {
            console.error('Progress tracker container not found');
            return;
        }

        this.container.innerHTML = this.getEnhancedContainerHTML();
        this.jobsList = this.container.querySelector('#jobs-list');
    }

    getEnhancedContainerHTML() {
        return `
            <div class="progress-tracker enhanced">
                <div class="tracker-header">
                    <h3>Training Job Monitor</h3>
                    <div class="tracker-stats">
                        <div class="stat-item">
                            <span class="stat-value" id="total-jobs">0</span>
                            <span class="stat-label">Total</span>
                        </div>
                        <div class="stat-item">
                            <span class="stat-value" id="active-jobs">0</span>
                            <span class="stat-label">Active</span>
                        </div>
                    </div>
                </div>
                <div class="jobs-list" id="jobs-list"></div>
            </div>
        `;
    }

    setupEventListeners() {
        // Event listeners setup
    }

    async loadJobs() {
        try {
            const response = await fetch(this.options.jobsUrl);
            const data = await response.json();
            
            this.jobs.clear();
            data.jobs.forEach(job => {
                this.jobs.set(job.id, job);
            });

            this.renderJobs();
        } catch (error) {
            console.error('Error loading jobs:', error);
        }
    }

    renderJobs() {
        const jobs = Array.from(this.jobs.values());
        this.jobsList.innerHTML = jobs.map(job => this.createJobCard(job)).join('');
    }

    createJobCard(job) {
        return `
            <div class="job-card enhanced" data-job-id="${job.id}">
                <div class="job-header">
                    <h4>${job.name}</h4>
                    <span class="job-status ${job.status}">${job.status}</span>
                </div>
                <div class="job-progress">
                    <div class="progress-bar">
                        <div class="progress-fill" style="width: ${job.progress || 0}%"></div>
                    </div>
                    <span class="progress-text">${Math.round(job.progress || 0)}%</span>
                </div>
            </div>
        `;
    }

    startRealTimeUpdates() {
        this.refreshTimer = setInterval(() => {
            this.loadJobs();
        }, this.options.refreshInterval);
    }
}

window.EnhancedProgressTrackerV2 = EnhancedProgressTrackerV2;