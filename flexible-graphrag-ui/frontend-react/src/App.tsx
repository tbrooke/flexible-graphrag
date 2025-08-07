import React, { useState, useEffect } from 'react';
import Container from '@mui/material/Container';
import Box from '@mui/material/Box';
import Typography from '@mui/material/Typography';
import Button from '@mui/material/Button';
import TextField from '@mui/material/TextField';
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

const App: React.FC = () => {
  // Default values
  const defaultFolderPath = import.meta.env.VITE_PROCESS_FOLDER_PATH || '/Shared/GraphRAG';
  
  // Data source state
  const [dataSource, setDataSource] = useState<string>('filesystem');
  const [folderPath, setFolderPath] = useState<string>(defaultFolderPath);
  
  // CMIS state
  const [cmisUrl, setCmisUrl] = useState<string>('http://localhost:8080/alfresco/api/-default-/public/cmis/versions/1.1/atom');
  const [cmisUsername, setCmisUsername] = useState<string>('admin');
  const [cmisPassword, setCmisPassword] = useState<string>('admin');
  
  // Alfresco state
  const [alfrescoUrl, setAlfrescoUrl] = useState<string>('http://localhost:8080/alfresco');
  const [alfrescoUsername, setAlfrescoUsername] = useState<string>('admin');
  const [alfrescoPassword, setAlfrescoPassword] = useState<string>('admin');
  
  // Query state
  const [activeTab, setActiveTab] = useState<string>('search');
  const [question, setQuestion] = useState<string>('');
  const [searchResults, setSearchResults] = useState<any[]>([]);
  const [qaAnswer, setQaAnswer] = useState<string>('');
  
  // UI state
  const [isProcessing, setIsProcessing] = useState<boolean>(false);
  const [isQuerying, setIsQuerying] = useState<boolean>(false);
  const [successMessage, setSuccessMessage] = useState<string>('');
  const [error, setError] = useState<string>('');

  // Clear messages when data source changes
  useEffect(() => {
    setError('');
    setSuccessMessage('');
  }, [dataSource]);

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

      const response = await axios.post<ApiResponse>('/api/ingest', request);
      
      // Check for both response formats: ingest uses 'status', search uses 'success'
      if (response.data.status === 'success' || response.data.success) {
        setSuccessMessage(response.data.message || 'Documents ingested successfully!');
      } else {
        setError(response.data.error || response.data.message || 'Error ingesting documents');
      }
    } catch (err) {
      console.error('Error processing documents:', err);
      const errorMessage = axios.isAxiosError(err)
        ? err.response?.data?.detail || err.response?.data?.error || 'Error processing documents'
        : 'An unknown error occurred';
      setError(errorMessage);
    } finally {
      setIsProcessing(false);
    }
  };

  const handleSearch = async (): Promise<void> => {
    if (!question.trim() || isQuerying) return;
    
    try {
      setIsQuerying(true);
      setError('');
      setSearchResults([]);
      setQaAnswer('');
      
      const queryType = activeTab === 'search' ? 'hybrid' : 'qa';
      const request: QueryRequest = {
        query: question,
        query_type: queryType,
        top_k: 10
      };
      
      const response = await axios.post<ApiResponse>('/api/search', request);
      
      if (response.data.success) {
        if (activeTab === 'search' && response.data.results) {
          setSearchResults(response.data.results);
        } else if (activeTab === 'qa' && response.data.answer) {
          setQaAnswer(response.data.answer);
        }
      } else {
        setError(response.data.error || 'Error executing query');
      }
    } catch (err) {
      console.error('Error querying:', err);
      const errorMessage = axios.isAxiosError(err)
        ? err.response?.data?.detail || err.response?.data?.error || 'Error executing query'
        : 'An unknown error occurred';
      setError(errorMessage);
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
              placeholder="e.g., http://localhost:8080/alfresco/api/-default-/public/cmis/versions/1.1/atom"
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
              placeholder="e.g., http://localhost:8080/alfresco"
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
        
        <Button
          variant="contained"
          onClick={processDocuments}
          disabled={!isFormValid() || isProcessing}
          sx={{ minWidth: 200 }}
        >
          {isProcessing ? <CircularProgress size={24} /> : 'Ingest Documents'}
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
            <Tabs value={activeTab} onChange={(e, newValue) => setActiveTab(newValue)}>
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