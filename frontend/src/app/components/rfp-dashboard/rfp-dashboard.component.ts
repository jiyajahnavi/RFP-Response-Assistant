import { Component, OnInit, inject } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { ApiService } from '../../services/api.service';
import { RFP, AnalyticsData } from '../../models/rfp.model';
import { RouterLink } from '@angular/router';

@Component({
  selector: 'app-rfp-dashboard',
  standalone: true,
  imports: [CommonModule, FormsModule, RouterLink],
  template: `
    <div class="sketch-dashboard">
      <!-- Top Stats KPI Row -->
      <section class="sketch-kpi-grid">
        <div class="sketch-card kpi-card rotate-neg">
          <div class="sketch-tape"></div>
          <div class="kpi-icon-box yellow">📋</div>
          <div class="kpi-info">
            <span class="kpi-label">Active RFPs</span>
            <span class="kpi-val">{{ analytics?.total_rfps ?? rfps.length }}</span>
          </div>
        </div>

        <div class="sketch-card kpi-card rotate-pos">
          <div class="sketch-tape"></div>
          <div class="kpi-icon-box blue">❓</div>
          <div class="kpi-info">
            <span class="kpi-label">Total Questions</span>
            <span class="kpi-val">{{ analytics?.total_questions ?? 0 }}</span>
          </div>
        </div>

        <div class="sketch-card kpi-card rotate-neg">
          <div class="sketch-tape"></div>
          <div class="kpi-icon-box green">✅</div>
          <div class="kpi-info">
            <span class="kpi-label">Approved Responses</span>
            <span class="kpi-val">{{ analytics?.total_approved_responses ?? 0 }}</span>
          </div>
        </div>

        <div class="sketch-card kpi-card rotate-pos">
          <div class="sketch-tape"></div>
          <div class="kpi-icon-box purple">📚</div>
          <div class="kpi-info">
            <span class="kpi-label">Knowledge Q&As</span>
            <span class="kpi-val">{{ analytics?.total_library_entries ?? 0 }}</span>
          </div>
        </div>
      </section>

      <!-- Action Toolbar -->
      <div class="sketch-toolbar">
        <div>
          <h2 class="sketch-title">Requests for Proposals (RFPs)</h2>
          <p class="sketch-subtitle">Manage enterprise proposals, questionnaire parsing, and response workflows</p>
        </div>
        <div class="actions">
          <button class="btn-sketch btn-sketch-primary" (click)="openCreateModal()">
            <span>✏️</span> + New RFP Proposal
          </button>
        </div>
      </div>

      <!-- RFP List Grid -->
      <div class="rfp-grid" *ngIf="!loading && rfps.length > 0; else noRfps">
        <div class="sketch-card rfp-sketch-card" *ngFor="let rfp of rfps; let i = index" [class.tilt-left]="i % 2 === 0" [class.tilt-right]="i % 2 !== 0">
          <div class="sketch-tape"></div>
          <div class="card-header">
            <div class="sketch-badge client-badge">👤 {{ rfp.CustomerName }}</div>
            <span class="sketch-badge" [ngClass]="getStatusBadgeClass(rfp.Status)">{{ rfp.Status }}</span>
          </div>

          <h3 class="rfp-title">{{ rfp.Title }}</h3>
          <p class="rfp-desc">{{ rfp.Description || 'No description notes provided for this proposal.' }}</p>

          <div class="sketch-meta-box">
            <div class="meta-line">
              <span>📅 <b>Due:</b> {{ rfp.DueDate ? (rfp.DueDate | date:'mediumDate') : 'No deadline set' }}</span>
            </div>
            <div class="meta-line">
              <span>🕒 <b>Created:</b> {{ rfp.CreatedDate | date:'shortDate' }}</span>
            </div>
          </div>

          <div class="card-footer">
            <a [routerLink]="['/rfp', rfp.RfpId]" class="btn-sketch btn-sketch-blue">
              Open Workbench ➔
            </a>
            <button class="btn-sketch btn-sketch-red delete-btn" (click)="deleteRFP(rfp.RfpId)" title="Delete RFP">
              🗑️
            </button>
          </div>
        </div>
      </div>

      <ng-template #noRfps>
        <div class="sketch-card empty-state" *ngIf="!loading">
          <div class="empty-icon">📂</div>
          <h3 class="sketch-title">No Proposals Found</h3>
          <p>Get started by creating your first Request for Proposal or importing a questionnaire.</p>
          <button class="btn-sketch btn-sketch-primary" (click)="openCreateModal()">Create Proposal</button>
        </div>
      </ng-template>

      <!-- Loading State -->
      <div class="loading-state" *ngIf="loading">
        <div class="sketch-spinner">✏️</div>
        <p>Loading proposal portfolio...</p>
      </div>

      <!-- Modal: Create RFP -->
      <div class="sketch-modal-backdrop" *ngIf="showCreateModal">
        <div class="sketch-card modal-card">
          <div class="modal-header">
            <h3 class="sketch-title">✏️ Create New RFP</h3>
            <button class="btn-sketch btn-sketch-secondary close-btn" (click)="showCreateModal = false">✕</button>
          </div>
          <form (ngSubmit)="submitCreateRFP()">
            <div class="form-group">
              <label>Proposal Title *</label>
              <input type="text" class="sketch-input" [(ngModel)]="newRfp.Title" name="title" required placeholder="e.g. Cloud Security & Infrastructure RFP" />
            </div>
            <div class="form-group">
              <label>Client / Customer Organization *</label>
              <input type="text" class="sketch-input" [(ngModel)]="newRfp.CustomerName" name="customer" required placeholder="e.g. Acme Health Corp" />
            </div>
            <div class="form-group">
              <label>Description & Scope</label>
              <textarea class="sketch-textarea" [(ngModel)]="newRfp.Description" name="desc" rows="3" placeholder="Overview of submission scope..."></textarea>
            </div>
            <div class="form-group">
              <label>Submission Due Date</label>
              <input type="date" class="sketch-input" [(ngModel)]="dueDateInput" name="dueDate" />
            </div>
            <div class="modal-footer">
              <button type="button" class="btn-sketch btn-sketch-secondary" (click)="showCreateModal = false">Cancel</button>
              <button type="submit" class="btn-sketch btn-sketch-primary" [disabled]="!newRfp.Title || !newRfp.CustomerName">Save & Launch</button>
            </div>
          </form>
        </div>
      </div>
    </div>
  `,
  styles: [`
    .sketch-dashboard {
      padding: 32px;
      max-width: 1400px;
      margin: 0 auto;
    }
    .sketch-kpi-grid {
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(240px, 1fr));
      gap: 24px;
      margin-bottom: 36px;
    }
    .kpi-card {
      display: flex;
      align-items: center;
      gap: 16px;
    }
    .rotate-neg { transform: rotate(-1deg); }
    .rotate-pos { transform: rotate(1deg); }
    .tilt-left { transform: rotate(-0.7deg); }
    .tilt-right { transform: rotate(0.7deg); }

    .kpi-icon-box {
      width: 50px;
      height: 50px;
      border: 2px solid var(--sketch-ink);
      border-radius: var(--sketch-border-radius-2);
      box-shadow: 2px 2px 0px var(--sketch-ink);
      display: flex;
      align-items: center;
      justify-content: center;
      font-size: 24px;
    }
    .kpi-icon-box.yellow { background: #fef08a; }
    .kpi-icon-box.blue { background: #bae6fd; }
    .kpi-icon-box.green { background: #bbf7d0; }
    .kpi-icon-box.purple { background: #e9d5ff; }

    .kpi-label {
      font-size: 14px;
      color: #64748b;
      font-weight: 600;
      display: block;
    }
    .kpi-val {
      font-family: 'Architects Daughter', cursive;
      font-size: 28px;
      font-weight: 700;
      color: var(--sketch-ink);
    }
    .sketch-toolbar {
      display: flex;
      justify-content: space-between;
      align-items: center;
      margin-bottom: 24px;
    }
    .sketch-title {
      font-size: 26px;
      margin-bottom: 4px;
    }
    .sketch-subtitle {
      font-size: 16px;
      color: #52525b;
    }
    .rfp-grid {
      display: grid;
      grid-template-columns: repeat(auto-fill, minmax(360px, 1fr));
      gap: 28px;
    }
    .rfp-sketch-card {
      display: flex;
      flex-direction: column;
      justify-content: space-between;
      min-height: 280px;
    }
    .card-header {
      display: flex;
      justify-content: space-between;
      align-items: center;
      margin-bottom: 12px;
    }
    .client-badge {
      background: #fef9c3;
      color: #854d0e;
    }
    .rfp-title {
      font-size: 20px;
      margin-bottom: 8px;
    }
    .rfp-desc {
      font-size: 15px;
      color: #52525b;
      flex: 1;
      margin-bottom: 16px;
      display: -webkit-box;
      -webkit-line-clamp: 2;
      -webkit-box-orient: vertical;
      overflow: hidden;
    }
    .sketch-meta-box {
      background: #fdfbf7;
      border: 1.5px dashed var(--sketch-ink);
      border-radius: var(--sketch-border-radius-3);
      padding: 8px 12px;
      margin-bottom: 16px;
      font-size: 14px;
    }
    .meta-line {
      margin-bottom: 4px;
    }
    .card-footer {
      display: flex;
      justify-content: space-between;
      align-items: center;
    }
    .delete-btn {
      padding: 6px 10px !important;
      font-size: 14px !important;
    }
    .empty-state {
      text-align: center;
      padding: 64px 20px;
    }
    .empty-icon {
      font-size: 48px;
      margin-bottom: 12px;
    }
    .loading-state {
      text-align: center;
      padding: 60px;
    }
    .sketch-spinner {
      font-size: 36px;
      animation: spin-pencil 1.5s infinite;
      display: inline-block;
      margin-bottom: 8px;
    }
    @keyframes spin-pencil {
      0% { transform: rotate(0deg); }
      50% { transform: rotate(45deg); }
      100% { transform: rotate(0deg); }
    }
    /* Modal */
    .sketch-modal-backdrop {
      position: fixed;
      top: 0; left: 0; right: 0; bottom: 0;
      background: rgba(33, 37, 41, 0.5);
      backdrop-filter: blur(2px);
      display: flex;
      align-items: center;
      justify-content: center;
      z-index: 1000;
    }
    .modal-card {
      width: 100%;
      max-width: 520px;
      background: #fffefb;
      transform: rotate(-0.5deg);
    }
    .modal-header {
      display: flex;
      justify-content: space-between;
      align-items: center;
      margin-bottom: 18px;
    }
    .close-btn {
      padding: 4px 10px !important;
    }
    .form-group {
      margin-bottom: 16px;
    }
    .form-group label {
      display: block;
      font-family: 'Architects Daughter', cursive;
      font-weight: 700;
      font-size: 15px;
      margin-bottom: 6px;
    }
    .modal-footer {
      display: flex;
      justify-content: flex-end;
      gap: 12px;
      margin-top: 24px;
    }
  `]
})
export class RfpDashboardComponent implements OnInit {
  private api = inject(ApiService);

