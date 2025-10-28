import { Component, ElementRef, ViewChild, inject } from '@angular/core';
import { CommonModule } from '@angular/common';
import { MatCardModule } from '@angular/material/card';
import { DashboardService, ScanRow } from '../dashboard.service';
import { Subscription } from 'rxjs';

@Component({
  selector: 'app-scans-table',
  standalone: true,
  imports: [CommonModule, MatCardModule],
  templateUrl: './scans-table.html',
  styleUrls: ['./scans-table.scss'],
})
export class ScansTableComponent {
  private api = inject(DashboardService);
  private sub?: Subscription;

  rows: ScanRow[] = [];
  paused = false;

  @ViewChild('scrollHost') host?: ElementRef<HTMLDivElement>;

  constructor() {
    this.sub = this.api.scans$().subscribe((data) => {
      if (!this.paused) {
        this.rows = data.slice(0, 20);
        // автоскролл вниз
        queueMicrotask(() => {
          const el = this.host?.nativeElement;
          if (el) el.scrollTop = el.scrollHeight;
        });
      }
    });
  }

  togglePause() {
    this.paused = !this.paused;
  }
}
