import { NgModule, APP_INITIALIZER } from '@angular/core';
import { BrowserModule } from '@angular/platform-browser';
import { BrowserAnimationsModule } from '@angular/platform-browser/animations';
import { HttpClientModule } from '@angular/common/http';
import { ReactiveFormsModule } from '@angular/forms';
import { MatButtonModule } from '@angular/material/button';
import { MatCardModule } from '@angular/material/card';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatInputModule } from '@angular/material/input';
import { MatProgressSpinnerModule } from '@angular/material/progress-spinner';
import { MatSnackBarModule } from '@angular/material/snack-bar';
import { MatToolbarModule } from '@angular/material/toolbar';
import { MatIconModule } from '@angular/material/icon';
import { TextFieldModule } from '@angular/cdk/text-field';
import { CommonModule } from '@angular/common';
import { firstValueFrom } from 'rxjs';

import { AppComponent } from './app.component';
import { ProcessFolderComponent } from './components/process-folder/process-folder.component';
import { QueryFormComponent } from './components/query-form/query-form.component';
import { EnvService } from './services/env.service';

// Factory function to initialize environment configuration
export function initializeEnv(envService: EnvService) {
  return () => firstValueFrom(envService.loadEnvConfig());
}

@NgModule({
  declarations: [
    AppComponent,
    ProcessFolderComponent,
    QueryFormComponent
  ],
  imports: [
    BrowserModule,
    CommonModule,
    BrowserAnimationsModule,
    HttpClientModule,
    ReactiveFormsModule,
    MatButtonModule,
    MatCardModule,
    MatFormFieldModule,
    MatInputModule,
    MatProgressSpinnerModule,
    MatSnackBarModule,
    MatToolbarModule,
    MatIconModule,
    TextFieldModule
  ],
  providers: [
    EnvService,
    {
      provide: APP_INITIALIZER,
      useFactory: initializeEnv,
      deps: [EnvService],
      multi: true
    }
  ],
  bootstrap: [AppComponent]
})
export class AppModule { }
