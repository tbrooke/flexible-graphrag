import { Component, Input, Output, EventEmitter, OnInit, OnChanges } from '@angular/core';
import { MatCheckboxChange } from '@angular/material/checkbox';
import { ApiService } from '../../services/api.service';
import { AsyncProcessingResponse, ProcessingStatusResponse } from '../../models/api.models';

interface FileItem {
  index: number;
  name: string;
  size: number;
  type: string;
}

@Component({
  selector: 'app-processing-tab',
  templateUrl: './processing-tab.html',
  styleUrls: ['./processing-tab.scss'],
  standalone: false
})
export class ProcessingTabComponent implements OnInit, OnChanges {
  @Input() hasConfiguredSources = false;
  @Input() configuredDataSource = '';
  @Input() configuredFiles: File[] = [];
  @Output() goToSources = new EventEmitter<void>();

  // Table configuration
  displayedColumns: string[] = ['select', 'name', 'size', 'progress', 'remove', 'status'];
  
  // State
  selectedItems = new Set<number>();
  displayFiles: FileItem[] = [];
  isProcessing = false;
  processingProgress = 0;
  processingStatus = '';
  currentProcessingId: string | null = null;
  statusData: ProcessingStatusResponse | null = null;
  successMessage = '';
  error = '';

  // Expose Math to template
  Math = Math;

  constructor(private apiService: ApiService) {}

  ngOnInit(): void {
    this.updateDisplayFiles();
  }

  ngOnChanges(): void {
    this.updateDisplayFiles();
    this.autoSelectFiles();
  }

  private updateDisplayFiles(): void {
    if (!this.hasConfiguredSources) {
      this.displayFiles = [];
      return;
    }
    
    if (this.configuredDataSource === 'upload') {
      this.displayFiles = this.configuredFiles.map((file, index) => ({
        index,
        name: file.name,
        size: file.size,
        type: 'file',
      }));
    } else if (this.configuredDataSource === 'cmis' || this.configuredDataSource === 'alfresco') {
      this.displayFiles = [{
        index: 0,
        name: 'Repository Path',
        size: 0,
        type: 'repository',
      }];
    }
  }

  private autoSelectFiles(): void {
    if (this.configuredDataSource === 'upload') {
      this.selectedItems = new Set(this.configuredFiles.map((_, index) => index));
    } else if (this.configuredDataSource === 'cmis' || this.configuredDataSource === 'alfresco') {
      this.selectedItems = new Set([0]);
    }
  }

  formatFileSize(bytes: number): string {
    if (bytes < 1024) {
      return bytes === 0 ? "0 B" : "1 KB";
    } else if (bytes < 1024 * 1024) {
      return `${Math.ceil(bytes / 1024)} KB`;
    } else {
      return `${(bytes / 1024 / 1024).toFixed(1)} MB`;
    }
  }

  getFileProgressData(filename: string): any {
    const files = this.statusData?.individual_files || [];
    
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
  }

  getFileProgress(filename: string): number {
    const progressData = this.getFileProgressData(filename);
    return progressData?.progress || 0;
  }

  getFilePhase(filename: string): string {
    const progressData = this.getFileProgressData(filename);
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
  }

  getFileStatus(filename: string): string {
    const progressData = this.getFileProgressData(filename);
    return progressData?.status || 'ready';
  }

  getStatusColor(status: string): string {
    switch (status) {
      case 'completed': return 'primary';
      case 'failed': return 'warn';
      case 'processing': return 'accent';
      default: return '';
    }
  }

  // Selection methods
  isAllSelected(): boolean {
    return this.displayFiles.length > 0 && this.selectedItems.size === this.displayFiles.length;
  }

  isIndeterminate(): boolean {
    return this.selectedItems.size > 0 && this.selectedItems.size < this.displayFiles.length;
  }

  isSelected(index: number): boolean {
    return this.selectedItems.has(index);
  }

