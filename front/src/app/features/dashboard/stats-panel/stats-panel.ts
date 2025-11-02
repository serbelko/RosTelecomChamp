import { Component, inject } from '@angular/core';
import { CommonModule } from '@angular/common';
import { MatCardModule } from '@angular/material/card';
import { DashboardService, ActivityPoint, Metric } from '../dashboard.service';
import { map } from 'rxjs/operators';
import { Observable } from 'rxjs';

@Component({
  selector: 'app-stats-panel',
  standalone: true,
  imports: [CommonModule, MatCardModule],
  templateUrl: './stats-panel.html',
  styleUrls: ['./stats-panel.scss'],
})
export class StatsPanelComponent {
  public api = inject(DashboardService);

  // Метрики и активность
  metrics$: Observable<Metric[]> = this.api.metrics$();

  // Из активности берём последние 60 точек (сканы/мин)
  points$: Observable<ActivityPoint[]> = this.api.activity$();

  // --- Вспомогательные методы для графика (чтобы не городить выражения в html) ---

  // Красивые тики по Y
  yTicks(points: ActivityPoint[], targetTicks = 5): number[] {
    if (!points?.length) return [0, 0.5, 1];
    const vals = points.map((p) => Number(p.v) || 0);
    const minV = Math.min(...vals);
    const maxV = Math.max(...vals);
    const range = Math.max(1e-6, maxV - minV);
    // nice step
    const rawStep = range / Math.max(1, targetTicks - 1);
    const mag = Math.pow(10, Math.floor(Math.log10(rawStep)));
    const norm = rawStep / mag;
    let step = mag;
    if (norm >= 5) step = 5 * mag;
    else if (norm >= 2) step = 2 * mag;

    const start = Math.floor(minV / step) * step;
    const end = Math.ceil(maxV / step) * step;
    const ticks: number[] = [];
    for (let v = start; v <= end + 1e-9; v += step) ticks.push(+v.toFixed(6));
    // гарантируем минимум 3 тика
    while (ticks.length < 3) ticks.push(+(ticks[ticks.length - 1] + step).toFixed(6));
    return ticks.slice(0, 6);
  }

  // Преобразование значения в Y-пиксели (0 внизу)
  yToPx(v: number, h: number, minV: number, maxV: number): number {
    const r = Math.max(1e-6, maxV - minV);
    const t = (v - minV) / r; // 0..1 вверх
    return Math.round((1 - t) * h);
  }

  // Генерация SVG-пути для линии
  buildPath(points: ActivityPoint[], w = 600, h = 140): string {
    if (!points?.length) return '';
    const vals = points.map((p) => Number(p.v) || 0);
    const minV = Math.min(...vals);
    const maxV = Math.max(...vals);
    const n = points.length;
    const stepX = n > 1 ? w / (n - 1) : 0;

    const xy = points.map((p, i) => {
      const x = Math.round(i * stepX);
      const y = this.yToPx(Number(p.v) || 0, h, minV, maxV);
      return `${x},${y}`;
    });

    return 'M ' + xy.join(' L ');
  }

  // Подготовка подписей OX (время, каждые 10 точек)
  xLabels(points: ActivityPoint[], w = 600): { x: number; label: string }[] {
    if (!points?.length) return [];
    const n = points.length;
    const stepX = n > 1 ? w / (n - 1) : 0;
    const labels: { x: number; label: string }[] = [];
    for (let i = 0; i < n; i += 10) {
      const d = new Date(points[i].t);
      const x = Math.round(i * stepX);
      labels.push({
        x,
        label: d.toLocaleTimeString('ru-RU', { hour: '2-digit', minute: '2-digit' }),
      });
    }
    // последний
    const last = new Date(points[n - 1].t);
    labels.push({
      x: Math.round((n - 1) * stepX),
      label: last.toLocaleTimeString('ru-RU', { hour: '2-digit', minute: '2-digit' }),
    });
    return labels;
  }

  // Формат числа для осей
  fmt(n: number): string {
    return (Math.round(n * 10) / 10).toString().replace('.', ',');
  }
}
