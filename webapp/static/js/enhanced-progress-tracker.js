/**
 * Enhanced Progress Tracker Component
 * Provides real-time training job monitoring with detailed metrics and management capabilities
 */

class EnhancedProgressTracker {
    constructor(options = {}) {
        this.options = {
            container: '#training-jobs-container',
            jobsUrl: '/api/llm-training/jobs',
            jobDetailsUrl: '/api/llm-training/job',
            cancelJobUrl: '/api/llm-training/cancel-job',
            resumeJobUrl: '/api/llm-training/resume-job',
            metricsUrl: '/api/llm-training/job-metrics',
            logsUrl: '/api/llm-training/job-logs',
            autoRefresh: true,
            refreshInterval: 2000, // 2 seconds for real-time updates
            maxLogLines: 100,
            ...options
        };

        this.jobs = new Map();
        this.activeConnections = new Map();
        this.refreshTimer = null;
        this.isLoading = false;
        this.selectedJobId = null;
        this.currentView = 'grid';
        this.filters = {
            status: 'all',
            sortBy: 'created_at',
            sortOrder: 'desc'
        };

        this.init();
    }

    init() {
        this.setupContainer();
        this.setupEventListeners();
        this.loadJobs();
        
        if (this.options.autoRefresh) {
            this.startAutoRefresh();
        }
    }

    setupContainer() {
        this.container = document.querySelector(this.options.container);
        if (!this.container) {
            console.error('Progress tracker container not found');
            return;
        }

        // Enhanced container HTML with real-time monitoring
        this.container.innerHTML = this.getContainerHTML();

        // Get element references
        this.jobsGrid = this.container.querySelector('#jobs-grid');
        this.loadingState = this.container.querySelector('#loading-state');
        this.emptyState = this.container.querySelector('#empty-state');
        this.detailsPanel = this.container.querySelector('#job-details-panel');
        this.panelContent = this.container.querySelector('#panel-content');
    }