  toggleAllSelection(event: MatCheckboxChange): void {
    if (event.checked) {
      this.selectedItems = new Set(this.displayFiles.map((_, index) => index));
    } else {
      this.selectedItems.clear();
    }
  }

  toggleSelection(index: number, event: MatCheckboxChange): void {
    if (event.checked) {
      this.selectedItems.add(index);
    } else {
      this.selectedItems.delete(index);
    }
  }

  removeFile(index: number): void {
    if (this.configuredDataSource === 'upload') {
      // Remove from configured files
      const newFiles = [...this.configuredFiles];
      newFiles.splice(index, 1);
      
      // Update selected indices - remove the index and shift down higher indices
      const newSelected = new Set<number>();
      this.selectedItems.forEach(i => {
        if (i < index) {
          newSelected.add(i);
        } else if (i > index) {
          newSelected.add(i - 1);
        }
        // Skip i === index (the removed file)
      });
      this.selectedItems = newSelected;
      
      // Note: In a real implementation, you'd emit an event to update the parent component
      console.log('File removed at index:', index, 'New files:', newFiles);
    }
  }

  removeSelectedFiles(): void {
    console.log('Remove selected files:', Array.from(this.selectedItems));
    
    if (this.configuredDataSource === 'upload') {
      // For upload files, remove from the configured files array
      const indicesToRemove = Array.from(this.selectedItems).sort((a, b) => b - a);
      const newFiles = [...this.configuredFiles];
      indicesToRemove.forEach(index => {
        newFiles.splice(index, 1);
      });
      // Update the configured files
      this.configuredFiles = newFiles;
      // Update display files
      this.updateDisplayFiles();
    }
    
    // Clear selection
    this.selectedItems.clear();
  }

  canStartProcessing(): boolean {
    return this.hasConfiguredSources && this.selectedItems.size > 0 && !this.isProcessing;
  }

  getProcessingButtonText(): string {
    if (this.isProcessing) return 'PROCESSING...';
    if (!this.hasConfiguredSources) return 'CONFIGURE SOURCES FIRST';
    if (this.selectedItems.size === 0) return 'SELECT FILES TO PROCESS';
    return 'START PROCESSING';
  }

  async startProcessing(): Promise<void> {
    if (!this.canStartProcessing()) return;
    
    console.log('Start processing with selected items:', Array.from(this.selectedItems));
    
    this.isProcessing = true;
    this.processingProgress = 0;
    this.statusData = null;
    
    try {
      // Prepare processing data
      const processingData: any = {};
      
      if (this.configuredDataSource === 'upload') {
        // For upload, upload files first then use filesystem processing
        const uploadedPaths = await this.uploadFiles();
        processingData.data_source = 'filesystem'; // Use filesystem processing for uploaded files
        processingData.paths = uploadedPaths;
      } else {
        processingData.data_source = this.configuredDataSource;
      }
      
      // Add configuration for other data sources
      if (this.configuredDataSource === 'filesystem') {
        // For direct filesystem access (not upload)
        processingData.paths = this.configuredFiles.map(f => f.name);
      } else if (this.configuredDataSource === 'cmis') {
        processingData.paths = ['/Sites/swsdp/documentLibrary']; // Default path
        processingData.cmis_config = {
          url: 'http://localhost:8080/alfresco/api/-default-/public/cmis/versions/1.1/atom',
          username: 'admin',
          password: 'admin',
          folder_path: '/Sites/swsdp/documentLibrary'
        };
      } else if (this.configuredDataSource === 'alfresco') {
        processingData.paths = ['/Sites/swsdp/documentLibrary']; // Default path
        processingData.alfresco_config = {
          url: 'http://localhost:8080/alfresco/api/-default-/public/alfresco/versions/1/nodes/-shared-/children',
          username: 'admin',
          password: 'admin',
          path: '/Sites/swsdp/documentLibrary'
        };
      }
      
      console.log('Starting processing with data:', processingData);
      
      this.apiService.ingestDocuments(processingData).subscribe({
        next: (response: AsyncProcessingResponse) => {
          console.log('Processing started:', response);
          
          if (response.processing_id) {
            this.currentProcessingId = response.processing_id;
            this.startStatusPolling();
          }
        },
        error: (error: any) => {
          console.error('Error starting processing:', error);
          this.isProcessing = false;
        }
      });
      
    } catch (error) {
      console.error('Error in startProcessing:', error);
      this.isProcessing = false;
    }
  }

