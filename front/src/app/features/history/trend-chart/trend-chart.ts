import { Component, Input, OnChanges, SimpleChanges, inject } from '@angular/core';
import { CommonModule } from '@angular/common';
import { HistoryFilters, HistoryService, TrendPoint } from '../history.service';

@Component({
  selector: 'history-trend-chart',
  standalone: true,
  imports: [CommonModule],
  templateUrl: './trend-chart.html',
  styleUrls: ['./trend-chart.scss'],
})
export class TrendChartComponent implements OnChanges {
  private api = inject(HistoryService);

  @Input() filters!: HistoryFilters;

  // данные
  points: TrendPoint[] = [];

  // геометрия
  readonly w = 640;
  readonly h = 180;
  readonly padL = 44;
  readonly padR = 10;
  readonly padT = 10;
  readonly padB = 28;

  // ось Y
  yMin = 0;
  yMax = 1;
  yTicks: number[] = [];

  // предвычисленные пути
  linePath = '';
  areaPath = '';
  xLabels: string[] = [];

  ngOnChanges(ch: SimpleChanges): void {
    if (ch['filters']) {
      this.load();
    }
  }

  private load(): void {
    this.api.fetchTrend(this.filters).subscribe((pts) => {
      // если бэк вернул пусто — нарисуем плоский ноль
      this.points = (pts ?? []).slice(-60);
      if (this.points.length === 0) {
        this.points = Array.from({ length: 10 }, (_, i) => ({
          t: new Date(Date.now() - (9 - i) * 60000).toISOString(),
          total: 0,
        }));
      }

      // диапазон
      const vals = this.points.map((p) => Number(p.total) || 0);
      const vMin = Math.min(...vals, 0);
      const vMax = Math.max(...vals, 1);
      // «приятные» границы
      const nice = this.niceRange(vMin, vMax, 5);
      this.yMin = nice.min;
      this.yMax = nice.max;
      this.yTicks = this.makeTicks(this.yMin, this.yMax, 5);

      // подписи X (каждая 5-я точка)
      this.xLabels = this.points.map((p, i) =>
        i % Math.max(1, Math.floor(this.points.length / 6)) === 0
          ? new Date(p.t).toLocaleTimeString('ru-RU', { hour: '2-digit', minute: '2-digit' })
          : '',
      );

      // пути
      this.rebuildPaths();
    });
  }

  private plotW(): number {
    return this.w - this.padL - this.padR;
  }
  private plotH(): number {
    return this.h - this.padT - this.padB;
  }

  xAt(i: number): number {
    if (this.points.length <= 1) return this.padL;
    const k = i / (this.points.length - 1);
    return this.padL + k * this.plotW();
  }
  yAt(v: number): number {
    const h = this.plotH();
    const span = Math.max(1e-9, this.yMax - this.yMin);
    const k = (v - this.yMin) / span;
    return this.padT + (1 - k) * h;
  }

  private rebuildPaths(): void {
    if (this.points.length === 0) {
      this.linePath = '';
      this.areaPath = '';
      return;
    }
    const d: string[] = [];
    const a: string[] = [];

    for (let i = 0; i < this.points.length; i++) {
      const x = this.xAt(i);
      const y = this.yAt(this.points[i].total);
      d.push(i === 0 ? `M ${x} ${y}` : `L ${x} ${y}`);
      a.push(`${x},${y}`);
    }
    // замкнём «подложку» к низу области графика
    const x0 = this.xAt(0);
    const xN = this.xAt(this.points.length - 1);
    const yBottom = this.padT + this.plotH();
    this.areaPath = `M ${x0} ${yBottom} L ${a.join(' ')} L ${xN} ${yBottom} Z`;
    this.linePath = d.join(' ');
  }

  private makeTicks(min: number, max: number, n = 5): number[] {
    if (n <= 1) return [min, max];
    const step = (max - min) / (n - 1);
    const res: number[] = [];
    for (let i = 0; i < n; i++) res.push(min + i * step);
    return res.map((x) => Math.round(x * 10) / 10);
  }

  private niceRange(minRaw: number, maxRaw: number, targetTicks = 5): { min: number; max: number } {
    if (!isFinite(minRaw) || !isFinite(maxRaw)) return { min: 0, max: 1 };
    if (minRaw === maxRaw) {
      const v = minRaw || 1;
      return { min: 0, max: v * 2 };
    }
    let span = maxRaw - minRaw;
    const step0 = span / Math.max(1, targetTicks - 1);
    const mag = Math.pow(10, Math.floor(Math.log10(step0)));
    const norms = [1, 2, 2.5, 5, 10];
    let niceStep = norms[0] * mag;
    for (const n of norms) {
      const s = n * mag;
      if (step0 <= s) {
        niceStep = s;
        break;
      }
    }
    const niceMin = Math.floor(minRaw / niceStep) * niceStep;
    const niceMax = Math.ceil(maxRaw / niceStep) * niceStep;
    return { min: niceMin, max: niceMax };
    
  }
}
