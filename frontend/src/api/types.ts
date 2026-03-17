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
