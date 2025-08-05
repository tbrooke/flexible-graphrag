export interface ProcessFolderRequest {
  folder_path: string;
}

export interface QueryRequest {
  question: string;
}

export interface ApiResponse<T = any> {
  status: string;
  message?: string;
  answer: string;
}

export interface ProcessFolderResponse extends ApiResponse {}

export interface QueryResponse extends ApiResponse {}
