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
}

export interface MeResponse {
  username: string;
}
