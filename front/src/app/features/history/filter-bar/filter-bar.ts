import { Component, EventEmitter, Input, Output, inject } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormBuilder, ReactiveFormsModule } from '@angular/forms';
import { MatDatepickerModule } from '@angular/material/datepicker';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatInputModule } from '@angular/material/input';
import { MatButtonModule } from '@angular/material/button';
import { MatIconModule } from '@angular/material/icon';
import { MatSelectModule } from '@angular/material/select';
import { MatCheckboxModule } from '@angular/material/checkbox';
import { provideNativeDateAdapter } from '@angular/material/core';
import { HistoryFilters } from '../history.service';

@Component({
  selector: 'app-filter-bar',
  standalone: true,
  providers: [provideNativeDateAdapter()],
  imports: [
    CommonModule,
    ReactiveFormsModule,
    MatDatepickerModule,
    MatFormFieldModule,
    MatInputModule,
    MatButtonModule,
    MatIconModule,
    MatSelectModule,
    MatCheckboxModule,
  ],
  templateUrl: './filter-bar.html',
  styleUrls: ['./filter-bar.scss'],
})
export class FilterBarComponent {
  private fb = inject(FormBuilder);

  @Input() filters?: HistoryFilters;
  @Output() apply = new EventEmitter<HistoryFilters>();

  zones = [
    'A',
    'B',
    'C',
    'D',
    'E',
    'F',
    'G',
    'H',
    'I',
    'J',
    'K',
    'L',
    'M',
    'N',
    'O',
    'P',
    'Q',
    'R',
    'S',
    'T',
    'U',
    'V',
    'W',
    'X',
    'Y',
    'Z',
  ];
  categories = ['Электроника', 'Сетевое', 'Кабель', 'Прочее'];

  form = this.fb.group({
    from: [null as Date | null],
    to: [null as Date | null],
    zones: [[] as string[]],
    categories: [[] as string[]],
    statusOK: [true],
    statusLOW: [true], // будет маппиться в LOW_STOCK
    statusCRIT: [true],
    query: [''],
    pageSize: [20],
  });

  ngOnChanges() {
    if (!this.filters) return;
    const f = this.filters;
    this.form.patchValue(
      {
        from: f.from ? new Date(f.from) : null,
        to: f.to ? new Date(f.to) : null,
        zones: f.zones ?? [],
        categories: (f as any).categories ?? [], // на случай если HistoryFilters без categories
        statusOK: f.status?.includes('OK') ?? true,
        statusLOW: f.status?.includes('LOW_STOCK') ?? true,
        statusCRIT: f.status?.includes('CRITICAL') ?? true,
        query: f.query ?? '',
        pageSize: f.pageSize ?? 20,
      },
      { emitEvent: false },
    );
  }

  quick(days: 'today' | 'yesterday' | 'week' | 'month') {
    const now = new Date();
    const start = new Date();
    if (days === 'today') start.setHours(0, 0, 0, 0);
    if (days === 'yesterday') {
      start.setDate(now.getDate() - 1);
      start.setHours(0, 0, 0, 0);
      now.setDate(now.getDate() - 1);
      now.setHours(23, 59, 59, 999);
    }
    if (days === 'week') {
      start.setDate(now.getDate() - 6);
      start.setHours(0, 0, 0, 0);
    }
    if (days === 'month') {
      start.setMonth(now.getMonth() - 1);
      start.setHours(0, 0, 0, 0);
    }
    this.form.patchValue({ from: start, to: now });
  }

  reset() {
    this.form.reset({
      from: null,
      to: null,
      zones: [],
      categories: [],
      statusOK: true,
      statusLOW: true,
      statusCRIT: true,
      query: '',
      pageSize: 20,
    });
    this.emit();
  }

  emit() {
    const v = this.form.value;
    const statuses = [
      v.statusOK ? 'OK' : null,
      v.statusLOW ? 'LOW_STOCK' : null, // ключевая правка здесь
      v.statusCRIT ? 'CRITICAL' : null,
    ].filter(Boolean) as Array<'OK' | 'LOW_STOCK' | 'CRITICAL'>;

    // Собираем объект фильтров. Если HistoryFilters у тебя не содержит categories,
    // приводим через unknown как HistoryFilters, чтобы не ругался компилятор.
    const payload: any = {
      from: v.from ? v.from.toISOString() : undefined,
      to: v.to ? v.to.toISOString() : undefined,
      zones: v.zones ?? [],
      categories: v.categories ?? [],
      status: statuses,
      query: v.query ?? '',
      pageSize: v.pageSize ?? 20,
    };

    this.apply.emit(payload as unknown as HistoryFilters);
  }
}
