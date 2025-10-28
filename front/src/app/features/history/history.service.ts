import { Injectable } from '@angular/core';
import { HttpClient, HttpParams, HttpRequest, HttpEvent } from '@angular/common/http';
import { environment } from '../../../environments/environment';
import { Observable } from 'rxjs';

export interface HistoryFilters {
  from?: string; // ISO
  to?: string; // ISO
  zones?: string[];
  categories?: string[];
  status?: Array<'OK' | 'LOW' | 'CRITICAL'>;
  query?: string; // артикул или название
  page?: number;
  pageSize?: number;
  sort?: string; // "field:asc|desc"
}

export interface HistoryRow {
  ts: string; // дата и время проверки
  robotId: string;
  zone: string;
  sku: string;
  name: string;
  expected: number;
  actual: number;
  delta: number; // actual - expected
  status: 'OK' | 'LOW' | 'CRITICAL';
}

export interface Paged<T> {
  items: T[];
  total: number;
}

export interface HistorySummary {
  checks: number;
  uniqueSkus: number;
  mismatches: number;
  avgZoneTimeMin: number;
}

export interface TrendPoint {
  t: string; // ISO
  [sku: string]: number | string;
}

@Injectable({ providedIn: 'root' })
export class HistoryService {
  private base = environment.apiUrl;

  constructor(private http: HttpClient) {}

  // подгони пути под свой бэк
  fetchHistory(filters: HistoryFilters): Observable<Paged<HistoryRow>> {
    let params = new HttpParams();
    Object.entries(filters).forEach(([k, v]) => {
      if (v == null) return;
      if (Array.isArray(v)) v.forEach((x) => (params = params.append(k, String(x))));
      else params = params.set(k, String(v));
    });
    return this.http.get<Paged<HistoryRow>>(`${this.base}/api/v1/history`, { params });
  }

  fetchSummary(filters: HistoryFilters): Observable<HistorySummary> {
    let params = new HttpParams();
    Object.entries(filters).forEach(([k, v]) => {
      if (v == null) return;
      if (Array.isArray(v)) v.forEach((x) => (params = params.append(k, String(x))));
      else params = params.set(k, String(v));
    });
    return this.http.get<HistorySummary>(`${this.base}/api/v1/history/summary`, { params });
  }

  fetchTrend(filters: HistoryFilters): Observable<TrendPoint[]> {
    let params = new HttpParams();
    if (filters.from) params = params.set('from', filters.from);
    if (filters.to) params = params.set('to', filters.to);
    if (filters.query) params = params.set('query', filters.query);
    return this.http.get<TrendPoint[]>(`${this.base}/api/v1/history/trend`, { params });
  }

  uploadCsv(file: File): Observable<HttpEvent<unknown>> {
    const form = new FormData();
    form.append('file', file);
    // если нужен другой путь, поменяй здесь
    const req = new HttpRequest('POST', `${this.base}/api/v1/history/upload-csv`, form, {
      reportProgress: true,
    });
    return this.http.request(req);
  }
}