  private uploadFiles(): Promise<string[]> {
    console.log('Uploading files:', this.configuredFiles);
    
    const formData = new FormData();
    this.configuredFiles.forEach(file => {
      formData.append('files', file);
    });
    
    return new Promise((resolve, reject) => {
      this.apiService.uploadFiles(formData).subscribe({
        next: (response: any) => {
          console.log('Files uploaded:', response);
          
          // Extract uploaded file paths for processing (match Vue/React pattern)
          let uploadedPaths: string[] = [];
          
          if (response.success && response.files) {
            uploadedPaths = response.files.map((file: any) => file.path);
            
            // Update configured files with server response if needed
            this.configuredFiles = response.files.map((serverFile: any) => {
              const originalFile = this.configuredFiles.find(f => f.name === serverFile.filename);
              if (originalFile) {
                // Create a new File object with the server filename
                const newFile = new File([originalFile], serverFile.saved_as, { type: originalFile.type });
                return newFile;
              }
              return originalFile;
            }).filter(Boolean);
          } else {
            // Fallback: use original file names
            uploadedPaths = this.configuredFiles.map(f => f.name);
          }
          
          resolve(uploadedPaths);
        },
        error: (error: any) => {
          console.error('Error uploading files:', error);
          reject(error);
        }
      });
    });
  }

  private startStatusPolling(): void {
    if (!this.currentProcessingId) return;
    
    console.log('Starting status polling for:', this.currentProcessingId);
    
    // Poll every 2 seconds
    const pollInterval = setInterval(() => {
      if (!this.currentProcessingId) {
        clearInterval(pollInterval);
        return;
      }
      
      this.apiService.getProcessingStatus(this.currentProcessingId).subscribe({
        next: (status: ProcessingStatusResponse) => {
          console.log('Status update:', status);
          this.statusData = status;
          
          if (status.progress !== undefined) {
            this.processingProgress = status.progress;
          }
          
          // Check if processing is complete
          if (status.status === 'completed') {
            console.log('Processing completed successfully');
            this.isProcessing = false;
            this.currentProcessingId = null;
            this.successMessage = status.message || 'Successfully ingested document(s)! Vector Index And Knowledge Graph And Elasticsearch Search ready.';
            clearInterval(pollInterval);
          } else if (status.status === 'failed') {
            console.log('Processing failed');
            this.isProcessing = false;
            this.currentProcessingId = null;
            this.error = status.error || 'Processing failed';
            clearInterval(pollInterval);
          } else if (status.status === 'cancelled') {
            console.log('Processing cancelled');
            this.isProcessing = false;
            this.currentProcessingId = null;
            this.successMessage = 'Processing cancelled successfully';
            clearInterval(pollInterval);
          }
        },
        error: (error: any) => {
          console.error('Error polling status:', error);
          clearInterval(pollInterval);
          this.isProcessing = false;
          this.currentProcessingId = null;
        }
      });
    }, 2000);
  }

  cancelProcessing(): void {
    if (!this.currentProcessingId) return;
    
    console.log('Cancel processing:', this.currentProcessingId);
    
    this.apiService.cancelProcessing(this.currentProcessingId).subscribe({
      next: (response: any) => {
        console.log('Processing cancelled:', response);
        this.isProcessing = false;
        this.currentProcessingId = null;
        this.processingProgress = 0;
        this.statusData = null;
      },
      error: (error: any) => {
        console.error('Error cancelling processing:', error);
        // Still reset the UI state
        this.isProcessing = false;
        this.currentProcessingId = null;
      }
    });
  }
}