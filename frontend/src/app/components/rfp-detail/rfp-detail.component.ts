import { Component, OnInit, inject } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { ActivatedRoute, RouterLink } from '@angular/router';
import { ApiService } from '../../services/api.service';
import {
  RFP,
  RFPQuestion,
  RFPResponse,
  ResponseVersion,
  AnalyticsData,
} from '../../models/rfp.model';

@Component({
  selector: 'app-rfp-detail',
  standalone: true,
  imports: [CommonModule, FormsModule, RouterLink],
  template: `
    <div class="sketch-workbench-container" *ngIf="rfp">
      <!-- Breadcrumb & Top Bar -->
      <div class="workbench-header">
        <div>
          <a routerLink="/" class="sketch-back-link">← ✏️ Back to Proposal Portfolio</a>
          <div class="title-row">
            <h1 class="sketch-title">{{ rfp.Title }}</h1>
            <span class="sketch-badge" [ngClass]="getStatusBadgeClass(rfp.Status)">{{ rfp.Status }}</span>
          </div>
          <p class="customer-subtitle">Customer: <b>{{ rfp.CustomerName }}</b> | Target Due Date: <b>{{ rfp.DueDate ? (rfp.DueDate | date:'longDate') : 'Open' }}</b></p>
        </div>

        <!-- Export Buttons (Phase 5) -->
        <div class="header-actions">
          <button class="btn-sketch btn-sketch-primary" (click)="triggerFileUpload()">
            📤 Ingest Questionnaire (PDF/DOCX/XLSX)
          </button>
          <input type="file" #fileInput (change)="onFileSelected($event)" style="display: none" accept=".pdf,.docx,.xlsx" />

          <div class="export-group">
            <span class="export-label">Export Package:</span>
            <a [href]="api.getExportDocxUrl(rfp.RfpId)" target="_blank" class="btn-sketch btn-sketch-blue btn-export">Word (.docx)</a>
            <a [href]="api.getExportXlsxUrl(rfp.RfpId)" target="_blank" class="btn-sketch btn-sketch-green btn-export">Excel (.xlsx)</a>
            <a [href]="api.getExportPdfUrl(rfp.RfpId)" target="_blank" class="btn-sketch btn-sketch-red btn-export">PDF</a>
          </div>
        </div>
      </div>

      <!-- RFP Progress Bar (Phase 5 SLA Analytics) -->
      <div class="sketch-card progress-banner" *ngIf="analytics">
        <div class="sketch-tape"></div>
        <div class="progress-info">
          <span>📊 Proposal Completion: <b>{{ analytics.completion_percentage }}%</b></span>
          <span>✅ Approved: {{ analytics.approved_questions }}/{{ analytics.total_questions }} Questions</span>
          <span *ngIf="analytics.days_remaining !== null && analytics.days_remaining !== undefined" [class.overdue]="analytics.is_overdue">
            ⏱ {{ analytics.is_overdue ? 'OVERDUE by ' + (-analytics.days_remaining!) + ' days' : analytics.days_remaining + ' days remaining' }}
          </span>
        </div>
        <div class="sketch-progress-track">
          <div class="sketch-progress-fill" [style.width.%]="analytics.completion_percentage"></div>
        </div>
      </div>

      <!-- Main Workbench Layout: Questions Matrix + Detail Workbench -->
      <div class="workbench-body">
        <!-- Left Panel: Questionnaire Matrix -->
        <div class="sketch-card questions-panel">
          <div class="panel-header">
            <h3 class="sketch-title">Questionnaire Matrix ({{ questions.length }})</h3>
            <button class="btn-sketch btn-sketch-primary btn-sm" (click)="openAddQuestionModal()">+ Add Item</button>
          </div>

          <div class="filter-bar">
            <input type="text" class="sketch-input" [(ngModel)]="searchFilter" placeholder="Filter questions..." />
            <select class="sketch-select" [(ngModel)]="categoryFilter">
              <option value="">All Categories</option>
              <option *ngFor="let cat of uniqueCategories" [value]="cat">{{ cat }}</option>
            </select>
          </div>

          <div class="questions-list">
            <div
              class="question-sketch-item"
              *ngFor="let q of filteredQuestions"
              [class.active-item]="selectedQuestion?.QuestionId === q.QuestionId"
              (click)="selectQuestion(q)"
            >
              <div class="q-seq-cat">
                <span class="sketch-badge seq-badge">#{{ q.Sequence }}</span>
                <span class="cat-pill">{{ q.Category || 'General' }}</span>
                <span class="sketch-badge q-status-badge" [ngClass]="getQuestionStatusClass(q)">
                  {{ q.response ? q.response.Status : 'Pending' }}
                </span>
              </div>
              <p class="q-text">{{ q.QuestionText }}</p>
              <div class="q-assignee" *ngIf="q.assigned_user">
                👤 SME: {{ q.assigned_user.DisplayName }}
              </div>
            </div>
          </div>
        </div>

        <!-- Right Panel: Intelligent Answer Drafting, Approval Workbench & Knowledge Promotion -->
        <div class="sketch-card editor-panel" *ngIf="selectedQuestion; else noQuestionSelected">
          <div class="editor-header">
            <div>
              <span class="seq-label">Question #{{ selectedQuestion.Sequence }}</span>
              <span class="sketch-badge cat-badge">{{ selectedQuestion.Category || 'General' }}</span>
            </div>
            <div class="editor-header-actions">
              <button class="btn-sketch btn-sketch-purple" (click)="generateAIDraft()" [disabled]="generatingAI">
                {{ generatingAI ? '✨ Formulating with Gemini 2.5 Flash...' : '✨ Generate AI Response (RAG)' }}
              </button>
            </div>
          </div>

          <div class="sketch-question-box">
            <h4>Question Prompt:</h4>
            <p>{{ selectedQuestion.QuestionText }}</p>
          </div>

          <!-- AI Citations & Confidence Pill (Phase 3) -->
          <div class="ai-citation-bar" *ngIf="aiResult">
            <div class="confidence-badge">
              <span>🎯 AI Confidence Score: <b>{{ aiResult.confidence_score * 100 | number:'1.0-0' }}%</b></span>
            </div>
            <div class="citations-list" *ngIf="aiResult.citations.length > 0">
              <span class="cit-label">📚 Citations:</span>
              <span class="sketch-badge cit-tag" *ngFor="let cit of aiResult.citations">
                Source #{{ cit.library_id }}
              </span>
            </div>
          </div>

          <!-- Response Editor & State Machine (Phase 4) -->
          <div class="response-section">
            <div class="section-title-row">
              <h4>Proposal Response Draft:</h4>
              <div class="sketch-badge" [ngClass]="getStatusBadgeClass(currentResponse?.Status)">
                Status: {{ currentResponse ? currentResponse.Status : 'Unanswered' }}
              </div>
            </div>

            <textarea
              [(ngModel)]="editorText"
              rows="8"
              class="sketch-textarea response-textarea"
              placeholder="Enter proposal response or generate with Gemini AI..."
            ></textarea>

            <div class="editor-controls">
              <button class="btn-sketch btn-sketch-primary" (click)="saveResponseText()" [disabled]="!editorText">
                💾 Save Revision (Create Version)
              </button>

              <!-- State Machine Buttons -->
              <div class="workflow-actions" *ngIf="currentResponse">
                <span class="workflow-label">State Machine:</span>
                <button
                  class="btn-sketch btn-sketch-primary review-btn"
                  *ngIf="currentResponse.Status === 'Draft' || currentResponse.Status === 'Rejected'"
                  (click)="transitionStatus('In Review')"
                >
                  Submit for Review
                </button>

                <button
                  class="btn-sketch btn-sketch-green"
                  *ngIf="currentResponse.Status === 'In Review'"
                  (click)="transitionStatus('Approved')"
                >
                  ✓ Approve
                </button>

                <button
                  class="btn-sketch btn-sketch-red"
                  *ngIf="currentResponse.Status === 'In Review'"
                  (click)="transitionStatus('Rejected')"
                >
                  ✕ Reject / Revise
                </button>

                <!-- Promotion Gate (Phase 4) -->
                <button
                  class="btn-sketch btn-sketch-purple"
                  *ngIf="currentResponse.Status === 'Approved'"
                  (click)="promoteToLibrary()"
                >
                  ⭐ Promote to Library
                </button>
              </div>
            </div>
          </div>

          <!-- Version History / Audit Trail Tab (Phase 4) -->
          <div class="versions-section" *ngIf="versions.length > 0">
            <h4>📜 Immutable Revision Audit Trail ({{ versions.length }})</h4>
            <div class="version-list">
              <div class="version-row" *ngFor="let ver of versions">
                <div class="ver-meta">
                  <span class="sketch-badge ver-badge">v{{ ver.VersionNumber }}</span>
                  <span class="ver-date">{{ ver.UpdatedDate | date:'medium' }}</span>
                </div>
                <div class="ver-preview">{{ ver.ResponseText }}</div>
                <button class="btn-sketch btn-sketch-secondary btn-restore" (click)="editorText = ver.ResponseText">Restore</button>
              </div>
            </div>
          </div>
        </div>

        <ng-template #noQuestionSelected>
          <div class="sketch-card empty-workbench">
            <div class="empty-icon">👈</div>
            <h3 class="sketch-title">Select a Questionnaire Item</h3>
            <p>Pick any item from the matrix to formulate draft answers, inspect Gemini RAG citations, or advance approval stages.</p>
          </div>
        </ng-template>
      </div>

      <!-- Add Question Modal -->
      <div class="sketch-modal-backdrop" *ngIf="showAddQuestionModal">
        <div class="sketch-card modal-card">
          <div class="modal-header">
            <h3 class="sketch-title">Add Questionnaire Item</h3>
            <button class="btn-sketch btn-sketch-secondary btn-sm" (click)="showAddQuestionModal = false">✕</button>
          </div>
          <form (ngSubmit)="submitAddQuestion()">
            <div class="form-group">
              <label>Question Text *</label>
              <textarea class="sketch-textarea" [(ngModel)]="newQuestionText" name="qtext" rows="3" required placeholder="e.g. Describe your architecture high availability SLA."></textarea>
            </div>
            <div class="form-group">
              <label>Category (Optional - auto-classified if empty)</label>
              <input type="text" class="sketch-input" [(ngModel)]="newQuestionCat" name="qcat" placeholder="e.g. Security & Compliance" />
            </div>
            <div class="modal-footer">
              <button type="button" class="btn-sketch btn-sketch-secondary" (click)="showAddQuestionModal = false">Cancel</button>
              <button type="submit" class="btn-sketch btn-sketch-primary" [disabled]="!newQuestionText">Add Question</button>
            </div>
          </form>
        </div>
      </div>
    </div>
  `,
  styles: [`
    .sketch-workbench-container {
      padding: 24px 32px;
      max-width: 1600px;
      margin: 0 auto;
    }
    .sketch-back-link {
      font-family: 'Architects Daughter', cursive;
      color: var(--sketch-ink);
      text-decoration: none;
      font-weight: 700;
      font-size: 15px;
      display: inline-block;
      margin-bottom: 6px;
    }
    .title-row {
      display: flex;
      align-items: center;
      gap: 12px;
    }
    .workbench-header {
      display: flex;
      justify-content: space-between;
      align-items: flex-start;
      margin-bottom: 20px;
    }
    .customer-subtitle {
      font-size: 16px;
      color: #52525b;
      margin-top: 4px;
    }
    .header-actions {
      display: flex;
      flex-direction: column;
      align-items: flex-end;
      gap: 12px;
    }
    .export-group {
      display: flex;
      align-items: center;
      gap: 8px;
    }
    .export-label {
      font-family: 'Architects Daughter', cursive;
      font-size: 14px;
      font-weight: 700;
      color: var(--sketch-ink);
    }
    .btn-export {
      padding: 4px 10px !important;
      font-size: 13px !important;
    }

    /* Progress Banner */
    .progress-banner {
      margin-bottom: 24px;
      padding: 16px 20px;
    }
    .progress-info {
      display: flex;
      justify-content: space-between;
      font-family: 'Architects Daughter', cursive;
      font-size: 15px;
      font-weight: 700;
      margin-bottom: 8px;
    }
    .overdue {
      color: var(--sketch-red);
    }
    .sketch-progress-track {
      height: 12px;
      background: #e2e8f0;
      border: 2px solid var(--sketch-ink);
      border-radius: var(--sketch-border-radius-1);
      overflow: hidden;
    }
    .sketch-progress-fill {
      height: 100%;
      background: #4ade80;
      border-right: 2px solid var(--sketch-ink);
      transition: width 0.3s;
    }

    /* Body 2-column layout */
    .workbench-body {
      display: grid;
      grid-template-columns: 420px 1fr;
      gap: 24px;
      min-height: 650px;
    }
    .questions-panel {
      display: flex;
      flex-direction: column;
      padding: 18px;
    }
    .panel-header {
      display: flex;
      justify-content: space-between;
      align-items: center;
      margin-bottom: 14px;
    }
    .filter-bar {
      display: flex;
      gap: 8px;
      margin-bottom: 14px;
    }
    .filter-bar input { flex: 1; }

    .questions-list {
      flex: 1;
      overflow-y: auto;
      max-height: 620px;
      display: flex;
      flex-direction: column;
      gap: 12px;
    }
    .question-sketch-item {
      padding: 12px;
      background: #ffffff;
      border: 2px solid var(--sketch-ink);
      border-radius: var(--sketch-border-radius-2);
      box-shadow: 2px 2px 0px var(--sketch-ink);
      cursor: pointer;
      transition: all 0.12s;
    }
    .question-sketch-item:hover {
      transform: translate(-1px, -2px);
      box-shadow: 3px 4px 0px var(--sketch-ink);
      background: #fefce8;
    }
    .question-sketch-item.active-item {
      background: #fef08a;
      transform: translate(-2px, -2px);
      box-shadow: 4px 5px 0px var(--sketch-ink);
    }
    .q-seq-cat {
      display: flex;
      gap: 6px;
      align-items: center;
      margin-bottom: 6px;
    }
    .seq-badge {
      background: #e0f2fe;
      color: #0369a1;
      font-size: 11px;
    }
    .cat-pill {
      font-family: 'Patrick Hand', cursive;
      font-size: 13px;
      background: #f1f5f9;
      border: 1px solid var(--sketch-ink);
      border-radius: var(--sketch-border-radius-1);
      padding: 1px 6px;
    }
    .q-status-badge {
      margin-left: auto;
      font-size: 10px;
    }
    .q-text {
      font-size: 15px;
      line-height: 1.35;
      display: -webkit-box;
      -webkit-line-clamp: 2;
      -webkit-box-orient: vertical;
      overflow: hidden;
      margin: 0;
    }
    .q-assignee {
      font-size: 12.5px;
      color: #71717a;
      margin-top: 6px;
    }

    /* Right Editor Panel */
    .editor-panel {
      padding: 24px;
      display: flex;
      flex-direction: column;
      gap: 18px;
    }
    .editor-header {
      display: flex;
      justify-content: space-between;
      align-items: center;
    }
    .seq-label {
      font-family: 'Architects Daughter', cursive;
      font-size: 22px;
      font-weight: 700;
      margin-right: 10px;
    }
    .cat-badge {
      background: #fef08a;
      color: #854d0e;
    }
    .sketch-question-box {
      background: #fdfbf7;
      border: 2px dashed var(--sketch-ink);
      border-radius: var(--sketch-border-radius-1);
      padding: 14px 18px;
    }
    .sketch-question-box h4 {
      font-size: 14px;
      color: #71717a;
      margin-bottom: 4px;
    }
    .sketch-question-box p {
      font-size: 18px;
      font-weight: 600;
      margin: 0;
    }

    /* AI Citations Bar */
    .ai-citation-bar {
      display: flex;
      align-items: center;
      gap: 16px;
      background: #f0fdf4;
      border: 2px solid var(--sketch-ink);
      border-radius: var(--sketch-border-radius-2);
      box-shadow: 2px 2px 0px var(--sketch-ink);
      padding: 10px 14px;
    }
    .confidence-badge {
      font-family: 'Architects Daughter', cursive;
      font-size: 14px;
      color: #166534;
      font-weight: 700;
    }
    .citations-list {
      display: flex;
      align-items: center;
      gap: 6px;
    }
    .cit-label {
      font-size: 14px;
      font-weight: 600;
    }
    .cit-tag {
      background: #dcfce7;
      color: #15803d;
      font-size: 11px;
    }

    /* Response section */
    .response-section {
      display: flex;
      flex-direction: column;
      gap: 12px;
    }
    .section-title-row {
      display: flex;
      justify-content: space-between;
      align-items: center;
    }
    .section-title-row h4 {
      font-size: 16px;
      margin: 0;
    }
    .response-textarea {
      font-size: 16px !important;
      line-height: 1.6 !important;
    }
    .editor-controls {
      display: flex;
      justify-content: space-between;
      align-items: center;
      flex-wrap: wrap;
      gap: 12px;
    }
    .workflow-actions {
      display: flex;
      align-items: center;
      gap: 8px;
    }
    .workflow-label {
      font-family: 'Architects Daughter', cursive;
      font-size: 14px;
      font-weight: 700;
      color: #71717a;
    }
    .review-btn { background: #fed7aa !important; }

    /* Versions Audit Trail */
    .versions-section {
      border-top: 2px dashed var(--sketch-ink);
      padding-top: 16px;
    }
    .versions-section h4 {
      font-size: 16px;
      margin-bottom: 10px;
    }
    .version-list {
      display: flex;
      flex-direction: column;
      gap: 8px;
    }
    .version-row {
      display: flex;
      align-items: center;
      justify-content: space-between;
      background: #ffffff;
      border: 1.5px solid var(--sketch-ink);
      border-radius: var(--sketch-border-radius-1);
      box-shadow: 1px 1px 0px var(--sketch-ink);
      padding: 6px 12px;
      font-size: 14px;
    }
    .ver-badge {
      background: #f1f5f9;
      font-size: 11px;
      margin-right: 8px;
    }
    .ver-date { color: #71717a; }
    .ver-preview {
      flex: 1;
      margin: 0 16px;
      color: #3f3f46;
      white-space: nowrap;
      overflow: hidden;
      text-overflow: ellipsis;
    }
    .btn-restore {
      padding: 2px 8px !important;
      font-size: 12px !important;
    }

    .empty-workbench {
      display: flex;
      flex-direction: column;
      align-items: center;
      justify-content: center;
      padding: 60px 20px;
      text-align: center;
    }
    .empty-workbench .empty-icon { font-size: 48px; margin-bottom: 12px; }

    /* Modals & Helpers */
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
      max-width: 500px;
      padding: 24px;
    }
    .modal-header {
      display: flex;
      justify-content: space-between;
      align-items: center;
      margin-bottom: 16px;
    }
    .form-group { margin-bottom: 14px; }
    .form-group label {
      display: block;
      font-family: 'Architects Daughter', cursive;
      font-size: 15px;
      font-weight: 700;
      margin-bottom: 6px;
    }
    .modal-footer { display: flex; justify-content: flex-end; gap: 10px; margin-top: 20px; }
    .btn-sm { padding: 4px 10px !important; font-size: 13px !important; }
  `]
})
export class RfpDetailComponent implements OnInit {
  api = inject(ApiService);
  private route = inject(ActivatedRoute);

