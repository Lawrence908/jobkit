export interface Job {
  id: number;
  url: string | null;
  company: string;
  role: string;
  location: string;
  status: string;
  slug: string;
  keywords: string[];
  source: string;
  created_at: string | null;
  updated_at: string | null;
  /** From job.json: word count of parsed description (only on GET /api/jobs/:id). */
  description_word_count?: number;
  /** First ~400 chars of description (only on GET /api/jobs/:id). */
  description_preview?: string | null;
  /** Full job description for editing (only on GET /api/jobs/:id). */
  raw_body?: string | null;
}

export interface MeResponse {
  username: string;
}
