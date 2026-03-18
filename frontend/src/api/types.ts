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
