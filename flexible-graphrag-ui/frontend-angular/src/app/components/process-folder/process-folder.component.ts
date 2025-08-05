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
  @Output() processed = new EventEmitter<{ path: string }>();
  
  form: FormGroup;
  isProcessing = false;

  constructor(
    private fb: FormBuilder,
    private apiService: ApiService,
    private snackBar: MatSnackBar,
    private envService: EnvService
  ) {
    this.form = this.fb.group({
      folderPath: ['', Validators.required]
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
  }

  onSubmit(): void {
    if (this.form.invalid || this.isProcessing) {
      return;
    }

    this.isProcessing = true;
    const request = {
      folder_path: this.form.value.folderPath
    };

    this.apiService.processFolder(request)
      .pipe(
        finalize(() => this.isProcessing = false)
      )
      .subscribe({
        next: () => {
          this.snackBar.open('Folder processed successfully!', 'Close', {
            duration: 3000,
            panelClass: ['success-snackbar']
          });
          this.processed.emit({ path: request.folder_path });
        },
        error: (error) => {
          this.snackBar.open(
            error.message || 'Error processing folder',
            'Close',
            { duration: 5000, panelClass: ['error-snackbar'] }
          );
        }
      });
  }
}
