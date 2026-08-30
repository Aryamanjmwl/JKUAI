export interface Source {
  citation_id: string;
  document_id: string;
  chunk_id: string;
  title: string;
  file_name: string;
  source_url: string | null;
  page_number: number | null;
  excerpt: string;
  score: number;
}

export interface SearchResult {
  answer: string;
  sources: Source[];
  exact_documents_used: string[];
  latency_ms: number;
}
