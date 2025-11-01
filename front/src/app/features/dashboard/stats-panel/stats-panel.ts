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
  points = '';

  constructor() {
    combineLatest([this.api.metrics$(), this.api.robots$()])
      .pipe(
        map(([metrics, robots]: [Metric[], Robot[]]) => {
          const get = (name: string) => metrics.find((m) => m.name === name)?.value ?? 0;
          const total = get('Всего роботов');
          const offline = get('Оффлайн');
          const criticalSkus = get('Критичных SKU');
          const checkedToday = get('Сканов за час');
          const active = Math.max(0, total - offline);
          const avgBattery = robots.length
            ? Math.round(
                (robots.reduce((s, r) => s + (Number(r.battery) || 0), 0) / robots.length) * 10,
              ) / 10
            : 0;
          return { total, active, checkedToday, criticalSkus, avgBattery } as MetricsVm;
        }),
      )
      .subscribe((vm) => (this.metrics = vm));

    this.api.activity$().subscribe((a: ActivityPoint[]) => {
      if (!a || a.length === 0) {
        this.points = '';
        return;
      }
      if (a.length === 1) {
        const y = 50; // стабильная линия по центру
        this.points = `0,${y} 300,${y}`;
        return;
      }
      const xs = a.map((_, i) => (i / (a.length - 1)) * 300);
      const vals = a.map((p) => (Number.isFinite(p.v) ? p.v : 0));
      const min = Math.min(...vals);
      const max = Math.max(...vals);
      const denom = max - min || 1;
      const ys = vals.map((v) => 100 - ((v - min) / denom) * 100);
      this.points = xs.map((x, i) => `${x},${ys[i]}`).join(' ');
    });
  }
}
