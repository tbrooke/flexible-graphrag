import React, { useState, useEffect, useCallback, useMemo, useRef } from 'react';
import Container from '@mui/material/Container';
import Box from '@mui/material/Box';
import Typography from '@mui/material/Typography';
import Button from '@mui/material/Button';
import TextField from '@mui/material/TextField';
import LinearProgress from '@mui/material/LinearProgress';
import Paper from '@mui/material/Paper';
import CircularProgress from '@mui/material/CircularProgress';
import FormControl from '@mui/material/FormControl';
import InputLabel from '@mui/material/InputLabel';
import Select from '@mui/material/Select';
import MenuItem from '@mui/material/MenuItem';
import Alert from '@mui/material/Alert';
import Tabs from '@mui/material/Tabs';
import Tab from '@mui/material/Tab';
import TabPanel from '@mui/lab/TabPanel';
import TabContext from '@mui/lab/TabContext';

import Table from '@mui/material/Table';
import TableBody from '@mui/material/TableBody';
import TableCell from '@mui/material/TableCell';
import TableContainer from '@mui/material/TableContainer';
import TableHead from '@mui/material/TableHead';
import TableRow from '@mui/material/TableRow';
import Checkbox from '@mui/material/Checkbox';
import IconButton from '@mui/material/IconButton';
import DeleteIcon from '@mui/icons-material/Delete';
import CloseIcon from '@mui/icons-material/Close';
import Chip from '@mui/material/Chip';
import SendIcon from '@mui/icons-material/Send';
import PersonIcon from '@mui/icons-material/Person';
import agentIcon from './agent.png';

import QuestionAnswerIcon from '@mui/icons-material/QuestionAnswer';
import List from '@mui/material/List';
import ListItem from '@mui/material/ListItem';

import Avatar from '@mui/material/Avatar';
import Divider from '@mui/material/Divider';
import axios from 'axios';

