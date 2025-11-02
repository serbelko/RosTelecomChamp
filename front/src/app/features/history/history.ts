import { Component, ChangeDetectionStrategy, inject } from '@angular/core';
import { CommonModule } from '@angular/common';
import { ReactiveFormsModule, FormBuilder } from '@angular/forms';
import { MatCardModule } from '@angular/material/card';
import { MatButtonModule } from '@angular/material/button';
import { MatIconModule } from '@angular/material/icon';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatInputModule } from '@angular/material/input';
import { MatDatepickerModule } from '@angular/material/datepicker';
import { MatNativeDateModule } from '@angular/material/core';
import { MatSelectModule } from '@angular/material/select';
import { MatCheckboxModule } from '@angular/material/checkbox';
import { MatChipsModule } from '@angular/material/chips';

import {
  HistoryService,
  HistoryFilters,
  HistoryRow,
  PageData,
  SummaryData,
} from './history.service';

@Component({
  selector: 'app-history',
  standalone: true,
  imports: [
    CommonModule,
    ReactiveFormsModule,
    MatCardModule,
    MatButtonModule,
    MatIconModule,
    MatFormFieldModule,
    MatInputModule,
    MatDatepickerModule,
    MatNativeDateModule,
    MatSelectModule,
    MatCheckboxModule,
    MatChipsModule,
  ],
  templateUrl: './history.html',
  styleUrls: ['./history.scss'],
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class HistoryComponent {
  private fb = inject(FormBuilder);
  private api = inject(HistoryService);

  zonesOptions: string[] = [];
  categoriesOptions: string[] = [];

  form = this.fb.group({
    from: this.fb.control<Date | null>(null),
    to: this.fb.control<Date | null>(null),
    zones: this.fb.nonNullable.control<string[]>([]),
    categories: this.fb.nonNullable.control<string[]>([]),
    statusOk: this.fb.nonNullable.control(true),
    statusLow: this.fb.nonNullable.control(true),
    statusCrit: this.fb.nonNullable.control(true),
    query: this.fb.nonNullable.control(''),
    page: this.fb.nonNullable.control(1),
    pageSize: this.fb.nonNullable.control(20),
    sort: this.fb.nonNullable.control('checked_at:desc'),
  });

  pageData?: PageData<HistoryRow>;
  summary?: SummaryData;
  selectedIds = new Set<number>();

  /** 👇 добавь эту строку 👇 */
  Math = Math;

  constructor() {
    // подтянем опции для фильтров
    this.api.fetchOptions().subscribe((o) => {
      this.zonesOptions = o.zones;
      this.categoriesOptions = o.categories;
    });

    this.apply(); // первичная загрузка
  }

  private buildFilters(): HistoryFilters {
    const v = this.form.value;
    const toISO = (d: Date | null | undefined) => (d ? new Date(d).toISOString() : null);
    return {
      from: toISO(v.from ?? null),
      to: toISO(v.to ?? null),
      zones: v.zones ?? [],
      categories: v.categories ?? [],
      statusOk: v.statusOk ?? true,
      statusLow: v.statusLow ?? true,
      statusCrit: v.statusCrit ?? true,
      query: v.query ?? '',
      page: v.page ?? 1,
      pageSize: v.pageSize ?? 20,
      sort: v.sort ?? 'checked_at:desc',
    };
  }

  apply(): void {
    const f = this.buildFilters();
    this.api.fetchSummary(f).subscribe((s) => (this.summary = s));
    this.api.fetchPage(f).subscribe((p) => {
      this.pageData = p;
      this.selectedIds.clear(); // сбрасываем выбор при новой выборке
    });
  }

  reset(): void {
    this.form.reset({
      from: null,
      to: null,
      zones: [],
      categories: [],
      statusOk: true,
      statusLow: true,
      statusCrit: true,
      query: '',
      page: 1,
      pageSize: 20,
      sort: 'checked_at:desc',
    });
    this.apply();
  }

  quick(range: 'today' | 'yesterday' | 'week' | 'month'): void {
    const end = new Date();
    const start = new Date();
    if (range === 'today') start.setHours(0, 0, 0, 0);
    if (range === 'yesterday') {
      start.setDate(end.getDate() - 1);
      start.setHours(0, 0, 0, 0);
      end.setDate(end.getDate() - 1);
      end.setHours(23, 59, 59, 999);
    }
    if (range === 'week') start.setDate(end.getDate() - 7);
    if (range === 'month') start.setMonth(end.getMonth() - 1);
    this.form.patchValue({ from: start, to: end, page: 1 });
    this.apply();
  }

  changePage(delta: number): void {
    const p = (this.form.value.page ?? 1) + delta;
    if (p < 1) return;
    this.form.patchValue({ page: p });
    this.apply();
  }
  changePageSize(sz: number): void {
    this.form.patchValue({ pageSize: sz, page: 1 });
    this.apply();
  }
  sortBy(field: string): void {
    const cur = this.form.value.sort ?? 'checked_at:desc';
    const [f, d] = cur.split(':');
    const next = f === field ? `${field}:${d === 'asc' ? 'desc' : 'asc'}` : `${field}:asc`;
    this.form.patchValue({ sort: next, page: 1 });
    this.apply();
  }

  toggleAll(ev: Event): void {
    const checked = (ev.target as HTMLInputElement).checked;
    this.selectedIds.clear();
    if (checked) this.pageData?.items.forEach((r) => this.selectedIds.add(r.id));
  }
  toggleOne(id: number, ev: Event): void {
    const checked = (ev.target as HTMLInputElement).checked;
    if (checked) this.selectedIds.add(id);
    else this.selectedIds.delete(id);
  }

  exportExcel(): void {
    const ids = Array.from(this.selectedIds);
    if (!ids.length) return;
    this.api.exportExcel(ids).subscribe((blob) => {
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = 'history.xlsx';
      a.click();
      URL.revokeObjectURL(url);
    });
  }
  exportPdf(): void {
    const ids = Array.from(this.selectedIds);
    if (!ids.length) return;
    this.api.exportPdf(ids).subscribe((blob) => {
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = 'history.pdf';
      a.click();
      URL.revokeObjectURL(url);
    });
  }

  statusClass(s: 'ok' | 'low' | 'crit') {
    return { ok: s === 'ok', low: s === 'low', crit: s === 'crit' };
  }
}