  rfpId!: number;
  rfp: (RFP & { questions: RFPQuestion[] }) | null = null;
  questions: RFPQuestion[] = [];
  selectedQuestion: RFPQuestion | null = null;
  currentResponse: RFPResponse | null = null;
  versions: ResponseVersion[] = [];
  analytics: AnalyticsData | null = null;

  editorText = '';
  generatingAI = false;
  aiResult: any = null;

  searchFilter = '';
  categoryFilter = '';

  showAddQuestionModal = false;
  newQuestionText = '';
  newQuestionCat = '';

  ngOnInit() {
    this.route.paramMap.subscribe(params => {
      const id = params.get('id');
      if (id) {
        this.rfpId = +id;
        this.loadRFP();
      }
    });
  }

  loadRFP() {
    this.api.getRFPById(this.rfpId).subscribe({
      next: (data) => {
        this.rfp = data;
        this.questions = data.questions || [];
        this.loadResponsesForQuestions();
        this.loadAnalytics();
        if (this.questions.length > 0 && !this.selectedQuestion) {
          this.selectQuestion(this.questions[0]);
        }
      },
      error: () => alert('Error loading RFP details')
    });
  }

  loadAnalytics() {
    this.api.getAnalytics(this.rfpId).subscribe({
      next: (a) => this.analytics = a,
      error: (e) => console.warn('Could not load RFP analytics', e)
    });
  }

