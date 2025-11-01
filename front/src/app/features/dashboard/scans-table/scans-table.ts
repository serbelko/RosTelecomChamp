import { Component, OnDestroy, OnInit, inject } from '@angular/core';
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
export class ScansTableComponent implements OnInit, OnDestroy {
  private api = inject(DashboardService);
  private sub = new Subscription();

  rows: ScanRow[] = [];

  ngOnInit(): void {
    // теперь берём поток без аргументов (данные уже в сторе)
    this.sub.add(
      this.api.scans$().subscribe((list) => {
        this.rows = (list ?? []).slice(0, 20);
      }),
    );
  }

  ngOnDestroy(): void {
    this.sub.unsubscribe();
  }

  /** trackBy для *ngFor, чтобы Angular не перерисовывал все строки */
  trackById(_index: number, row: ScanRow): number | string {
    return row.id ?? `${row.productId}-${row.scannedAt}`;
  }
}
