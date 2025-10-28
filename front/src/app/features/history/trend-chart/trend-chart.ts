import { Component, Input, OnDestroy, OnInit, inject } from '@angular/core';
import { CommonModule } from '@angular/common';
import { HistoryFilters, HistoryService, TrendPoint } from '../history.service';
import { MatCardModule } from '@angular/material/card';
import {
  Chart,
  LineController,
  LineElement,
  PointElement,
  LinearScale,
  TimeScale,
  Title,
  Tooltip,
  Legend,
  CategoryScale,
} from 'chart.js';

Chart.register(
  LineController,
  LineElement,
  PointElement,
  LinearScale,
  CategoryScale,
  Title,
  Tooltip,
  Legend,
);

@Component({
  selector: 'app-trend-chart',
  standalone: true,
  imports: [CommonModule, MatCardModule],
  templateUrl: './trend-chart.html',
  styleUrls: ['./trend-chart.scss'],
})
export class TrendChartComponent implements OnInit, OnDestroy {
  private api = inject(HistoryService);
  @Input() filters!: HistoryFilters;

  private chart?: Chart;

  ngOnInit() {
    this.load();
  }
  ngOnChanges() {
    this.load();
  }

  ngOnDestroy() {
    this.chart?.destroy();
  }

  private load() {
    if (!this.filters) return;
    this.api.fetchTrend(this.filters).subscribe((points) => {
      this.render(points);
    });
  }

  private render(points: TrendPoint[]) {
    const labels = points.map((p) => p.t);
    const keys = Object.keys(points[0] || {}).filter((k) => k !== 't');
    const datasets = keys.map((sku, idx) => ({
      label: sku,
      data: points.map((p) => Number(p[sku] ?? 0)),
      fill: false,
      tension: 0.25,
    }));

    const canvas = document.getElementById('trend-canvas') as HTMLCanvasElement;
    this.chart?.destroy();
    this.chart = new Chart(canvas, {
      type: 'line',
      data: { labels, datasets },
      options: {
        responsive: true,
        plugins: {
          legend: { position: 'bottom' },
          title: { display: true, text: 'Тренд остатков' },
        },
        scales: { x: { ticks: { maxRotation: 0 } }, y: { beginAtZero: true } },
      },
    });
  }
}
