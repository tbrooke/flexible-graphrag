<template>
  <v-card class="pa-4 mb-4">
    <v-card-title>Process Folder</v-card-title>
    <v-card-text>
      <v-text-field
        v-model="folderPath"
        label="Folder Path"
        variant="outlined"
        :disabled="isProcessing"
        class="mb-4"
      ></v-text-field>
      <v-btn
        color="primary"
        @click="handleProcessFolder"
        :disabled="!folderPath.trim() || isProcessing"
        :loading="isProcessing"
      >
        {{ isProcessing ? 'Processing...' : 'Process Folder' }}
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
import { ref } from 'vue';
import axios from 'axios';
import type { ProcessFolderRequest, ApiResponse } from '../types/api';

const emit = defineEmits<{
  (e: 'processed', payload: { path: string }): void;
}>();

// Get folder path from environment variables or use default
const defaultFolderPath = import.meta.env.VITE_PROCESS_FOLDER_PATH || '/Shared/GraphRAG';

// Define reactive variables
const folderPath = ref(defaultFolderPath);
const isProcessing = ref(false);
const error = ref('');
const success = ref('');

const processFolder = async (): Promise<boolean> => {
  if (!folderPath.value.trim()) return false;
  
  try {
    isProcessing.value = true;
    error.value = '';
    success.value = '';
    
    console.log('Sending request to process folder:', folderPath.value);
    
    const response = await axios({
      method: 'post',
      url: '/api/process-folder',
      data: { folder_path: folderPath.value },
      headers: {
        'Content-Type': 'application/json',
        'Accept': 'application/json'
      }
    });
    
    console.log('Response received:', response);
    success.value = 'Folder processed successfully!';
    emit('processed', { path: folderPath.value });
    return true;
  } catch (err: any) {
    console.error('Error processing folder:', {
      message: err.message,
      response: err.response?.data,
      status: err.response?.status,
      headers: err.response?.headers
    });
    error.value = err.response?.data?.detail || 'Error processing folder';
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