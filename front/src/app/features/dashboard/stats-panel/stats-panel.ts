import { Component, inject } from '@angular/core';
import { CommonModule } from '@angular/common';
import { MatCardModule } from '@angular/material/card';
import { DashboardService, Metrics, ActivityPoint } from '../dashboard.service';

@Component({
  selector: 'app-stats-panel',
  standalone: true,
  imports: [CommonModule, MatCardModule],
  templateUrl: './stats-panel.html',
  styleUrls: ['./stats-panel.scss'],
})
export class StatsPanelComponent {
  private api = inject(DashboardService);

  metrics?: Metrics;
  points = '';

  constructor() {
    this.api.metrics$().subscribe((m) => (this.metrics = m));
    this.api.activity$().subscribe((a) => {
      // нормализуем точки в 300x100
      if (!a?.length) {
        this.points = '';
        return;
      }
      const xs = a.map((_, i) => (i / (a.length - 1)) * 300);
      const vals = a.map((p) => p.value);
      const min = Math.min(...vals),
        max = Math.max(...vals) || 1;
      const ys = vals.map((v) => 100 - ((v - min) / (max - min || 1)) * 100);
      this.points = xs.map((x, i) => `${x},${ys[i]}`).join(' ');
    });
  }
}
