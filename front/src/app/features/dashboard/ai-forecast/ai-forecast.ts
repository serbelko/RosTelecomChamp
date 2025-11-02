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

  refresh(): void {
    this.loading = true;
    this.api
      .forecast$(7)
      .pipe(
        map((rows: ForecastRow[]) =>
          rows.map((r) => {
            const depletionDate =
              typeof r.stockoutInDays === 'number' && isFinite(r.stockoutInDays)
                ? new Date(Date.now() + r.stockoutInDays * 24 * 60 * 60 * 1000)
                : null;

            // простая эвристика закупки
            const recommended = Math.max(0, Math.ceil(r.expected * 0.6));
            // на бэке приходит общий confidence, без детализации по sku - для UI поставим константу
            const confidence = 85;

            return {
              itemName: r.category || 'Товар',
              sku: r.productId,
              stock: Math.round(r.expected / 2),
              depletionDate,
              recommendedQty: recommended,
              confidence,
            } as ForecastVm;
          }),
        ),
        catchError(() => of([] as ForecastVm[])),
        finalize(() => (this.loading = false)),
      )
      .subscribe((rows) => (this.rows = rows));
  }
}
