import { Component, OnInit, Inject, ViewEncapsulation } from '@angular/core';
import { DOCUMENT } from '@angular/common';
import { MatSlideToggleChange } from '@angular/material/slide-toggle';

@Component({
  selector: 'app-root',
  templateUrl: './app.component.html',
  styleUrls: ['./app.component.scss'],
  encapsulation: ViewEncapsulation.None,
  standalone: false
})
export class AppComponent implements OnInit {
  title = 'Flexible GraphRAG (Angular)';
  selectedTabIndex = 0;
  hasConfiguredSources = false;
  configuredDataSource = '';
  configuredFiles: File[] = [];
  
  // Theme management
  isDarkMode = false;
  isLightMode = true;

  constructor(@Inject(DOCUMENT) private document: Document) {}

  ngOnInit(): void {
    // Initialize theme from localStorage
    const savedTheme = localStorage.getItem('angular-theme-mode');
    this.isDarkMode = savedTheme === 'dark'; // Default to light mode if no saved theme
    this.isLightMode = !this.isDarkMode;
    this.applyTheme();
  }

  toggleTheme(event: MatSlideToggleChange): void {
    this.isLightMode = event.checked;
    this.isDarkMode = !event.checked;
    localStorage.setItem('angular-theme-mode', this.isDarkMode ? 'dark' : 'light');
    this.applyTheme();
  }

  toggleThemeSimple(): void {
    this.isLightMode = !this.isLightMode;
    this.isDarkMode = !this.isDarkMode;
    localStorage.setItem('angular-theme-mode', this.isDarkMode ? 'dark' : 'light');
    this.applyTheme();
  }

  private applyTheme(): void {
    const body = this.document.body;
    if (this.isDarkMode) {
      body.classList.add('dark-theme');
      body.classList.remove('light-theme');
    } else {
      body.classList.add('light-theme');
      body.classList.remove('dark-theme');
    }
  }
  
  onConfigureProcessing(): void {
    this.selectedTabIndex = 1; // Switch to Processing tab
  }

  onSourcesConfigured(data: { dataSource: string; files: File[] }): void {
    this.hasConfiguredSources = true;
    this.configuredDataSource = data.dataSource;
    this.configuredFiles = data.files;
  }
}