interface IngestRequest {
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

interface QueryRequest {
  query: string;
  query_type?: string;
  top_k?: number;
}

interface ApiResponse {
  success?: boolean;  // Used by search endpoint
  status?: string;    // Used by ingest endpoint
  message?: string;
  error?: string;
  answer?: string;
  results?: any[];
}

// New async processing response
interface AsyncProcessingResponse {
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
interface ProcessingStatusResponse {
  processing_id: string;
  status: 'started' | 'processing' | 'completed' | 'failed' | 'cancelled';
  message: string;
  progress: number;
  started_at: string;
  updated_at: string;
  error?: string;
  individual_files?: Array<{
    filename: string;
    status: string;
    progress: number;
    phase: string;
    message?: string;
    error?: string;
    started_at?: string;
    completed_at?: string;
  }>;
  current_file?: string;
  current_phase?: string;
  files_completed?: number;
  total_files?: number;
  estimated_time_remaining?: string;
}

interface ChatMessage {
  id: string;
  type: 'user' | 'assistant';
  content: string;
  timestamp: Date;
  queryType?: 'search' | 'qa';
  results?: any[];
  isLoading?: boolean;
}

const App: React.FC = () => {
  // Default values
  const defaultFolderPath = import.meta.env.VITE_PROCESS_FOLDER_PATH || '/Shared/GraphRAG';
  
  // Main tab state
  const [mainTab, setMainTab] = useState<string>('sources');
  
  // Data source state
  const [dataSource, setDataSource] = useState<string>('upload');
  const [folderPath, setFolderPath] = useState<string>(defaultFolderPath);
  
  // File upload state
  const [selectedFiles, setSelectedFiles] = useState<File[]>([]);
  const [uploadProgress, setUploadProgress] = useState<number>(0);
  const [isUploading, setIsUploading] = useState<boolean>(false);
  const [isDragOver, setIsDragOver] = useState<boolean>(false);
  
  // File table state
  const [selectedFileIndices, setSelectedFileIndices] = useState<Set<number>>(new Set());
  
  // CMIS state - use environment variables with fallback
  const [cmisUrl, setCmisUrl] = useState<string>(`${import.meta.env.VITE_CMIS_BASE_URL || 'http://localhost:8080'}/alfresco/api/-default-/public/cmis/versions/1.1/atom`);
  const [cmisUsername, setCmisUsername] = useState<string>('admin');
  const [cmisPassword, setCmisPassword] = useState<string>('admin');
  
  // Alfresco state - use environment variables with fallback
  const [alfrescoUrl, setAlfrescoUrl] = useState<string>(`${import.meta.env.VITE_ALFRESCO_BASE_URL || 'http://localhost:8080'}/alfresco`);
  const [alfrescoUsername, setAlfrescoUsername] = useState<string>('admin');
  const [alfrescoPassword, setAlfrescoPassword] = useState<string>('admin');
  
  // Query state (legacy - keeping for Search tab)
  const [activeTab, setActiveTab] = useState<string>('search');
  const [question, setQuestion] = useState<string>('');
  const [searchResults, setSearchResults] = useState<any[]>([]);
  const [qaAnswer, setQaAnswer] = useState<string>('');
  const [hasSearched, setHasSearched] = useState<boolean>(false);
  const [lastSearchQuery, setLastSearchQuery] = useState<string>('');
  
  // Chat state
  const [chatMessages, setChatMessages] = useState<ChatMessage[]>([]);
  const [chatInput, setChatInput] = useState<string>('');
  const chatContainerRef = useRef<HTMLDivElement>(null);
  
  // UI state
  const [isProcessing, setIsProcessing] = useState<boolean>(false);
  const [isQuerying, setIsQuerying] = useState<boolean>(false);
  const [successMessage, setSuccessMessage] = useState<string>('');
  const [error, setError] = useState<string>('');
  const [processingStatus, setProcessingStatus] = useState<string>('');
  const [processingProgress, setProcessingProgress] = useState<number>(0);
  const [currentProcessingId, setCurrentProcessingId] = useState<string | null>(null);
  const [statusData, setStatusData] = useState<any>(null);
  const [lastStatusData, setLastStatusData] = useState<any>(null); // Keep last status for debugging

  const [showDebugPanel, setShowDebugPanel] = useState<boolean>(false); // Control debug panel visibility
  const [hasConfiguredSources, setHasConfiguredSources] = useState<boolean>(false); // Track if user has configured sources
  const [configuredDataSource, setConfiguredDataSource] = useState<string>(''); // Track which data source was configured
  const [configuredFiles, setConfiguredFiles] = useState<File[]>([]); // Store files that were configured for processing

  // Memoized placeholder values (safer than using import.meta.env in JSX)
  const cmisPlaceholder = useMemo(() => {
    const baseUrl = import.meta.env.VITE_CMIS_BASE_URL || 'http://localhost:8080';
    return `e.g., ${baseUrl}/alfresco/api/-default-/public/cmis/versions/1.1/atom`;
  }, []);

  const alfrescoPlaceholder = useMemo(() => {
    const baseUrl = import.meta.env.VITE_ALFRESCO_BASE_URL || 'http://localhost:8080';
    return `e.g., ${baseUrl}/alfresco`;
  }, []);

  // Clear messages when data source changes
  useEffect(() => {
    setError('');
    setSuccessMessage('');
    setProcessingStatus('');
    setProcessingProgress(0);
    setHasConfiguredSources(false); // Reset configuration flag when data source changes
    setConfiguredDataSource(''); // Reset configured data source
    setConfiguredFiles([]); // Reset configured files
  }, [dataSource]);

  // Polling function for processing status
  const pollProcessingStatus = useCallback(async (processingId: string) => {
    try {
      const response = await axios.get<ProcessingStatusResponse>(`/api/processing-status/${processingId}`);
      const status = response.data;
      
      setProcessingStatus(status.message);
      setProcessingProgress(status.progress);
      setStatusData(status);  // Store full status for enhanced progress display
      setLastStatusData(status); // Always keep the last status for debugging
      
      // Debug: Log the status data to see what we're getting
      console.log('Processing status data:', status);
      
      // Save to localStorage for persistence
      localStorage.setItem('lastProcessingStatus', JSON.stringify(status));
      
      // Individual files data is now handled automatically in getFileProgressData
      
      // Special logging for completion
      if (status.status === 'completed') {
        console.log('FINAL STATUS (COMPLETED):', JSON.stringify(status, null, 2));
        console.log('Individual files data:', status.individual_files);
      }
      
      if (status.status === 'completed') {
        setIsProcessing(false);
        setProcessingStatus('');
        setProcessingProgress(0);
        setCurrentProcessingId(null);
        setSuccessMessage(status.message || 'Documents ingested successfully!');
        // Keep per-file progress visible after completion
      } else if (status.status === 'failed') {
        setIsProcessing(false);
        setProcessingStatus('');
        setProcessingProgress(0);
        setCurrentProcessingId(null);
        setError(status.error || 'Processing failed');
      } else if (status.status === 'cancelled') {
        setIsProcessing(false);
        setProcessingStatus('');
        setProcessingProgress(0);
        setCurrentProcessingId(null);
        setSuccessMessage('Processing cancelled successfully');
      } else if (status.status === 'started' || status.status === 'processing') {
        // Continue polling
        setTimeout(() => pollProcessingStatus(processingId), 2000);
      }
    } catch (err) {
      console.error('Error checking processing status:', err);
      setError('Error checking processing status');
      setIsProcessing(false);
      setCurrentProcessingId(null);
    }
  }, []);

  const cancelProcessing = async (): Promise<void> => {
    if (!currentProcessingId) return;
    
    try {
      const response = await axios.post(`/api/cancel-processing/${currentProcessingId}`, {});
      
      if (response.data.success) {
        // Success will be handled by the polling status check
      } else {
        setError('Failed to cancel processing');
        setSuccessMessage('');
      }
    } catch (err) {
      console.error('Error cancelling processing:', err);
      const errorMessage = axios.isAxiosError(err)
        ? err.response?.data?.detail || err.response?.data?.error || 'Error cancelling processing'
        : 'An unknown error occurred';
      setError(errorMessage);
      setSuccessMessage('');
    }
  };

  const isFormValid = (): boolean => {
    switch (dataSource) {
      case 'upload':
        return selectedFiles.length > 0;
      case 'cmis':
        return folderPath.trim() !== '' && 
               cmisUrl.trim() !== '' && 
               cmisUsername.trim() !== '' && 
               cmisPassword.trim() !== '';
      case 'alfresco':
        return folderPath.trim() !== '' && 
               alfrescoUrl.trim() !== '' && 
               alfrescoUsername.trim() !== '' && 
               alfrescoPassword.trim() !== '';
      default:
        return false;
    }
  };

  const processDocuments = async (): Promise<void> => {
    if (!isFormValid() || isProcessing) return;
    
    try {
      setIsProcessing(true);
      setError('');
      setSuccessMessage('');
      // Clear previous status data when starting new ingest
      setStatusData(null);
      setLastStatusData(null);
      
      const request: IngestRequest = {
        data_source: dataSource
      };

      if (dataSource === 'filesystem') {
        request.paths = [folderPath];
      } else if (dataSource === 'upload') {
        // Upload files first, then use their paths
        const uploadedPaths = await uploadFiles();
        request.paths = uploadedPaths;
        request.data_source = 'filesystem'; // Use filesystem processing for uploaded files
      } else if (dataSource === 'cmis') {
        request.paths = [folderPath];
        request.cmis_config = {
          url: cmisUrl,
          username: cmisUsername,
          password: cmisPassword,
          folder_path: folderPath
        };
      } else if (dataSource === 'alfresco') {
        request.paths = [folderPath];
        request.alfresco_config = {
          url: alfrescoUrl,
          username: alfrescoUsername,
          password: alfrescoPassword,
          path: folderPath
        };
      }

      const response = await axios.post<AsyncProcessingResponse>('/api/ingest', request);
      
      // Handle async processing response
      if (response.data.status === 'started') {
        setProcessingStatus(response.data.message);
        setProcessingProgress(0);
        setCurrentProcessingId(response.data.processing_id);
        setSuccessMessage(`Processing started: ${response.data.estimated_time || 'Please wait...'}`);
        // Start polling for status
        setTimeout(() => pollProcessingStatus(response.data.processing_id), 2000);
      } else if (response.data.status === 'completed') {
        setIsProcessing(false);
        setSuccessMessage('Documents ingested successfully!');
      } else if (response.data.status === 'failed') {
        setIsProcessing(false);
        setError(response.data.error || 'Processing failed');
      }
    } catch (err) {
      console.error('Error processing documents:', err);
      const errorMessage = axios.isAxiosError(err)
        ? err.response?.data?.detail || err.response?.data?.error || 'Error processing documents'
        : 'An unknown error occurred';
      setError(errorMessage);
      setIsProcessing(false);
      setCurrentProcessingId(null);
    }
  };

  const handleSearch = async (): Promise<void> => {
    if (!question.trim() || isQuerying) return;
    
    try {
      setIsQuerying(true);
      setError('');
      setSearchResults([]);
      setQaAnswer('');
      setLastSearchQuery(question);
      
      const queryType = activeTab === 'search' ? 'hybrid' : 'qa';
      const request: QueryRequest = {
        query: question,
        query_type: queryType,
        top_k: 10
      };
      
      const response = await axios.post<ApiResponse>('/api/search', request);
      
      if (response.data.success) {
        setHasSearched(true);
        if (activeTab === 'search' && response.data.results) {
          setSearchResults(response.data.results);
        } else if (activeTab === 'qa' && response.data.answer) {
          setQaAnswer(response.data.answer);
        }
      } else {
        setHasSearched(true);
        setError(response.data.error || 'Error executing query');
      }
    } catch (err) {
      console.error('Error querying:', err);
      const errorMessage = axios.isAxiosError(err)
        ? err.response?.data?.detail || err.response?.data?.error || 'Error executing query'
        : 'An unknown error occurred';
      setError(errorMessage);
      setHasSearched(true);
    } finally {
      setIsQuerying(false);
    }
  };

  const handleFileSelect = (event: React.ChangeEvent<HTMLInputElement>) => {
    const files = event.target.files;
    if (files) {
      const fileArray = Array.from(files);
      setSelectedFiles(fileArray);
      // Auto-select all uploaded files
      setSelectedFileIndices(new Set(fileArray.map((_, index) => index)));
    }
  };

  const handleFileDrop = (event: React.DragEvent<HTMLDivElement>) => {
    event.preventDefault();
    event.stopPropagation();
    setIsDragOver(false);
    
    const files = event.dataTransfer.files;
    if (files) {
      const fileArray = Array.from(files);
      setSelectedFiles(fileArray);
      // Auto-select all uploaded files
      setSelectedFileIndices(new Set(fileArray.map((_, index) => index)));
    }
  };

  const handleDragOver = (event: React.DragEvent<HTMLDivElement>) => {
    event.preventDefault();
    event.stopPropagation();
    
    // Set drag effect for better visual feedback
    if (event.dataTransfer) {
      event.dataTransfer.dropEffect = 'copy';
    }
  };

  const handleDragEnter = (event: React.DragEvent<HTMLDivElement>) => {
    event.preventDefault();
    event.stopPropagation();
    setIsDragOver(true);
    
    // Improve drag feedback by setting custom drag effect
    if (event.dataTransfer) {
      event.dataTransfer.dropEffect = 'copy';
    }
  };

  const handleDragLeave = (event: React.DragEvent<HTMLDivElement>) => {
    event.preventDefault();
    event.stopPropagation();
    
    // Only set drag over to false if we're leaving the drop zone entirely
    const rect = event.currentTarget.getBoundingClientRect();
    const x = event.clientX;
    const y = event.clientY;
    
    if (x < rect.left || x > rect.right || y < rect.top || y > rect.bottom) {
      setIsDragOver(false);
    }
  };

  const removeFile = (index: number) => {
    setSelectedFiles(prev => prev.filter((_, i) => i !== index));
  };

  const formatFileSize = (bytes: number): string => {
    if (bytes < 1024) {
      // Windows-style: anything under 1KB shows as "1 KB" (rounded up)
      return bytes === 0 ? "0 B" : "1 KB";
    } else if (bytes < 1024 * 1024) {
      // Round up to next KB like Windows
      return `${Math.ceil(bytes / 1024)} KB`;
    } else {
      // Round to 1 decimal place for MB
      return `${(bytes / 1024 / 1024).toFixed(1)} MB`;
    }
  };

  const getPhaseDisplayName = (phase: string): string => {
    const phaseNames: { [key: string]: string } = {
      'ready': 'Ready',
      'waiting': 'Waiting',
      'docling': 'Converting',
      'chunking': 'Chunking',
      'kg_extraction': 'Extracting Graph',
      'indexing': 'Indexing',
      'completed': 'Completed',
      'error': 'Error'
    };
    return phaseNames[phase] || phase;
  };



  const uploadFiles = async (): Promise<string[]> => {
    if (selectedFiles.length === 0) return [];
    
    setIsUploading(true);
    setUploadProgress(0);
    
    try {
      const formData = new FormData();
      selectedFiles.forEach(file => {
        formData.append('files', file);
      });
      
      const response = await axios.post('/api/upload', formData, {
        headers: {
          'Content-Type': 'multipart/form-data',
        },
        onUploadProgress: (progressEvent) => {
          if (progressEvent.total) {
            const progress = Math.round((progressEvent.loaded * 100) / progressEvent.total);
            setUploadProgress(progress);
          }
        },
      });
      
      if (response.data.success) {
        // Show information about skipped files if any
        if (response.data.skipped && response.data.skipped.length > 0) {
          const skippedInfo = response.data.skipped
            .map((file: any) => `${file.filename}: ${file.reason}`)
            .join('\n');
          setError(`Some files were skipped:\n${skippedInfo}`);
        }
        // Update selectedFiles to use the saved filenames for progress matching
        const uploadedFiles = response.data.files.map((uploadedFile: any) => {
          // Find the original file and create a new file object with the saved filename
          const originalFile = selectedFiles.find(f => f.name === uploadedFile.filename);
          if (originalFile) {
            // Create a new File object with the saved filename
            const newFile = new File([originalFile], uploadedFile.saved_as, { type: originalFile.type });
            return newFile;
          }
          return originalFile;
        }).filter(Boolean);
        
        // Update selectedFiles with the new filenames
        setSelectedFiles(uploadedFiles);
        
        // Also update configuredFiles if they exist (for upload data source)
        if (configuredDataSource === 'upload') {
          setConfiguredFiles(uploadedFiles);
        }
        
        return response.data.files.map((file: any) => file.path);
      } else {
        throw new Error('Upload failed');
      }
    } finally {
      setIsUploading(false);
      setUploadProgress(0);
    }
  };

  // File table management functions
  const handleSelectAllFiles = (checked: boolean) => {
    if (checked) {
      setSelectedFileIndices(new Set(getDisplayFiles().map((_, index) => index)));
    } else {
      setSelectedFileIndices(new Set());
    }
  };

  const handleSelectFile = (index: number, checked: boolean) => {
    const newSelected = new Set(selectedFileIndices);
    if (checked) {
      newSelected.add(index);
    } else {
      newSelected.delete(index);
    }
    setSelectedFileIndices(newSelected);
  };

  const removeSelectedFiles = () => {
    if (configuredDataSource === 'upload') {
      // For upload files, remove from the configured files array
      const indicesToRemove = Array.from(selectedFileIndices).sort((a, b) => b - a);
      let newFiles = [...configuredFiles];
      indicesToRemove.forEach(index => {
        newFiles.splice(index, 1);
      });
      setConfiguredFiles(newFiles);
      // Also update selectedFiles if they match
      let newSelectedFiles = [...selectedFiles];
      indicesToRemove.forEach(index => {
        if (index < newSelectedFiles.length) {
          newSelectedFiles.splice(index, 1);
        }
      });
      setSelectedFiles(newSelectedFiles);
    } else {
      // For filesystem/CMIS/Alfresco, "removing" means unconfiguring the source
      setHasConfiguredSources(false);
      setConfiguredDataSource('');
      setConfiguredFiles([]);
      setSelectedFileIndices(new Set());
    }
    setSelectedFileIndices(new Set());
  };

  const getFileProgressData = (filename: string) => {
    const files = statusData?.individual_files || lastStatusData?.individual_files || [];
    
    // Debug logging in development
    if (process.env.NODE_ENV === 'development' && files.length > 0) {
      console.log('🔍 Looking for progress data for:', filename);
      console.log('📋 Available progress files:', files.map(f => f.filename));
      console.log('📁 Current display files:', getDisplayFiles().map(f => f.name));
    }
    
    // Try exact match first
    let match = files.find((file: any) => file.filename === filename);
    if (!match) {
      // Try matching just the basename if full path doesn't match
      match = files.find((file: any) => {
        const fileBasename = file.filename?.split(/[/\\]/).pop();
        return fileBasename === filename;
      });
    }
    if (!match) {
      // Try matching if our filename is contained in the stored filename
      match = files.find((file: any) => 
        file.filename?.includes(filename) || filename.includes(file.filename)
      );
    }
    
    if (process.env.NODE_ENV === 'development') {
      console.log('✅ Progress match for', filename, ':', match ? `Found (${match.progress}% - ${match.phase})` : 'NOT FOUND');
    }
    
    return match;
  };

  // Generate file entries for display based on data source type
  const getDisplayFiles = () => {
    if (!hasConfiguredSources) return [];
    
    if (configuredDataSource === 'upload') {
      // Show the files that were configured for processing
      return configuredFiles.map(file => ({
        name: file.name,
        size: file.size,
        type: 'file'
      }));
    } else if (configuredDataSource === 'cmis' || configuredDataSource === 'alfresco') {
      // For repositories, create a single entry representing the path
      return [{
        name: folderPath.split(/[/\\]/).pop() || folderPath,
        size: 0, // Unknown size for repositories
        type: 'repository'
      }];
    }
    return [];
  };

  // Check if there are files ready to process
  const hasFilesToProcess = () => {
    if (!hasConfiguredSources) return false;
    
    if (configuredDataSource === 'upload') {
      // For upload, need at least one configured file selected
      return selectedFileIndices.size > 0 && configuredFiles.length > 0;
    } else {
      // For other sources, need at least one file selected if there are display files
      const displayFiles = getDisplayFiles();
      return displayFiles.length === 0 || selectedFileIndices.size > 0;
    }
  };

  // Auto-scroll to bottom of chat
  const scrollToBottom = () => {
    if (chatContainerRef.current) {
      chatContainerRef.current.scrollTop = chatContainerRef.current.scrollHeight;
    }
  };

  // Auto-scroll when messages change
  useEffect(() => {
    scrollToBottom();
  }, [chatMessages]);

  // Chat functionality
  const handleChatSubmit = async (): Promise<void> => {
    if (!chatInput.trim() || isQuerying) return;
    
    const userMessage: ChatMessage = {
      id: Date.now().toString(),
      type: 'user',
      content: chatInput.trim(),
      timestamp: new Date(),
      queryType: 'qa'
    };
    
    // Add user message
    setChatMessages(prev => [...prev, userMessage]);
    
    // Add loading assistant message
    const loadingMessage: ChatMessage = {
      id: (Date.now() + 1).toString(),
      type: 'assistant',
      content: '',
      timestamp: new Date(),
      queryType: 'qa',
      isLoading: true
    };
    setChatMessages(prev => [...prev, loadingMessage]);
    
    const currentInput = chatInput;
    setChatInput('');
    
    try {
      setIsQuerying(true);
      setError('');
      
      const request: QueryRequest = {
        query: currentInput,
        query_type: 'qa',
        top_k: 10
      };
      
      const response = await axios.post<ApiResponse>('/api/search', request);
      
      // Remove loading message and add response
      setChatMessages(prev => {
        const withoutLoading = prev.filter(msg => msg.id !== loadingMessage.id);
        
        if (response.data.success) {
          const assistantMessage: ChatMessage = {
            id: (Date.now() + 2).toString(),
            type: 'assistant',
            content: response.data.answer || 'No answer provided',
            timestamp: new Date(),
            queryType: 'qa'
          };
          return [...withoutLoading, assistantMessage];
        } else {
          const errorMessage: ChatMessage = {
            id: (Date.now() + 2).toString(),
            type: 'assistant',
            content: `Error: ${response.data.error || 'Unknown error occurred'}`,
            timestamp: new Date(),
            queryType: 'qa'
          };
          return [...withoutLoading, errorMessage];
        }
      });
    } catch (err) {
      console.error('Error in chat query:', err);
      const errorMessage = axios.isAxiosError(err)
        ? err.response?.data?.detail || err.response?.data?.error || 'Error executing query'
        : 'An unknown error occurred';
      
      // Remove loading message and add error
      setChatMessages(prev => {
        const withoutLoading = prev.filter(msg => msg.id !== loadingMessage.id);
        const errorMsg: ChatMessage = {
          id: (Date.now() + 2).toString(),
          type: 'assistant',
          content: `Error: ${errorMessage}`,
          timestamp: new Date(),
          queryType: 'qa'
        };
        return [...withoutLoading, errorMsg];
      });
    } finally {
      setIsQuerying(false);
    }
  };

  const clearChatHistory = () => {
    setChatMessages([]);
  };

  const renderDataSourceFields = () => {
    switch (dataSource) {

      case 'upload':
        return (
          <Box sx={{ mb: 2 }}>
            <Box
              sx={{
                border: isDragOver ? '2px solid #1976d2' : '2px dashed #ccc',
                borderRadius: 2,
                p: 3,
                textAlign: 'center',
                cursor: 'pointer',
                backgroundColor: isDragOver ? '#e3f2fd' : '#1976d2',
                transition: 'all 0.2s ease-in-out',
                '&:hover': {
                  borderColor: isDragOver ? '#1976d2' : '#999',
                  backgroundColor: isDragOver ? '#e3f2fd' : '#f9f9f9',
                  '& .MuiTypography-root': {
                    color: isDragOver ? '#1976d2' : '#333333'
                  }
                }
              }}
              onDrop={handleFileDrop}
              onDragOver={handleDragOver}
              onDragEnter={handleDragEnter}
              onDragLeave={handleDragLeave}
              onClick={() => document.getElementById('file-input')?.click()}
            >
              <Typography variant="h6" gutterBottom sx={{ color: isDragOver ? '#1976d2' : '#ffffff' }}>
                Drop files here or click to select
              </Typography>
              <Typography variant="body2" sx={{ color: isDragOver ? '#1976d2' : '#ffffff' }}>
                Supports: PDF, DOCX, XLSX, PPTX, TXT, MD, HTML, CSV, PNG, JPG
              </Typography>
              <input
                id="file-input"
                type="file"
                multiple
                accept=".pdf,.docx,.xlsx,.pptx,.txt,.md,.html,.csv,.png,.jpg,.jpeg"
                onChange={handleFileSelect}
                aria-label="Select files to upload"
                style={{ display: 'none' }}
              />
            </Box>
            
            {selectedFiles.length > 0 && (
              <Box sx={{ mt: 2 }}>
                <Typography variant="subtitle2" gutterBottom>
                  Selected Files ({selectedFiles.length}):
                </Typography>
                {selectedFiles.map((file, index) => (
                  <Box key={index} sx={{ 
                    display: 'flex', 
                    alignItems: 'center', 
                    justifyContent: 'space-between',
                    p: 1,
                    border: '1px solid #e0e0e0',
                    borderRadius: 1,
                    mb: 1
                  }}>
                    <Box>
                      <Typography variant="body2">{file.name}</Typography>
                      <Typography variant="caption" color="text.secondary">
                        {formatFileSize(file.size)}
                      </Typography>
                    </Box>
                    <Button
                      size="small"
                      color="error"
                      onClick={() => removeFile(index)}
                    >
                      Remove
                    </Button>
                  </Box>
                ))}
              </Box>
            )}
            
            {isUploading && (
              <Box sx={{ mt: 2 }}>
                <Typography variant="body2" gutterBottom>
                  Uploading files... {uploadProgress}%
                </Typography>
                <LinearProgress variant="determinate" value={uploadProgress} />
              </Box>
            )}
          </Box>
        );
      
      case 'cmis':
        return (
          <>
            <TextField
              fullWidth
              label="CMIS Repository URL"
              variant="outlined"
              value={cmisUrl}
              onChange={(e) => setCmisUrl(e.target.value)}
              size="small"
              sx={{ mb: 2 }}
              placeholder={cmisPlaceholder}
            />
            <Box sx={{ display: 'flex', gap: 2, mb: 2 }}>
              <TextField
                fullWidth
                label="Username"
                variant="outlined"
                value={cmisUsername}
                onChange={(e) => setCmisUsername(e.target.value)}
                size="small"
              />
              <TextField
                fullWidth
                label="Password"
                type="password"
                variant="outlined"
                value={cmisPassword}
                onChange={(e) => setCmisPassword(e.target.value)}
                size="small"
              />
            </Box>
            <TextField
              fullWidth
              label="Folder Path"
              variant="outlined"
              value={folderPath}
              onChange={(e) => setFolderPath(e.target.value)}
              size="small"
              sx={{ mb: 2 }}
              placeholder="e.g., /Sites/example/documentLibrary"
            />
          </>
        );
      
      case 'alfresco':
        return (
          <>
            <TextField
              fullWidth
              label="Alfresco Base URL"
              variant="outlined"
              value={alfrescoUrl}
              onChange={(e) => setAlfrescoUrl(e.target.value)}
              size="small"
              sx={{ mb: 2 }}
              placeholder={alfrescoPlaceholder}
            />
            <Box sx={{ display: 'flex', gap: 2, mb: 2 }}>
              <TextField
                fullWidth
                label="Username"
                variant="outlined"
                value={alfrescoUsername}
                onChange={(e) => setAlfrescoUsername(e.target.value)}
                size="small"
              />
              <TextField
                fullWidth
                label="Password"
                type="password"
                variant="outlined"
                value={alfrescoPassword}
                onChange={(e) => setAlfrescoPassword(e.target.value)}
                size="small"
              />
            </Box>
            <TextField
              fullWidth
              label="Path"
              variant="outlined"
              value={folderPath}
              onChange={(e) => setFolderPath(e.target.value)}
              size="small"
              sx={{ mb: 2 }}
              placeholder="e.g., /Sites/example/documentLibrary"
            />
          </>
        );
      
      default:
        return null;
    }
  };

  const renderSourcesTab = () => (
    <Box sx={{ p: 3 }}>
      <Typography variant="h6" gutterBottom>
        Data Source Configuration
      </Typography>
      
      <FormControl fullWidth sx={{ mb: 2 }}>
        <InputLabel>Data Source</InputLabel>
        <Select
          value={dataSource}
          label="Data Source"
          onChange={(e) => setDataSource(e.target.value)}
          size="small"
        >
          <MenuItem value="upload">File Upload</MenuItem>
          <MenuItem value="cmis">CMIS Repository</MenuItem>
          <MenuItem value="alfresco">Alfresco Repository</MenuItem>
        </Select>
      </FormControl>
      
      {renderDataSourceFields()}
      
      <Box sx={{ display: 'flex', gap: 1, alignItems: 'center', mt: 2 }}>
        <Button
          variant="contained"
          onClick={() => {
            setHasConfiguredSources(true);
            setConfiguredDataSource(dataSource);
            // Save current files for upload data source
            if (dataSource === 'upload') {
              setConfiguredFiles([...selectedFiles]);
            } else {
              setConfiguredFiles([]);
              // For filesystem/CMIS/Alfresco, auto-select the single entry
              setSelectedFileIndices(new Set([0]));
            }
            setMainTab('processing');
          }}
          disabled={!isFormValid()}
          sx={{ minWidth: 200 }}
        >
          Configure Processing →
        </Button>
      </Box>
    </Box>
  );

  const renderProcessingTab = () => (
    <Box sx={{ p: 3 }}>
      <Typography variant="h6" gutterBottom>
        File Processing
      </Typography>
      
      {/* Show prompt only when not configured */}
      {!hasConfiguredSources && (
        <Paper sx={{ p: 3, mb: 3, textAlign: 'center', bgcolor: '#e8f4fd', border: '1px solid #b3d9ff' }}>
          <Typography variant="h6" sx={{ color: '#333333', fontWeight: 600 }} gutterBottom>
            No Data Source Configured
          </Typography>
          <Typography variant="body2" sx={{ color: '#555555', mb: 2 }}>
            Please go to the Sources tab to configure your data source first.
          </Typography>
          <Button
            variant="outlined"
            onClick={() => setMainTab('sources')}
            color="primary"
          >
            ← Go to Sources
          </Button>
        </Paper>
      )}
      
      {/* File Table - Show for all configured sources */}
      {hasConfiguredSources && (
        <TableContainer component={Paper} sx={{ mb: 3 }}>
          <Table size="small">
            <TableHead>
              <TableRow>
                <TableCell padding="checkbox" sx={{ width: 50 }}>
                  <Checkbox
                    indeterminate={selectedFileIndices.size > 0 && selectedFileIndices.size < getDisplayFiles().length}
                    checked={getDisplayFiles().length > 0 && selectedFileIndices.size === getDisplayFiles().length}
                    onChange={(e) => handleSelectAllFiles(e.target.checked)}
                  />
                </TableCell>
                <TableCell sx={{ width: 200 }}>Filename</TableCell>
                <TableCell sx={{ width: 100 }}>File Size</TableCell>
                <TableCell sx={{ minWidth: 400 }}>Progress</TableCell>
                <TableCell sx={{ width: 50 }}>×</TableCell>
                <TableCell sx={{ width: 100 }}>Status</TableCell>

              </TableRow>
            </TableHead>
            <TableBody>
              {getDisplayFiles().map((file, index) => {
                const progressData = getFileProgressData(file.name);
                const isSelected = selectedFileIndices.has(index);
                
                return (
                  <TableRow key={index} selected={isSelected}>
                    <TableCell padding="checkbox">
                      <Checkbox
                        checked={isSelected}
                        onChange={(e) => handleSelectFile(index, e.target.checked)}
                      />
                    </TableCell>
                    <TableCell>
                      <Typography variant="body2" noWrap title={file.name}>
                        {file.name}
                      </Typography>
                    </TableCell>
                    <TableCell>
                      <Typography variant="caption">
                        {file.size > 0 ? formatFileSize(file.size) : 
                         file.type === 'path' ? 'Folder' : 
                         file.type === 'repository' ? 'Repository' : '-'}
                      </Typography>
                    </TableCell>
                    <TableCell>
                      <Box sx={{ display: 'flex', alignItems: 'center', width: '100%' }}>
                        <Box sx={{ width: '100%', mr: 1 }}>
                          <Box
                            sx={{
                              width: '100%',
                              height: 8,
                              borderRadius: 4,
                              backgroundColor: '#e0e0e0',
                              position: 'relative',
                              overflow: 'hidden'
                            }}
                          >
                            <Box
                              sx={{
                                width: `${Math.max(progressData?.progress || 0, 2)}%`, // Always show at least 2%
                                height: '100%',
                                backgroundColor: '#1976d2',
                                borderRadius: 4,
                                transition: 'width 0.3s ease'
                              }}
                            />
                          </Box>
                        </Box>
                        <Typography variant="caption" sx={{ minWidth: 100, ml: 1, color: '#333333' }}>
                          {progressData?.progress || 0}% - {getPhaseDisplayName(progressData?.phase || 'ready')}

                        </Typography>
                      </Box>
                    </TableCell>
                    <TableCell>
                      {file.type === 'file' ? (
                        <IconButton
                          size="small"
                          onClick={() => removeFile(index)}
                          color="error"
                        >
                          <CloseIcon fontSize="small" />
                        </IconButton>
                      ) : (
                        <Typography variant="caption" color="text.secondary">-</Typography>
                      )}
                    </TableCell>
                    <TableCell>
                      <Chip
                        label={progressData?.status || 'ready'}
                        size="small"
                        color={
                          progressData?.status === 'completed' ? 'success' :
                          progressData?.status === 'failed' ? 'error' :
                          progressData?.status === 'processing' ? 'primary' : 'default'
                        }
                      />
                    </TableCell>

                  </TableRow>
                );
              })}
            </TableBody>
          </Table>
        </TableContainer>
      )}
      
      {/* Upload Progress */}
      {isUploading && (
        <Box sx={{ mb: 2 }}>
          <Typography variant="body2" gutterBottom>
            Uploading files... {uploadProgress}%
          </Typography>
          <LinearProgress variant="determinate" value={uploadProgress} />
        </Box>
      )}
      
      {/* Processing Status */}
      {isProcessing && (
        <Box sx={{ mb: 2 }}>
          <Box display="flex" alignItems="center" justifyContent="space-between" mb={2}>
            <Box display="flex" alignItems="center">
              <CircularProgress size={20} sx={{ mr: 1 }} />
              <Typography variant="body2">
                {processingStatus || 'Processing documents...'}
              </Typography>
            </Box>
            <Button 
              variant="outlined" 
              color="error" 
              size="small" 
              onClick={cancelProcessing}
              disabled={!currentProcessingId}
            >
              Cancel
            </Button>
          </Box>
          
          <Box sx={{ mb: 2 }}>
            <LinearProgress 
              variant="determinate" 
              value={processingProgress} 
              sx={{ mb: 1 }} 
            />
            <Typography variant="caption" color="text.secondary">
              Overall Progress: {processingProgress}% complete
              {statusData?.estimated_time_remaining && (
                <span> • Est. time remaining: {statusData.estimated_time_remaining}</span>
              )}
            </Typography>
          </Box>
        </Box>
      )}
      
      {/* Action Buttons */}
      <Box sx={{ display: 'flex', gap: 2, alignItems: 'center' }}>
        <Button
          variant="contained"
          onClick={processDocuments}
          disabled={!isFormValid() || isProcessing || !hasConfiguredSources || !hasFilesToProcess()}
          sx={{ minWidth: 200 }}
        >
          {isProcessing ? 'Processing...' : 
           !hasConfiguredSources ? 'Configure Sources First' :
           !hasFilesToProcess() ? 'Select Files to Process' :
           'Start Processing'}
        </Button>
        
        {selectedFileIndices.size > 0 && getDisplayFiles().length > 0 && (
          <Button
            variant="outlined"
            color="error"
            startIcon={<DeleteIcon />}
            onClick={removeSelectedFiles}
          >
            Remove Selected ({selectedFileIndices.size})
          </Button>
        )}
        
        {/* Debug toggle */}
        <Button
          variant="text"
          size="small"
          onDoubleClick={() => setShowDebugPanel(!showDebugPanel)}
          sx={{ 
            minWidth: 'auto', 
            color: 'transparent',
            '&:hover': { color: '#666' }
          }}
          title="Double-click to toggle debug panel"
        >
          🔧
        </Button>
      </Box>
      
      {/* Debug Panel */}
      {showDebugPanel && (statusData || isProcessing || lastStatusData) && (
        <Box sx={{ 
          mt: 2, 
          p: 2, 
          bgcolor: '#2d3748', 
          border: '1px solid #4a5568',
          borderRadius: 1,
          fontSize: '0.8rem', 
          fontFamily: 'monospace',
          color: '#ffffff'
        }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '8px' }}>
            <strong>Debug Status Data {!statusData && lastStatusData ? '(LAST STATUS)' : '(CURRENT)'}:</strong>
            <button 
              onClick={() => {
                const saved = localStorage.getItem('lastProcessingStatus');
                if (saved) {
                  const parsed = JSON.parse(saved);
                  setLastStatusData(parsed);
                  console.log('Retrieved from localStorage:', parsed);
                } else {
                  console.log('No saved status found in localStorage');
                }
              }}
              style={{ 
                fontSize: '0.7rem', 
                padding: '2px 6px', 
                backgroundColor: '#4a5568', 
                color: 'white', 
                border: '1px solid #718096',
                borderRadius: '3px',
                cursor: 'pointer'
              }}
            >
              Load Last
            </button>
          </div>
          <pre style={{ 
            fontSize: '0.7rem', 
            margin: '4px 0', 
            backgroundColor: '#1a202c',
            color: '#e2e8f0',
            padding: '8px',
            borderRadius: '4px',
            overflow: 'auto',
            maxHeight: '200px'
          }}>
            {JSON.stringify(statusData || lastStatusData, null, 2)}
          </pre>
        </Box>
      )}
      
      {successMessage && (
        <Alert severity="success" sx={{ mt: 2 }}>
          {successMessage}
        </Alert>
      )}
    </Box>
  );

