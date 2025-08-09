export interface IngestRequest {
  data_source: string;
  paths?: string[];
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

export interface ProcessFolderRequest {
  folder_path: string;
}

export interface QueryRequest {
  query: string;
  query_type?: string;
  top_k?: number;
}

export interface ApiResponse {
  status: string;
  message?: string;
  error?: string;
  answer?: string;
  results?: any[];
}

// New async processing response
export interface AsyncProcessingResponse {
  processing_id: string;
  status: 'started' | 'processing' | 'completed' | 'failed';
  message: string;
  progress?: number;
  estimated_time?: string;
  started_at?: string;
  updated_at?: string;
  error?: string;
}

// Processing status check response
export interface ProcessingStatusResponse {
  processing_id: string;
  status: 'started' | 'processing' | 'completed' | 'failed';
  message: string;
  progress: number;
  started_at: string;
  updated_at: string;
  error?: string;
}