  loadResponsesForQuestions() {
    this.questions.forEach(q => {
      this.api.getResponseForQuestion(q.QuestionId).subscribe({
        next: (resp) => {
          if (resp) {
            q.response = resp;
            if (this.selectedQuestion?.QuestionId === q.QuestionId) {
              this.currentResponse = resp;
            }
          }
        }
      });
    });
  }

  get uniqueCategories(): string[] {
    const set = new Set<string>();
    this.questions.forEach(q => {
      if (q.Category) set.add(q.Category);
    });
    return Array.from(set);
  }

  get filteredQuestions(): RFPQuestion[] {
    return this.questions.filter(q => {
      const matchesSearch = !this.searchFilter || q.QuestionText.toLowerCase().includes(this.searchFilter.toLowerCase());
      const matchesCat = !this.categoryFilter || q.Category === this.categoryFilter;
      return matchesSearch && matchesCat;
    });
  }

  selectQuestion(q: RFPQuestion) {
    this.selectedQuestion = q;
    this.aiResult = null;
    this.api.getResponseForQuestion(q.QuestionId).subscribe({
      next: (resp) => {
        this.currentResponse = resp;
        this.editorText = resp ? resp.ResponseText : '';
        if (resp) {
          this.loadVersions(resp.ResponseId);
        } else {
          this.versions = [];
        }
      },
      error: () => {
        this.currentResponse = null;
        this.editorText = '';
        this.versions = [];
      }
    });
  }