  const renderSearchTab = () => (
    <Box sx={{ p: 3 }}>

      
      <TabContext value={activeTab}>
        <Box sx={{ borderBottom: 1, borderColor: 'divider', mb: 2 }}>
          <Tabs value={activeTab} onChange={(_, newValue) => {
            setActiveTab(newValue);
            setSearchResults([]);
            setQaAnswer('');
            setError('');
            setHasSearched(false);
            setLastSearchQuery('');
          }}>
            <Tab label="Hybrid Search" value="search" />
            <Tab label="Q&A Query" value="qa" />
          </Tabs>
        </Box>
        
        <Box sx={{ display: 'flex', gap: 2, mb: 2 }}>
          <TextField
            fullWidth
            label={activeTab === 'search' ? 'Search terms' : 'Ask a question'}
            variant="outlined"
            value={question}
            onChange={(e) => setQuestion(e.target.value)}
            onKeyPress={(e) => e.key === 'Enter' && handleSearch()}
            size="small"
            placeholder={activeTab === 'search' 
              ? 'e.g., machine learning algorithms' 
              : 'e.g., What are the key findings?'
            }
          />
          <Button
            variant="contained"
            color="secondary"
            onClick={handleSearch}
            disabled={isQuerying || !question.trim()}
            sx={{ minWidth: 150 }}
          >
            {isQuerying ? <CircularProgress size={24} /> : (activeTab === 'search' ? 'Search' : 'Ask')}
          </Button>
        </Box>
        
        <TabPanel value="search" sx={{ p: 0 }}>
          {searchResults.length > 0 && (
            <Box sx={{ mt: 2 }}>
              <Typography variant="h6" gutterBottom>
                Search Results ({searchResults.length})
              </Typography>
              {searchResults.map((result, index) => (
                <Paper key={index} sx={{ p: 2, mb: 2 }} elevation={1}>
                  <Typography variant="body2" color="text.secondary" gutterBottom>
                    <strong>Source:</strong> {result.metadata?.source || 'Unknown'} | 
                    <strong> Score:</strong> {result.score?.toFixed(3) || 'N/A'}
                  </Typography>
                  <Typography variant="body1">
                    {result.text || result.content || 'No content available'}
                  </Typography>
                </Paper>
              ))}
            </Box>
          )}
          {hasSearched && searchResults.length === 0 && !isQuerying && (
            <Paper sx={{ p: 3, mt: 2, textAlign: 'center' }} elevation={1}>
              <Typography variant="h6" color="text.secondary" gutterBottom>
                No results found
              </Typography>
              <Typography variant="body1" color="text.secondary">
                No results found for "{lastSearchQuery}". Try different search terms.
              </Typography>
            </Paper>
          )}
        </TabPanel>
        
        <TabPanel value="qa" sx={{ p: 0 }}>
          {qaAnswer && (
            <Paper sx={{ p: 2, mt: 2, bgcolor: 'background.paper' }} elevation={1}>
              <Typography variant="body1" component="div">
                <strong>Answer:</strong> {qaAnswer}
              </Typography>
            </Paper>
          )}
        </TabPanel>
      </TabContext>
    </Box>
  );

