import { Component } from '@angular/core';
import { FormBuilder, FormGroup, Validators } from '@angular/forms';
import { MatSnackBar } from '@angular/material/snack-bar';
import { finalize } from 'rxjs/operators';
import { ApiService } from '../../services/api.service';
import { ApiResponse } from '../../models/api.models';

@Component({
  selector: 'app-query-form',
  templateUrl: './query-form.component.html',
  styleUrls: ['./query-form.component.scss'],
  standalone: false
})
export class QueryFormComponent {
  form: FormGroup;
  isQuerying = false;
  answer: string | null = null;

  constructor(
    private fb: FormBuilder,
    private apiService: ApiService,
    private snackBar: MatSnackBar
  ) {
    this.form = this.fb.group({
      question: ['', Validators.required]
    });
  }

  onSubmit(): void {
    if (this.form.invalid || this.isQuerying) {
      return;
    }

    const request = {
      question: this.form.value.question
    };

    console.log('Submitting query:', request);
    this.isQuerying = true;
    this.answer = null;
    
    this.apiService.query(request)
      .pipe(
        finalize(() => this.isQuerying = false)
      )
      .subscribe({
        next: (response: ApiResponse) => {
          console.log('Response received:', response);
          
          // Handle simplified response structure
          if (response.answer) {
            this.answer = response.answer;
          } else {
            this.answer = 'No answer found';
          }
          
          console.log('Final answer value:', this.answer);
        },
        error: (error) => {
          console.error('Query error:', error);
          this.snackBar.open(
            error.message || 'Error executing query',
            'Close',
            { duration: 5000, panelClass: ['error-snackbar'] }
          );
        }
      });
  }

  onClear(): void {
    this.answer = null;
    this.form.reset();
  }
}
