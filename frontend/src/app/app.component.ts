import { Component, OnInit, inject } from '@angular/core';
import { RouterOutlet, RouterLink, RouterLinkActive } from '@angular/router';
import { CommonModule } from '@angular/common';
import { ApiService } from './services/api.service';

@Component({
  selector: 'app-root',
  standalone: true,
  imports: [RouterOutlet, RouterLink, RouterLinkActive, CommonModule],
  template: `
    <div class="sketch-app-layout">
      <!-- Sketch Navbar Header -->
      <header class="sketch-nav">
        <div class="nav-left">
          <div class="sketch-logo-box">✏️</div>
          <div class="sketch-brand">
            <span class="brand-title">RFP Response Assistant</span>
            <span class="sketch-badge sketch-version-badge">Sketch Edition</span>
          </div>
        </div>

        <nav class="nav-links">
          <a routerLink="/" routerLinkActive="active-tab" [routerLinkActiveOptions]="{ exact: true }" class="sketch-tab">
            📋 Proposal Portfolio
          </a>
          <a routerLink="/library" routerLinkActive="active-tab" class="sketch-tab">
            📚 Response Library (RAG)
          </a>
        </nav>

        <div class="nav-right">
          <div class="sketch-status-pill" [class.online]="backendOnline" [class.offline]="!backendOnline">
            <span class="status-scribble"></span>
            <span>{{ backendOnline ? '⚡ API Connected' : '⚠️ API Offline' }}</span>
          </div>
        </div>
      </header>

      <!-- Main Application Views -->
      <main class="sketch-content">
        <router-outlet></router-outlet>
      </main>
    </div>
  `,
  styles: [`
    .sketch-app-layout {
      min-height: 100vh;
      display: flex;
      flex-direction: column;
    }
    .sketch-nav {
      background: #fffefb;
      border-bottom: 2px solid var(--sketch-ink);
      box-shadow: 0 4px 0px rgba(33, 37, 41, 0.08);
      display: flex;
      align-items: center;
      justify-content: space-between;
      padding: 12px 32px;
      position: sticky;
      top: 0;
      z-index: 100;
    }
    .nav-left {
      display: flex;
      align-items: center;
      gap: 12px;
    }
    .sketch-logo-box {
      background: #fde047;
      border: 2px solid var(--sketch-ink);
      border-radius: 255px 15px 225px 15px / 15px 225px 15px 255px;
      box-shadow: 2px 2px 0px var(--sketch-ink);
      width: 40px;
      height: 40px;
      display: flex;
      align-items: center;
      justify-content: center;
      font-size: 20px;
      transform: rotate(-4deg);
    }
    .sketch-brand {
      display: flex;
      align-items: center;
      gap: 10px;
    }
    .brand-title {
      font-family: 'Architects Daughter', cursive;
      font-weight: 800;
      font-size: 20px;
      color: var(--sketch-ink);
    }
    .sketch-version-badge {
      background: #e0f2fe;
      color: #0369a1;
      font-size: 11px;
    }
    .nav-links {
      display: flex;
      gap: 14px;
    }
    .sketch-tab {
      font-family: 'Architects Daughter', cursive;
      color: var(--sketch-ink);
      text-decoration: none;
      font-size: 16px;
      font-weight: 700;
      padding: 6px 16px;
      border: 2px dashed transparent;
      border-radius: var(--sketch-border-radius-2);
      transition: all 0.15s;
    }
    .sketch-tab:hover {
      background: #fef08a;
      border-color: var(--sketch-ink);
      transform: translateY(-2px);
    }
    .sketch-tab.active-tab {
      background: #fde047;
      border: 2px solid var(--sketch-ink);
      box-shadow: 2px 3px 0px var(--sketch-ink);
      transform: rotate(-1deg);
    }
    .sketch-status-pill {
      font-family: 'Architects Daughter', cursive;
      font-size: 13px;
      font-weight: 700;
      padding: 4px 12px;
      border: 2px solid var(--sketch-ink);
      border-radius: var(--sketch-border-radius-1);
      box-shadow: 2px 2px 0px var(--sketch-ink);
    }
    .sketch-status-pill.online {
      background: #bbf7d0;
      color: #14532d;
    }
    .sketch-status-pill.offline {
      background: #fecaca;
      color: #991b1b;
    }
    .sketch-content {
      flex: 1;
    }
  `]
})
export class AppComponent implements OnInit {
  private api = inject(ApiService);
  backendOnline = false;

  ngOnInit() {
    this.api.checkHealth().subscribe({
      next: (h) => this.backendOnline = h.database_connected !== false,
      error: () => this.backendOnline = false
    });
  }
}
