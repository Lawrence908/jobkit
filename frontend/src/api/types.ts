export interface Job {
  id: number;
  url: string | null;
  company: string;
  role: string;
  location: string;
  status: string;
  rejection_reason: string | null;
  slug: string;
  keywords: string[];
  source: string;
  source_platform?: string | null;
  work_arrangement?: string | null;
  applied_at?: string | null;
  first_response_at?: string | null;
  interview_at?: string | null;
  rejected_at?: string | null;
  offered_at?: string | null;
  withdrawn_at?: string | null;
  created_at: string | null;
  updated_at: string | null;
  description_word_count?: number;
  description_preview?: string | null;
  raw_body?: string | null;
  /** From list: tailored/generated content exists (resume, cover, notes). */
  has_generated_content?: boolean;
  /** From list: number of saved artifacts (PDFs, Drive links). */
  artifact_count?: number;
  /** Result of pushing this update to the user's Google Sheet tracker. Present on PATCH responses only. */
  sheet_sync?: {
    status: "synced" | "not_configured" | "failed";
    reason: string | null;
  };
}

/** Interview prep summary_json structure from API */
export interface InterviewPrepSummaryJson {
  likely_questions?: Record<string, string[]>;
  talking_points?: Record<string, string[]>;
  match_analysis?: {
    strongest_alignment?: string[];
    weakest_alignment?: string[];
    likely_probed_areas?: string[];
    missing_keywords?: string[];
  };
  star_responses?: Array<{
    prompt?: string;
    situation?: string;
    task?: string;
    action?: string;
    result?: string;
  }>;
  technical_prep?: {
    topics_to_review?: string[];
    tools_frameworks?: string[];
    system_design_themes?: string[];
    coding_areas?: string[];
  };
  questions_to_ask?: string[];
  personal_pitch?: string;
}

export interface InterviewPrepRecord {
  id: number;
  job_id: number;
  version: number;
  markdown_text: string;
  summary_json: InterviewPrepSummaryJson | null;
  created_at: string | null;
  updated_at: string | null;
}

export interface InterviewPrepVersionSummary {
  id: number;
  version: number;
  created_at: string | null;
}

/** Options for job dropdowns (from /api/jobs/options). */
export interface JobOptions {
  application_status: string[];
  rejection_reasons: string[];
}

/** Allowed exemplar role families (mirror backend exemplar_store.ROLE_FAMILIES). */
export const EXEMPLAR_ROLE_FAMILIES = [
  "devops_sre",
  "platform",
  "data_ml",
  "ai_llm",
  "backend",
  "infra",
  "other",
] as const;
export type ExemplarRoleFamily = (typeof EXEMPLAR_ROLE_FAMILIES)[number];

export const EXEMPLAR_SENIORITIES = ["mid", "senior"] as const;
export type ExemplarSeniority = (typeof EXEMPLAR_SENIORITIES)[number];

/** Request body for POST /api/jobs/{id}/promote-exemplar (admin only). */
export interface PromoteExemplarRequest {
  doc_type: "resume" | "cover_letter";
  role_family: ExemplarRoleFamily;
  seniority: ExemplarSeniority;
  target_role?: string;
  tags?: string[];
  quality_notes?: string;
  jd_summary?: string;
}

/** A stored exemplar record (frontmatter + body) returned by the promote endpoint. */
export interface ExemplarRecord {
  id: string;
  doc_type: string;
  role_family: string;
  seniority: string;
  target_role: string;
  jd_summary: string;
  tags: string[];
  quality_notes: string;
  body: string;
}

/** Response from POST /api/jobs/{id}/promote-exemplar. */
export interface PromoteExemplarResponse {
  ok: boolean;
  id: string;
  file: string;
  exemplar: ExemplarRecord;
}

export interface MeResponse {
  user_id: string;
  email: string | null;
}

/** Admin: invite code from API */
export interface InviteCode {
  id: number;
  code: string;
  label: string;
  max_uses: number;
  used_count: number;
  created_by: string | null;
  expires_at: string | null;
  is_active: boolean;
  created_at: string;
}

export interface InviteCodeCreate {
  code?: string;
  label?: string;
  max_uses?: number;
  expires_at?: string | null;
}

export interface InviteCodeUpdate {
  label?: string;
  max_uses?: number;
  expires_at?: string | null;
  is_active?: boolean;
}
