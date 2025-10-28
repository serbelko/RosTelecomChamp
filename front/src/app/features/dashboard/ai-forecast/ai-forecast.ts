import { Component, inject } from '@angular/core';
import { CommonModule } from '@angular/common';
import { MatCardModule } from '@angular/material/card';
import { MatButtonModule } from '@angular/material/button';
import { DashboardService, ForecastRow } from '../dashboard.service';

@Component({
  selector: 'app-ai-forecast',
  standalone: true,
  imports: [CommonModule, MatCardModule, MatButtonModule],
  templateUrl: './ai-forecast.html',
  styleUrls: ['./ai-forecast.scss'],
})
export class AiForecastComponent {
  private api = inject(DashboardService);

  rows: ForecastRow[] = [];

  constructor() {
    this.api.forecast$().subscribe((r) => (this.rows = (r || []).slice(0, 5)));
  }

  refresh() {
    this.api.forecast$().subscribe((r) => (this.rows = (r || []).slice(0, 5)));
  }
}