  const renderChatTab = () => (
    <Box sx={{ p: 3, height: 'calc(100vh - 200px)', display: 'flex', flexDirection: 'column' }}>
      {/* Header */}
      <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 2 }}>
        <Typography variant="h6">
          Chat Interface
        </Typography>
        <Box sx={{ display: 'flex', gap: 1, alignItems: 'center' }}>
          <Chip
            icon={<QuestionAnswerIcon />}
            label="Q&A Mode"
            color="primary"
            variant="outlined"
          />
          <Button
            variant="outlined"
            size="small"
            onClick={clearChatHistory}
            disabled={chatMessages.length === 0}
          >
            Clear History
          </Button>
        </Box>
      </Box>

      {/* Chat Messages */}
      <Paper 
        ref={chatContainerRef}
        sx={{ 
          flex: 1, 
          p: 2, 
          mb: 2, 
          overflowY: 'auto',
          bgcolor: '#f8f9fa',
          border: '1px solid #e0e0e0'
        }}
      >
        {chatMessages.length === 0 ? (
          <Box sx={{ 
            display: 'flex', 
            flexDirection: 'column', 
            alignItems: 'center', 
            justifyContent: 'center', 
            height: '100%',
            color: '#666666'
          }}>
            <img 
              src={agentIcon} 
              alt="Assistant" 
              style={{ 
                width: 48, 
                height: 48, 
                opacity: 0.5, 
                marginBottom: 16,
                backgroundColor: 'transparent',
                borderRadius: '50%'
              }} 
            />
            <Typography variant="h6" gutterBottom sx={{ color: '#333333', fontWeight: 600 }}>
              Welcome to Flexible GraphRAG Chat
            </Typography>
            <Typography variant="body2" textAlign="center" sx={{ color: '#555555' }}>
              Ask questions about your documents and get conversational answers.
              <br />
              The AI will provide detailed responses based on your processed documents.
            </Typography>
          </Box>
        ) : (
          <List sx={{ p: 0 }}>
            {chatMessages.map((message, index) => (
              <React.Fragment key={message.id}>
                <ListItem 
                  sx={{ 
                    display: 'flex', 
                    flexDirection: message.type === 'user' ? 'row-reverse' : 'row',
                    alignItems: 'flex-start',
                    px: 1,
                    py: 1
                  }}
                >
                  <Avatar 
                    sx={{ 
                      bgcolor: message.type === 'user' ? '#1976d2' : '#4caf50',
                      mx: 1,
                      width: 32,
                      height: 32
                    }}
                  >
                    {message.type === 'user' ? (
                      <PersonIcon />
                    ) : (
                      <img 
                        src={agentIcon} 
                        alt="Assistant" 
                        style={{ 
                          width: 28, 
                          height: 28, 
                          backgroundColor: 'transparent',
                          borderRadius: '50%'
                        }}
                      />
                    )}
                  </Avatar>
                  
                  <Box sx={{ 
                    maxWidth: message.type === 'user' ? '70%' : '80%',
                    bgcolor: message.type === 'user' ? '#e3f2fd' : '#ffffff',
                    borderRadius: 2,
                    p: 2,
                    border: '1px solid #e0e0e0',
                    color: '#000000'
                  }}>
                    {message.isLoading ? (
                      <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                        <CircularProgress size={16} />
                        <Typography variant="body2" color="text.secondary">
                          Thinking...
                        </Typography>
                      </Box>
                    ) : (
                      <>
                        <Typography variant="body1" sx={{ mb: 1 }}>
                          {message.content}
                        </Typography>

                        
                        <Typography variant="caption" sx={{ display: 'block', mt: 1, color: '#333333', fontWeight: 500 }}>
                          {message.timestamp.toLocaleTimeString()}
                        </Typography>
                      </>
                    )}
                  </Box>
                </ListItem>
                {index < chatMessages.length - 1 && <Divider sx={{ my: 1 }} />}
              </React.Fragment>
            ))}
          </List>
        )}
      </Paper>

