export interface ProcessFolderRequest {
  folder_path: string;
}

export interface IngestRequest {
  paths?: string[];
  data_source?: string;
  cmis_config?: {
    url: string;
    username: string;
    password: string;
    folder_path: string;
  };
  alfresco_config?: {
    url: string;
    username: string;
    password: string;
    path: string;
  };
}

export interface QueryRequest {
  query: string;
  top_k?: number;
}

export interface SearchResult {
  rank: number;
  content: string;
  score: number;
  source: string;
  file_type: string;
  file_name: string;
}

export interface ApiResponse<T = any> {
  status: string;
  message?: string;
  answer?: string;
  results?: SearchResult[];
  system_status?: any;
}

export interface ProcessFolderResponse extends ApiResponse {}

export interface QueryResponse extends ApiResponse {}

export interface SearchResponse extends ApiResponse {
  results: SearchResult[];
}
