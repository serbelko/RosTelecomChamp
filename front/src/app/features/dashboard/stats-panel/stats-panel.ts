import { Component, inject } from '@angular/core';
import { CommonModule } from '@angular/common';
import { MatCardModule } from '@angular/material/card';
import { DashboardService, Metric, ActivityPoint, Robot } from '../dashboard.service';
import { combineLatest } from 'rxjs';
import { map } from 'rxjs/operators';

type MetricsVm = {
  total: number;
  active: number;
  checkedToday: number;
  criticalSkus: number;
  avgBattery: number;
};

@Component({
  selector: 'app-stats-panel',
  standalone: true,
  imports: [CommonModule, MatCardModule],
  templateUrl: './stats-panel.html',
  styleUrls: ['./stats-panel.scss'],
})
export class StatsPanelComponent {
  private api = inject(DashboardService);

  metrics: MetricsVm | null = null;

  readonly W = 300;
  readonly H = 120;
  readonly PAD_TOP = 10;
  readonly PAD_BOTTOM = 18;

  points = '';
  areaPoints = '';
  gridY: number[] = [];
  gridLbl: string[] = [];
  unit = 'сканы/мин';

  private fmt = new Intl.NumberFormat('ru-RU', { maximumFractionDigits: 1 });

  constructor() {
    // KPI
    combineLatest([this.api.metrics$(), this.api.robots$()])
      .pipe(
        map(([metrics, robots]: [Metric[], Robot[]]) => {
          const get = (name: string) => metrics.find((m) => m.name === name)?.value ?? 0;
          const total = get('Всего роботов') || robots.length;
          const offline = get('Оффлайн');
          const criticalSkus = get('Критичных SKU');
          const checkedToday = get('Сканов за час');
          const avgBattery = robots.length
            ? Math.round(
                robots.reduce((s, r) => s + (Number.isFinite(r.battery) ? r.battery : 0), 0) /
                  robots.length,
              )
            : 0;
          return {
            total,
            active: Math.max(0, total - offline),
            checkedToday,
            criticalSkus,
            avgBattery,
          } as MetricsVm;
        }),
      )
      .subscribe((v) => (this.metrics = v));

    // график активности
    this.api.activity$().subscribe((arr: ActivityPoint[]) => {
      const w = this.W;
      const h = this.H;
      const padT = this.PAD_TOP;
      const padB = this.PAD_BOTTOM;
      const usableH = h - padT - padB;

      // последние 60 точек; переводим "сканы/час" -> "сканы/мин"
      const windowed = arr.slice(-60);
      const perMin = windowed.map((p) => {
        const v = Number.isFinite(p.v) ? p.v : 0;
        return v / 60;
      });

      // сглаживание окном 3
      const smooth = (a: number[]) =>
        a.map((_, i) => {
          const a0 = a[Math.max(0, i - 1)];
          const a1 = a[i];
          const a2 = a[Math.min(a.length - 1, i + 1)];
          return (a0 + a1 + a2) / 3;
        });
      const vals = smooth(perMin);

      if (!vals.length) {
        const y = padT + usableH;
        this.points = `0,${y} ${w},${y}`;
        this.areaPoints = `0,${h} 0,${y} ${w},${y} ${w},${h}`;
        this.gridY = [padT + usableH * 0.25, padT + usableH * 0.5, padT + usableH * 0.75];
        this.gridLbl = ['', '', ''];
        return;
      }

      // «красивый» диапазон и шаг
      const { minV, maxV, step } = this.niceRange(Math.min(...vals), Math.max(...vals), 5);
      const scaleY = (v: number) => padT + (1 - (v - minV) / (maxV - minV)) * usableH;

      // сетка
      const ticks: number[] = [];
      for (let t = minV; t <= maxV + 1e-9; t += step) ticks.push(+t.toFixed(6));
      this.gridY = ticks.map((t) => scaleY(t));
      this.gridLbl = ticks.map((t) => this.fmt.format(t));

      // линия и заливка
      if (vals.length === 1) {
        const y = scaleY(vals[0]);
        this.points = `0,${y} ${w},${y}`;
        this.areaPoints = `0,${h} 0,${y} ${w},${y} ${w},${h}`;
        return;
      }

      const xs = vals.map((_, i) => (i / (vals.length - 1)) * w);
      const ys = vals.map((v) => scaleY(v));

      this.points = xs.map((x, i) => `${x},${ys[i]}`).join(' ');
      const baseY = padT + usableH;
      this.areaPoints = [`0,${baseY}`, ...xs.map((x, i) => `${x},${ys[i]}`), `${w},${baseY}`].join(
        ' ',
      );
    });
  }

  /**
   * Подбирает «красивый» диапазон и шаг делений (1 / 2 / 2.5 / 5 · 10^k).
   */
  private niceRange(
    minVraw: number,
    maxVraw: number,
    targetTicks = 5,
  ): { minV: number; maxV: number; step: number } {
    if (maxVraw === minVraw) {
      if (maxVraw === 0) return { minV: 0, maxV: 1, step: 0.2 };
      const span = Math.abs(maxVraw) * 0.2;
      return this.niceRange(maxVraw - span, maxVraw + span, targetTicks);
    }

    let minV = Math.min(minVraw, maxVraw);
    let maxV = Math.max(minVraw, maxVraw);
    const span = maxV - minV;

    const rawStep = span / Math.max(2, targetTicks - 1);
    const pow = Math.pow(10, Math.floor(Math.log10(rawStep)));
    const candidates = [1, 2, 2.5, 5, 10].map((m) => m * pow);

    let step = candidates[0];
    for (const s of candidates) if (Math.abs(s - rawStep) < Math.abs(step - rawStep)) step = s;

    minV = Math.floor(minV / step) * step;
    maxV = Math.ceil(maxV / step) * step;

    return { minV, maxV, step };
  }
}
