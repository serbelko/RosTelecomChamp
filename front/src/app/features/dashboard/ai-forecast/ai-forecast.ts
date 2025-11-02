import { Component, OnInit, inject } from '@angular/core';
import { CommonModule } from '@angular/common';
import { MatCardModule } from '@angular/material/card';
import { MatButtonModule } from '@angular/material/button';
import { DashboardService, ForecastRow } from '../dashboard.service';
import { map, catchError, finalize } from 'rxjs/operators';
import { of } from 'rxjs';

interface ForecastVm {
  itemName: string;
  sku: string;
  stock: number;
  depletionDate: Date | null;
  recommendedQty: number;
  confidence: number;
}

@Component({
  selector: 'app-forecast-panel',
  standalone: true,
  imports: [CommonModule, MatCardModule, MatButtonModule],
  templateUrl: './ai-forecast.html',
  styleUrls: ['./ai-forecast.scss'],
})
export class ForecastPanelComponent implements OnInit {
  private api = inject(DashboardService);
  loading = false;
  rows: ForecastVm[] = [];

  ngOnInit(): void {
    this.refresh();
  }

  trackBySku = (_: number, r: ForecastVm) => r.sku;

  refresh(): void {
    this.loading = true;
    this.api
      .forecast$(7)
      .pipe(
        map((rows: ForecastRow[]) => {
          const mapped = rows.map((r) => {
            const depletionDate =
              typeof r.stockoutInDays === 'number' && isFinite(r.stockoutInDays)
                ? new Date(Date.now() + r.stockoutInDays * 24 * 60 * 60 * 1000)
                : null;
            const recommended = Math.max(0, Math.ceil(r.expected * 0.6));
            return {
              itemName: r.category || 'Товар',
              sku: r.productId,
              stock: Math.max(0, Math.round(r.expected / 2)),
              depletionDate,
              recommendedQty: recommended,
              confidence: 85,
            } as ForecastVm;
          });

          // сортировка по ближайшей дате исчерпания и отбор топ-5
          return mapped
            .sort((a, b) => {
              const ta = a.depletionDate?.getTime() ?? Number.POSITIVE_INFINITY;
              const tb = b.depletionDate?.getTime() ?? Number.POSITIVE_INFINITY;
              return ta - tb;
            })
            .slice(0, 5);
        }),
        catchError(() => of([] as ForecastVm[])),
        finalize(() => (this.loading = false)),
      )
      .subscribe((rows) => (this.rows = rows));
  }
}
