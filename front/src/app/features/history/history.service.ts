// src/app/features/history/history.service.ts
import { Injectable } from '@angular/core';
import { HttpClient, HttpParams, HttpEvent } from '@angular/common/http';
import { Observable } from 'rxjs';
import { map } from 'rxjs/operators';

export interface HistoryFilters {
  from?: string | null;
  to?: string | null;
  zones?: string[];
  categories?: string[];
  statusOk?: boolean;
  statusLow?: boolean;
  statusCrit?: boolean;
  query?: string;
  page?: number;
  pageSize?: number;
  sort?: string; // "field:asc|desc"
}

export interface HistoryRow {
  id: number;
  checked_at: string; // ISO
  robot_id: string;
  zone: string;
  sku: string;
  name: string;
  expected_qty: number;
  actual_qty: number;
  diff: number; // actual - expected
  status: 'ok' | 'low' | 'crit';
}

export interface PageData<T> {
  items: T[];
  total: number;
  page: number;
  pageSize: number;
}

export interface SummaryData {
  checks: number;
  uniqueSkus: number;
  mismatches: number;
  avgZoneMinutes: number;
}

// --- Экспорт-алиас для совместимости с импортами в подкомпонентах ---
export type Summary = SummaryData;

// --- Точки для тренд-чарта истории ---
export interface TrendPoint {
  t: string; // ISO дата/время
  total: number; // агрегированное значение (кол-во проверок/сканов и т.п.)
}

@Injectable({ providedIn: 'root' })
export class HistoryService {
  constructor(private http: HttpClient) {}

  fetchPage(f: HistoryFilters): Observable<PageData<HistoryRow>> {
    let p = new HttpParams();
    const add = (k: string, v: any) => {
      if (v !== undefined && v !== null && v !== '') p = p.set(k, v);
    };
    add('from', f.from);
    add('to', f.to);
    (f.zones ?? []).forEach((z) => (p = p.append('zones', z)));
    (f.categories ?? []).forEach((c) => (p = p.append('categories', c)));
    add('statusOk', f.statusOk);
    add('statusLow', f.statusLow);
    add('statusCrit', f.statusCrit);
    add('query', f.query);
    add('page', f.page ?? 1);
    add('pageSize', f.pageSize ?? 20);
    add('sort', f.sort ?? 'checked_at:desc');

    return this.http.get<any>('/api/history/page', { params: p }).pipe(
      map((resp) => ({
        items: (resp?.items ?? []).map((x: any) => ({
          id: Number(x.id),
          checked_at: String(x.checked_at),
          robot_id: String(x.robot_id ?? '—'),
          zone: String(x.zone ?? ''),
          sku: String(x.sku ?? ''),
          name: String(x.name ?? ''),
          expected_qty: Number(x.expected_qty ?? 0),
          actual_qty: Number(x.actual_qty ?? 0),
          diff: Number(x.actual_qty ?? 0) - Number(x.expected_qty ?? 0),
          status: String(x.status ?? 'ok').toLowerCase() as 'ok' | 'low' | 'crit',
        })),
        total: Number(resp?.total ?? 0),
        page: Number(resp?.page ?? f.page ?? 1),
        pageSize: Number(resp?.pageSize ?? f.pageSize ?? 20),
      })),
    );
  }
  uploadCsv(file: File): Observable<HttpEvent<any>> {
    const form = new FormData();
    form.append('file', file);
    return this.http.post<any>('/api/history/import/csv', form, {
      reportProgress: true,
      observe: 'events',
    });
  }
  // Тренд для графика (даты/фильтры учитываются)
  fetchTrend(f: HistoryFilters): Observable<TrendPoint[]> {
    let p = new HttpParams();
    const add = (k: string, v: any) => {
      if (v !== undefined && v !== null && v !== '') p = p.set(k, v);
    };
    add('from', f.from);
    add('to', f.to);
    (f.zones ?? []).forEach((z) => (p = p.append('zones', z)));
    (f.categories ?? []).forEach((c) => (p = p.append('categories', c)));
    add('statusOk', f.statusOk);
    add('statusLow', f.statusLow);
    add('statusCrit', f.statusCrit);
    add('query', f.query);

    return this.http.get<any>('/api/history/trend', { params: p }).pipe(
      map((resp) => {
        const arr = resp?.points ?? resp ?? [];
        return arr.map((x: any) => ({
          t: String(x.t ?? x.time ?? x.date ?? new Date().toISOString()),
          total: Number(x.total ?? x.value ?? x.count ?? 0),
        })) as TrendPoint[];
      }),
    );
  }

  // Сводка по выбранному периоду/фильтрам
  fetchSummary(f: HistoryFilters): Observable<SummaryData> {
    let p = new HttpParams();
    const add = (k: string, v: any) => {
      if (v !== undefined && v !== null && v !== '') p = p.set(k, v);
    };
    add('from', f.from);
    add('to', f.to);
    (f.zones ?? []).forEach((z) => (p = p.append('zones', z)));
    (f.categories ?? []).forEach((c) => (p = p.append('categories', c)));
    add('statusOk', f.statusOk);
    add('statusLow', f.statusLow);
    add('statusCrit', f.statusCrit);
    add('query', f.query);

    return this.http.get<any>('/api/history/summary', { params: p }).pipe(
      map((r) => ({
        checks: Number(r?.checks ?? 0),
        uniqueSkus: Number(r?.uniqueSkus ?? 0),
        mismatches: Number(r?.mismatches ?? 0),
        avgZoneMinutes: Number(r?.avgZoneMinutes ?? 0),
      })),
    );
  }

  // Опции для фильтров
  fetchOptions(): Observable<{ zones: string[]; categories: string[] }> {
    return this.http.get<any>('/api/history/options').pipe(
      map((r) => ({
        zones: (r?.zones ?? []).map((x: any) => String(x)),
        categories: (r?.categories ?? []).map((x: any) => String(x)),
      })),
    );
  }

  // Экспорт
  exportExcel(ids: number[]) {
    return this.http.post('/api/history/export/excel', { ids }, { responseType: 'blob' });
  }

  exportPdf(ids: number[]) {
    return this.http.post('/api/history/export/pdf', { ids }, { responseType: 'blob' });
  }
}
