<template>
  <div class="pa-4">
    <h2 class="mb-4">File Processing</h2>

    <!-- No Sources Configured Message -->
    <v-card
      v-if="!hasConfiguredSources"
      class="pa-6 mb-4 text-center"
      color="blue-lighten-5"
      variant="outlined"
    >
      <h3 class="mb-2">No Data Source Configured</h3>
      <p class="mb-4">Please go to the Sources tab to configure your data source first.</p>
      <v-btn
        color="primary"
        variant="outlined"
        @click="$emit('go-to-sources')"
      >
        ← Go to Sources
      </v-btn>
    </v-card>

    <!-- File Processing Table -->
    <v-card v-if="hasConfiguredSources" class="mb-4" variant="outlined">
      <v-data-table
        v-model="selectedItems"
        :headers="tableHeaders"
        :items="displayFiles"
        item-value="index"
        show-select
        class="elevation-0"
        density="compact"
        :items-per-page="-1"
        hide-default-footer
      >
        <!-- Filename column -->
        <template #item.name="{ item }">
          <div class="text-truncate" style="max-width: 200px;" :title="item.name">
            {{ item.name }}
          </div>
        </template>

        <!-- File Size column -->
        <template #item.size="{ item }">
          <span class="text-caption">
            {{ item.size > 0 ? formatFileSize(item.size) : 
               item.type === 'repository' ? 'Repository' : '-' }}
          </span>
        </template>

        <!-- Progress column -->
        <template #item.progress="{ item }">
          <div class="d-flex align-center" style="width: 100%;">
            <div style="width: 100%; margin-right: 8px;">
              <v-progress-linear
                :model-value="Math.max(getFileProgress(item.name), 2)"
                color="primary"
                height="8"
                rounded
              ></v-progress-linear>
            </div>
            <span class="text-caption" style="min-width: 100px; margin-left: 8px;">
              {{ getFileProgress(item.name) }}% - {{ getFilePhase(item.name) }}
            </span>
          </div>
        </template>

        <!-- Remove column -->
        <template #item.remove="{ item }">
          <div class="text-center">
            <v-btn
              v-if="item.type === 'file'"
              icon="mdi-close"
              size="small"
              variant="text"
              color="error"
              @click="removeFile(item.index)"
            >
            </v-btn>
            <span v-else class="text-caption text-medium-emphasis">-</span>
          </div>
        </template>

        <!-- Status column -->
        <template #item.status="{ item }">
          <v-chip
            :color="getStatusColor(getFileStatus(item.name))"
            size="small"
            variant="flat"
          >
            {{ getFileStatus(item.name) }}
          </v-chip>
        </template>
      </v-data-table>
    </v-card>

    <!-- Upload Progress -->
    <v-card v-if="isUploading" class="pa-4 mb-4" color="blue-lighten-5">
      <p class="mb-2">Uploading files... {{ uploadProgress }}%</p>
      <v-progress-linear
        :model-value="uploadProgress"
        color="primary"
      ></v-progress-linear>
    </v-card>

    <!-- Processing Status -->
    <v-card v-if="isProcessing" class="pa-4 mb-4" color="blue-lighten-5">
      <div class="d-flex align-center justify-space-between mb-2">
        <div class="d-flex align-center">
          <v-progress-circular
            indeterminate
            size="20"
            width="2"
            color="primary"
            class="mr-2"
          ></v-progress-circular>
          <span>{{ processingStatus || 'Processing documents...' }}</span>
        </div>
        <v-btn
          color="error"
          variant="outlined"
          size="small"
          :disabled="!currentProcessingId"
          @click="cancelProcessing"
        >
          Cancel
        </v-btn>
      </div>
      
      <div class="mb-2">
        <v-progress-linear
          :model-value="processingProgress"
          color="primary"
          class="mb-1"
        ></v-progress-linear>
        <p class="text-caption text-medium-emphasis">
          Overall Progress: {{ processingProgress }}% complete
          <span v-if="statusData?.estimated_time_remaining">
            • Est. time remaining: {{ statusData.estimated_time_remaining }}
          </span>
        </p>
      </div>
    </v-card>

    <!-- Action Buttons -->
    <div class="d-flex align-center ga-4">
      <v-btn
        color="primary"
        size="large"
        :disabled="!canStartProcessing"
        :loading="isProcessing"
        @click="startProcessing"
      >
        {{ getProcessingButtonText }}
      </v-btn>

      <v-btn
        v-if="selectedItems.length > 0 && displayFiles.length > 0"
        color="error"
        variant="outlined"
        prepend-icon="mdi-delete"
        @click="removeSelectedFiles"
      >
        REMOVE SELECTED ({{ selectedItems.length }})
      </v-btn>

      <!-- Debug toggle -->
      <v-btn
        variant="text"
        size="small"
        style="min-width: auto; color: transparent;"
        title="Double-click to toggle debug panel"
        @dblclick="showDebugPanel = !showDebugPanel"
      >
        🔧
      </v-btn>
    </div>

    <!-- Debug Panel -->
    <v-card
      v-if="showDebugPanel && (statusData || isProcessing || lastStatusData)"
      class="pa-4 mt-4"
      color="grey-darken-4"
      theme="dark"
    >
      <div class="d-flex justify-space-between align-center mb-2">
        <strong>Debug Status Data {{ !statusData && lastStatusData ? '(LAST STATUS)' : '(CURRENT)' }}:</strong>
        <v-btn
          size="small"
          variant="outlined"
          @click="loadLastStatus"
        >
          Load Last
        </v-btn>
      </div>
      <pre class="text-caption" style="background-color: #1a1a1a; padding: 8px; border-radius: 4px; overflow: auto; max-height: 200px;">{{ JSON.stringify(statusData || lastStatusData, null, 2) }}</pre>
    </v-card>

    <!-- Success Message -->
    <v-alert
      v-if="successMessage"
      type="success"
      class="mt-4"
      closable
      @click:close="successMessage = ''"
    >
      {{ successMessage }}
    </v-alert>

    <!-- Error Message -->
    <v-alert
      v-if="error"
      type="error"
      class="mt-4"
      closable
      @click:close="error = ''"
    >
      {{ error }}
    </v-alert>
  </div>
