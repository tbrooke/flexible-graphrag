<template>
  <v-card class="pa-4 mb-4">
    <v-card-title>Process Documents</v-card-title>
    <v-card-text>
      <!-- Data Source Selection -->
      <v-select
        v-model="dataSource"
        :items="dataSourceOptions"
        label="Data Source"
        variant="outlined"
        class="mb-4"
        :disabled="isProcessing"
      ></v-select>

      <!-- File System Fields -->
      <template v-if="dataSource === 'filesystem'">
        <v-text-field
          v-model="folderPath"
          label="Folder Path (file or directory)"
          variant="outlined"
          :disabled="isProcessing"
          class="mb-4"
          placeholder="e.g., C:\Documents\reports or /home/user/docs/report.pdf"
        ></v-text-field>
      </template>

      <!-- CMIS Fields -->
      <template v-if="dataSource === 'cmis'">
        <v-text-field
          v-model="cmisUrl"
          label="CMIS Repository URL"
          variant="outlined"
          :disabled="isProcessing"
          class="mb-4"
          placeholder="e.g., http://localhost:8080/alfresco/api/-default-/public/cmis/versions/1.1/atom"
        ></v-text-field>
        <v-row>
          <v-col cols="6">
            <v-text-field
              v-model="cmisUsername"
              label="Username"
              variant="outlined"
              :disabled="isProcessing"
              class="mb-4"
            ></v-text-field>
          </v-col>
          <v-col cols="6">
            <v-text-field
              v-model="cmisPassword"
              label="Password"
              type="password"
              variant="outlined"
              :disabled="isProcessing"
              class="mb-4"
            ></v-text-field>
          </v-col>
        </v-row>
        <v-text-field
          v-model="folderPath"
          label="Folder Path"
          variant="outlined"
          :disabled="isProcessing"
          class="mb-4"
          placeholder="e.g., /Sites/example/documentLibrary"
        ></v-text-field>
      </template>

      <!-- Alfresco Fields -->
      <template v-if="dataSource === 'alfresco'">
        <v-text-field
          v-model="alfrescoUrl"
          label="Alfresco Base URL"
          variant="outlined"
          :disabled="isProcessing"
          class="mb-4"
          placeholder="e.g., http://localhost:8080/alfresco"
        ></v-text-field>
        <v-row>
          <v-col cols="6">
            <v-text-field
              v-model="alfrescoUsername"
              label="Username"
              variant="outlined"
              :disabled="isProcessing"
              class="mb-4"
            ></v-text-field>
          </v-col>
          <v-col cols="6">
            <v-text-field
              v-model="alfrescoPassword"
              label="Password"
              type="password"
              variant="outlined"
              :disabled="isProcessing"
              class="mb-4"
            ></v-text-field>
          </v-col>
        </v-row>
        <v-text-field
          v-model="folderPath"
          label="Path"
          variant="outlined"
          :disabled="isProcessing"
          class="mb-4"
          placeholder="e.g., /Sites/example/documentLibrary"
        ></v-text-field>
      </template>

      <v-btn
        color="primary"
        @click="handleProcessFolder"
        :disabled="!isFormValid || isProcessing"
        :loading="isProcessing"
        size="large"
      >
        Ingest Documents
      </v-btn>

      <v-alert
        v-if="error"
        type="error"
        class="mt-4"
      >
        {{ error }}
      </v-alert>

      <v-alert
        v-if="success"
        type="success"
        class="mt-4"
      >
        {{ success }}
      </v-alert>
    </v-card-text>
  </v-card>
</template>

<script setup lang="ts">
import { ref, computed, watch } from 'vue';
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

interface ApiResponse {
  status: string;
  message?: string;
  error?: string;
}

const emit = defineEmits<{
  (e: 'processed', payload: { dataSource: string, path?: string }): void;
}>();

// Get folder path from environment variables or use default
const defaultFolderPath = import.meta.env.VITE_PROCESS_FOLDER_PATH || '/Shared/GraphRAG';

// Data source options
const dataSourceOptions = [
  { title: 'File System', value: 'filesystem' },
  { title: 'CMIS Repository', value: 'cmis' },
  { title: 'Alfresco Repository', value: 'alfresco' }
];

// Define reactive variables
const dataSource = ref('filesystem');
const folderPath = ref(defaultFolderPath);

// CMIS fields
const cmisUrl = ref('http://localhost:8080/alfresco/api/-default-/public/cmis/versions/1.1/atom');
const cmisUsername = ref('admin');
const cmisPassword = ref('admin');

// Alfresco fields
const alfrescoUrl = ref('http://localhost:8080/alfresco');
const alfrescoUsername = ref('admin');
const alfrescoPassword = ref('admin');

// UI state
const isProcessing = ref(false);
const error = ref('');
const success = ref('');

// Computed property for form validation
const isFormValid = computed(() => {
  switch (dataSource.value) {
    case 'filesystem':
      return folderPath.value.trim() !== '';
    case 'cmis':
      return folderPath.value.trim() !== '' && 
             cmisUrl.value.trim() !== '' && 
             cmisUsername.value.trim() !== '' && 
             cmisPassword.value.trim() !== '';
    case 'alfresco':
      return folderPath.value.trim() !== '' && 
             alfrescoUrl.value.trim() !== '' && 
             alfrescoUsername.value.trim() !== '' && 
             alfrescoPassword.value.trim() !== '';
    default:
      return false;
  }
});

// Clear messages when data source changes
watch(dataSource, () => {
  error.value = '';
  success.value = '';
});

const processFolder = async (): Promise<boolean> => {
  if (!isFormValid.value || isProcessing.value) return false;
  
  try {
    isProcessing.value = true;
    error.value = '';
    success.value = '';
    
    console.log('Sending request to process documents with data source:', dataSource.value);
    
    const request: IngestRequest = {
      data_source: dataSource.value
    };

    if (dataSource.value === 'filesystem') {
      request.paths = [folderPath.value];
    } else if (dataSource.value === 'cmis') {
      request.paths = [folderPath.value];
      request.cmis_config = {
        url: cmisUrl.value,
        username: cmisUsername.value,
        password: cmisPassword.value,
        folder_path: folderPath.value
      };
    } else if (dataSource.value === 'alfresco') {
      request.paths = [folderPath.value];
      request.alfresco_config = {
        url: alfrescoUrl.value,
        username: alfrescoUsername.value,
        password: alfrescoPassword.value,
        path: folderPath.value
      };
    }
    
    const response = await axios({
      method: 'post',
      url: '/api/ingest',
      data: request,
      headers: {
        'Content-Type': 'application/json',
        'Accept': 'application/json'
      }
    });
    
    console.log('Response received:', response);
    
    if (response.data.status === 'success') {
      success.value = response.data.message || 'Documents ingested successfully!';
      emit('processed', { 
        dataSource: dataSource.value, 
        path: folderPath.value 
      });
      return true;
    } else {
      error.value = response.data.error || response.data.message || 'Error ingesting documents';
      return false;
    }
  } catch (err: any) {
    console.error('Error processing documents:', {
      message: err.message,
      response: err.response?.data,
      status: err.response?.status,
      headers: err.response?.headers
    });
    error.value = err.response?.data?.detail || err.response?.data?.error || 'Error processing documents';
    return false;
  } finally {
    isProcessing.value = false;
  }
};

const handleProcessFolder = (event: Event) => {
  event.preventDefault();
  processFolder();
};
</script>