      {/* Input Area */}
      <Box sx={{ display: 'flex', gap: 1, alignItems: 'flex-end' }}>
        <TextField
          fullWidth
          multiline
          maxRows={3}
          value={chatInput}
          onChange={(e) => setChatInput(e.target.value)}
          onKeyPress={(e) => {
            if (e.key === 'Enter' && !e.shiftKey) {
              e.preventDefault();
              handleChatSubmit();
            }
          }}
          placeholder="Ask a question... (e.g., 'What are the key findings about AI?')"
          variant="outlined"
          size="small"
          disabled={isQuerying}
          sx={{ 
            '& .MuiOutlinedInput-root': {
              borderRadius: 2
            }
          }}
        />
        <IconButton
          color="primary"
          onClick={handleChatSubmit}
          disabled={!chatInput.trim() || isQuerying}
          sx={{ 
            bgcolor: 'primary.main',
            color: 'white',
            '&:hover': { bgcolor: 'primary.dark' },
            '&:disabled': { 
              bgcolor: 'primary.main',
              color: 'white',
              opacity: 0.4
            },
            width: 48,
            height: 48
          }}
        >
          {isQuerying ? <CircularProgress size={20} color="inherit" /> : <SendIcon />}
        </IconButton>
      </Box>
      
      <Typography variant="caption" color="text.secondary" sx={{ mt: 1, textAlign: 'center' }}>
        Press Enter to send, Shift+Enter for new line • 
        Q&A mode: Provides conversational answers
      </Typography>
    </Box>
  );



  return (
    <Container maxWidth="xl" sx={{ py: 4 }}>
      <Box sx={{ mb: 4 }}>
        <Typography variant="h5" component="h1" gutterBottom>
          Flexible GraphRAG (React)
        </Typography>
      </Box>

      <Paper sx={{ mb: 4 }} elevation={3}>
        <TabContext value={mainTab}>
          <Box sx={{ borderBottom: 1, borderColor: 'divider' }}>
            <Tabs 
              value={mainTab} 
              onChange={(_, newValue) => setMainTab(newValue)}
              variant="fullWidth"
              sx={{
                '& .MuiTab-root': {
                  fontWeight: 500,
                  textTransform: 'none',
                  letterSpacing: '0.5px',
                },
                '& .MuiTab-root.Mui-selected': {
                  backgroundColor: '#1976d2',
                  color: 'white !important',
                },
                '& .MuiTabs-indicator': {
                  height: 3,
                  backgroundColor: '#1976d2',
                },
              }}
            >
              <Tab label="Sources" value="sources" />
              <Tab label="Processing" value="processing" />
              <Tab label="Search" value="search" />
              <Tab label="Chat" value="chat" />
              {/* <Tab label="Graph" value="graph" /> */}
            </Tabs>
          </Box>
          
          <TabPanel value="sources" sx={{ p: 0 }}>
            {renderSourcesTab()}
          </TabPanel>
          
          <TabPanel value="processing" sx={{ p: 0 }}>
            {renderProcessingTab()}
          </TabPanel>
          
          <TabPanel value="search" sx={{ p: 0 }}>
            {renderSearchTab()}
          </TabPanel>
          
          <TabPanel value="chat" sx={{ p: 0 }}>
            {renderChatTab()}
          </TabPanel>
          
          {/* <TabPanel value="graph" sx={{ p: 0 }}>
            {renderGraphTab()}
          </TabPanel> */}
        </TabContext>
      </Paper>
      
      {error && (
        <Alert severity="error" sx={{ mt: 2 }}>
          {error}
        </Alert>
      )}
    </Container>
  );
};

export default App;