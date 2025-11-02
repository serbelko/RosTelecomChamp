import { Component, OnDestroy, OnInit, inject } from '@angular/core';
import { CommonModule } from '@angular/common';
import { MatCardModule } from '@angular/material/card';
import { Subscription } from 'rxjs';
import { DashboardService, ScanRow } from '../dashboard.service';

@Component({
  selector: 'app-scans-table',
  standalone: true,
  imports: [CommonModule, MatCardModule],
  templateUrl: './scans-table.html',
  styleUrls: ['./scans-table.scss'],
})
export class ScansTableComponent implements OnInit, OnDestroy {
  private api = inject(DashboardService);
  private sub = new Subscription();

  rows: ScanRow[] = [];
  pausedFlag = false;

  ngOnInit(): void {
    this.sub.add(
      this.api.scans$().subscribe((list) => {
        if (this.pausedFlag) return;
        this.rows = list.slice(-20);
        queueMicrotask(() => this.autoScroll());
      }),
    );
  }
  ngOnDestroy(): void {
    this.sub.unsubscribe();
  }

  togglePause(): void {
    this.pausedFlag = !this.pausedFlag;
  }
  paused(): boolean {
    return this.pausedFlag;
  }

  status(r: ScanRow): 'ok' | 'low' | 'crit' {
    return r.stockStatus;
  }

  trackById(_: number, r: ScanRow) {
    return r.id;
  }

  private autoScroll(): void {
    const el = document.querySelector('.scans-body');
    if (!el) return;
    (el as HTMLElement).scrollTop = (el as HTMLElement).scrollHeight;
  }
}
