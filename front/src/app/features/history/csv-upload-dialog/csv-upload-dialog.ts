// src/app/features/history/csv-upload-dialog/csv-upload-dialog.ts
import { Component, inject } from '@angular/core';
import { CommonModule } from '@angular/common';
import { MatDialogModule, MatDialogRef } from '@angular/material/dialog';
import { MatButtonModule } from '@angular/material/button';
import { MatIconModule } from '@angular/material/icon';
import { MatProgressBarModule } from '@angular/material/progress-bar';
import { HttpEventType } from '@angular/common/http';
import { HistoryService } from '../history.service';

@Component({
  selector: 'app-csv-upload-dialog',
  standalone: true,
  imports: [CommonModule, MatDialogModule, MatButtonModule, MatIconModule, MatProgressBarModule],
  templateUrl: './csv-upload-dialog.html',
  styleUrls: ['./csv-upload-dialog.scss'],
})
export class CsvUploadDialogComponent {
  private readonly api = inject(HistoryService);
  private readonly ref = inject(MatDialogRef<CsvUploadDialogComponent, boolean>);

  file: File | null = null;
  dragging = false;

  uploading = false;
  progress = 0;
  error: string | null = null;

  preview: string[][] = []; // первые ~10 строк CSV

  dragOver(ev: DragEvent) {
    ev.preventDefault();
    this.dragging = true;
  }
  dragLeave() {
    this.dragging = false;
  }
  drop(ev: DragEvent) {
    ev.preventDefault();
    this.dragging = false;
    const f = ev.dataTransfer?.files?.[0];
    if (f) this.setFile(f);
  }

  pick(input: HTMLInputElement) {
    input.value = '';
    input.click();
  }
  onFile(ev: Event) {
    const input = ev.target as HTMLInputElement;
    const f = input.files?.[0] ?? null;
    if (f) this.setFile(f);
  }

  private setFile(f: File) {
    if (!f.name.toLowerCase().endsWith('.csv')) {
      this.error = 'Выберите CSV-файл';
      return;
    }
    this.error = null;
    this.file = f;
    this.readPreview(f);
  }

  private readPreview(f: File) {
    const reader = new FileReader();
    reader.onload = () => {
      const text = String(reader.result || '');
      const lines = text.split(/\r?\n/).slice(0, 11); // до 10 строк + заголовок
      this.preview = lines
        .filter((l) => l.trim().length > 0)
        .map((l) => l.split(',').map((c) => c.trim()));
    };
    reader.readAsText(f, 'utf-8');
  }

  upload() {
    if (!this.file || this.uploading) return;
    this.error = null;
    this.uploading = true;
    this.progress = 0;

    this.api.uploadCsv(this.file).subscribe({
      next: (ev) => {
        if (ev.type === HttpEventType.UploadProgress && ev.total) {
          this.progress = Math.round((100 * ev.loaded) / ev.total);
        }
        if (ev.type === HttpEventType.Response) {
          // ожидаем { success, failed, errors[] }
          const body = ev.body as any;
          if (body?.errors?.length) {
            this.error = `Импорт завершён с ошибками (${body.errors.length}).`;
          }
          this.uploading = false;
          this.ref.close(true);
        }
      },
      error: (err) => {
        this.error = err?.error?.detail || err?.error?.message || 'Ошибка загрузки';
        this.uploading = false;
      },
    });
  }

  close() {
    this.ref.close(false);
  }
}
