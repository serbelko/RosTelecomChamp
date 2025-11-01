import { Injectable } from '@angular/core';
import { HttpClient, HttpParams } from '@angular/common/http';
import { environment } from '../../../environments/environment';
import { catchError, map, switchMap } from 'rxjs/operators';
import { BehaviorSubject, Observable, of, timer } from 'rxjs';

const BASE = environment.apiUrl;

// ---- Типы ----
export interface Robot {
  id: string;
  x: number;
  y: number;
  battery: number;
  status: 'active' | 'low' | 'offline';
  zone: string;
  updatedAt: string;
}
export interface ZoneStatus {
  zone: string;
  robots: number;
}
export interface Metric {
  name: string;
  value: number;
}
export interface ActivityPoint {
  t: string;
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
  stockoutInDays?: number | null;
}

interface DashboardResponse {
  robots: Array<{
    id: string;
    x: number;
    y: number;
    battery: number;
    status: 'active' | 'low' | 'offline';
    zone: string;
    updated_at: string;
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
  constructor(private http: HttpClient) {}

  // ---- Стор состояния ----
  private robotsSub = new BehaviorSubject<Robot[]>([]);
  private zonesSub = new BehaviorSubject<ZoneStatus[]>([]);
  private metricsSub = new BehaviorSubject<Metric[]>([]);
  private activitySub = new BehaviorSubject<ActivityPoint[]>([]);
  private scansSub = new BehaviorSubject<ScanRow[]>([]);

  // паблик-стримы для компонентов
  robots$(): Observable<Robot[]> {
    return this.robotsSub.asObservable();
  }
  zones$(): Observable<ZoneStatus[]> {
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

  // единая загрузка current → обновить все сабджекты
  private loadOnce(): Observable<void> {
    return this.http.get<DashboardResponse>(`${BASE}/dashboard/current`).pipe(
      map((r) => {
        // robots
        const robots: Robot[] = (r.robots ?? []).map((x) => ({
          id: x.id,
          x: x.x,
          y: x.y,
          battery: x.battery,
          status: x.status,
          zone: x.zone,
          updatedAt: x.updated_at,
        }));
        this.robotsSub.next(robots);

        // zones (агрегация по роботам)
        const mapz = new Map<string, number>();
        robots.forEach((rr) => mapz.set(rr.zone, (mapz.get(rr.zone) ?? 0) + 1));
        this.zonesSub.next(Array.from(mapz, ([zone, robots]) => ({ zone, robots })));

        // metrics
        const m: Metric[] = [
          { name: 'Всего роботов', value: r.statistics?.total_robots ?? 0 },
          { name: 'Оффлайн', value: r.statistics?.offline_robots ?? 0 },
          { name: 'Критичных SKU', value: r.statistics?.critical_items ?? 0 },
          { name: 'Мало остатков', value: r.statistics?.low_stock_items ?? 0 },
          { name: 'Сканов за час', value: r.statistics?.scans_last_hour ?? 0 },
        ];
        this.metricsSub.next(m);

        // activity (точка на сейчас)
        const pt: ActivityPoint = {
          t: new Date().toISOString(),
          v: r.statistics?.scans_last_hour ?? 0,
        };
        const prev = this.activitySub.getValue();
        const next = [...prev, pt].slice(-60); // ограничим хвост
        this.activitySub.next(next);

        // scans
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
      catchError(() => {
        // при ошибке не роняем UI, просто не обновляем
        return of(void 0);
      }),
    );
  }

  // публичный триггер для WS/кнопок
  forceRefresh(): void {
    this.loadOnce().subscribe();
  }

  // запустить фоновый опрос (резерв) + первая загрузка
  start(): void {
    this.forceRefresh();
    timer(5000, 5000)
      .pipe(switchMap(() => this.loadOnce()))
      .subscribe();
  }

  // ------- AI FORECAST (мягкий фоллбек) -------
  forecast$(): Observable<ForecastRow[]> {
    const mapResp = (res: any): ForecastRow[] =>
      (res?.predictions ?? res ?? []).map((p: any) => ({
        productId: p.product_id ?? p.productId ?? p.sku ?? '',
        category: p.category ?? p.itemName ?? '',
        expected: Number(p.expected_demand ?? p.expected ?? p.demand ?? 0),
        stockoutInDays: p.expected_stockout_in_days ?? p.stockoutInDays ?? null,
      }));

    const getForecast = (path: string) =>
      this.http
        .get<any>(`${BASE}${path}`, { params: new HttpParams().set('days', 7) })
        .pipe(map(mapResp));

    return getForecast('/ai/forecast').pipe(
      catchError(() =>
        getForecast('/v1/ai/forecast').pipe(
          catchError(() =>
            this.http.post<any>(`${BASE}/ai/predict`, { period_days: 7 }).pipe(
              map(mapResp),
              catchError(() =>
                getForecast('/api/v1/ai/forecast').pipe(catchError(() => of([] as ForecastRow[]))),
              ),
            ),
          ),
        ),
      ),
    );
  }
}