  loadVersions(responseId: number) {
    this.api.getResponseVersions(responseId).subscribe({
      next: (vers) => this.versions = vers,
      error: (err) => console.warn('Could not load versions', err)
    });
  }

  generateAIDraft() {
    if (!this.selectedQuestion) return;
    this.generatingAI = true;
    this.api.generateAIDraft(this.selectedQuestion.QuestionId).subscribe({
      next: (res) => {
        this.generatingAI = false;
        this.aiResult = res;
        this.editorText = res.draft_text;
        if (res.saved_response) {
          this.currentResponse = res.saved_response;
          this.selectedQuestion!.response = res.saved_response;
          this.loadVersions(res.saved_response.ResponseId);
        }
        this.loadAnalytics();
      },
      error: (err) => {
        this.generatingAI = false;
        alert('AI generation failed: ' + (err.error?.message || err.message));
      }
    });
  }

  saveResponseText() {
    if (!this.selectedQuestion || !this.editorText) return;
    if (this.currentResponse) {
      this.api.updateResponseText(this.currentResponse.ResponseId, this.editorText).subscribe({
        next: (updated) => {
          this.currentResponse = updated;
          this.selectedQuestion!.response = updated;
          this.loadVersions(updated.ResponseId);
          alert('Revision saved with version audit.');
        }
      });
    } else {
      this.api.saveManualResponse(this.selectedQuestion.QuestionId, this.editorText).subscribe({
        next: (created) => {
          this.currentResponse = created;
          this.selectedQuestion!.response = created;
          this.loadVersions(created.ResponseId);
          this.loadAnalytics();
        }
      });
    }
  }

