import { Injectable } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { environment } from '../../../environments/environment';
import { map, switchMap, startWith } from 'rxjs/operators';
import { Observable, timer } from 'rxjs';

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
  level: 'ok' | 'warn' | 'critical';
  updatedAt: string;
}
export interface Metrics {
  active: number;
  total: number;
  checkedToday: number;
  criticalSkus: number;
  avgBattery: number;
}
export interface ActivityPoint {
  t: string;
  value: number;
}
export interface ScanRow {
  ts: string;
  robotId: string;
  zone: string;
  itemName: string;
  sku: string;
  qty: number;
  status: 'OK' | 'LOW' | 'CRITICAL';
}
export interface ForecastRow {
  itemName: string;
  sku: string;
  stock: number;
  depletionDate: string;
  recommendedQty: number;
  confidence: number;
}

const BASE = environment.apiUrl;

@Injectable({ providedIn: 'root' })
export class DashboardService {
  constructor(private http: HttpClient) {}

  robots$(): Observable<Robot[]> {
    return timer(0, 5000).pipe(switchMap(() => this.http.get<Robot[]>(`${BASE}/api/v1/robots`)));
  }

  zones$(): Observable<ZoneStatus[]> {
    return timer(0, 5000).pipe(
      switchMap(() => this.http.get<ZoneStatus[]>(`${BASE}/api/v1/zones/status`)),
    );
  }

  metrics$(): Observable<Metrics> {
    return timer(0, 5000).pipe(switchMap(() => this.http.get<Metrics>(`${BASE}/api/v1/metrics`)));
  }

  activity$(): Observable<ActivityPoint[]> {
    return timer(0, 5000).pipe(
      switchMap(() => this.http.get<ActivityPoint[]>(`${BASE}/api/v1/metrics/activity?window=1h`)),
    );
  }

  scans$(limit = 20): Observable<ScanRow[]> {
    return timer(0, 5000).pipe(
      switchMap(() => this.http.get<ScanRow[]>(`${BASE}/api/v1/scans?limit=${limit}`)),
    );
  }

  forecast$(): Observable<ForecastRow[]> {
    // по кнопке обновления будем дергать вручную; тут базовая версия
    return this.http
      .get<ForecastRow[]>(`${BASE}/api/v1/ai/forecast?days=7`)
      .pipe(startWith([] as ForecastRow[]));
  }
}
