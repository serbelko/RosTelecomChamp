import { Component, EventEmitter, Input, Output, OnChanges, SimpleChanges } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormControl, FormGroup, ReactiveFormsModule } from '@angular/forms';
import { MatDatepickerModule } from '@angular/material/datepicker';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatInputModule } from '@angular/material/input';
import { MatButtonModule } from '@angular/material/button';
import { MatIconModule } from '@angular/material/icon';
import { MatSelectModule } from '@angular/material/select';
import { MatCheckboxModule } from '@angular/material/checkbox';
import { provideNativeDateAdapter } from '@angular/material/core';
import { HistoryFilters } from '../history.service';

type FilterForm = {
  from: FormControl<Date | null>;
  to: FormControl<Date | null>;
  zones: FormControl<string[]>;
  categories: FormControl<string[]>;
  statusOK: FormControl<boolean>;
  statusLOW: FormControl<boolean>;
  statusCRIT: FormControl<boolean>;
  query: FormControl<string>;
  pageSize: FormControl<number>;
};

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
export class FilterBarComponent implements OnChanges {
  @Input() filters?: HistoryFilters;
  @Output() apply = new EventEmitter<HistoryFilters>();
  // Переименовал событие, чтобы не конфликтовало с методом
  @Output() cleared = new EventEmitter<void>();

  // Списки опций
  @Input() zonesOptions: string[] = Array.from({ length: 26 }, (_, i) =>
    String.fromCharCode(65 + i),
  );
  @Input() categoryOptions: string[] = ['Электроника', 'Сетевое', 'Кабель', 'Прочее'];

  form = new FormGroup<FilterForm>({
    from: new FormControl<Date | null>(null),
    to: new FormControl<Date | null>(null),
    zones: new FormControl<string[]>([], { nonNullable: true }),
    categories: new FormControl<string[]>([], { nonNullable: true }),
    statusOK: new FormControl<boolean>(true, { nonNullable: true }),
    statusLOW: new FormControl<boolean>(true, { nonNullable: true }),
    statusCRIT: new FormControl<boolean>(true, { nonNullable: true }),
    query: new FormControl<string>('', { nonNullable: true }),
    pageSize: new FormControl<number>(20, { nonNullable: true }),
  });

  ngOnChanges(_: SimpleChanges): void {
    if (!this.filters) return;
    const f = this.filters;
    this.form.patchValue(
      {
        from: f.from ? new Date(f.from) : null,
        to: f.to ? new Date(f.to) : null,
        zones: f.zones ?? [],
        categories: f.categories ?? [],
        statusOK: f.statusOk ?? true,
        statusLOW: f.statusLow ?? true,
        statusCRIT: f.statusCrit ?? true,
        query: f.query ?? '',
        pageSize: f.pageSize ?? 20,
      },
      { emitEvent: false },
    );
  }

  quick(range: 'today' | 'yesterday' | 'week' | 'month'): void {
    const now = new Date();
    const start = new Date(now);

    if (range === 'today') start.setHours(0, 0, 0, 0);
    if (range === 'yesterday') {
      start.setDate(now.getDate() - 1);
      start.setHours(0, 0, 0, 0);
      now.setHours(23, 59, 59, 999);
    }
    if (range === 'week') {
      start.setDate(now.getDate() - 6);
      start.setHours(0, 0, 0, 0);
    }
    if (range === 'month') {
      start.setMonth(now.getMonth() - 1);
      start.setHours(0, 0, 0, 0);
    }
    this.form.patchValue({ from: start, to: now });
  }

  onReset(): void {
    this.form.setValue(
      {
        from: null,
        to: null,
        zones: [],
        categories: [],
        statusOK: true,
        statusLOW: true,
        statusCRIT: true,
        query: '',
        pageSize: 20,
      },
      { emitEvent: false },
    );
    this.cleared.emit();
    this.emit();
  }

  emit(): void {
    const v = this.form.getRawValue();
    const payload: HistoryFilters = {
      from: v.from ? v.from.toISOString() : undefined,
      to: v.to ? v.to.toISOString() : undefined,
      zones: v.zones,
      categories: v.categories,
      statusOk: v.statusOK,
      statusLow: v.statusLOW,
      statusCrit: v.statusCRIT,
      query: v.query.trim(),
      pageSize: v.pageSize,
      page: 1,
    };
    this.apply.emit(payload);
  }
}
