import { Component, OnDestroy, OnInit, inject } from '@angular/core';
import { CommonModule } from '@angular/common';

import { WarehouseMapComponent } from './warehouse-map/warehouse-map';
import { StatsPanelComponent } from './stats-panel/stats-panel';
import { ScansTableComponent } from './scans-table/scans-table';
import { ForecastPanelComponent } from './ai-forecast/ai-forecast';

import { WsService, WsStatus } from '../../core/realtime/ws'; // ✅ путь к новому WsService
import { Subscription } from 'rxjs';
import { DashboardService } from './dashboard.service';

@Component({
  selector: 'app-dashboard',
  standalone: true,
  imports: [
    CommonModule,
    WarehouseMapComponent,
    StatsPanelComponent,
    ScansTableComponent,
    ForecastPanelComponent,
  ],
  templateUrl: './dashboard.html',
  styleUrls: ['./dashboard.scss'],
})
export class DashboardComponent implements OnInit, OnDestroy {
  private readonly ws = inject(WsService);
  private readonly dash = inject(DashboardService);

  wsStatus: WsStatus = 'disconnected';
  private subs = new Subscription();

  ngOnInit() {
    // первая загрузка + периодический опрос
    this.dash.start();

    // следим за статусом сокета
    this.subs.add(this.ws.status$.subscribe((s) => (this.wsStatus = s)));

    // подключаемся к WS-уведомлениям
    this.subs.add(
      this.ws.connect('notifications').subscribe({
        next: (_msg) => this.dash.forceRefresh(),
        error: () => {
          // стор продолжит опрос, если WS временно недоступен
        },
      }),
    );
  }

  ngOnDestroy() {
    this.subs.unsubscribe();
    this.ws.disconnect(); // корректно закрываем соединение
  }
}