    getContainerHTML() {
        return `
            <div class="progress-tracker">
                <!-- Header with controls -->
                <div class="tracker-header">
                    <div class="header-left">
                        <h3 class="section-title">Training Jobs</h3>
                        <div class="job-stats">
                            <span class="stat-item">
                                <span class="stat-value" id="total-jobs">0</span>
                                <span class="stat-label">Total</span>
                            </span>
                            <span class="stat-item">
                                <span class="stat-value" id="running-jobs">0</span>
                                <span class="stat-label">Running</span>
                            </span>
                            <span class="stat-item">
                                <span class="stat-value" id="completed-jobs">0</span>
                                <span class="stat-label">Completed</span>
                            </span>
                            <span class="stat-item">
                                <span class="stat-value" id="failed-jobs">0</span>
                                <span class="stat-label">Failed</span>
                            </span>
                        </div>
                    </div>
                    <div class="header-actions">
                        <button class="btn btn-secondary" id="refresh-jobs-btn">
                            <i class="fas fa-sync-alt"></i> Refresh
                        </button>
                        <button class="btn btn-secondary" id="toggle-auto-refresh-btn">
                            <i class="fas fa-pause"></i> Auto Refresh
                        </button>
                        <button class="btn btn-secondary" id="export-logs-btn">
                            <i class="fas fa-download"></i> Export Logs
                        </button>
                    </div>
                </div>

                <!-- Job Filters -->
                <div class="job-filters">
                    <div class="filter-row">
                        <div class="filter-group">
                            <select id="status-filter" class="form-select">
                                <option value="all">All Status</option>
                                <option value="pending">Pending</option>
                                <option value="preparing">Preparing</option>
                                <option value="training">Training</option>
                                <option value="evaluating">Evaluating</option>
                                <option value="completed">Completed</option>
                                <option value="failed">Failed</option>
                                <option value="cancelled">Cancelled</option>
                            </select>
                            <select id="sort-filter" class="form-select">
                                <option value="created_at">Date Created</option>
                                <option value="name">Name</option>
                                <option value="status">Status</option>
                                <option value="progress">Progress</option>
                            </select>
                            <button id="sort-order-btn" class="btn btn-secondary" title="Toggle sort order">
                                <i class="fas fa-sort-amount-down"></i>
                            </button>
                        </div>
                        <div class="view-controls">
                            <button class="btn btn-secondary view-btn active" data-view="grid">
                                <i class="fas fa-th"></i> Grid
                            </button>
                            <button class="btn btn-secondary view-btn" data-view="list">
                                <i class="fas fa-list"></i> List
                            </button>
                        </div>
                    </div>
                </div>

                <!-- Jobs Container -->
                <div class="jobs-container">
                    <div class="jobs-grid" id="jobs-grid">
                        <!-- Jobs will be rendered here -->
                    </div>
                    
                    <!-- Loading State -->
                    <div class="loading-state" id="loading-state" style="display: none;">
                        <div class="spinner"></div>
                        <p>Loading training jobs...</p>
                    </div>
                    
                    <!-- Empty State -->
                    <div class="empty-state" id="empty-state" style="display: none;">
                        <div class="empty-icon">🤖</div>
                        <h3>No training jobs</h3>
                        <p>Create your first training job to start fine-tuning models.</p>
                        <button class="btn btn-primary" onclick="showCreateTrainingModal()">
                            <i class="fas fa-play"></i> Start Training
                        </button>
                    </div>
                </div>

                <!-- Job Details Panel -->
                <div class="job-details-panel" id="job-details-panel" style="display: none;">
                    <div class="panel-header">
                        <h4 class="panel-title" id="panel-title">Job Details</h4>
                        <button class="btn btn-secondary btn-sm" id="close-panel-btn">
                            <i class="fas fa-times"></i>
                        </button>
                    </div>
                    <div class="panel-content" id="panel-content">
                        <!-- Job details will be loaded here -->
                    </div>
                </div>
            </div>
        `;
    }
}    setupE
ventListeners() {
        // Header actions
        this.container.querySelector('#refresh-jobs-btn')?.addEventListener('click', () => {
            this.loadJobs(true);
        });

        this.container.querySelector('#toggle-auto-refresh-btn')?.addEventListener('click', () => {
            this.toggleAutoRefresh();
        });

        this.container.querySelector('#export-logs-btn')?.addEventListener('click', () => {
            this.exportLogs();
        });

        // Filters
        this.container.querySelector('#status-filter')?.addEventListener('change', (e) => {
            this.filters.status = e.target.value;
            this.applyFilters();
        });

        this.container.querySelector('#sort-filter')?.addEventListener('change', (e) => {
            this.filters.sortBy = e.target.value;
            this.applyFilters();
        });

        this.container.querySelector('#sort-order-btn')?.addEventListener('click', () => {
            this.toggleSortOrder();
        });

        // View controls
        this.container.querySelectorAll('.view-btn').forEach(btn => {
            btn.addEventListener('click', (e) => {
                this.switchView(e.target.dataset.view);
            });
        });

        // Panel controls
        this.container.querySelector('#close-panel-btn')?.addEventListener('click', () => {
            this.hideDetailsPanel();
        });
    }

    // Job loading and management
    async loadJobs(force = false) {
        if (this.isLoading && !force) return;
        
        this.isLoading = true;
        if (force) this.showLoading();

        try {
            const response = await fetch(this.options.jobsUrl);
            if (!response.ok) throw new Error('Failed to load jobs');
            
            const data = await response.json();
            
            // Update jobs map
            data.jobs.forEach(job => {
                const existingJob = this.jobs.get(job.id);
                if (existingJob) {
                    // Preserve UI state while updating data
                    Object.assign(existingJob, job);
                } else {
                    this.jobs.set(job.id, job);
                }
            });

            // Remove jobs that no longer exist
            const currentJobIds = new Set(data.jobs.map(job => job.id));
            for (const [jobId] of this.jobs) {
                if (!currentJobIds.has(jobId)) {
                    this.jobs.delete(jobId);
                }
            }

            this.updateStats();
            this.renderJobs();
            
            // Update selected job details if panel is open
            if (this.selectedJobId && this.detailsPanel.style.display !== 'none') {
                this.loadJobDetails(this.selectedJobId);
            }
            
        } catch (error) {
            console.error('Error loading jobs:', error);
            this.showError('Failed to load training jobs. Please try again.');
        } finally {
            this.isLoading = false;
            this.hideLoading();
        }
    }

    renderJobs() {
        const filteredJobs = this.getFilteredJobs();
        
        if (filteredJobs.length === 0) {
            this.showEmptyState();
            return;
        }

        this.hideEmptyState();
        this.jobsGrid.innerHTML = '';
        this.jobsGrid.className = `jobs-${this.currentView}`;

        filteredJobs.forEach(job => {
            const jobElement = this.createJobCard(job);
            this.jobsGrid.appendChild(jobElement);
        });
    }

    createJobCard(job) {
        const card = document.createElement('div');
        card.className = 'job-card';
        card.dataset.jobId = job.id;

        const statusClass = this.getStatusClass(job.status);
        const progressPercentage = this.calculateProgress(job);
        const timeRemaining = this.estimateTimeRemaining(job);
        
        card.innerHTML = this.getJobCardHTML(job, statusClass, progressPercentage, timeRemaining);

        // Add event listeners
        this.setupJobCardEvents(card, job);
        
        return card;
    }

    getJobCardHTML(job, statusClass, progressPercentage, timeRemaining) {
        return `
            <div class="job-card-header">
                <div class="job-info">
                    <div class="job-name" title="${job.name}">
                        ${job.name}
                    </div>
                    <div class="job-model">
                        <i class="fas fa-robot"></i>
                        ${job.model_name || 'Unknown Model'}
                    </div>
                </div>
                <div class="job-status ${statusClass}">
                    <i class="${this.getStatusIcon(job.status)}"></i>
                    <span class="status-text">${this.getStatusText(job.status)}</span>
                </div>
            </div>
            
            <div class="job-progress">
                <div class="progress-info">
                    <span class="progress-text">${this.getProgressText(job)}</span>
                    <span class="progress-percentage">${progressPercentage}%</span>
                </div>
                <div class="progress-bar">
                    <div class="progress-fill ${statusClass}" style="width: ${progressPercentage}%"></div>
                </div>
                ${timeRemaining ? `
                    <div class="time-remaining">
                        <i class="fas fa-clock"></i>
                        ${timeRemaining} remaining
                    </div>
                ` : ''}
            </div>
            
            <div class="job-metrics">
                ${this.renderJobMetrics(job)}
            </div>
            
            <div class="job-meta">
                <div class="meta-item">
                    <i class="fas fa-calendar"></i>
                    Started: ${this.formatDate(job.created_at)}
                </div>
                ${job.completed_at ? `
                    <div class="meta-item">
                        <i class="fas fa-check-circle"></i>
                        Completed: ${this.formatDate(job.completed_at)}
                    </div>
                ` : ''}
                ${job.dataset_name ? `
                    <div class="meta-item">
                        <i class="fas fa-database"></i>
                        Dataset: ${job.dataset_name}
                    </div>
                ` : ''}
            </div>
            
            <div class="job-actions">
                ${this.getJobActions(job)}
            </div>
            
            ${job.error_message ? `
                <div class="job-error">
                    <div class="error-summary">
                        <i class="fas fa-exclamation-triangle"></i>
                        Error: ${job.error_message}
                    </div>
                </div>
            ` : ''}
        `;
    }

    renderJobMetrics(job) {
        if (!job.metrics) return '';

        const metrics = [];
        
        if (job.metrics.current_epoch !== undefined) {
            metrics.push(`
                <div class="metric-item">
                    <span class="metric-label">Epoch</span>
                    <span class="metric-value">${job.metrics.current_epoch}/${job.metrics.total_epochs || '?'}</span>
                </div>
            `);
        }
        
        if (job.metrics.loss !== undefined) {
            metrics.push(`
                <div class="metric-item">
                    <span class="metric-label">Loss</span>
                    <span class="metric-value">${job.metrics.loss.toFixed(4)}</span>
                </div>
            `);
        }
        
        if (job.metrics.learning_rate !== undefined) {
            metrics.push(`
                <div class="metric-item">
                    <span class="metric-label">LR</span>
                    <span class="metric-value">${job.metrics.learning_rate.toExponential(2)}</span>
                </div>
            `);
        }
        
        if (job.metrics.accuracy !== undefined) {
            metrics.push(`
                <div class="metric-item">
                    <span class="metric-label">Accuracy</span>
                    <span class="metric-value">${(job.metrics.accuracy * 100).toFixed(1)}%</span>
                </div>
            `);
        }

        return metrics.length > 0 ? `
            <div class="metrics-grid">
                ${metrics.join('')}
            </div>
        ` : '';
    }

    getJobActions(job) {
        const actions = [];
        
        // View details action (always available)
        actions.push(`
            <button class="btn btn-sm btn-secondary" onclick="progressTracker.showJobDetails('${job.id}')" title="View Details">
                <i class="fas fa-eye"></i> Details
            </button>
        `);
        
        // Status-specific actions
        if (job.status === 'training' || job.status === 'preparing') {
            actions.push(`
                <button class="btn btn-sm btn-danger" onclick="progressTracker.cancelJob('${job.id}')" title="Cancel Job">
                    <i class="fas fa-stop"></i> Cancel
                </button>
            `);
        }
        
        if (job.status === 'failed' && job.can_resume) {
            actions.push(`
                <button class="btn btn-sm btn-primary" onclick="progressTracker.resumeJob('${job.id}')" title="Resume Job">
                    <i class="fas fa-play"></i> Resume
                </button>
            `);
        }
        
        if (job.status === 'completed') {
            actions.push(`
                <button class="btn btn-sm btn-secondary" onclick="progressTracker.downloadModel('${job.id}')" title="Download Model">
                    <i class="fas fa-download"></i> Download
                </button>
            `);
            
            actions.push(`
                <button class="btn btn-sm btn-primary" onclick="showCreateTestModal('${job.id}')" title="Test Model">
                    <i class="fas fa-vial"></i> Test
                </button>
            `);
        }
        
        return actions.join('');
    }

    setupJobCardEvents(card, job) {
        // Click to show details
        card.addEventListener('click', (e) => {
            // Don't trigger if clicking on buttons
            if (e.target.closest('.btn')) return;
            
            this.showJobDetails(job.id);
        });

        // Add hover effects for real-time updates
        card.addEventListener('mouseenter', () => {
            if (job.status === 'training' || job.status === 'preparing') {
                this.startRealTimeUpdates(job.id);
            }
        });

        card.addEventListener('mouseleave', () => {
            this.stopRealTimeUpdates(job.id);
        });
    }

    // Job actions
    async cancelJob(jobId) {
        if (!confirm('Are you sure you want to cancel this training job?')) {
            return;
        }

        try {
            const response = await fetch(`${this.options.cancelJobUrl}/${jobId}`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': this.getCSRFToken()
                }
            });

            if (!response.ok) throw new Error('Failed to cancel job');
            
            const result = await response.json();
            this.showSuccess('Training job cancellation initiated');
            
            // Update job status immediately
            const job = this.jobs.get(jobId);
            if (job) {
                job.status = 'cancelling';
                this.renderJobs();
            }
            
        } catch (error) {
            console.error('Error cancelling job:', error);
            this.showError('Failed to cancel training job. Please try again.');
        }
    }

    async resumeJob(jobId) {
        try {
            const response = await fetch(`${this.options.resumeJobUrl}/${jobId}`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': this.getCSRFToken()
                }
            });

            if (!response.ok) throw new Error('Failed to resume job');
            
            const result = await response.json();
            this.showSuccess('Training job resumed successfully');
            
            // Update job status immediately
            const job = this.jobs.get(jobId);
            if (job) {
                job.status = 'preparing';
                job.resume_count = (job.resume_count || 0) + 1;
                this.renderJobs();
            }
            
        } catch (error) {
            console.error('Error resuming job:', error);
            this.showError('Failed to resume training job. Please try again.');
        }
    }

    async showJobDetails(jobId) {
        this.selectedJobId = jobId;
        const job = this.jobs.get(jobId);
        
        if (!job) return;

        // Update panel title
        this.container.querySelector('#panel-title').textContent = `${job.name} - Details`;
        
        // Show loading in panel
        this.panelContent.innerHTML = `
            <div class="panel-loading">
                <div class="spinner"></div>
                <p>Loading job details...</p>
            </div>
        `;
        
        this.detailsPanel.style.display = 'block';
        
        try {
            await this.loadJobDetails(jobId);
        } catch (error) {
            this.panelContent.innerHTML = `
                <div class="panel-error">
                    <i class="fas fa-exclamation-triangle"></i>
                    <p>Failed to load job details</p>
                </div>
            `;
        }
    }

    async loadJobDetails(jobId) {
        try {
            const [detailsResponse, metricsResponse, logsResponse] = await Promise.all([
                fetch(`${this.options.jobDetailsUrl}/${jobId}`),
                fetch(`${this.options.metricsUrl}/${jobId}`),
                fetch(`${this.options.logsUrl}/${jobId}?limit=${this.options.maxLogLines}`)
            ]);

            const details = await detailsResponse.json();
            const metrics = await metricsResponse.json();
            const logs = await logsResponse.json();

            this.renderJobDetails(details, metrics, logs);
            
        } catch (error) {
            console.error('Error loading job details:', error);
            throw error;
        }
    }    rende
