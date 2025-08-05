import React, { useState } from 'react';
import Container from '@mui/material/Container';
import Box from '@mui/material/Box';
import Typography from '@mui/material/Typography';
import Button from '@mui/material/Button';
import TextField from '@mui/material/TextField';
import Paper from '@mui/material/Paper';
import CircularProgress from '@mui/material/CircularProgress';
import axios from 'axios';

interface ProcessFolderRequest {
  folder_path: string;
}

interface QueryRequest {
  question: string;
}

interface ApiResponse {
  status: string;
  message?: string;
  answer: string;
}

const App: React.FC = () => {
  const defaultFolderPath = import.meta.env.VITE_PROCESS_FOLDER_PATH || '/Shared/GraphRAG';
  const [folderPath, setFolderPath] = useState<string>(defaultFolderPath);
  const [question, setQuestion] = useState<string>('');
  const [answer, setAnswer] = useState<string>('');
  const [isProcessing, setIsProcessing] = useState<boolean>(false);
  const [isQuerying, setIsQuerying] = useState<boolean>(false);
  const [error, setError] = useState<string>('');

  const processFolder = async (): Promise<void> => {
    try {
      setIsProcessing(true);
      setError('');
      const response = await axios.post<ApiResponse>(
        '/api/process-folder',
        { folder_path: folderPath } as ProcessFolderRequest
      );
      console.log('Processing complete:', response.data);
    } catch (err) {
      console.error('Error processing folder:', err);
      const errorMessage = axios.isAxiosError(err)
        ? err.response?.data?.detail || 'Error processing folder'
        : 'An unknown error occurred';
      setError(errorMessage);
    } finally {
      setIsProcessing(false);
    }
  };

  const handleQuery = async (): Promise<void> => {
    if (!question.trim()) return;
    
    try {
      setIsQuerying(true);
      setError('');
      const response = await axios.post<ApiResponse>(
        '/api/query',
        { question } as QueryRequest
      );
      
      // Handle simplified response structure
      if (response.data.answer) {
        setAnswer(response.data.answer);
      } else {
        setAnswer('No answer found');
      }
    } catch (err) {
      console.error('Error querying:', err);
      const errorMessage = axios.isAxiosError(err)
        ? err.response?.data?.detail || 'Error executing query'
        : 'An unknown error occurred';
      setError(errorMessage);
    } finally {
      setIsQuerying(false);
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

      <Paper sx={{ p: 3, mb: 4 }} elevation={3}>
        <Typography variant="h6" gutterBottom>
          Process Documents
        </Typography>
        <Box sx={{ display: 'flex', gap: 2, mb: 2 }}>
          <TextField
            fullWidth
            label="Folder Path"
            variant="outlined"
            value={folderPath}
            onChange={(e: React.ChangeEvent<HTMLInputElement>) => 
              setFolderPath(e.target.value)
            }
            size="small"
          />
          <Button
            variant="contained"
            onClick={processFolder}
            disabled={isProcessing}
            sx={{ minWidth: 150 }}
          >
            {isProcessing ? <CircularProgress size={24} /> : 'Process Folder'}
          </Button>
        </Box>
      </Paper>

      <Paper sx={{ p: 3 }} elevation={3}>
        <Typography variant="h6" gutterBottom>
          Query Knowledge Graph
        </Typography>
        <Box sx={{ display: 'flex', gap: 2, mb: 2 }}>
          <TextField
            fullWidth
            label="Ask a question"
            variant="outlined"
            value={question}
            onChange={(e: React.ChangeEvent<HTMLInputElement>) => 
              setQuestion(e.target.value)
            }
            onKeyPress={(e: React.KeyboardEvent) => 
              e.key === 'Enter' && handleQuery()
            }
            size="small"
          />
          <Button
            variant="contained"
            color="secondary"
            onClick={handleQuery}
            disabled={isQuerying || !question.trim()}
            sx={{ minWidth: 150 }}
          >
            {isQuerying ? <CircularProgress size={24} /> : 'Ask'}
          </Button>
        </Box>
        
        {answer && (
          <Paper sx={{ p: 2, mt: 2, bgcolor: 'background.paper' }} elevation={0}>
            <Typography variant="body1" component="div">
              <strong>Answer:</strong> {answer}
            </Typography>
          </Paper>
        )}
        
        {error && (
          <Typography color="error" sx={{ mt: 2 }}>
            {error}
          </Typography>
        )}
      </Paper>
    </Container>
  );
};

export default App;
