// src/app/features/history/summary-bar/summary-bar.ts
import { Component, Input } from '@angular/core';
import { CommonModule } from '@angular/common';
import { MatCardModule } from '@angular/material/card';
import { Observable } from 'rxjs';
import { Summary } from '../history.service';

@Component({
  selector: 'history-summary-bar',
  standalone: true,
  imports: [CommonModule, MatCardModule],
  templateUrl: './summary-bar.html',
  styleUrls: ['./summary-bar.scss'],
})
export class SummaryBarComponent {
  @Input() summary$!: Observable<Summary>;
}