</template>

<script lang="ts">
import { defineComponent, ref, computed, watch } from 'vue';
import axios from 'axios';

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

export default defineComponent({
  name: 'ProcessingTab',
  props: {
    hasConfiguredSources: {
      type: Boolean,
      required: true,
    },
    configuredDataSource: {
      type: String,
      required: true,
    },
    configuredFiles: {
      type: Array as () => File[],
      required: true,
    },
  },
  emits: ['go-to-sources', 'files-removed'],
  setup(props, { emit }) {
    // State
    const selectedItems = ref<number[]>([]);
    const isProcessing = ref(false);
    const isUploading = ref(false);
    const uploadProgress = ref(0);
    const processingProgress = ref(0);
    const processingStatus = ref('');
    const currentProcessingId = ref<string | null>(null);
    const statusData = ref<ProcessingStatusResponse | null>(null);
    const lastStatusData = ref<ProcessingStatusResponse | null>(null);
    const showDebugPanel = ref(false);
    const successMessage = ref('');
    const error = ref('');

    // Table headers
    const tableHeaders = [
      { title: 'Filename', key: 'name', width: '200px' },
      { title: 'File Size', key: 'size', width: '100px' },
      { title: 'Progress', key: 'progress', width: '400px', sortable: false },
      { title: '×', key: 'remove', width: '50px', sortable: false, align: 'center' },
      { title: 'Status', key: 'status', width: '100px' },
    ];

    // Computed
    const displayFiles = computed(() => {
      if (!props.hasConfiguredSources) return [];
      
      if (props.configuredDataSource === 'upload') {
        return props.configuredFiles.map((file, index) => ({
          index,
          name: file.name,
          size: file.size,
          type: 'file',
        }));
      } else if (props.configuredDataSource === 'cmis' || props.configuredDataSource === 'alfresco') {
        return [{
          index: 0,
          name: 'Repository Path',
          size: 0,
          type: 'repository',
        }];
      }
      return [];
    });

    const canStartProcessing = computed(() => {
      return props.hasConfiguredSources && selectedItems.value.length > 0 && !isProcessing.value;
    });

    const getProcessingButtonText = computed(() => {
      if (isProcessing.value) return 'PROCESSING...';
      if (!props.hasConfiguredSources) return 'CONFIGURE SOURCES FIRST';
      if (selectedItems.value.length === 0) return 'SELECT FILES TO PROCESS';
      return 'START PROCESSING';
    });

    // Methods
    const formatFileSize = (bytes: number): string => {
      if (bytes < 1024) {
        return bytes === 0 ? "0 B" : "1 KB";
      } else if (bytes < 1024 * 1024) {
        return `${Math.ceil(bytes / 1024)} KB`;
      } else {
        return `${(bytes / 1024 / 1024).toFixed(1)} MB`;
      }
    };

    const getFileProgressData = (filename: string) => {
      const files = statusData.value?.individual_files || lastStatusData.value?.individual_files || [];
      
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
      
      return match;
    };

    const getFileProgress = (filename: string): number => {
      const progressData = getFileProgressData(filename);
      return progressData?.progress || 0;
    };

    const getFilePhase = (filename: string): string => {
      const progressData = getFileProgressData(filename);
      const phase = progressData?.phase || 'ready';
      
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

    const getFileStatus = (filename: string): string => {
      const progressData = getFileProgressData(filename);
      return progressData?.status || 'ready';
    };

    const getStatusColor = (status: string): string => {
      switch (status) {
        case 'completed': return 'success';
        case 'failed': return 'error';
        case 'processing': return 'primary';
        default: return 'default';
      }
    };

    const removeFile = (index: number) => {
      // Remove file logic here
      console.log('Remove file at index:', index);
    };

    const removeSelectedFiles = () => {
      console.log('Remove selected files:', selectedItems.value);
      
      if (props.configuredDataSource === 'upload') {
        // For upload files, remove from the configured files array
        const indicesToRemove = [...selectedItems.value].sort((a, b) => b - a);
        const newFiles = [...props.configuredFiles];
        indicesToRemove.forEach(index => {
          newFiles.splice(index, 1);
        });
        // Emit event to parent to update configured files
        emit('filesRemoved', newFiles);
      }
      
      // Clear selection
      selectedItems.value = [];
    };

    const pollProcessingStatus = async (processingId: string) => {
      try {
        const response = await axios.get<ProcessingStatusResponse>(`/api/processing-status/${processingId}`);
        const status = response.data;
        
        processingStatus.value = status.message;
        processingProgress.value = status.progress;
        statusData.value = status;
        lastStatusData.value = status;
        
        console.log('Processing status data:', status);
        localStorage.setItem('lastProcessingStatus', JSON.stringify(status));
        
        if (status.status === 'completed') {
          isProcessing.value = false;
          processingStatus.value = '';
          processingProgress.value = 0;
          currentProcessingId.value = null;
          successMessage.value = status.message || 'Documents ingested successfully!';
        } else if (status.status === 'failed') {
          isProcessing.value = false;
          processingStatus.value = '';
          processingProgress.value = 0;
          currentProcessingId.value = null;
          error.value = status.error || 'Processing failed';
        } else if (status.status === 'cancelled') {
          isProcessing.value = false;
          processingStatus.value = '';
          processingProgress.value = 0;
          currentProcessingId.value = null;
          successMessage.value = 'Processing cancelled successfully';
        } else if (status.status === 'started' || status.status === 'processing') {
          setTimeout(() => pollProcessingStatus(processingId), 2000);
        }
      } catch (err) {
        console.error('Error checking processing status:', err);
        error.value = 'Error checking processing status';
        isProcessing.value = false;
        currentProcessingId.value = null;
      }
    };

    const cancelProcessing = async () => {
      if (!currentProcessingId.value) return;
      
      try {
        const response = await axios.post(`/api/cancel-processing/${currentProcessingId.value}`, {});
        
        if (!response.data.success) {
          error.value = 'Failed to cancel processing';
        }
      } catch (err) {
        console.error('Error cancelling processing:', err);
        error.value = 'Error cancelling processing';
      }
    };

    const startProcessing = async () => {
      if (!canStartProcessing.value) return;
      
      try {
        isProcessing.value = true;
        error.value = '';
        successMessage.value = '';
        statusData.value = null;
        lastStatusData.value = null;
        
        const request: any = {
          data_source: props.configuredDataSource
        };

        if (props.configuredDataSource === 'upload') {
          // For upload, we need to upload files first, then use their paths
          const uploadedPaths = await uploadFiles();
          request.paths = uploadedPaths;
          request.data_source = 'filesystem'; // Use filesystem processing for uploaded files
        } else if (props.configuredDataSource === 'cmis') {
          request.paths = ['/Shared/GraphRAG']; // Default path - should be configurable
          request.cmis_config = {
            url: 'http://localhost:8080/alfresco/api/-default-/public/cmis/versions/1.1/atom',
            username: 'admin',
            password: 'admin',
            folder_path: '/Shared/GraphRAG'
          };
        } else if (props.configuredDataSource === 'alfresco') {
          request.paths = ['/Shared/GraphRAG']; // Default path - should be configurable
          request.alfresco_config = {
            url: 'http://localhost:8080/alfresco',
            username: 'admin',
            password: 'admin',
            path: '/Shared/GraphRAG'
          };
        }

        const response = await axios.post('/api/ingest', request);
        
        // Handle async processing response
        if (response.data.status === 'started') {
          processingStatus.value = response.data.message;
          processingProgress.value = 0;
          currentProcessingId.value = response.data.processing_id;
          successMessage.value = `Processing started: ${response.data.estimated_time || 'Please wait...'}`;
          // Start polling for status
          setTimeout(() => pollProcessingStatus(response.data.processing_id), 2000);
        } else if (response.data.status === 'completed') {
          isProcessing.value = false;
          successMessage.value = 'Documents ingested successfully!';
        } else if (response.data.status === 'failed') {
          isProcessing.value = false;
          error.value = response.data.error || 'Processing failed';
        }
        
      } catch (err: any) {
        console.error('Error processing documents:', err);
        const errorMessage = err?.response?.data?.detail || err?.response?.data?.error || 'Error processing documents';
        error.value = errorMessage;
        isProcessing.value = false;
        currentProcessingId.value = null;
      }
    };

    const uploadFiles = async (): Promise<string[]> => {
      if (props.configuredFiles.length === 0) return [];
      
      isUploading.value = true;
      uploadProgress.value = 0;
      
      try {
        const formData = new FormData();
        props.configuredFiles.forEach(file => {
          formData.append('files', file);
        });
        
        const response = await axios.post('/api/upload', formData, {
          headers: {
            'Content-Type': 'multipart/form-data',
          },
          onUploadProgress: (progressEvent) => {
            if (progressEvent.total) {
              const progress = Math.round((progressEvent.loaded * 100) / progressEvent.total);
              uploadProgress.value = progress;
            }
          },
        });
        
        if (response.data.success) {
          // Show information about skipped files if any
          if (response.data.skipped && response.data.skipped.length > 0) {
            const skippedInfo = response.data.skipped
              .map((file: any) => `${file.filename}: ${file.reason}`)
              .join('\n');
            error.value = `Some files were skipped:\n${skippedInfo}`;
          }
          
          return response.data.files.map((file: any) => file.path);
        } else {
          throw new Error('Upload failed');
        }
      } finally {
        isUploading.value = false;
        uploadProgress.value = 0;
      }
    };

    const loadLastStatus = () => {
      const saved = localStorage.getItem('lastProcessingStatus');
      if (saved) {
        const parsed = JSON.parse(saved);
        lastStatusData.value = parsed;
        console.log('Retrieved from localStorage:', parsed);
      } else {
        console.log('No saved status found in localStorage');
      }
    };

    // Auto-select all files when configured files change
    watch(() => props.configuredFiles, () => {
      if (props.configuredDataSource === 'upload') {
        selectedItems.value = props.configuredFiles.map((_, index) => index);
      } else if (props.configuredDataSource === 'cmis' || props.configuredDataSource === 'alfresco') {
        selectedItems.value = [0];
      }
    }, { immediate: true });

    return {
      selectedItems,
      isProcessing,
      isUploading,
      uploadProgress,
      processingProgress,
      processingStatus,
      currentProcessingId,
      statusData,
      lastStatusData,
      showDebugPanel,
      successMessage,
      error,
      tableHeaders,
      displayFiles,
      canStartProcessing,
      getProcessingButtonText,
      formatFileSize,
      getFileProgress,
      getFilePhase,
      getFileStatus,
      getStatusColor,
      removeFile,
      removeSelectedFiles,
      cancelProcessing,
      startProcessing,
      uploadFiles,
      loadLastStatus,
    };
  },
});
</script>

<style scoped>
.text-truncate {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
</style>
