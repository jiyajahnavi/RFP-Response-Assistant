import { Component, OnInit, inject } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { ApiService } from '../../services/api.service';
import { ResponseLibraryItem, LibrarySearchResult } from '../../models/rfp.model';

@Component({
  selector: 'app-library-search',
  standalone: true,
  imports: [CommonModule, FormsModule],
  template: `
    <div class="sketch-library-container">
      <div class="library-header">
        <div>
          <h2 class="sketch-title">Response Library & Semantic Knowledge Base</h2>
          <p class="sketch-subtitle">Search, inspect, and contribute verified historical proposal Q&As powered by Gemini vector embeddings</p>
        </div>
        <button class="btn-sketch btn-sketch-primary" (click)="openAddModal()">+ Add Knowledge Item</button>
      </div>

      <!-- Search Box with Category Selector -->
      <div class="sketch-card search-card">
        <div class="sketch-tape"></div>
        <div class="search-input-wrapper">
          <span class="search-icon">🔍</span>
          <input
            type="text"
            class="sketch-input"
            [(ngModel)]="searchQuery"
            (keyup.enter)="executeSearch()"
            placeholder="Search responses using natural language (e.g. 'How do you handle SOC 2 encryption and HIPAA audits?')..."
          />
          <button class="btn-sketch btn-sketch-primary" (click)="executeSearch()" [disabled]="searching || !searchQuery">
            {{ searching ? 'Searching...' : '✨ Semantic Search' }}
          </button>
        </div>
      </div>

      <!-- Search Results View -->
      <div class="results-section" *ngIf="searchResults.length > 0">
        <div class="results-header">
          <h3 class="sketch-title">Top Semantic Matches ({{ searchResults.length }})</h3>
          <button class="btn-sketch btn-sketch-secondary btn-sm" (click)="searchResults = []">Clear Search</button>
        </div>
        <div class="results-grid">
          <div class="sketch-card result-card" *ngFor="let item of searchResults">
            <div class="result-top">
              <span class="sketch-badge cat-badge">{{ item.category || 'General' }}</span>
              <span class="sketch-badge tech-badge" *ngIf="item.technology">{{ item.technology }}</span>
              <span class="sketch-badge score-badge">Match: {{ item.confidence_score * 100 | number:'1.0-0' }}%</span>
            </div>
            <h4 class="q-title">Q: {{ item.question }}</h4>
            <div class="a-body">{{ item.answer }}</div>
          </div>
        </div>
      </div>

      <!-- Complete Repository View -->
      <div class="repository-section" *ngIf="searchResults.length === 0">
        <div class="repo-header">
          <h3 class="sketch-title">Verified Knowledge Entries ({{ allEntries.length }})</h3>
          <div class="category-filters">
            <button
              class="btn-sketch btn-sm filter-pill"
              [class.active-cat]="selectedCategory === ''"
              (click)="filterCategory('')"
            >
              All Categories
            </button>
            <button
              class="btn-sketch btn-sm filter-pill"
              *ngFor="let cat of categories"
              [class.active-cat]="selectedCategory === cat"
              (click)="filterCategory(cat)"
            >
              {{ cat }}
            </button>
          </div>
        </div>

        <div class="entries-grid" *ngIf="allEntries.length > 0; else emptyLib">
          <div class="sketch-card entry-card" *ngFor="let entry of allEntries">
            <div class="entry-header">
              <span class="sketch-badge cat-badge">{{ entry.Category || 'General' }}</span>
              <span class="sketch-badge tech-badge" *ngIf="entry.Technology">{{ entry.Technology }}</span>
              <span class="entry-date">{{ entry.CreatedDate | date:'mediumDate' }}</span>
            </div>
            <h4 class="entry-q">Q: {{ entry.Question }}</h4>
            <p class="entry-a">{{ entry.Answer }}</p>
          </div>
        </div>

        <ng-template #emptyLib>
          <div class="sketch-card empty-state">
            <div class="empty-icon">📖</div>
            <h4 class="sketch-title">Knowledge Base Empty</h4>
            <p>Promote approved proposal responses from the workbench or manually create standard entries.</p>
          </div>
        </ng-template>
      </div>

      <!-- Add Knowledge Modal -->
      <div class="sketch-modal-backdrop" *ngIf="showAddModal">
        <div class="sketch-card modal-card">
          <div class="modal-header">
            <h3 class="sketch-title">Add Verified Knowledge Entry</h3>
            <button class="btn-sketch btn-sketch-secondary btn-sm" (click)="showAddModal = false">✕</button>
          </div>
          <form (ngSubmit)="submitNewEntry()">
            <div class="form-group">
              <label>Question *</label>
              <textarea class="sketch-textarea" [(ngModel)]="newEntry.Question" name="q" rows="2" required placeholder="Standard RFP Question..."></textarea>
            </div>
            <div class="form-group">
              <label>Approved Response Answer *</label>
              <textarea class="sketch-textarea" [(ngModel)]="newEntry.Answer" name="a" rows="5" required placeholder="Authoritative verified response..."></textarea>
            </div>
            <div class="form-row">
              <div class="form-group">
                <label>Category</label>
                <input type="text" class="sketch-input" [(ngModel)]="newEntry.Category" name="cat" placeholder="Security & Compliance" />
              </div>
              <div class="form-group">
                <label>Technology / Domain</label>
                <input type="text" class="sketch-input" [(ngModel)]="newEntry.Technology" name="tech" placeholder="e.g. AWS, Kubernetes" />
              </div>
            </div>
            <div class="modal-footer">
              <button type="button" class="btn-sketch btn-sketch-secondary" (click)="showAddModal = false">Cancel</button>
              <button type="submit" class="btn-sketch btn-sketch-primary" [disabled]="!newEntry.Question || !newEntry.Answer">Save to Library</button>
            </div>
          </form>
        </div>
      </div>
    </div>
  `,
  styles: [`
    .sketch-library-container {
      padding: 32px;
      max-width: 1400px;
      margin: 0 auto;
    }
    .library-header {
      display: flex;
      justify-content: space-between;
      align-items: center;
      margin-bottom: 24px;
    }
    .sketch-title { font-size: 26px; }
    .sketch-subtitle { color: #52525b; font-size: 16px; margin-top: 4px; }

    /* Search bar */
    .search-card {
      padding: 20px;
      margin-bottom: 32px;
    }
    .search-input-wrapper {
      display: flex;
      align-items: center;
      gap: 14px;
    }
    .search-icon { font-size: 24px; }

    /* Results */
    .results-section, .repository-section {
      margin-bottom: 40px;
    }
    .results-header, .repo-header {
      display: flex;
      justify-content: space-between;
      align-items: center;
      margin-bottom: 20px;
    }
    .category-filters {
      display: flex;
      gap: 10px;
      flex-wrap: wrap;
    }
    .filter-pill {
      background: white !important;
      color: var(--sketch-ink) !important;
    }
    .filter-pill.active-cat {
      background: #fde047 !important;
      transform: rotate(-1deg);
    }

    .results-grid, .entries-grid {
      display: grid;
      grid-template-columns: repeat(auto-fill, minmax(420px, 1fr));
      gap: 24px;
    }
    .result-card, .entry-card {
      display: flex;
      flex-direction: column;
    }
    .result-top, .entry-header {
      display: flex;
      align-items: center;
      gap: 8px;
      margin-bottom: 12px;
    }
    .cat-badge {
      background: #e0f2fe;
      color: #0369a1;
    }
    .tech-badge {
      background: #f1f5f9;
      color: #475569;
    }
    .score-badge {
      margin-left: auto;
      background: #dcfce7;
      color: #15803d;
    }
    .entry-date {
      margin-left: auto;
      font-size: 13px;
      color: #71717a;
    }
    .q-title, .entry-q {
      font-size: 18px;
      margin-bottom: 8px;
    }
    .a-body, .entry-a {
      font-size: 15px;
      line-height: 1.5;
      background: #fdfbf7;
      border: 1.5px dashed var(--sketch-ink);
      border-radius: var(--sketch-border-radius-1);
      padding: 12px;
    }
    .empty-state {
      text-align: center;
      padding: 60px;
    }
    .empty-icon { font-size: 40px; margin-bottom: 8px; }

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
      max-width: 540px;
      padding: 24px;
    }
    .modal-header {
      display: flex;
      justify-content: space-between;
      align-items: center;
      margin-bottom: 16px;
    }
    .form-group { margin-bottom: 14px; }
    .form-row { display: flex; gap: 12px; }
    .form-row .form-group { flex: 1; }
    .form-group label {
      display: block;
      font-family: 'Architects Daughter', cursive;
      font-weight: 700;
      font-size: 15px;
      margin-bottom: 6px;
    }
    .modal-footer { display: flex; justify-content: flex-end; gap: 12px; margin-top: 20px; }
    .btn-sm { padding: 4px 10px !important; font-size: 13px !important; }
  `]
})
export class LibrarySearchComponent implements OnInit {
  private api = inject(ApiService);

