import { Injectable, inject } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Observable } from 'rxjs';
import {
  RFP,
  RFPQuestion,
  RFPResponse,
  ResponseVersion,
  ResponseLibraryItem,
  LibrarySearchResult,
  AIGenerateResponse,
  AnalyticsData,
} from '../models/rfp.model';

@Injectable({
  providedIn: 'root',
})
export class ApiService {
  private http = inject(HttpClient);
  private baseUrl = 'http://127.0.0.1:8000/api/v1';

  // --- Health ---
  checkHealth(): Observable<any> {
    return this.http.get(`${this.baseUrl}/health`);
  }

  // --- RFPs ---
  getRFPs(skip = 0, limit = 100): Observable<RFP[]> {
    return this.http.get<RFP[]>(`${this.baseUrl}/rfps?skip=${skip}&limit=${limit}`);
  }

  getRFPById(rfpId: number): Observable<RFP & { questions: RFPQuestion[] }> {
    return this.http.get<RFP & { questions: RFPQuestion[] }>(`${this.baseUrl}/rfps/${rfpId}`);
  }

  createRFP(data: Partial<RFP>): Observable<RFP> {
    return this.http.post<RFP>(`${this.baseUrl}/rfps`, data);
  }

  updateRFP(rfpId: number, data: Partial<RFP>): Observable<RFP> {
    return this.http.put<RFP>(`${this.baseUrl}/rfps/${rfpId}`, data);
  }

  deleteRFP(rfpId: number): Observable<void> {
    return this.http.delete<void>(`${this.baseUrl}/rfps/${rfpId}`);
  }

  // --- Document Ingestion ---
  ingestDocument(rfpId: number, file: File): Observable<any> {
    const formData = new FormData();
    formData.append('file', file);
    return this.http.post(`${this.baseUrl}/rfps/${rfpId}/ingest`, formData);
  }

  // --- Questions ---
  createQuestion(rfpId: number, question: Partial<RFPQuestion>): Observable<RFPQuestion> {
    return this.http.post<RFPQuestion>(`${this.baseUrl}/rfps/${rfpId}/questions`, question);
  }

  updateQuestion(questionId: number, question: Partial<RFPQuestion>): Observable<RFPQuestion> {
    return this.http.put<RFPQuestion>(`${this.baseUrl}/questions/${questionId}`, question);
  }

  deleteQuestion(questionId: number): Observable<void> {
    return this.http.delete<void>(`${this.baseUrl}/questions/${questionId}`);
  }

  assignQuestion(questionId: number, assignedTo: number | null): Observable<RFPQuestion> {
    return this.http.patch<RFPQuestion>(`${this.baseUrl}/questions/${questionId}/assign`, {
      AssignedTo: assignedTo,
    });
  }

  // --- AI Drafting (Phase 3) ---
  generateAIDraft(questionId: number, contextNotes?: string): Observable<AIGenerateResponse> {
    return this.http.post<AIGenerateResponse>(
      `${this.baseUrl}/questions/${questionId}/generate-draft`,
      { ContextNotes: contextNotes || '' }
    );
  }

  // --- Responses & Workflow (Phase 4) ---
  getResponseForQuestion(questionId: number): Observable<RFPResponse> {
    return this.http.get<RFPResponse>(`${this.baseUrl}/questions/${questionId}/response`);
  }

  saveManualResponse(questionId: number, text: string, userId?: number): Observable<RFPResponse> {
    return this.http.post<RFPResponse>(`${this.baseUrl}/questions/${questionId}/response`, {
      ResponseText: text,
      UpdatedBy: userId,
    });
  }

  updateResponseText(responseId: number, text: string, userId?: number): Observable<RFPResponse> {
    return this.http.put<RFPResponse>(`${this.baseUrl}/responses/${responseId}`, {
      ResponseText: text,
      UpdatedBy: userId,
    });
  }

  updateResponseStatus(
    responseId: number,
    status: 'Draft' | 'In Review' | 'Approved' | 'Rejected',
    reviewerId?: number
  ): Observable<RFPResponse> {
    return this.http.patch<RFPResponse>(`${this.baseUrl}/responses/${responseId}/status`, {
      Status: status,
      ReviewerId: reviewerId,
    });
  }

  getResponseVersions(responseId: number): Observable<ResponseVersion[]> {
    return this.http.get<ResponseVersion[]>(`${this.baseUrl}/responses/${responseId}/versions`);
  }

  promoteToLibrary(responseId: number, category?: string, technology?: string): Observable<ResponseLibraryItem> {
    return this.http.post<ResponseLibraryItem>(`${this.baseUrl}/responses/${responseId}/promote`, {
      Category: category,
      Technology: technology,
    });
  }

  // --- Response Library (RAG Knowledge Base) ---
  getLibraryEntries(category?: string): Observable<ResponseLibraryItem[]> {
    const url = category ? `${this.baseUrl}/library?category=${encodeURIComponent(category)}` : `${this.baseUrl}/library`;
    return this.http.get<ResponseLibraryItem[]>(url);
  }

  searchLibrary(query: string, category?: string): Observable<LibrarySearchResult[]> {
    let url = `${this.baseUrl}/library/search?q=${encodeURIComponent(query)}`;
    if (category) {
      url += `&category=${encodeURIComponent(category)}`;
    }
    return this.http.get<LibrarySearchResult[]>(url);
  }

  createLibraryEntry(entry: Partial<ResponseLibraryItem>): Observable<ResponseLibraryItem> {
    return this.http.post<ResponseLibraryItem>(`${this.baseUrl}/library`, entry);
  }

  // --- Analytics & Export (Phase 5) ---
  getAnalytics(rfpId?: number): Observable<AnalyticsData> {
    const url = rfpId ? `${this.baseUrl}/analytics?rfp_id=${rfpId}` : `${this.baseUrl}/analytics`;
    return this.http.get<AnalyticsData>(url);
  }

  getExportDocxUrl(rfpId: number): string {
    return `${this.baseUrl}/export/${rfpId}/docx`;
  }

  getExportXlsxUrl(rfpId: number): string {
    return `${this.baseUrl}/export/${rfpId}/xlsx`;
  }

  getExportPdfUrl(rfpId: number): string {
    return `${this.baseUrl}/export/${rfpId}/pdf`;
  }
}
