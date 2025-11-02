// src/app/features/dashboard/dashboard.service.ts
import { Injectable } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { BehaviorSubject, Observable, of, timer } from 'rxjs';
import { catchError, map, switchMap } from 'rxjs/operators';

// ===== Экспортируемые типы, которые используют компоненты =====
export interface Robot {
  id: string;
  // индексы сетки: A..Z -> 0..25, 1..50 -> 0..49
  x: number;
  y: number;
  battery: number;
  status: 'active' | 'low' | 'offline';
  zone: string; // напр. "A12"
  updatedAt: string; // ISO
}

export interface ZoneSummary {
  zone: string; // "A1", "B7", ...
  robots: number; // число роботов в зоне
}

export interface Metric {
  name: string;
  value: number;
}

export interface ActivityPoint {
  t: string; // ISO
  v: number;
}

export interface ScanRow {
  id: number;
  productId: string;
  productName: string;
  zone: string;
  quantity: number;
  scannedAt: string;
}

export interface ForecastRow {
  productId: string;
  category: string;
  expected: number;
  stockoutInDays: number | null;
}

// ===== Формат ответа бэка для /api/dashboard/current =====
interface DashboardResponse {
  robots: Array<{
    robot_id: string;
    status: string;
    battery_level: number;
    last_update: string;
    zone: string; // 'A'..'Z'
    row: number; // 1..50
    shelf: number;
  }>;
  recent_scans: Array<{
    id: number;
    product_id: string;
    product_name: string;
    zone: string;
    quantity: number;
    scanned_at: string;
  }>;
  statistics: {
    total_robots: number;
    offline_robots: number;
    critical_items: number;
    low_stock_items: number;
    scans_last_hour: number;
  };
}

@Injectable({ providedIn: 'root' })
export class DashboardService {
  private robotsSub = new BehaviorSubject<Robot[]>([]);
  private zonesSub = new BehaviorSubject<ZoneSummary[]>([]);
  private metricsSub = new BehaviorSubject<Metric[]>([]);
  private activitySub = new BehaviorSubject<ActivityPoint[]>([]);
  private scansSub = new BehaviorSubject<ScanRow[]>([]);

  constructor(private readonly http: HttpClient) {}

  robots$(): Observable<Robot[]> {
    return this.robotsSub.asObservable();
  }
  zones$(): Observable<ZoneSummary[]> {
    return this.zonesSub.asObservable();
  }
  metrics$(): Observable<Metric[]> {
    return this.metricsSub.asObservable();
  }
  activity$(): Observable<ActivityPoint[]> {
    return this.activitySub.asObservable();
  }
  scans$(): Observable<ScanRow[]> {
    return this.scansSub.asObservable();
  }

  // Разовый опрос состояния дашборда
  private loadOnce(): Observable<void> {
    return this.http.get<DashboardResponse>(`/api/dashboard/current`).pipe(
      map((r) => {
        // Роботы: переводим (zone,row) в индексы сетки (x,y)
        const robots: Robot[] = (r.robots ?? []).map((x) => {
          const colChar = (x.zone ?? 'A').toString().toUpperCase().charCodeAt(0);
          const ci = Math.max(0, Math.min(25, Number.isFinite(colChar) ? colChar - 65 : 0)); // A=0..Z=25
          const ri = Math.max(0, Math.min(49, (x.row ?? 1) - 1)); // 1..50 -> 0..49

          const status: Robot['status'] =
            (x.status ?? '').toLowerCase() === 'offline'
              ? 'offline'
              : (x.battery_level ?? 0) < 20
                ? 'low'
                : 'active';

          return {
            id: x.robot_id,
            x: ci,
            y: ri,
            battery: Math.round(Number(x.battery_level ?? 0)),
            status,
            zone: `${x.zone ?? 'A'}${x.row ?? ''}`,
            updatedAt: x.last_update,
          };
        });
        this.robotsSub.next(robots);

        // Сводка по зонам (для тепловой карты): агрегируем по "A12"
        const zoneMap = new Map<string, number>();
        for (const rbt of robots) {
          zoneMap.set(rbt.zone, (zoneMap.get(rbt.zone) ?? 0) + 1);
        }
        const zones: ZoneSummary[] = Array.from(zoneMap, ([zone, robots]) => ({ zone, robots }));
        this.zonesSub.next(zones);

        // Метрики
        const m: Metric[] = [
          { name: 'Всего роботов', value: r.statistics?.total_robots ?? robots.length },
          {
            name: 'Оффлайн',
            value:
              r.statistics?.offline_robots ?? robots.filter((x) => x.status === 'offline').length,
          },
          { name: 'Критичных SKU', value: r.statistics?.critical_items ?? 0 },
          { name: 'Мало остатков', value: r.statistics?.low_stock_items ?? 0 },
          { name: 'Сканов за час', value: r.statistics?.scans_last_hour ?? 0 },
        ];
        this.metricsSub.next(m);

        // Активность
        const pt: ActivityPoint = {
          t: new Date().toISOString(),
          v: r.statistics?.scans_last_hour ?? 0,
        };
        const prev = this.activitySub.getValue();
        this.activitySub.next([...prev, pt].slice(-60));

        // Последние сканы
        const scans: ScanRow[] = (r.recent_scans ?? []).map((s) => ({
          id: s.id,
          productId: s.product_id,
          productName: s.product_name,
          zone: s.zone,
          quantity: s.quantity,
          scannedAt: s.scanned_at,
        }));
        this.scansSub.next(scans);
      }),
      catchError(() => of(void 0)),
    );
  }

  // Публичные методы запуска
  forceRefresh(): void {
    this.loadOnce().subscribe();
  }

  start(): void {
    this.forceRefresh();
    timer(5000, 5000)
      .pipe(switchMap(() => this.loadOnce()))
      .subscribe();
  }

  // ------- Прогноз (кнопка "Обновить прогноз") -------
  /**
   * Сразу обращаемся к POST /api/ai/predict (на бэке реализовано),
   * чтобы избежать 404 на несуществующий GET /api/ai/forecast.
   * Возвращаем унифицированный массив ForecastRow.
   */
  forecast$(periodDays = 7, categories?: string[]): Observable<ForecastRow[]> {
    const body: any = { period_days: periodDays };
    if (categories?.length) body.categories = categories;

    const mapResp = (res: any): ForecastRow[] =>
      (res?.predictions ?? res ?? []).map((p: any) => ({
        productId: p.product_id ?? p.productId ?? p.sku ?? p.id ?? '',
        category: p.category ?? p.itemName ?? p.name ?? '',
        expected: Number(p.expected_demand ?? p.expected ?? p.forecast ?? p.value ?? p.mean ?? 0),
        stockoutInDays: p.expected_stockout_in_days ?? p.stockoutInDays ?? null,
      }));

    return this.http.post<any>(`/api/ai/predict`, body).pipe(
      map(mapResp),
      catchError(() => of([] as ForecastRow[])),
    );
  }
}
