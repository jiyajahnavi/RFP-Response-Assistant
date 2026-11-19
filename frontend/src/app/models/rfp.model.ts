export interface RFP {
  RfpId: number;
  Title: string;
  CustomerName: string;
  Description?: string;
  DueDate?: string;
  Status: string;
  CreatedBy?: number;
  CreatedDate: string;
  UpdatedDate: string;
}

export interface ApplicationUser {
  UserId: number;
  DisplayName: string;
  Email: string;
  Role: string;
}

export interface RFPQuestion {
  QuestionId: number;
  RfpId: number;
  QuestionText: string;
  Category?: string;
  Sequence: number;
  Status: string;
  AssignedTo?: number;
  assigned_user?: ApplicationUser;
  CreatedDate: string;
  // Optional client-side loaded response
  response?: RFPResponse;
}

export interface RFPResponse {
  ResponseId: number;
  QuestionId: number;
  ResponseText: string;
  IsAIGenerated: boolean;
  Status: 'Draft' | 'In Review' | 'Approved' | 'Rejected' | string;
  UpdatedBy?: number;
  UpdatedDate: string;
  ApprovedBy?: number;
  ApprovedDate?: string;
  approver?: ApplicationUser;
  versions?: ResponseVersion[];
}

export interface ResponseVersion {
  VersionId: number;
  ResponseId: number;
  ResponseText: string;
  VersionNumber: number;
  UpdatedBy?: number;
  UpdatedDate: string;
}

export interface ResponseLibraryItem {
  LibraryId: number;
  Question: string;
  Answer: string;
  Category?: string;
  Technology?: string;
  SourceRfpId?: number;
  CreatedDate: string;
}

export interface LibrarySearchResult {
  library_id: number;
  question: string;
  answer: string;
  category?: string;
  technology?: string;
  confidence_score: number;
}

export interface AIGenerateResponse {
  draft_text: string;
  confidence_score: number;
  citations: Array<{
    library_id: number;
    category?: string;
    confidence_score: number;
  }>;
  status: string;
  is_ai_generated: boolean;
  saved_response?: RFPResponse;
}

export interface AnalyticsData {
  rfp_id?: number;
  title?: string;
  customer_name?: string;
  total_questions?: number;
  answered_questions?: number;
  approved_questions?: number;
  completion_percentage?: number;
  status_distribution?: Record<string, number>;
  category_distribution?: Record<string, number>;
  due_date?: string;
  days_remaining?: number;
  is_overdue?: boolean;
  total_rfps?: number;
  total_responses?: number;
  total_approved_responses?: number;
  total_library_entries?: number;
  overall_approval_rate?: number;
}
