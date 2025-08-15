import React, { useState, useEffect, useCallback, useMemo } from 'react';
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
  status: 'started' | 'processing' | 'completed' | 'failed';
  message: string;
  progress: number;
  started_at: string;
  updated_at: string;
  error?: string;
}

const App: React.FC = () => {
  // Default values
  const defaultFolderPath = import.meta.env.VITE_PROCESS_FOLDER_PATH || '/Shared/GraphRAG';
  
  // Data source state
  const [dataSource, setDataSource] = useState<string>('filesystem');
  const [folderPath, setFolderPath] = useState<string>(defaultFolderPath);
  
  // CMIS state - use environment variables with fallback
  const [cmisUrl, setCmisUrl] = useState<string>(`${import.meta.env.VITE_CMIS_BASE_URL || 'http://localhost:8080'}/alfresco/api/-default-/public/cmis/versions/1.1/atom`);
  const [cmisUsername, setCmisUsername] = useState<string>('admin');
  const [cmisPassword, setCmisPassword] = useState<string>('admin');
  
  // Alfresco state - use environment variables with fallback
  const [alfrescoUrl, setAlfrescoUrl] = useState<string>(`${import.meta.env.VITE_ALFRESCO_BASE_URL || 'http://localhost:8080'}/alfresco`);
  const [alfrescoUsername, setAlfrescoUsername] = useState<string>('admin');
  const [alfrescoPassword, setAlfrescoPassword] = useState<string>('admin');
  
  // Query state
  const [activeTab, setActiveTab] = useState<string>('search');
  const [question, setQuestion] = useState<string>('');
  const [searchResults, setSearchResults] = useState<any[]>([]);
  const [qaAnswer, setQaAnswer] = useState<string>('');
  const [hasSearched, setHasSearched] = useState<boolean>(false);
  const [lastSearchQuery, setLastSearchQuery] = useState<string>('');
  
  // UI state
  const [isProcessing, setIsProcessing] = useState<boolean>(false);
  const [isQuerying, setIsQuerying] = useState<boolean>(false);
  const [successMessage, setSuccessMessage] = useState<string>('');
  const [error, setError] = useState<string>('');
  const [processingStatus, setProcessingStatus] = useState<string>('');
  const [processingProgress, setProcessingProgress] = useState<number>(0);
  const [currentProcessingId, setCurrentProcessingId] = useState<string | null>(null);
  const [statusData, setStatusData] = useState<any>(null);

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
  }, [dataSource]);

  // Polling function for processing status
  const pollProcessingStatus = useCallback(async (processingId: string) => {
    try {
      const response = await axios.get<ProcessingStatusResponse>(`/api/processing-status/${processingId}`);
      const status = response.data;
      
      setProcessingStatus(status.message);
      setProcessingProgress(status.progress);
      setStatusData(status);  // Store full status for enhanced progress display
      
      if (status.status === 'completed') {
        setIsProcessing(false);
        setProcessingStatus('');
        setProcessingProgress(0);
        setCurrentProcessingId(null);
        setSuccessMessage(status.message || 'Documents ingested successfully!');
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
      case 'filesystem':
        return folderPath.trim() !== '';
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
      
      const request: IngestRequest = {
        data_source: dataSource
      };

      if (dataSource === 'filesystem') {
        request.paths = [folderPath];
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

  const renderDataSourceFields = () => {
    switch (dataSource) {
      case 'filesystem':
        return (
          <TextField
            fullWidth
            label="Folder Path (file or directory)"
            variant="outlined"
            value={folderPath}
            onChange={(e) => setFolderPath(e.target.value)}
            size="small"
            sx={{ mb: 2 }}
            placeholder="e.g., C:\Documents\reports or /home/user/docs/report.pdf"
          />
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

  return (
    <Container maxWidth="lg" sx={{ py: 4 }}>
      <Box sx={{ mb: 4 }}>
        <Typography variant="h3" component="h1" gutterBottom>
          Flexible GraphRAG (React)
        </Typography>
        <Typography variant="subtitle1" color="text.secondary">
          Process and query documents with AI-powered knowledge graph
        </Typography>
      </Box>

      {/* Document Processing Section */}
      <Paper sx={{ p: 3, mb: 4 }} elevation={3}>
        <Typography variant="h6" gutterBottom>
          Process Documents
        </Typography>
        
        <FormControl fullWidth sx={{ mb: 2 }}>
          <InputLabel>Data Source</InputLabel>
          <Select
            value={dataSource}
            label="Data Source"
            onChange={(e) => setDataSource(e.target.value)}
            size="small"
          >
            <MenuItem value="filesystem">File System</MenuItem>
            <MenuItem value="cmis">CMIS Repository</MenuItem>
            <MenuItem value="alfresco">Alfresco Repository</MenuItem>
          </Select>
        </FormControl>
        
        {renderDataSourceFields()}
        
        {/* Processing Status */}
        {isProcessing && (
          <Box sx={{ mt: 2, mb: 2 }}>
            <Box display="flex" alignItems="center" mb={1}>
              <CircularProgress size={20} sx={{ mr: 1 }} />
              <Typography variant="body2">
                {processingStatus || 'Processing documents...'}
              </Typography>
            </Box>
            <LinearProgress 
              variant="determinate" 
              value={processingProgress} 
              sx={{ mb: 1 }} 
            />
            <Typography variant="caption" color="text.secondary">
              {processingProgress}% complete
              {statusData?.file_progress && (
                <Box sx={{ mt: 0.5 }}>
                  {statusData.file_progress}
                </Box>
              )}
              {statusData?.current_file && (
                <Box sx={{ mt: 0.5 }}>
                  Processing: {statusData.current_file.split(/[/\\]/).pop()}
                </Box>
              )}
              {statusData?.current_phase && (
                <Box sx={{ mt: 0.5 }}>
                  Phase: {statusData.current_phase}
                </Box>
              )}
              {statusData?.estimated_time_remaining && (
                <Box sx={{ mt: 0.5 }}>
                  Time remaining: {statusData.estimated_time_remaining}
                </Box>
              )}
            </Typography>
            <Box sx={{ mt: 2 }}>
              <Button
                variant="outlined"
                color="error"
                onClick={cancelProcessing}
                disabled={!currentProcessingId}
                size="small"
              >
                Cancel Processing
              </Button>
            </Box>
          </Box>
        )}
        
        <Button
          variant="contained"
          onClick={processDocuments}
          disabled={!isFormValid() || isProcessing}
          sx={{ minWidth: 200 }}
        >
          {isProcessing ? 'Processing...' : 'Ingest Documents'}
        </Button>
        
        {successMessage && (
          <Alert severity="success" sx={{ mt: 2 }}>
            {successMessage}
          </Alert>
        )}
      </Paper>

      {/* Query Section */}
      <Paper sx={{ p: 3 }} elevation={3}>
        <Typography variant="h6" gutterBottom>
          Search and Query
        </Typography>
        
        <TabContext value={activeTab}>
          <Box sx={{ borderBottom: 1, borderColor: 'divider', mb: 2 }}>
            <Tabs value={activeTab} onChange={(e, newValue) => {
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
        
        {error && (
          <Alert severity="error" sx={{ mt: 2 }}>
            {error}
          </Alert>
        )}
      </Paper>
    </Container>
  );
};

export default App;