rJobDetails(details, metrics, logs) {
        this. }}
     ;
              `span>
    s)}</tuob.staText(jtusis.getStat">${th-texatus"stan class=         <sp    /i>
   us)}"><.statn(jobetStatusIco"${this.g<i class=                L = `
HTMement.innersEl       status)}`;
     job.status(StatusClas${this.getatus me = `job-stssNaent.clastatusElem            t) {
usElemen   if (status');
     stat'.job-elector(card.querySement = nst statusEl     coatus
   date st      // Up}

          >', '');
lace('</div).rep">', ''s-gridetrics="m<div claslace('ep).retrics(jobenderJobM this.r.innerHTML =idsGr      metric      {
 icsGrid) if (metr      );
 rics-grid'r('.meterySelectod.qucarsGrid = ricnst met    corics
    ate met Upd     //   }

   
     (job);ogressText.getPrt = thistextContenessText.      progr`;
      gress}% `${pro =tContententage.texogressPerc  pr  
        }%`; `${progressdth =le.wiessFill.sty    progr     
   s(job);ogrescalculatePrs. thirogress =nst p       co     Text) {
 && progressntagercesPe && progresssFillrogre if (p 
              ');
gress-textor('.prouerySelectt = card.qexsTonst progres       centage');
 rc-peprogress'.erySelector(qu card. =ssPercentageonst progre       c);
 ogress-fill'prctor('.rd.querySelessFill = ca progreonst    c    ss bar
te progre   // Updarn;

     job) retu!card || ! (        if
        
Id);et(job.g.jobsb = this  const jo      Id}"]`);
="${jobjob-idor(`[data-lectySeer.querontain this.cconst card =        {
 d(jobId)arpdateJobC  }

    u }
     );
    te(jobIdections.deleonnveCactiis.    th      
  rval);rval(interInteclea           
 l) {erva if (int);
       jobIdections.get(nn.activeCo thisl =interva     const 
   ) {es(jobIdmeUpdatstopRealTi   

 
    }l);ateInterva upds.set(jobId,nnectionactiveCo this.

       ctive jobsd for aconsevery pdate e // U00);      }, 10  }
           error);
  ting job:',r updarror('Erro   console.e           ) {
  error catch (        }      }
              
       }      
       ard(jobId);JobC this.update                  ta);
     , jobDaJobsting.assign(exict Obje                   {
     ingJob) if (exist                d);
   bIbs.get(jo.joisb = thxistingJonst e         co           .json();
t response= awaijobData    const                  k) {
onse.o    if (resp        d}`);
    l}/${jobIilsUrbDeta.options.johis`${t fetch( awaitonse =onst resp          c      ry {
   t     > {
    nc () =rval(asyal = setIntentervnst updateI
        co
rn;bId)) retu.has(joonsConnectiive(this.act
        if  {ates(jobId)RealTimeUpd
    starttesl-time upda
    // Rea
    }
 }     sh';
  > Auto Refre"></ifa-pauses lass="faHTML = '<i c').innerresh-btnle-auto-ref#toggelector('er.querySis.contain          thtrue;
   = Refreshons.autoopti   this.    sh();
     AutoRefrethis.start       
     else { }        fresh';
i> Auto Re"></plays="fas fa-L = '<i clasTMtn').innerHh-brefresoggle-auto-#tSelector('r.queryis.containe         thfalse;
   sh = freoReoptions.aut       this.  sh();
   topAutoRefre      this.s
      efresh) {ions.autoRpt if (this.o     
   {()eAutoRefreshtoggl}

    
    obs();enderJis.r   th 
           ;
         })== view);
taset.view =n.dative', bt'acgle(t.tog.classLisbtn           {
  Each(btn =>n').forw-bt'.vieSelectorAll(r.querycontaine  this.tes
      button state   // Upda  
      
      ew; vientView =curr this.
       w) {(vie  switchView   }

  ters();
 pplyFilthis.a        
';unt-downrt-amoas fa-so' : 'fnt-upfa-sort-amouc' ? 'fas 'as=== ortOrder ters.s.filhislassName = t  btn.c      r-btn i');
deor('#sort-orctquerySeleer.s.contain = thi btn const      : 'asc';
 '  'desc'asc' ? === .sortOrdererslt= this.firder rtOs.filters.sothi  ) {
      eSortOrder(
    toggl   }
s();
 erJobhis.rend
        tFilters() {   apply
    }

 turn jobs;  re

        });on;
      omparisn : cpariso-com' ? r === 'desc.sortOrdes.filters return thi         

  on = 1;risbVal) compa (aVal >       if      -1;
mparison = l) co (aVal < bVa          if   0;
rison = let compa    

                 };
  owerCase()oLVal.t    bVal = b     );
       e(werCasl.toLoal = aVa aV               tring') {
== 'speof aVal =  if (ty     
             }
(b);
    gresslculatePros.cathi bVal =            
    s(a);ateProgresul = this.calc       aVal    
     progress') {By === 'rs.sort (this.filte if      

     By];rs.sortb[this.filteVal =  let b          By];
 rt.filters.soisthaVal = a[ let          {
   => a, b)t((sors. job
       ly sortingpp       // A   }

   tus);
   staters.fil=== this.tus => job.staer(job  = jobs.filt        jobs  'all') {
  =  !=ters.status (this.fil ifr
        filteply status   // Ap
     ));
jobs.values(from(this.rray. Alet jobs =    {
     teredJobs()
    getFilmanagementiew tering and v // Fil }

    null;
   ctedJobId =s.sele thi      none';
  'le.display =sPanel.stythis.detail        l() {
ailsPaneet
    hideD
    }
oke();    ctx.str
        });
     }
    ;
       lineTo(x, y)ctx.                se {
    } el         y);
veTo(x,      ctx.mo
          === 0) { (index      if        
           e) * 170;
Val) / rang minue -190 - ((valst y =       con 10;
      80 +1)) * 3length - es.x / (valu (indeonst x =          c{
  => ex) lue, indach((va values.forE
       inPath();
beg  ctx.     2;
  = ineWidthtx.l;
        cle = colortx.strokeSty  c;

      nVal || 1miVal -  max = const range       .values);
 Math.min(..inVal =st m      conlues);
  .max(...vaVal = Mathst max      conn;

  ur ret0)gth === (values.len
        if ned);!== undefi(v => v ]).filteretric> d[m =ata.map(ds = dt value       cons
  {ric, color)data, mettx, eChart(cmpleLin  drawSi    }

   }
     4');
  ', '#ef444tory, 'lossart(ctx, hispleLineChSimis.draw       th) {
     efined)oss !== undome(h => h.l.s (history if  loss
     or ne chart f simple li     // Draw      
   t('2d');
  ntexvas.getCo ctx = canonst

        cnvas);(ca.appendChildnerchartContai      00;
  eight = 2anvas.h    c    400;
 h =idtnvas.w     ca;
   nt('canvas')eElemeument.creatnvas = docst ca        con;

) returnrtContainer (!cha   if    
 bId}`);t-${joharrics-centById(`metetElem.gumentainer = doc chartCont     constlar
   js or simihart. C'd usel app, youin a reaon - ntatit implemearmple ch Si//        y) {
obId, historart(jsChderMetric
    ren  }
in('');
  ems.joreturn it

        
        }         `);   v>
      </di        pan>
  ixed(1)}%</spu_usage.toF{health.gvalue">$lth-"heaan class=sp    <         
       >   </div             
    >iv"></du_usage}% ${health.gpidth:" style="whealth-fillass="  <div cl                     ">
 health-bar class="iv      <d       >
       sage</spanl">GPU U"health-labess=n cla   <spa            m">
     "health-itediv class=  <           h(`
   pusems.it         {
    d)ineundefu_usage !== f (health.gp   i  
       }
      );
       `          
 >div   </            span>
 }%</xed(1)usage.toFiemory_lth.mlue">${hea"health-va class=     <span                   </div>
     
           iv>age}%"></dmory_usalth.medth: ${he"wil" style="health-fil<div class=                        >
health-bar"lass="div c      <            span>
  ry Usage</moel">Melth-lab"heaspan class= <            ">
       alth-item"helass=    <div c          `
  push(    items.      {
  efined) == undmory_usage !(health.meif                
        }
      `);
         </div>
          
    %</span>)}Fixed(1usage.to{health.cpu_alue">$th-vhealass=" cl  <span                </div>
                   div>
   usage}%"></pu_h.cealtidth: ${h"w" style=ealth-filllass="h      <div c                 
 ">ars="health-b clas  <div              
    ge</span> UsaPUh-label">Clts="hea clas <span                 
  -item">ealth"hiv class=        <d`
        ush(  items.p      ned) {
    undefi==  !pu_usagelth.ceaif (h
              = [];
   nst items      co) {
  ltheahMetrics(hderHealtren  
      }
       `;
</div>
    }
         '')in(      `).jo  >
            </div             iv>
   alue)}</due(key, vtMetricValthis.formavalue">${="metric-class <div                        
ey)}</div>cKey(kMetriis.format${thc-label">metris="las    <div c                   card">
 "metric-class=iv         <d          `
  e]) => , valut).map(([keytries(current.en ${Objec            grid">
   s-etricurrent-m"c <div class=           
    return `    ;

''return nt) (!curre if 
       rent) {etrics(currentMerCur rend

      }      }
 
  cs.history);etrid, metails.iricsChart(drenderMet     this.       gth > 0) {
story.lenrics.hi metistory &&ics.h  if (metr  lable
    s avait if data irics charRender met//              `;

>
   iv         </d   ` : ''}
                 </div>
                   iv>
      </d           
       n>butto         </                    Refresh
alt"></i>sync-as fa- class="f  <i                        ">
      ls.id}')gs('${detaifreshLoacker.reprogressTr" onclick="ndaryco btn-sesmtn-"btn bclass=on tt    <bu                   
     n>  </butto                      s
    Logad Full > Downlownload"></i="fas fa-do<i class                               ">
 ils.id}')('${detaLogsr.downloadrackeessTgr="proy" onclick-secondartnn btn-sm bbt class="utton  <b               
           ">gs-actionsclass="lo<div                    v>
        </di                    }
 ('')     `).join                
             </div>                    >
      pan</sge}essa">${log.mage-messs="logan clas   <sp                             
    </span>level}{log.-level">$"log<span class=                                n>
    stamp)}</spae(log.timeTimhis.format">${tg-timestamplo="ss<span cla                             >
       ase()}"oLowerC.level.t ${logg-entrys="lo   <div clas                        `
      (log =>apogs.logs.m        ${l                   
 iner">gs-contaass="lov cldi        <                gs</h5>
ent Lo-title">Recss="sectioncla<h5                        ">
 ls-sectionlass="detai c    <div         `
       ngth > 0 ? leogs..l logss.logs &&log   ${          
   Logs -->ent - Rec    <!-      
      }
: ''         `   v>
            </di          >
     </div                    ics)}
  metrs.health_detailthMetrics(enderHeal${this.r                      
      th-grid">"heals=lasiv c      <d           >
       us</h5tat">Health Stion-titleass="sec   <h5 cl                   n">
  sectioetails-iv class="d   <d            ? `
     trics health_meails.det     ${        
    Status --> Health   <!--             ''}

    ` :       
      v>      </di            </div>
                        ent)}
  .currcs(metricsrirrentMeterCus.rend   ${thi                  
       >metrics"s="current-<div clas                        </div>
                 
       d here -->enderet will be r- Char         <!-                
   s.id}">${detailt-etrics-char id="mhart"rics-cet"m<div class=                   >
     rics</h5Metng Trainititle">on-s="secti   <h5 clas                     
ection">ails-slass="det    <div c             `
     ? > 0ory.lengthics.hist&& metrory st.hietrics       ${m       cs -->
  Metrig Trainin  <!--             }

     ` : ''           >
  /div      <            
    </div>                     in('')}
     `).jo                  
           </div>                         n>
  spalue}</alue">${vaconfig-v="pan class         <s                           
n>key)}</spaKey(ormatConfig">${this.ffig-labels="con  <span clas                                 
 em">itnfig-s="coasdiv cl          <                      lue]) => `
ap(([key, vals.config).mies(detai.entrct  ${Obje                  ">
        gridconfig-lass="    <div c             h5>
       uration</Confign-title">io"sect<h5 class=                       ection">
 ="details-s <div class               ? `
     tails.config  ${de          
    -->tion iguraaining Conf-- Tr  <!          div>

         </         div>
    </                  
   ` : ''}                   
       </div>                >
       )}</spanontails.duratiDuration(de.format{thisalue">$="detail-v <span class                             span>
  tion</">Duraail-labelass="detpan cl<s                           
     item">tail-ss="de   <div cla                      `
    .duration ?   ${details                  }
    : '' `               v>
              </di              n>
        ed_at)}</spacomplete(details.rmatDateTim">${this.foail-valuess="det   <span cla                      an>
       /spd<letelabel">Comptail-class="de   <span                             m">
 "detail-itelass=iv c       <d                   at ? `
  .completed_${details                   }
          ` : ''               div>
             </              
     an>ted_at)}</sptardetails.seTime(matDatis.forthlue">${val-detaiss=" <span cla                       
        n>arted</spal-label">St="detaiclass    <span                       
      -item">detaildiv class="    <                
         `ed_at ?s.start${detail                     
    </div>                       }</span>
_at)createdime(details.rmatDateTthis.fo">${aluel-vs="detai <span clas                    an>
       ated</spCrel-label">aiass="det<span cl                            tem">
detail-idiv class=" <                     div>
            </           /span>
   own'}<Unkne || '_namls.dataset{detaiue">$il-val"detalass=n c<spa                 
           >spanataset</">Dlabe="detail-l <span class                          item">
 "detail-v class=       <di             v>
     </di                       pan>
n'}</snknow_name || 'Uails.modelue">${detetail-vals="dn clas <spa                 
          an>">Model</spil-labelclass="detaan    <sp                         ">
itemil-"detaclass=v <di                  >
        </div                 pan>
           </s           
               </span>                     s)}
       s.statuailt(detetStatusTexs.g      ${thi                           i>
   s)}"></atutails.sttatusIcon(de{this.getS"$lass=i c       <                             )}">
