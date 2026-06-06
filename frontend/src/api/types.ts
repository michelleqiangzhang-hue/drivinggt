// Shared API types — keep in sync with backend/app/schemas.py

export type BlockStatus =
  | "planned"
  | "completed"
  | "partial"
  | "missed"
  | "unlogged";

export interface UserRead {
  id: number;
  email: string;
  name: string;
}

export interface LogRead {
  id: number;
  block_id: number | null;
  what_happened: string;
  category: string;
  subcategory: string | null;
  description: string | null;
  productive: boolean;
  actual_minutes: number | null;
  reason: string | null;
  start: string | null;
  end: string | null;
  created_at: string;
}

export interface BlockRead {
  id: number;
  title: string;
  category: string;
  subcategory: string | null;
  notes: string | null;
  start: string;
  end: string;
  status: BlockStatus;
  planned_minutes: number;
  log: LogRead | null;
}

export interface BlockCreate {
  title: string;
  category?: string;
  subcategory?: string | null;
  notes?: string | null;
  start: string;
  end: string;
}

export interface BlockUpdate {
  title?: string;
  category?: string;
  subcategory?: string | null;
  notes?: string | null;
  start?: string;
  end?: string;
  status?: BlockStatus;
}

export interface LogCreate {
  block_id?: number | null;
  what_happened: string;
  category?: string;
  subcategory?: string | null;
  description?: string | null;
  productive?: boolean;
  actual_minutes?: number | null;
  reason?: string | null;
  start?: string | null;
  end?: string | null;
}

export interface PlanRequest {
  text: string;
  date?: string | null;
}

export interface PlanResponse {
  blocks: BlockRead[];
  message: string;
  pattern_warnings: string[];
}

export interface ChatMessage {
  role: string;
  content: string;
}

export interface ChatRequest {
  conversation_id?: number | null;
  message: string;
}

export interface ChatResponse {
  conversation_id: number;
  reply: string;
  history: ChatMessage[];
}

export interface CategoryTotal {
  category: string;
  minutes: number;
}

export type Period = "day" | "week" | "month" | "year";

export interface GapSummary {
  period: Period;
  start: string;
  end: string;
  planned_minutes: number;
  logged_minutes: number;
  productive_minutes: number;
  unproductive_minutes: number;
  completed_blocks: number;
  partial_blocks: number;
  missed_blocks: number;
  unlogged_blocks: number;
  adherence_rate: number;
  planned_by_category: CategoryTotal[];
  actual_by_category: CategoryTotal[];
}

export interface PatternRead {
  id: number;
  category: string | null;
  summary: string;
  confidence: number;
  sample_size: number;
  suggestion: string | null;
  updated_at: string;
}

export interface GoalRead {
  id: number;
  title: string;
  horizon: string;
  target_category: string | null;
  achieved: boolean | null;
}

export interface GoalCreate {
  title: string;
  horizon?: string;
  target_category?: string | null;
}
