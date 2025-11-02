// src/app/features/dashboard/dashboard.service.ts
import { Injectable } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { BehaviorSubject, Observable, of, timer } from 'rxjs';
import { catchError, map, switchMap } from 'rxjs/operators';

export interface Robot {
  id: string;
  x: number;
  y: number;
  battery: number;
  status: 'active' | 'low' | 'offline';
  zone: string;
  updatedAt: string;
}

export interface ZoneSummary {
  zone: string;
  robots: number;
}
export interface Metric {
  name: string;
  value: number;
}

export interface ActivityPoint {
  t: string; // ISO
  v: number; // scans per minute
}

export interface ScanRow {
  id: number; // id записи
  robotId: string; // ID робота (если бэк не отдаёт, будет '—')
  productId: string; // артикул
  productName: string; // название
  zone: string; // зона
  quantity: number; // остаток / отсканированное кол-во
  scannedAt: string; // ISO
  stockStatus: 'ok' | 'low' | 'crit';
}

export interface ForecastRow {
  productId: string;
  category: string;
  expected: number;
  stockoutInDays: number | null;
}

interface DashboardResponse {
  robots: Array<{
    robot_id: string;
    status: string;
    battery_level: number;
    last_update: string;
    zone: string;
    row: number;
    shelf: number;
  }>;
  recent_scans: Array<{
    id: number;
    robot_id?: string;
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
    scans_last_hour: number; // кол-во сканов за последний час
    // плюс могут быть разные варианты "проверено сегодня":
    checked_today?: number;
    items_checked_today?: number;
    processed_today?: number;
    scans_today?: number;
  };
}

@Injectable({ providedIn: 'root' })
export class DashboardService {
  private robotsSub = new BehaviorSubject<Robot[]>([]);
  private zonesSub = new BehaviorSubject<ZoneSummary[]>([]);
  private metricsSub = new BehaviorSubject<Metric[]>([]);
  private activitySub = new BehaviorSubject<ActivityPoint[]>([]);
  private scansSub = new BehaviorSubject<ScanRow[]>([]);
  private checkedTodaySub = new BehaviorSubject<number>(0);
  private avgBatterySub = new BehaviorSubject<number>(0);

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
  checkedToday$(): Observable<number> {
    return this.checkedTodaySub.asObservable();
  }
  avgBattery$(): Observable<number> {
    return this.avgBatterySub.asObservable();
  }

  private stockBadge(qty: number): 'ok' | 'low' | 'crit' {
    const q = Number(qty) || 0;
    if (q <= 5) return 'crit';
    if (q <= 15) return 'low';
    return 'ok';
  }

  private loadOnce(): Observable<void> {
    return this.http.get<DashboardResponse>(`/api/dashboard/current`).pipe(
      map((r) => {
        // --- Роботы ---
        const robots: Robot[] = (r.robots ?? []).map((x) => {
          const zoneChar = String(x.zone ?? 'A')
            .trim()
            .toUpperCase();
          const colCode = zoneChar.charCodeAt(0);
          const ci = Math.max(0, Math.min(25, Number.isFinite(colCode) ? colCode - 65 : 0));
          const rowNum = Number(x.row ?? 1);
          const ri = Math.max(0, Math.min(49, (Number.isFinite(rowNum) ? rowNum : 1) - 1));

          const rawStatus = String(x.status ?? '').toLowerCase();
          const status: Robot['status'] =
            rawStatus === 'offline' ? 'offline' : (x.battery_level ?? 0) < 20 ? 'low' : 'active';

          return {
            id: String(x.robot_id ?? ''),
            x: ci,
            y: ri,
            battery: Math.round(Number(x.battery_level ?? 0)),
            status,
            zone: `${zoneChar}${rowNum || ''}`,
            updatedAt: String(x.last_update ?? ''),
          };
        });
        this.robotsSub.next(robots);

        // Средний заряд (в %)
        const avg = robots.length
          ? +(robots.reduce((s, r) => s + (r.battery ?? 0), 0) / robots.length).toFixed(1)
          : 0;
        this.avgBatterySub.next(avg);

        // --- Зоны ---
        const zoneMap = new Map<string, number>();
        for (const rbt of robots) zoneMap.set(rbt.zone, (zoneMap.get(rbt.zone) ?? 0) + 1);
        this.zonesSub.next(Array.from(zoneMap, ([zone, robots]) => ({ zone, robots })));

        // --- Метрики (без «Проверено сегодня», его даём отдельным стримом) ---
        const m: Metric[] = [
          { name: 'Всего роботов', value: r.statistics?.total_robots ?? robots.length },
          {
            name: 'Оффлайн',
            value:
              r.statistics?.offline_robots ?? robots.filter((x) => x.status === 'offline').length,
          },
          { name: 'Критичных SKU', value: r.statistics?.critical_items ?? 0 },
          { name: 'Мало остатков', value: r.statistics?.low_stock_items ?? 0 },
        ];
        this.metricsSub.next(m);

        // --- Проверено сегодня (поддержка разных ключей) ---
        const checkedToday =
          (r.statistics as any)?.checked_today ??
          (r.statistics as any)?.items_checked_today ??
          (r.statistics as any)?.processed_today ??
          (r.statistics as any)?.scans_today ??
          0;
        this.checkedTodaySub.next(Number(checkedToday) || 0);

        // --- Активность: сканы/мин ---
        const perMinRaw = (r.statistics?.scans_last_hour ?? 0) / 60;
        const perMin = Math.max(0, Math.round(perMinRaw * 10) / 10);
        const prev = this.activitySub.getValue();
        this.activitySub.next([...prev, { t: new Date().toISOString(), v: perMin }].slice(-60));

        // --- Последние сканы (макс. 20) ---
        const scans: ScanRow[] = (r.recent_scans ?? []).map((s) => ({
          id: Number(s.id),
          robotId: String(s.robot_id ?? '—'),
          productId: String(s.product_id ?? ''),
          productName: String(s.product_name ?? ''),
          zone: String(s.zone ?? ''),
          quantity: Number(s.quantity ?? 0),
          scannedAt: String(s.scanned_at ?? ''),
          stockStatus: this.stockBadge(Number(s.quantity ?? 0)),
        }));
        this.scansSub.next(scans.slice(-20));
      }),
      catchError(() => of(void 0)),
    );
  }

  forceRefresh(): void {
    this.loadOnce().subscribe();
  }

  start(): void {
    this.forceRefresh();
    timer(5000, 5000)
      .pipe(switchMap(() => this.loadOnce()))
      .subscribe();
  }

  // --- Прогноз ---
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
