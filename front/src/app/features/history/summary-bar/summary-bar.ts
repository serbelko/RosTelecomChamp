import { Component, Input, inject } from '@angular/core';
import { CommonModule } from '@angular/common';
import { MatCardModule } from '@angular/material/card';
import { HistoryFilters, HistoryService } from '../history.service';
import { AsyncPipe } from '@angular/common';

@Component({
  selector: 'app-summary-bar',
  standalone: true,
  imports: [CommonModule, MatCardModule, AsyncPipe],
  templateUrl: './summary-bar.html',
  styleUrls: ['./summary-bar.scss'],
})
export class SummaryBarComponent {
  private api = inject(HistoryService);
  @Input() filters!: HistoryFilters;

  summary$ = this.api.fetchSummary(this.filters);
}