  transitionStatus(status: 'Draft' | 'In Review' | 'Approved' | 'Rejected') {
    if (!this.currentResponse) return;
    this.api.updateResponseStatus(this.currentResponse.ResponseId, status).subscribe({
      next: (res) => {
        this.currentResponse = res;
        this.selectedQuestion!.response = res;
        this.loadAnalytics();
      },
      error: (err) => alert('Status transition failed: ' + (err.error?.message || err.message))
    });
  }

  promoteToLibrary() {
    if (!this.currentResponse) return;
    this.api.promoteToLibrary(this.currentResponse.ResponseId, this.selectedQuestion?.Category).subscribe({
      next: (item) => {
        alert(`Successfully promoted question to knowledge library! Entry #${item.LibraryId}`);
      },
      error: (err) => alert('Promotion failed: ' + (err.error?.message || err.message))
    });
  }

  triggerFileUpload() {
    const input: HTMLInputElement = document.querySelector('input[type="file"]')!;
    input.click();
  }

  onFileSelected(event: any) {
    const file: File = event.target.files[0];
    if (file) {
      this.api.ingestDocument(this.rfpId, file).subscribe({
        next: (res) => {
          alert(`Successfully ingested questionnaire! Extracted ${res.questions_extracted} questions.`);
          this.loadRFP();
        },
        error: (err) => alert('Document ingestion failed: ' + (err.error?.message || err.message))
      });
    }
  }

  openAddQuestionModal() {
    this.newQuestionText = '';
    this.newQuestionCat = '';
    this.showAddQuestionModal = true;
  }

  submitAddQuestion() {
    if (!this.newQuestionText) return;
    this.api.createQuestion(this.rfpId, {
      QuestionText: this.newQuestionText,
      Category: this.newQuestionCat || undefined,
    }).subscribe({
      next: () => {
        this.showAddQuestionModal = false;
        this.loadRFP();
      },
      error: () => alert('Failed to add question')
    });
  }

  getQuestionStatusClass(q: RFPQuestion): string {
    if (!q.response) return 'badge-draft';
    return this.getStatusBadgeClass(q.response.Status);
  }

  getStatusBadgeClass(status?: string): string {
    switch ((status || '').toLowerCase()) {
      case 'approved': return 'badge-approved';
      case 'in review': return 'badge-inreview';
      case 'rejected': return 'badge-rejected';
      default: return 'badge-draft';
    }
  }
}
