export interface ProcessFolderRequest {
    folder_path: string;
  }
  
  export interface QueryRequest {
    question: string;
  }
  
  export interface ApiResponse {
    status: string;
    message?: string;
    answer: string;
  }