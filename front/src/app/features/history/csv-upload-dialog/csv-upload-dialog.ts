import { Component, inject } from '@angular/core';
import { CommonModule } from '@angular/common';
import { MatDialogModule, MatDialogRef } from '@angular/material/dialog';
import { MatButtonModule } from '@angular/material/button';
import { MatIconModule } from '@angular/material/icon';
import { MatProgressBarModule } from '@angular/material/progress-bar';
import { HistoryService } from '../history.service';

@Component({
  selector: 'app-csv-upload-dialog',
  standalone: true,
  imports: [CommonModule, MatDialogModule, MatButtonModule, MatIconModule, MatProgressBarModule],
  templateUrl: './csv-upload-dialog.html',
  styleUrls: ['./csv-upload-dialog.scss'],
})
export class CsvUploadDialogComponent {
  private ref = inject(MatDialogRef<CsvUploadDialogComponent>);
  private api = inject(HistoryService);

  file?: File;
  dragging = false;
  preview: string[][] = [];
  progress = 0;
  uploading = false;
  error = '';

  pick(input: HTMLInputElement) {
    input.click();
  }

  onFile(e: Event) {
    const f = (e.target as HTMLInputElement).files?.[0];
    if (f) {
      this.file = f;
      this.makePreview(f);
    }
  }

  drop(e: DragEvent) {
    e.preventDefault();
    this.dragging = false;
    const f = e.dataTransfer?.files?.[0];
    if (f) {
      this.file = f;
      this.makePreview(f);
    }
  }
  dragOver(e: DragEvent) {
    e.preventDefault();
    this.dragging = true;
  }
  dragLeave() {
    this.dragging = false;
  }

  private async makePreview(file: File) {
    const text = await file.text();
    const rows = text.split(/\r?\n/).filter(Boolean).slice(0, 6); // заголовок + 5 строк
    this.preview = rows.map((r) => r.split(';'));
  }

  upload() {
    if (!this.file) return;
    this.uploading = true;
    this.error = '';
    this.api.uploadCsv(this.file).subscribe({
      next: (ev) => {
        // @ts-ignore
        if (ev?.type === 1 && ev?.loaded && ev?.total)
          this.progress = Math.round((100 * ev.loaded) / ev.total);
      },
      error: (err) => {
        this.error = err?.error?.message || 'Ошибка загрузки';
        this.uploading = false;
      },
      complete: () => {
        this.uploading = false;
        this.ref.close(true);
      },
    });
  }

  close() {
    this.ref.close(false);
  }
}
