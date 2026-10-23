export type Role = "student" | "agent" | "unit_head" | "admin";
export type Priority = "Critical" | "High" | "Medium" | "Low";
export type Lang = "en" | "ru" | "kz";

export interface User {
  id: number;
  name: string;
  email: string;
  role: Role;
  unit_id: number | null;
  unit_name: string | null;
  language: Lang;
  is_active: boolean;
}

export interface Brief {
  id: number;
  name: string;
}

export interface SLAState {
  target: "first_response" | "resolution";
  due_at: string;
  remaining_seconds: number;
  remaining_fraction: number;
  color: "green" | "yellow" | "red" | "black";
  paused: boolean;
  breached: boolean;
}

export interface RequestCard {
  id: string;
  subject: string;
  status: string;
  priority: Priority;
  priority_score: number;
  category: Brief | null;
  unit: Brief | null;
  assignee: Brief | null;
  student: Brief | null;
  ai_confidence: number | null;
  escalated: boolean;
  sla: SLAState | null;
  created_at: string;
  updated_at: string;
}

export interface AIDecision {
  predicted_category: Brief | null;
  confidence: number | null;
  alternatives: { category: string; confidence: number }[];
  keywords: string[];
  predicted_priority: string | null;
  priority_reasons: string[];
  predicted_unit: Brief | null;
  student_category: Brief | null;
  model_version: string | null;
}

export interface RequestDetail extends RequestCard {
  description: string;
  workflow: string;
  workflow_steps: string[];
  workflow_step: number;
  first_response_at: string | null;
  resolved_at: string | null;
  csat: { rating: number; comment: string; created_at: string } | null;
  allowed_transitions: string[];
  ai: AIDecision | null;
}

export interface Page<T> {
  items: T[];
  total: number;
  page: number;
  page_size: number;
  pages: number;
}

export interface TimelineEvent {
  id: string;
  kind: "submitted" | "status" | "ai" | "routing" | "message" | "note" | "escalation" | "step" | "csat";
  title: string;
  detail: string | null;
  status: string | null;
  actor: string | null;
  internal: boolean;
  created_at: string;
}

export interface Attachment {
  id: number;
  filename: string;
  content_type: string;
  size: number;
  url: string;
}

export interface Message {
  id: number;
  request_id: string;
  author: Brief;
  author_role: Role;
  body: string;
  is_internal: boolean;
  read_at: string | null;
  created_at: string;
  attachments: Attachment[];
}

export interface Notification {
  id: number;
  type: string;
  title: string;
  body: string;
  request_id: string | null;
  is_read: boolean;
  created_at: string;
}

export interface CategoryMeta {
  id: number;
  name: string;
  unit_id: number | null;
  default_workflow: string;
}

export interface UnitMeta {
  id: number;
  name: string;
  is_triage: boolean;
}

export interface AgentMeta {
  id: number;
  name: string;
  role: Role;
  unit_id: number | null;
  online: boolean;
  open_tickets: number;
}

// ---- Sprint 4 ----
export type FAQStatus = "draft" | "published" | "archived";

export interface FAQArticle {
  id: number;
  slug: string;
  title: string;
  body: string;
  category_id: number | null;
  category_name: string | null;
  unit_id: number | null;
  unit_name: string | null;
  language: Lang;
  tags: string[];
  status: FAQStatus;
  version: number;
  views: number;
  helpful_yes: number;
  helpful_no: number;
  helpful_pct: number | null;
  author: Brief | null;
  approved_by: number | null;
  source_request_id: string | null;
  created_at: string;
  updated_at: string;
  published_at: string | null;
}

export interface FAQVersion {
  id: number;
  version: number;
  title: string;
  body: string;
  language: string;
  status: string;
  editor: Brief | null;
  created_at: string;
}

export interface ReplyTemplate {
  id: number;
  title: string;
  body: string;
  category_id: number | null;
  category_name: string | null;
  unit_id: number | null;
  unit_name: string | null;
  language: Lang;
  usage_count: number;
  is_active: boolean;
  author_id: number | null;
  created_at: string;
  updated_at: string;
}

export interface SuggestionItem {
  id: string;
  source: "faq" | "similar_case";
  title: string;
  snippet: string;
  body: string | null;
  score: number;
  language: Lang;
  category: string | null;
  unit: string | null;
}

export interface SimilarOut {
  language: Lang;
  faq: SuggestionItem[];
  cases: SuggestionItem[];
}

export interface SmartReply {
  text: string;
  source: "template" | "similar_case" | "kb";
  source_id: string;
  title: string;
  score: number;
  language: Lang;
}

export interface ModelVersion {
  id: number;
  version: string;
  model_type: "classifier" | "priority";
  algorithm: string;
  accuracy: number;
  macro_f1: number;
  train_size: number;
  feedback_count: number;
  status: "active" | "candidate" | "archived";
  is_active: boolean;
  trained_at: string;
  activated_at: string | null;
  metrics: {
    per_class_f1?: Record<string, number>;
    confusion_matrix?: { labels: string[]; matrix: number[][] };
    test_size?: number;
    [k: string]: unknown;
  } | null;
}

export interface TrainingRun {
  id: number;
  status: "queued" | "running" | "done" | "failed";
  trigger: string;
  force: boolean;
  feedback_count: number;
  logs: string;
  result: Record<string, { version: string; macro_f1: number; promoted: boolean } | null> | null;
  error: string | null;
  created_at: string;
  started_at: string | null;
  finished_at: string | null;
}

export interface ReportJob {
  id: number;
  type: "excel" | "pdf";
  filters: Record<string, string | number>;
  status: "queued" | "running" | "done" | "failed";
  row_count: number | null;
  file_size: number | null;
  error: string | null;
  created_at: string;
  finished_at: string | null;
  download_url: string | null;
}
