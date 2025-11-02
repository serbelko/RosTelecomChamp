// src/app/features/dashboard/warehouse-map/warehouse-map.ts
import {
  AfterViewInit,
  ChangeDetectionStrategy,
  ChangeDetectorRef,
  Component,
  ElementRef,
  NgZone,
  ViewChild,
  inject,
  OnDestroy,
} from '@angular/core';
import { CommonModule } from '@angular/common';
import { MatCardModule } from '@angular/material/card';
import { MatButtonModule } from '@angular/material/button';
import { MatIconModule } from '@angular/material/icon';
import { MatDialog, MatDialogModule } from '@angular/material/dialog';

import { DashboardService, Robot, ZoneSummary } from '../dashboard.service';
import { CsvUploadDialogComponent } from '../../history/csv-upload-dialog/csv-upload-dialog';
import { Subscription } from 'rxjs';
import { map } from 'rxjs/operators';

type HeatCell = { x: number; y: number; level: 'ok' | 'warn' | 'critical' };
type PlacedRobot = Robot & { px: number; py: number; dotR: number; label?: string };

@Component({
  selector: 'app-warehouse-map',
  standalone: true,
  imports: [CommonModule, MatCardModule, MatButtonModule, MatIconModule, MatDialogModule],
  templateUrl: './warehouse-map.html',
  styleUrls: ['./warehouse-map.scss'],
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class WarehouseMapComponent implements AfterViewInit, OnDestroy {
  private api = inject(DashboardService);
  private cdr = inject(ChangeDetectorRef);
  private zone = inject(NgZone);
  private dialog = inject(MatDialog);

  private subs = new Subscription();

  // сетка A..Z × 1..50
  cols = Array.from({ length: 26 }, (_, i) => String.fromCharCode(65 + i));
  rows = Array.from({ length: 50 }, (_, i) => i + 1);

  // геометрия
  cell = 28;
  leftPad = 20;
  topPad = 18;

  get mapWidth(): number {
    return this.leftPad + this.cols.length * this.cell + 1;
  }
  get mapHeight(): number {
    return this.topPad + this.rows.length * this.cell + 1;
  }

  @ViewChild('viewport', { static: true }) viewportRef?: ElementRef<HTMLDivElement>;
  fitScale = 1;
  userZoom = 1;
  get scale(): number {
    return this.fitScale * this.userZoom;
  }
  // безопасный масштаб для viewBox (не NaN/0)
  get safeScale(): number {
    const s = this.scale;
    return Number.isFinite(s) && s > 0 ? s : 1;
  }

  offsetX = 0;
  offsetY = 0;

  // pan state
  private dragging = false;
  private dragStartX = 0;
  private dragStartY = 0;
  private startOffsetX = 0;
  private startOffsetY = 0;

  robots: PlacedRobot[] = [];
  zones: HeatCell[] = [];

  // tooltip
  tipVisible = false;
  tipX = 0;
  tipY = 0;
  tipRobot: Robot | null = null;

  ngAfterViewInit(): void {
    // первичный расчёт после отрисовки
    this.zone.runOutsideAngular(() => {
      requestAnimationFrame(() => {
        this.zone.run(() => {
          this.recalcFit();
          this.cdr.markForCheck();
        });
      });
    });

    // пересчёт при ресайзе контейнера
    const host = this.viewportRef?.nativeElement;
    if (host) {
      const ro = new ResizeObserver(() => {
        this.zone.runOutsideAngular(() => {
          requestAnimationFrame(() => {
            this.zone.run(() => {
              this.recalcFit();
              this.cdr.markForCheck();
            });
          });
        });
      });
      ro.observe(host);
      // отписка при destroy
      this.subs.add({
        unsubscribe: () => ro.disconnect(),
      });
    }

    // === роботы: группировка по клетке + раскладка по окружностям ===
    this.subs.add(
      this.api.robots$().subscribe((list: Robot[]) => {
        const groups = new Map<string, Robot[]>();
        for (const r of list) {
          const key = `${r.x}_${r.y}`;
          const arr = groups.get(key);
          arr ? arr.push(r) : groups.set(key, [r]);
        }

        const placed: PlacedRobot[] = [];
        const cxOf = (gx: number) => this.leftPad + gx * this.cell + this.cell / 2;
        const cyOf = (gy: number) => this.topPad + gy * this.cell + this.cell / 2;

        const maxRing = Math.floor((this.cell - 6) / 2);
        const midRing = Math.max(8, Math.floor(this.cell * 0.35));
        const inRing = Math.max(6, Math.floor(this.cell * 0.25));

        for (const [key, arr] of groups.entries()) {
          const [gx, gy] = key.split('_').map((v) => +v);
          const cx = cxOf(gx);
          const cy = cyOf(gy);

          const n = arr.length;
          const dotR =
            n <= 3
              ? Math.min(7, Math.floor(this.cell * 0.28))
              : n <= 6
                ? Math.min(6, Math.floor(this.cell * 0.24))
                : n <= 12
                  ? Math.min(5, Math.floor(this.cell * 0.2))
                  : Math.min(4, Math.floor(this.cell * 0.17));

          const placeRing = (items: Robot[], radius: number) => {
            const k = items.length;
            for (let i = 0; i < k; i++) {
              const angle = (2 * Math.PI * i) / k;
              placed.push({
                ...items[i],
                px: cx + radius * Math.cos(angle),
                py: cy + radius * Math.sin(angle),
                dotR,
                label: dotR >= 6 ? (items[i].id?.slice(-2) ?? '') : undefined,
              });
            }
          };

          if (n === 1) {
            placed.push({
              ...arr[0],
              px: cx,
              py: cy,
              dotR,
              label: dotR >= 6 ? arr[0].id?.slice(-2) : undefined,
            });
          } else if (n <= 6) {
            placeRing(arr, Math.min(maxRing, Math.max(midRing, dotR + 3)));
          } else {
            placed.push({ ...arr[0], px: cx, py: cy, dotR, label: undefined });
            const rest = arr.slice(1);
            const ring1 = rest.slice(0, Math.min(6, rest.length));
            const ring2 = rest.slice(ring1.length);
            placeRing(ring1, Math.min(maxRing, Math.max(midRing, dotR + 4)));
            if (ring2.length > 0) {
              const r2 = Math.min(maxRing, Math.max(midRing - dotR - 3, inRing));
              placeRing(ring2, r2);
            }
          }
        }

        this.robots = placed.filter((r) => Number.isFinite(r.px) && Number.isFinite(r.py));
        this.cdr.markForCheck();
      }),
    );

    // === зоны ===
    this.subs.add(
      this.api
        .zones$()
        .pipe(
          map((list: ZoneSummary[]): HeatCell[] =>
            list.map((z) => {
              const col = z.zone.replace(/[0-9]/g, '');
              const rowNum = Number(z.zone.replace(/[A-Za-z]/g, ''));
              const colChar = (col[0] || 'A').toUpperCase().charCodeAt(0);
              const ci = Math.max(0, Math.min(25, Number.isFinite(colChar) ? colChar - 65 : 0));
              const ri = Math.max(0, Math.min(49, (Number.isFinite(rowNum) ? rowNum : 1) - 1));
              const level: HeatCell['level'] =
                z.robots === 0 ? 'ok' : z.robots < 3 ? 'warn' : 'critical';
              return { x: this.leftPad + ci * this.cell, y: this.topPad + ri * this.cell, level };
            }),
          ),
        )
        .subscribe((zones) => {
          this.zones = zones;
          this.cdr.markForCheck();
        }),
    );
  }

  ngOnDestroy(): void {
    this.subs.unsubscribe();
  }

  private recalcFit(): void {
    const host = this.viewportRef?.nativeElement;
    if (!host) {
      this.fitScale = 1;
      this.offsetX = 0;
      this.offsetY = 0;
      return;
    }

    // страхуемся от нулевых размеров на этапе инициализации
    const availW = Math.max(320, host.clientWidth - 16);
    const availH = Math.max(320, host.clientHeight - 40);

    const sx = availW / this.mapWidth;
    const sy = availH / this.mapHeight;
    const fit = Math.max(0.1, Math.min(sx, sy)); // clamp

    this.fitScale = Number.isFinite(fit) ? fit : 1;

    const scaledW = this.mapWidth * this.fitScale;
    const scaledH = this.mapHeight * this.fitScale;

    this.offsetX = (availW - scaledW) / (2 * this.fitScale);
    this.offsetY = (availH - scaledH) / (2 * this.fitScale);

    if (!Number.isFinite(this.offsetX)) this.offsetX = 0;
    if (!Number.isFinite(this.offsetY)) this.offsetY = 0;
  }

  // zoom / pan
  zoomIn(): void {
    this.userZoom = Math.min(2.5, +(this.userZoom + 0.1).toFixed(2));
    this.cdr.markForCheck();
  }
  zoomOut(): void {
    this.userZoom = Math.max(0.5, +(this.userZoom - 0.1).toFixed(2));
    this.cdr.markForCheck();
  }
  reset(): void {
    this.userZoom = 1;
    this.offsetX = 0;
    this.offsetY = 0;
    this.zone.runOutsideAngular(() =>
      requestAnimationFrame(() =>
        this.zone.run(() => {
          this.recalcFit();
          this.cdr.markForCheck();
        }),
      ),
    );
  }
  startPan(ev: MouseEvent | TouchEvent): void {
    const p =
      ev instanceof MouseEvent
        ? { x: ev.clientX, y: ev.clientY }
        : {
            x: (ev.touches[0] ?? ev.changedTouches[0]).clientX,
            y: (ev.touches[0] ?? ev.changedTouches[0]).clientY,
          };
    this.dragging = true;
    this.dragStartX = p.x;
    this.dragStartY = p.y;
    this.startOffsetX = this.offsetX;
    this.startOffsetY = this.offsetY;
  }
  movePan(ev: MouseEvent | TouchEvent): void {
    if (!this.dragging) return;
    const p =
      ev instanceof MouseEvent
        ? { x: ev.clientX, y: ev.clientY }
        : {
            x: (ev.touches[0] ?? ev.changedTouches[0]).clientX,
            y: (ev.touches[0] ?? ev.changedTouches[0]).clientY,
          };
    this.offsetX = this.startOffsetX + (p.x - this.dragStartX) / this.safeScale;
    this.offsetY = this.startOffsetY + (p.y - this.dragStartY) / this.safeScale;
  }
  endPan(): void {
    this.dragging = false;
  }

  // hover tooltip
  showTip(ev: MouseEvent, r: Robot): void {
    this.tipRobot = r;
    this.tipVisible = true;
    this.moveTip(ev);
  }
  moveTip(ev: MouseEvent): void {
    const host = this.viewportRef?.nativeElement;
    if (!host) return;
    const rect = host.getBoundingClientRect();
    this.tipX = ev.clientX - rect.left + 12;
    this.tipY = ev.clientY - rect.top + 12;
  }
  hideTip(): void {
    this.tipVisible = false;
    this.tipRobot = null;
  }

  // helpers
  fontSize(r: { dotR: number }): number {
    const val = Math.floor(r.dotR * 1.1);
    return val < 8 ? 8 : val;
  }
  robotColor(s: Robot['status']): string {
    return s === 'active' ? '#2e7d32' : s === 'low' ? '#f9a825' : '#c62828';
  }
  zoneColor(l: HeatCell['level']): string {
    return l === 'ok' ? '#2e7d32' : l === 'warn' ? '#f9a825' : '#c62828';
  }
  trackByRobotId = (_: number, r: { id: string }) => r.id;

  // загрузка CSV
  openUploadDialog(): void {
    this.dialog
      .open(CsvUploadDialogComponent, {
        width: '560px',
        autoFocus: false,
        restoreFocus: false,
      })
      .afterClosed()
      .subscribe((ok) => {
        if (ok) {
          this.api.forceRefresh();
        }
      });
  }

  // время в тултипе
  fmtUpdated(iso?: string | null): string {
    if (!iso) return '—';
    const d = new Date(iso);
    if (Number.isNaN(d.getTime())) return String(iso);

    const now = new Date();
    const diffSec = Math.max(0, Math.floor((now.getTime() - d.getTime()) / 1000));

    let rel: string;
    if (diffSec < 60) rel = 'только что';
    else if (diffSec < 3600) rel = `${Math.floor(diffSec / 60)} мин назад`;
    else if (diffSec < 86400) rel = `${Math.floor(diffSec / 3600)} ч назад`;
    else rel = `${Math.floor(diffSec / 86400)} дн назад`;

    const abs = d.toLocaleString('ru-RU', {
      year: 'numeric',
      month: '2-digit',
      day: '2-digit',
      hour: '2-digit',
      minute: '2-digit',
      second: '2-digit',
    });

    return `${abs} (${rel})`;
  }
}
