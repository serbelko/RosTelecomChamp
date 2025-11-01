import {
  AfterViewInit,
  ChangeDetectionStrategy,
  ChangeDetectorRef,
  Component,
  ElementRef,
  NgZone,
  ViewChild,
  inject,
} from '@angular/core';
import { CommonModule } from '@angular/common';
import { MatCardModule } from '@angular/material/card';
import { MatButtonModule } from '@angular/material/button';
import { DashboardService, Robot } from '../dashboard.service';
import { map } from 'rxjs/operators';

@Component({
  selector: 'app-warehouse-map',
  standalone: true,
  imports: [CommonModule, MatCardModule, MatButtonModule],
  templateUrl: './warehouse-map.html',
  styleUrls: ['./warehouse-map.scss'],
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class WarehouseMapComponent implements AfterViewInit {
  private api = inject(DashboardService);
  private cdr = inject(ChangeDetectorRef);
  private zone = inject(NgZone);

  // колонки A..Z и 50 реальных строк
  cols = Array.from({ length: 26 }, (_, i) => String.fromCharCode(65 + i));
  rows = Array.from({ length: 50 }, (_, i) => i + 1);

  // геометрия
  cell = 28;
  leftPad = 20; // поле слева для цифр строк
  topPad = 18; // поле сверху для букв колонок

  get mapWidth() {
    return this.leftPad + this.cols.length * this.cell + 1;
  }
  get mapHeight() {
    return this.topPad + this.rows.length * this.cell + 1;
  }

  @ViewChild('viewport', { static: true }) viewportRef?: ElementRef<HTMLDivElement>;
  fitScale = 1;
  userZoom = 1;
  get scale() {
    return this.fitScale * this.userZoom;
  }
  offsetX = 0;
  offsetY = 0;

  // pan state
  private dragging = false;
  private dragStartX = 0;
  private dragStartY = 0;
  private startOffsetX = 0;
  private startOffsetY = 0;

  robots: Robot[] = [];
  zones: Array<{ x: number; y: number; level: 'ok' | 'warn' | 'critical' }> = [];

  ngAfterViewInit() {
    // Первичный пересчёт — после первого рендера (во избежание NG0100)
    this.zone.runOutsideAngular(() => {
      requestAnimationFrame(() => {
        this.zone.run(() => {
          this.recalcFit();
          this.cdr.markForCheck();
        });
      });
    });

    // ResizeObserver — обновляем через rAF
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
    }

    // координаты учитывают верхний отступ topPad
    this.api.robots$().subscribe((r) => {
      this.robots = r.map((x) => ({
        ...x,
        x: this.leftPad + x.x * this.cell + this.cell / 2,
        y: this.topPad + x.y * this.cell + this.cell / 2,
      }));
      this.cdr.markForCheck();
    });

    // зоны + вычисление уровня
    this.api
      .zones$()
      .pipe(
        map((list) =>
          list.map((z) => {
            const col = z.zone.replace(/[0-9]/g, '');
            const row = Number(z.zone.replace(/[A-Z]/g, ''));
            const ci = Math.max(0, Math.min(25, col.charCodeAt(0) - 65));
            const ri = Math.max(0, Math.min(49, row - 1));
            const level: 'ok' | 'warn' | 'critical' =
              z.robots === 0 ? 'ok' : z.robots < 3 ? 'warn' : 'critical';
            return {
              x: this.leftPad + ci * this.cell,
              y: this.topPad + ri * this.cell,
              level,
            };
          }),
        ),
      )
      .subscribe((z) => {
        this.zones = z;
        this.cdr.markForCheck();
      });
  }

  private recalcFit() {
    const host = this.viewportRef!.nativeElement;
    const paddingX = 16;
    const paddingY = 40;
    const availW = Math.max(100, host.clientWidth - paddingX);
    const availH = Math.max(100, host.clientHeight - paddingY);
    const sx = availW / this.mapWidth;
    const sy = availH / this.mapHeight;
    this.fitScale = Math.min(sx, sy);

    const scaledW = this.mapWidth * this.fitScale;
    const scaledH = this.mapHeight * this.fitScale;
    this.offsetX = (availW - scaledW) / (2 * this.fitScale);
    this.offsetY = (availH - scaledH) / (2 * this.fitScale);
  }

  // zoom
  zoomIn() {
    this.userZoom = Math.min(2.5, +(this.userZoom + 0.1).toFixed(2));
    this.cdr.markForCheck();
  }
  zoomOut() {
    this.userZoom = Math.max(0.5, +(this.userZoom - 0.1).toFixed(2));
    this.cdr.markForCheck();
  }
  reset() {
    this.userZoom = 1;
    this.offsetX = 0;
    this.offsetY = 0;
    // пересчёт после сброса
    this.zone.runOutsideAngular(() => {
      requestAnimationFrame(() => {
        this.zone.run(() => {
          this.recalcFit();
          this.cdr.markForCheck();
        });
      });
    });
  }

  // pan
  startPan(ev: MouseEvent | TouchEvent) {
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
  movePan(ev: MouseEvent | TouchEvent) {
    if (!this.dragging) return;
    const p =
      ev instanceof MouseEvent
        ? { x: ev.clientX, y: ev.clientY }
        : {
            x: (ev.touches[0] ?? ev.changedTouches[0]).clientX,
            y: (ev.touches[0] ?? ev.changedTouches[0]).clientY,
          };
    this.offsetX = this.startOffsetX + (p.x - this.dragStartX) / this.scale;
    this.offsetY = this.startOffsetY + (p.y - this.dragStartY) / this.scale;
  }
  endPan() {
    this.dragging = false;
  }

  // цвета
  robotColor(s: Robot['status']) {
    return s === 'active' ? '#2e7d32' : s === 'low' ? '#f9a825' : '#c62828';
  }
  zoneColor(l: 'ok' | 'warn' | 'critical') {
    return l === 'ok' ? '#2e7d32' : l === 'warn' ? '#f9a825' : '#c62828';
  }
}
