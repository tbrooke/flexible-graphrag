import { Component, EventEmitter, Output, OnInit } from '@angular/core';
import { FormBuilder, FormGroup, Validators } from '@angular/forms';
import { MatSnackBar } from '@angular/material/snack-bar';
import { finalize } from 'rxjs/operators';
import { ApiService } from '../../services/api.service';
import { EnvService } from '../../services/env.service';

@Component({
  selector: 'app-process-folder',
  templateUrl: './process-folder.component.html',
  styleUrls: ['./process-folder.component.scss'],
  standalone: false
})
export class ProcessFolderComponent implements OnInit {
  @Output() processed = new EventEmitter<{ dataSource: string, path?: string }>();
  
  form: FormGroup;
  isProcessing = false;

  constructor(
    private fb: FormBuilder,
    private apiService: ApiService,
    private snackBar: MatSnackBar,
    private envService: EnvService
  ) {
    this.form = this.fb.group({
      dataSource: ['filesystem', Validators.required],
      folderPath: [''],
      // CMIS fields
      cmisUrl: [''],
      cmisUsername: [''],
      cmisPassword: [''],
      // Alfresco fields
      alfrescoUrl: [''],
      alfrescoUsername: [''],
      alfrescoPassword: ['']
    });

    // Set up conditional validators
    this.form.get('dataSource')?.valueChanges.subscribe(dataSource => {
      this.updateValidators(dataSource);
    });
  }

  ngOnInit(): void {
    // Set default folder path from environment config
    const defaultPath = this.envService.defaultFolderPath;
    if (defaultPath) {
      this.form.patchValue({
        folderPath: defaultPath
      });
    }
    
    // Set initial validators
    this.updateValidators('filesystem');
  }

  private updateValidators(dataSource: string): void {
    // Clear all validators first
    Object.keys(this.form.controls).forEach(key => {
      if (key !== 'dataSource') {
        this.form.get(key)?.clearValidators();
      }
    });

    // Set validators based on data source
    switch (dataSource) {
      case 'filesystem':
        this.form.get('folderPath')?.setValidators([Validators.required]);
        break;
      case 'cmis':
        this.form.get('cmisUrl')?.setValidators([Validators.required]);
        this.form.get('cmisUsername')?.setValidators([Validators.required]);
        this.form.get('cmisPassword')?.setValidators([Validators.required]);
        this.form.get('folderPath')?.setValidators([Validators.required]);
        break;
      case 'alfresco':
        this.form.get('alfrescoUrl')?.setValidators([Validators.required]);
        this.form.get('alfrescoUsername')?.setValidators([Validators.required]);
        this.form.get('alfrescoPassword')?.setValidators([Validators.required]);
        this.form.get('folderPath')?.setValidators([Validators.required]);
        break;
    }

    // Update validity
    Object.keys(this.form.controls).forEach(key => {
      this.form.get(key)?.updateValueAndValidity();
    });
  }

  onSubmit(): void {
    if (this.form.invalid || this.isProcessing) {
      return;
    }

    this.isProcessing = true;
    const formValue = this.form.value;
    
    // Build request based on data source
    const request: any = {
      data_source: formValue.dataSource
    };

    if (formValue.dataSource === 'filesystem') {
      request.paths = [formValue.folderPath];
    } else if (formValue.dataSource === 'cmis') {
      // For now, we'll pass the paths as the folder path since CMIS isn't fully implemented
      request.paths = [formValue.folderPath];
      // In future, these would be used to configure CMIS connection
      request.cmis_config = {
        url: formValue.cmisUrl,
        username: formValue.cmisUsername,
        password: formValue.cmisPassword,
        folder_path: formValue.folderPath
      };
    } else if (formValue.dataSource === 'alfresco') {
      // For now, we'll pass the paths as the folder path since Alfresco isn't fully implemented
      request.paths = [formValue.folderPath];
      // In future, these would be used to configure Alfresco connection
      request.alfresco_config = {
        url: formValue.alfrescoUrl,
        username: formValue.alfrescoUsername,
        password: formValue.alfrescoPassword,
        path: formValue.folderPath
      };
    }

    this.apiService.ingestDocuments(request)
      .pipe(
        finalize(() => this.isProcessing = false)
      )
      .subscribe({
        next: () => {
          this.snackBar.open('Documents ingested successfully!', 'Close', {
            duration: 3000,
            panelClass: ['success-snackbar']
          });
          this.processed.emit({ 
            dataSource: formValue.dataSource, 
            path: formValue.folderPath 
          });
        },
        error: (error) => {
          this.snackBar.open(
            error.message || 'Error ingesting documents',
            'Close',
            { duration: 5000, panelClass: ['error-snackbar'] }
          );
        }
      });
  }
}