  allEntries: ResponseLibraryItem[] = [];
  searchResults: LibrarySearchResult[] = [];
  searchQuery = '';
  searching = false;
  selectedCategory = '';

  categories = [
    'Security & Compliance',
    'Technical Architecture & Infrastructure',
    'Pricing & Commercials',
    'Support & SLA',
    'Company & Experience',
  ];

  showAddModal = false;
  newEntry: Partial<ResponseLibraryItem> = {
    Question: '',
    Answer: '',
    Category: '',
    Technology: '',
  };

  ngOnInit() {
    this.loadEntries();
  }

  loadEntries() {
    this.api.getLibraryEntries(this.selectedCategory || undefined).subscribe({
      next: (entries) => this.allEntries = entries,
      error: (err) => console.error('Failed to load library', err)
    });
  }

  filterCategory(cat: string) {
    this.selectedCategory = cat;
    this.searchResults = [];
    this.loadEntries();
  }

  executeSearch() {
    if (!this.searchQuery.trim()) return;
    this.searching = true;
    this.api.searchLibrary(this.searchQuery).subscribe({
      next: (results) => {
        this.searching = false;
        this.searchResults = results;
      },
      error: (err) => {
        this.searching = false;
        alert('Semantic search failed: ' + (err.error?.message || err.message));
      }
    });
  }

  openAddModal() {
    this.newEntry = { Question: '', Answer: '', Category: '', Technology: '' };
    this.showAddModal = true;
  }

  submitNewEntry() {
    if (!this.newEntry.Question || !this.newEntry.Answer) return;
    this.api.createLibraryEntry(this.newEntry).subscribe({
      next: () => {
        this.showAddModal = false;
        this.loadEntries();
        alert('Knowledge entry successfully added.');
      },
      error: () => alert('Failed to save knowledge item')
    });
  }
}
