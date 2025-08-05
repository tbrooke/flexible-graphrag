import { Component } from '@angular/core';
import { CommonModule } from '@angular/common';

@Component({
  selector: 'app-root',
  templateUrl: './app.component.html',
  styleUrls: ['./app.component.scss'],
  standalone: false
})
export class AppComponent {
  title = 'Flexible GraphRAG (Angular)';
  
  onFolderProcessed(event: { path: string }): void {
    console.log('Folder was processed:', event.path);
    // You can add any additional logic here when a folder is processed
  }
}
