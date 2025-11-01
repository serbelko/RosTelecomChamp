import { Component, inject, signal } from '@angular/core';
import { CommonModule } from '@angular/common';
import { MatCardModule } from '@angular/material/card';
import { FilterBarComponent } from './filter-bar/filter-bar';
import { SummaryBarComponent } from './summary-bar/summary-bar';
import { HistoryTableComponent } from './history-table/history-table';
import { TrendChartComponent } from './trend-chart/trend-chart';
import { HistoryFilters } from './history.service';

@Component({
  selector: 'app-history',
  standalone: true,
  imports: [
    CommonModule,
    MatCardModule,
    FilterBarComponent,
    SummaryBarComponent,
    HistoryTableComponent,
    TrendChartComponent,
  ],
  templateUrl: './history.html',
  styleUrls: ['./history.scss'],
})
export class HistoryComponent {
  filters = signal<HistoryFilters>({ page: 0, pageSize: 20, status: ['OK', 'LOW_STOCK', 'CRITICAL'] });

  onApply(f: HistoryFilters) {
    // сбрасываем страницу
    this.filters.update(() => ({ ...f, page: 0 }));
  }
}
