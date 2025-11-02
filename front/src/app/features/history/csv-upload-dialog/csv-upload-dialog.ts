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
  private api = inject(HistoryService);
  private ref = inject(MatDialogRef<CsvUploadDialogComponent>);

  file: File | null = null;
  preview: string[][] = []; // превью CSV: массив строк, каждая строка — массив ячеек
  uploading = false;
  progress = 0;

  close(ok = false): void {
    this.ref.close(ok);
  }

  onFileChange(ev: Event): void {
    const input = ev.target as HTMLInputElement;
    const f = input.files?.[0] ?? null;
    this.file = f;
    this.preview = [];

    if (!f) return;

    const reader = new FileReader();
    reader.onload = () => {
      const text = String(reader.result ?? '');
      this.preview = this.parseCsvForPreview(text).slice(0, 15); // не спамим, максимум 15 строк
    };
    reader.readAsText(f, 'utf-8');
  }

  upload(): void {
    if (!this.file || this.uploading) return;
    this.uploading = true;
    this.progress = 0;

    this.api.uploadCsv(this.file).subscribe({
      next: (ev: any) => {
        // HttpEvent типизировать не обязательно здесь
        if (ev?.type === 1 && typeof ev.total === 'number' && ev.total > 0) {
          this.progress = Math.round((100 * ev.loaded) / ev.total);
        }
        if (ev?.type === 4) {
          // HttpResponse
          this.progress = 100;
          this.uploading = false;
          this.close(true);
        }
      },
      error: () => {
        this.uploading = false;
        this.progress = 0;
      },
    });
  }

  // очень простой CSV парсер для превью
  private parseCsvForPreview(text: string): string[][] {
    const lines = text.replace(/\r\n/g, '\n').replace(/\r/g, '\n').split('\n').filter(Boolean);
    return lines.map((line) => this.splitCsvLine(line));
  }

  private splitCsvLine(line: string): string[] {
    const out: string[] = [];
    let cur = '';
    let q = false;

    for (let i = 0; i < line.length; i++) {
      const ch = line[i];
      if (ch === '"') {
        if (q && line[i + 1] === '"') {
          cur += '"';
          i++;
        } else {
          q = !q;
        }
      } else if (ch === ',' && !q) {
        out.push(cur);
        cur = '';
      } else {
        cur += ch;
      }
    }
    out.push(cur);
    return out.map((s) => s.trim());
  }
}
