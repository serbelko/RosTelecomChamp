import { Component, inject } from '@angular/core';
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
export class ForecastPanelComponent {
  private api = inject(DashboardService);
  rows: ForecastVm[] = [];
  loading = false;

  // ВАЖНО: не вызываем загрузку в конструкторе/OnInit — чтобы избежать 404 при старте
  refresh() {
    this.loading = true;
    this.api
      .forecast$()
      .pipe(
        map((data: ForecastRow[]) =>
          (data ?? []).map((r) => {
            const depletionDate =
              r.stockoutInDays != null
                ? new Date(Date.now() + r.stockoutInDays * 24 * 3600 * 1000)
                : null;
            const recommended = Math.max(Math.round(r.expected * 1.1), 1);
            const confidence = 90; // фикс для UI
            return {
              itemName: r.category,
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