usls.statClass(detai.getStatus{thisb-status $n class="jo     <spa                          value">
 detail-ass="n cl      <spa                n>
      paatus</sel">Stil-labs="deta clas     <span               
        ">-itemail class="det <div                       >
id"ils-grs="deta clas       <div             
iew</h5>verve">Otitls="section-clas <h5              n">
      ctioetails-se"div class=     <d          -->
 Overview <!-- Job                 ils">
deta"job-lass= c   <div
         erHTML = `tent.innonelCpan    // U
tility methods
    calculateProgress(job) {
        if (job.status === 'completed') return 100;
        if (job.status === 'failed' || job.status === 'cancelled') return 0;
        
        if (job.metrics && job.metrics.current_epoch && job.metrics.total_epochs) {
            return Math.round((job.metrics.current_epoch / job.metrics.total_epochs) * 100);
        }
        
        // Default progress based on status
        const statusProgress = {
            'pending': 0,
            'preparing': 10,
            'training': 50,
            'evaluating': 90,
            'completed': 100
        };
        
        return statusProgress[job.status] || 0;
    }

    estimateTimeRemaining(job) {
        if (!job.metrics || !job.started_at || job.status !== 'training') return null;
        
        const startTime = new Date(job.started_at);
        const now = new Date();
        const elapsed = now - startTime;
        
        const progress = this.calculateProgress(job);
        if (progress <= 0) return null;
        
        const totalEstimated = (elapsed / progress) * 100;
        const remaining = totalEstimated - elapsed;
        
        if (remaining <= 0) return null;
        
        return this.formatDuration(remaining);
    }

    getProgressText(job) {
        if (job.metrics && job.metrics.current_epoch && job.metrics.total_epochs) {
            return `Epoch ${job.metrics.current_epoch}/${job.metrics.total_epochs}`;
        }
        
        const statusTexts = {
            'pending': 'Waiting to start',
            'preparing': 'Preparing data',
            'training': 'Training in progress',
            'evaluating': 'Evaluating model',
            'completed': 'Training completed',
            'failed': 'Training failed',
            'cancelled': 'Training cancelled'
        };
        
        return statusTexts[job.status] || 'Unknown status';
    }

    getStatusClass(status) {
        const statusClasses = {
            'pending': 'status-pending',
            'preparing': 'status-preparing',
            'training': 'status-training',
            'evaluating': 'status-evaluating',
            'completed': 'status-completed',
            'failed': 'status-failed',
            'cancelled': 'status-cancelled'
        };
        return statusClasses[status] || 'status-unknown';
    }

    getStatusIcon(status) {
        const statusIcons = {
            'pending': 'fas fa-clock',
            'preparing': 'fas fa-cog fa-spin',
            'training': 'fas fa-brain fa-pulse',
            'evaluating': 'fas fa-chart-line',
            'completed': 'fas fa-check-circle',
            'failed': 'fas fa-exclamation-circle',
            'cancelled': 'fas fa-ban'
        };
        return statusIcons[status] || 'fas fa-question-circle';
    }

    getStatusText(status) {
        const statusTexts = {
            'pending': 'Pending',
            'preparing': 'Preparing',
            'training': 'Training',
            'evaluating': 'Evaluating',
            'completed': 'Completed',
            'failed': 'Failed',
            'cancelled': 'Cancelled'
        };
        return statusTexts[status] || 'Unknown';
    }

    formatDate(dateString) {
        return new Date(dateString).toLocaleDateString();
    }

    formatDateTime(dateString) {
        return new Date(dateString).toLocaleString();
    }

    formatTime(dateString) {
        return new Date(dateString).toLocaleTimeString();
    }

    formatDuration(milliseconds) {
        const seconds = Math.floor(milliseconds / 1000);
        const minutes = Math.floor(seconds / 60);
        const hours = Math.floor(minutes / 60);
        const days = Math.floor(hours / 24);

        if (days > 0) return `${days}d ${hours % 24}h`;
        if (hours > 0) return `${hours}h ${minutes % 60}m`;
        if (minutes > 0) return `${minutes}m ${seconds % 60}s`;
        return `${seconds}s`;
    }

    formatConfigKey(key) {
        return key.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase());
    }

    formatMetricKey(key) {
        const keyMap = {
            'loss': 'Loss',
            'accuracy': 'Accuracy',
            'learning_rate': 'Learning Rate',
            'current_epoch': 'Current Epoch',
            'total_epochs': 'Total Epochs'
        };
        return keyMap[key] || this.formatConfigKey(key);
    }

    formatMetricValue(key, value) {
        if (key === 'accuracy') {
            return `${(value * 100).toFixed(2)}%`;
        }
        if (key === 'learning_rate') {
            return value.toExponential(3);
        }
        if (typeof value === 'number') {
            return value.toFixed(4);
        }
        return value;
    }

    updateStats() {
        const jobs = Array.from(this.jobs.values());
        const totalJobs = jobs.length;
        const runningJobs = jobs.filter(job => 
            job.status === 'training' || job.status === 'preparing' || job.status === 'evaluating'
        ).length;
        const completedJobs = jobs.filter(job => job.status === 'completed').length;
        const failedJobs = jobs.filter(job => job.status === 'failed').length;

        this.container.querySelector('#total-jobs').textContent = totalJobs;
        this.container.querySelector('#running-jobs').textContent = runningJobs;
        this.container.querySelector('#completed-jobs').textContent = completedJobs;
        this.container.querySelector('#failed-jobs').textContent = failedJobs;
    }

    showLoading() {
        this.loadingState.style.display = 'block';
        this.jobsGrid.style.display = 'none';
        this.emptyState.style.display = 'none';
    }

    hideLoading() {
        this.loadingState.style.display = 'none';
        this.jobsGrid.style.display = 'grid';
    }

    showEmptyState() {
        this.emptyState.style.display = 'block';
        this.jobsGrid.style.display = 'none';
    }

    hideEmptyState() {
        this.emptyState.style.display = 'none';
        this.jobsGrid.style.display = 'grid';
    }

    showSuccess(message) {
        if (window.UIComponents) {
            window.UIComponents.showNotification(message, 'success');
        } else {
            console.log('Success:', message);
        }
    }

    showError(message) {
        if (window.UIComponents) {
            window.UIComponents.showNotification(message, 'error');
        } else {
            console.error('Error:', message);
        }
    }

    getCSRFToken() {
        return document.querySelector('meta[name="csrf-token"]')?.getAttribute('content') || '';
    }

    startAutoRefresh() {
        this.refreshTimer = setInterval(() => {
            if (!this.isLoading) {
                this.loadJobs();
            }
        }, this.options.refreshInterval);
    }

    stopAutoRefresh() {
        if (this.refreshTimer) {
            clearInterval(this.refreshTimer);
            this.refreshTimer = null;
        }
        
        // Stop all real-time updates
        for (const [jobId] of this.activeConnections) {
            this.stopRealTimeUpdates(jobId);
        }
    }

    destroy() {
        this.stopAutoRefresh();
    }

    // Export functionality
    async exportLogs() {
        try {
            const jobs = Array.from(this.jobs.values());
            const selectedJobs = jobs.filter(job => job.status === 'completed' || job.status === 'failed');
            
            if (selectedJobs.length === 0) {
                this.showError('No completed or failed jobs to export logs for');
                return;
            }

            const logsData = await Promise.all(
                selectedJobs.map(async job => {
                    try {
                        const response = await fetch(`${this.options.logsUrl}/${job.id}`);
                        const logs = await response.json();
                        return {
                            jobId: job.id,
                            jobName: job.name,
                            status: job.status,
                            logs: logs.logs || []
                        };
                    } catch (error) {
                        return {
                            jobId: job.id,
                            jobName: job.name,
                            status: job.status,
                            logs: [],
                            error: error.message
                        };
                    }
                })
            );

            // Create and download file
            const blob = new Blob([JSON.stringify(logsData, null, 2)], { type: 'application/json' });
            const url = URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.href = url;
            a.download = `training-logs-${new Date().toISOString().split('T')[0]}.json`;
            document.body.appendChild(a);
            a.click();
            document.body.removeChild(a);
            URL.revokeObjectURL(url);

            this.showSuccess('Training logs exported successfully');
            
        } catch (error) {
            console.error('Error exporting logs:', error);
            this.showError('Failed to export logs. Please try again.');
        }
    }

    async downloadLogs(jobId) {
        try {
            const response = await fetch(`${this.options.logsUrl}/${jobId}`);
            if (!response.ok) throw new Error('Failed to download logs');
            
            const logs = await response.json();
            const job = this.jobs.get(jobId);
            
            const blob = new Blob([JSON.stringify(logs, null, 2)], { type: 'application/json' });
            const url = URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.href = url;
            a.download = `${job?.name || jobId}-logs.json`;
            document.body.appendChild(a);
            a.click();
            document.body.removeChild(a);
            URL.revokeObjectURL(url);

            this.showSuccess('Job logs downloaded successfully');
            
        } catch (error) {
            console.error('Error downloading logs:', error);
            this.showError('Failed to download logs. Please try again.');
        }
    }

    async refreshLogs(jobId) {
        if (this.selectedJobId === jobId) {
            await this.loadJobDetails(jobId);
        }
    }

    async downloadModel(jobId) {
        try {
            const job = this.jobs.get(jobId);
            if (!job || job.status !== 'completed') {
                this.showError('Model is not available for download');
                return;
            }

            // Trigger download - this would typically be handled by the backend
            window.open(`/api/llm-training/download-model/${jobId}`, '_blank');
            this.showSuccess('Model download initiated');
            
        } catch (error) {
            console.error('Error downloading model:', error);
            this.showError('Failed to download model. Please try again.');
        }
    }
}

// Global registration
if (typeof window !== 'undefined') {
    window.EnhancedProgressTracker = EnhancedProgressTracker;
} 
   // Utility methods
    calculateProgress(job) {
        if (job.status === 'completed') return 100;
        if (job.status === 'failed' || job.status === 'cancelled') return 0;
        
        if (job.metrics && job.metrics.current_epoch && job.metrics.total_epochs) {
            return Math.round((job.metrics.current_epoch / job.metrics.total_epochs) * 100);
        }
        
        // Fallback progress based on status
        const statusProgress = {
            'pending': 0,
            'preparing': 10,
            'training': 50,
            'evaluating': 90,
            'completed': 100,
            'failed': 0,
            'cancelled': 0
        };
        
        return statusProgress[job.status] || 0;
    }

    estimateTimeRemaining(job) {
        if (!job.metrics || !job.started_at || job.status !== 'training') return null;
        
        const startTime = new Date(job.started_at);
        const now = new Date();
        const elapsed = now - startTime;
        
        const progress = this.calculateProgress(job);
        if (progress <= 0) return null;
        
        const totalEstimated = (elapsed / progress) * 100;
        const remaining = totalEstimated - elapsed;
        
        if (remaining <= 0) return null;
        
        return this.formatDuration(remaining);
    }

    getProgressText(job) {
        if (job.metrics && job.metrics.current_epoch && job.metrics.total_epochs) {
            return `Epoch ${job.metrics.current_epoch}/${job.metrics.total_epochs}`;
        }
        
        const statusTexts = {
            'pending': 'Waiting to start',
            'preparing': 'Preparing data',
            'training': 'Training in progress',
            'evaluating': 'Evaluating model',
            'completed': 'Training completed',
            'failed': 'Training failed',
            'cancelled': 'Training cancelled'
        };
        
        return statusTexts[job.status] || 'Unknown status';
    }

    getStatusClass(status) {
        const statusClasses = {
            'pending': 'status-pending',
            'preparing': 'status-preparing',
            'training': 'status-training',
            'evaluating': 'status-evaluating',
            'completed': 'status-completed',
            'failed': 'status-failed',
            'cancelled': 'status-cancelled'
        };
        return statusClasses[status] || 'status-unknown';
    }

    getStatusIcon(status) {
        const statusIcons = {
            'pending': 'fas fa-clock',
            'preparing': 'fas fa-cog fa-spin',
            'training': 'fas fa-brain fa-pulse',
            'evaluating': 'fas fa-chart-line',
            'completed': 'fas fa-check-circle',
            'failed': 'fas fa-exclamation-circle',
            'cancelled': 'fas fa-ban'
        };
        return statusIcons[status] || 'fas fa-question-circle';
    }

    getStatusText(status) {
        const statusTexts = {
            'pending': 'Pending',
            'preparing': 'Preparing',
            'training': 'Training',
            'evaluating': 'Evaluating',
            'completed': 'Completed',
            'failed': 'Failed',
            'cancelled': 'Cancelled'
        };
        return statusTexts[status] || 'Unknown';
    }

    formatDate(dateString) {
        return new Date(dateString).toLocaleDateString();
    }

    formatDateTime(dateString) {
        return new Date(dateString).toLocaleString();
    }

    formatTime(dateString) {
        return new Date(dateString).toLocaleTimeString();
    }

    formatDuration(milliseconds) {
        const seconds = Math.floor(milliseconds / 1000);
        const minutes = Math.floor(seconds / 60);
        const hours = Math.floor(minutes / 60);
        const days = Math.floor(hours / 24);

        if (days > 0) return `${days}d ${hours % 24}h`;
        if (hours > 0) return `${hours}h ${minutes % 60}m`;
        if (minutes > 0) return `${minutes}m ${seconds % 60}s`;
        return `${seconds}s`;
    }

    formatConfigKey(key) {
        return key.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase());
    }

    formatMetricKey(key) {
        const keyMappings = {
            'loss': 'Loss',
            'accuracy': 'Accuracy',
            'learning_rate': 'Learning Rate',
            'current_epoch': 'Current Epoch',
            'total_epochs': 'Total Epochs'
        };
        return keyMappings[key] || this.formatConfigKey(key);
    }

    formatMetricValue(key, value) {
        if (key === 'accuracy') {
            return `${(value * 100).toFixed(2)}%`;
        }
        if (key === 'learning_rate') {
            return value.toExponential(3);
        }
        if (typeof value === 'number') {
            return value.toFixed(4);
        }
        return value;
    }

    updateStats() {
        const jobs = Array.from(this.jobs.values());
        const totalJobs = jobs.length;
        const runningJobs = jobs.filter(job => 
            job.status === 'training' || job.status === 'preparing' || job.status === 'evaluating'
        ).length;
        const completedJobs = jobs.filter(job => job.status === 'completed').length;
        const failedJobs = jobs.filter(job => job.status === 'failed').length;

        this.container.querySelector('#total-jobs').textContent = totalJobs;
        this.container.querySelector('#running-jobs').textContent = runningJobs;
        this.container.querySelector('#completed-jobs').textContent = completedJobs;
        this.container.querySelector('#failed-jobs').textContent = failedJobs;
    }

    showLoading() {
        this.loadingState.style.display = 'block';
        this.jobsGrid.style.display = 'none';
        this.emptyState.style.display = 'none';
    }

    hideLoading() {
        this.loadingState.style.display = 'none';
        this.jobsGrid.style.display = 'grid';
    }

    showEmptyState() {
        this.emptyState.style.display = 'block';
        this.jobsGrid.style.display = 'none';
    }

    hideEmptyState() {
        this.emptyState.style.display = 'none';
        this.jobsGrid.style.display = 'grid';
    }

    showSuccess(message) {
        if (window.UIComponents) {
            window.UIComponents.showNotification(message, 'success');
        } else {
            console.log('Success:', message);
        }
    }

    showError(message) {
        if (window.UIComponents) {
            window.UIComponents.showNotification(message, 'error');
        } else {
            console.error('Error:', message);
        }
    }

    getCSRFToken() {
        return document.querySelector('meta[name="csrf-token"]')?.getAttribute('content') || '';
    }

    startAutoRefresh() {
        this.refreshTimer = setInterval(() => {
            if (!this.isLoading) {
                this.loadJobs();
            }
        }, this.options.refreshInterval);
    }

    stopAutoRefresh() {
        if (this.refreshTimer) {
            clearInterval(this.refreshTimer);
            this.refreshTimer = null;
        }
    }

    // Additional utility methods
    async exportLogs() {
        try {
            const jobs = Array.from(this.jobs.values());
            const completedJobs = jobs.filter(job => job.status === 'completed' || job.status === 'failed');
            
            if (completedJobs.length === 0) {
                this.showError('No completed or failed jobs to export logs from');
                return;
            }

            // Create a simple CSV export
            let csvContent = 'Job Name,Status,Created,Completed,Duration,Error\n';
            
            completedJobs.forEach(job => {
                const duration = job.completed_at ? 
                    new Date(job.completed_at) - new Date(job.created_at) : '';
                csvContent += `"${job.name}","${job.status}","${job.created_at}","${job.completed_at || ''}","${this.formatDuration(duration)}","${job.error_message || ''}"\n`;
            });

            // Download the CSV
            const blob = new Blob([csvContent], { type: 'text/csv' });
            const url = window.URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.href = url;
            a.download = `training-jobs-export-${new Date().toISOString().split('T')[0]}.csv`;
            document.body.appendChild(a);
            a.click();
            document.body.removeChild(a);
            window.URL.revokeObjectURL(url);

            this.showSuccess('Training jobs exported successfully');
            
        } catch (error) {
            console.error('Error exporting logs:', error);
            this.showError('Failed to export logs');
        }
    }

    async downloadLogs(jobId) {
        try {
            const response = await fetch(`${this.options.logsUrl}/${jobId}?full=true`);
            if (!response.ok) throw new Error('Failed to download logs');
            
            const logs = await response.text();
            const blob = new Blob([logs], { type: 'text/plain' });
            const url = window.URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.href = url;
            a.download = `training-job-${jobId}-logs.txt`;
            document.body.appendChild(a);
            a.click();
            document.body.removeChild(a);
            window.URL.revokeObjectURL(url);

            this.showSuccess('Logs downloaded successfully');
            
        } catch (error) {
            console.error('Error downloading logs:', error);
            this.showError('Failed to download logs');
        }
    }

    async refreshLogs(jobId) {
        if (this.selectedJobId === jobId) {
            await this.loadJobDetails(jobId);
        }
    }

    async downloadModel(jobId) {
        try {
            const response = await fetch(`/api/llm-training/download-model/${jobId}`);
            if (!response.ok) throw new Error('Failed to download model');
            
            const blob = await response.blob();
            const url = window.URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.href = url;
            a.download = `trained-model-${jobId}.zip`;
            document.body.appendChild(a);
            a.click();
            document.body.removeChild(a);
            window.URL.revokeObjectURL(url);

            this.showSuccess('Model download started');
            
        } catch (error) {
            console.error('Error downloading model:', error);
            this.showError('Failed to download model');
        }
    }

    destroy() {
        this.stopAutoRefresh();
        
        // Clear all real-time update intervals
        for (const [jobId, interval] of this.activeConnections) {
            clearInterval(interval);
        }
        this.activeConnections.clear();
    }
}

// Global registration
if (typeof window !== 'undefined') {
    window.EnhancedProgressTracker = EnhancedProgressTracker;
}