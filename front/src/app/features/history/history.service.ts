import { Injectable } from '@angular/core';
import { HttpClient, HttpParams, HttpRequest, HttpEvent } from '@angular/common/http';
import { environment } from '../../../environments/environment';
import { Observable } from 'rxjs';
import { map } from 'rxjs/operators';

const BASE = environment.apiUrl;

export interface HistoryFilters {
  from?: string; // ISO
  to?: string; // ISO
  zones?: string[];
  status?: Array<'OK' | 'LOW_STOCK' | 'CRITICAL'>;
  query?: string; // артикул или название
  page?: number;
  pageSize?: number;
  sort?: string; // "field:asc|desc"
}

export interface HistoryPage {
  total: number;
  items: Array<{
    id: number;
    productId: string;
    productName: string;
    quantity: number;
    zone: string;
    row?: string | null;
    shelf?: string | null;
    status: 'OK' | 'LOW_STOCK' | 'CRITICAL';
    scannedAt: string; // ISO
  }>;
  pagination: { limit: number; offset: number };
}

export type HistoryRow = HistoryPage['items'][number];
/**
 * Точка тренда: t — метка времени (строка), остальные ключи (названия SKU) — числовые значения.
 * Индексная сигнатура допускает number | string, чтобы свойство t не конфликтовало.
 */
export type TrendPoint = { t: string } & { [sku: string]: number | string };

export interface HistorySummary {
  checks: number;
  uniqueSkus: number;
  mismatches: number; // LOW_STOCK + CRITICAL
  avgZoneTimeMin: number; // нет на бэке — считаем 0
}

@Injectable({ providedIn: 'root' })
export class HistoryService {
  constructor(private http: HttpClient) {}

  list(filters: HistoryFilters): Observable<HistoryPage> {
    let params = new HttpParams();
    if (filters.from) params = params.set('dt_from', filters.from);
    if (filters.to) params = params.set('dt_to', filters.to);
    (filters.zones ?? []).forEach((z) => (params = params.append('zones', z)));
    (filters.status ?? []).forEach((s) => (params = params.append('statuses', s)));
    if (filters.query) params = params.set('query', filters.query);

    if (filters.sort) {
      const [field, dir] = filters.sort.split(':');
      params = params.set('sort_by', field).set('sort_dir', dir === 'desc' ? 'desc' : 'asc');
    }

    const page = filters.page ?? 1;
    const pageSize = filters.pageSize ?? 20;
    params = params.set('limit', pageSize).set('offset', String((page - 1) * pageSize));

    // BASE уже содержит /api
    return this.http.get<any>(`${BASE}/inventory/history`, { params }).pipe(
      map((res) => ({
        total: res.total,
        items: (res.items ?? []).map((r: any) => ({
          id: r.id,
          productId: r.product_id,
          productName: r.product_name,
          quantity: Number(r.quantity ?? 0),
          zone: r.zone,
          row: r.row ?? null,
          shelf: r.shelf ?? null,
          status: r.status as 'OK' | 'LOW_STOCK' | 'CRITICAL',
          scannedAt: r.scanned_at,
        })),
        pagination: res.pagination,
      })),
    );
  }

  /**
   * Клиентская агрегация тренда по дням (YYYY-MM-DD) и по SKU.
   * Значение — сумма quantity за день.
   */
  fetchTrend(filters: HistoryFilters): Observable<TrendPoint[]> {
    return this.list(filters).pipe(
      map((page) => {
        const buckets = new Map<string, Record<string, number>>();
        const allSkus = new Set<string>();

        for (const it of page.items) {
          const day = it.scannedAt ? new Date(it.scannedAt) : new Date();
          const key = new Date(Date.UTC(day.getFullYear(), day.getMonth(), day.getDate()))
            .toISOString()
            .slice(0, 10);

          const sku = it.productName || it.productId || 'UNKNOWN';
          allSkus.add(sku);

          const rec = buckets.get(key) ?? {};
          rec[sku] = (rec[sku] ?? 0) + Number(it.quantity ?? 0);
          buckets.set(key, rec);
        }

        const days = Array.from(buckets.keys()).sort(); // ISO-дата сортируема лексикографически
        const points: TrendPoint[] = days.map((d) => {
          const row: TrendPoint = { t: d };
          const src = buckets.get(d)!;
          for (const sku of allSkus) {
            if (src[sku] != null) {
              // индексная сигнатура разрешает number | string
              (row as any)[sku] = src[sku];
            }
          }
          return row;
        });

        return points;
      }),
    );
  }

  /**
   * Сводка для SummaryBar: проверки, уникальные SKU, несоответствия (LOW_STOCK+CRITICAL), среднее время в зоне (0).
   */
  fetchSummary(filters: HistoryFilters): Observable<HistorySummary> {
    return this.list(filters).pipe(
      map((page) => {
        const checks = page.total ?? page.items.length;
        const skuSet = new Set<string>();
        let mismatches = 0;

        for (const it of page.items) {
          skuSet.add(it.productId || it.productName);
          if (it.status === 'LOW_STOCK' || it.status === 'CRITICAL') mismatches++;
        }

        return {
          checks,
          uniqueSkus: skuSet.size,
          mismatches,
          avgZoneTimeMin: 0,
        };
      }),
    );
  }

  uploadCsv(file: File): Observable<HttpEvent<unknown>> {
    const form = new FormData();
    form.append('file', file);
    const req = new HttpRequest('POST', `${BASE}/inventory/import`, form, { reportProgress: true });
    return this.http.request(req);
  }

  exportSelectedToExcel(ids: string[]): Observable<Blob> {
    const params = new HttpParams().set('ids', ids.join(','));
    return this.http
      .get(`${BASE}/export/excel`, { params, responseType: 'blob' })
      .pipe(map((res) => res as Blob));
  }
}
