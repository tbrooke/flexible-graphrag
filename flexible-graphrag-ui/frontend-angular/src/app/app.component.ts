import { Component } from '@angular/core';

@Component({
  selector: 'app-root',
  templateUrl: './app.component.html',
  styleUrls: ['./app.component.scss'],
  standalone: false
})
export class AppComponent {
  title = 'Flexible GraphRAG (Angular)';
  selectedTabIndex = 0;
  hasConfiguredSources = false;
  configuredDataSource = '';
  configuredFiles: File[] = [];
  
  onConfigureProcessing(): void {
    this.selectedTabIndex = 1; // Switch to Processing tab
  }

  onSourcesConfigured(data: { dataSource: string; files: File[] }): void {
    this.hasConfiguredSources = true;
    this.configuredDataSource = data.dataSource;
    this.configuredFiles = data.files;
  }
}
