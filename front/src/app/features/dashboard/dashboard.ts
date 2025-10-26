import { Component, inject, OnDestroy, OnInit, signal } from '@angular/core';
import { CommonModule } from '@angular/common';
import { WarehouseMapComponent } from './warehouse-map/warehouse-map';
import { StatsPanelComponent } from './stats-panel/stats-panel';
import { ScansTableComponent } from './scans-table/scans-table';
import { AiForecastComponent } from './ai-forecast/ai-forecast';
import { WsService, WsStatus } from '../../core/realtime/ws';
import { Subscription } from 'rxjs';

@Component({
  selector: 'app-dashboard',
  standalone: true,
  imports: [
    CommonModule,
    WarehouseMapComponent,
    StatsPanelComponent,
    ScansTableComponent,
    AiForecastComponent,
  ],
  templateUrl: './dashboard.html',
  styleUrls: ['./dashboard.scss'],
})
export class DashboardComponent implements OnInit, OnDestroy {
  private ws = inject(WsService);
  wsStatus: WsStatus = 'disconnected';
  private sub?: Subscription;

  ngOnInit() {
    this.sub = this.ws.status$.subscribe((s) => (this.wsStatus = s));
    this.ws.connect('/ws/robots').subscribe(); // сообщения о роботах по вебсокету
  }

  ngOnDestroy() {
    this.sub?.unsubscribe();
  }
}