  rfps: RFP[] = [];
  analytics: AnalyticsData | null = null;
  loading = true;
  showCreateModal = false;

  newRfp: Partial<RFP> = {
    Title: '',
    CustomerName: '',
    Description: '',
    Status: 'Draft',
  };
  dueDateInput = '';

  ngOnInit() {
    this.loadData();
  }

  loadData() {
    this.loading = true;
    this.api.getRFPs().subscribe({
      next: (rfps) => {
        this.rfps = rfps;
        this.loading = false;
      },
      error: (err) => {
        console.error('Failed to load RFPs', err);
        this.loading = false;
      }
    });

    this.api.getAnalytics().subscribe({
      next: (analytics) => {
        this.analytics = analytics;
      },
      error: (err) => console.warn('Could not load system analytics', err)
    });
  }

  getStatusBadgeClass(status: string): string {
    switch ((status || '').toLowerCase()) {
      case 'in progress': return 'badge-inreview';
      case 'in review': return 'badge-inreview';
      case 'completed': return 'badge-approved';
      default: return 'badge-draft';
    }
  }

  openCreateModal() {
    this.newRfp = { Title: '', CustomerName: '', Description: '', Status: 'Draft' };
    this.dueDateInput = '';
    this.showCreateModal = true;
  }

  submitCreateRFP() {
    if (!this.newRfp.Title?.trim() || !this.newRfp.CustomerName?.trim()) {
      return;
    }
    const payload: Partial<RFP> = {
      Title: this.newRfp.Title.trim(),
      CustomerName: this.newRfp.CustomerName.trim(),
      Description: this.newRfp.Description?.trim() || undefined,
      Status: this.newRfp.Status || 'Draft',
    };
    if (this.dueDateInput) {
      payload.DueDate = new Date(this.dueDateInput).toISOString();
    }
    this.api.createRFP(payload).subscribe({
      next: (created) => {
        this.showCreateModal = false;
        this.loadData();
      },
      error: (err) => {
        console.error('Error creating RFP:', err);
        alert('Error creating RFP: ' + (err.error?.message || err.message || 'Please check backend connection'));
      }
    });
  }

  deleteRFP(rfpId: number) {
    if (confirm('Are you sure you want to delete this RFP?')) {
      this.api.deleteRFP(rfpId).subscribe({
        next: () => this.loadData(),
        error: () => alert('Failed to delete RFP')
      });
    }
  }
}
