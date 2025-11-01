import { Component, EventEmitter, Input, Output, ViewChild, inject } from '@angular/core';
import { CommonModule } from '@angular/common';
import { MatTableModule } from '@angular/material/table';
import { MatPaginator, MatPaginatorModule } from '@angular/material/paginator';
import { MatSort, MatSortModule, Sort } from '@angular/material/sort';
import { MatCheckboxModule } from '@angular/material/checkbox';
import { MatButtonModule } from '@angular/material/button';
import { MatIconModule } from '@angular/material/icon';
import { SelectionModel } from '@angular/cdk/collections';
import { HistoryFilters, HistoryRow, HistoryService } from '../history.service';
import { AsyncPipe, DatePipe } from '@angular/common';
import * as XLSX from 'xlsx';
import { MatDialog, MatDialogModule } from '@angular/material/dialog';
import { CsvUploadDialogComponent } from '../csv-upload-dialog/csv-upload-dialog';

@Component({
  selector: 'app-history-table',
  standalone: true,
  imports: [
    CommonModule,
    MatTableModule,
    MatPaginatorModule,
    MatSortModule,
    MatCheckboxModule,
    MatButtonModule,
    MatIconModule,
    DatePipe,
    MatDialogModule,
  ],
  templateUrl: './history-table.html',
  styleUrls: ['./history-table.scss'],
})
export class HistoryTableComponent {
  private api = inject(HistoryService);
  private dialog = inject(MatDialog);

  @Input() filters!: HistoryFilters;
  @Output() filtersChange = new EventEmitter<HistoryFilters>();

  displayedColumns = [
    'select',
    'ts',
    'robotId',
    'zone',
    'sku',
    'name',
    'expected',
    'actual',
    'delta',
    'status',
  ];
  selection = new SelectionModel<HistoryRow>(true, []);

  @ViewChild(MatPaginator) paginator!: MatPaginator;
  @ViewChild(MatSort) sort!: MatSort;

  data: HistoryRow[] = [];
  total = 0;
  loading = false;

  ngOnInit() {
    this.load();
  }
  ngOnChanges() {
    this.load();
  }

  load() {
    if (!this.filters) return;
    this.loading = true;
    this.api.list(this.filters).subscribe({
      next: (res: any) => {
        this.data = res.items;
        this.total = res.total;
        this.loading = false;
      },
      error: () => {
        this.loading = false;
      },
    });
  }

  pageChange(e: any) {
    this.filtersChange.emit({ ...this.filters, page: e.pageIndex, pageSize: e.pageSize });
  }

  sortChange(sort: Sort) {
    const dir = sort.direction || 'asc';
    const fld = sort.active || 'ts';
    this.filtersChange.emit({ ...this.filters, sort: `${fld}:${dir}`, page: 0 });
  }

  isAllSelected() {
    return this.selection.selected.length === this.data.length;
  }
  masterToggle() {
    this.isAllSelected()
      ? this.selection.clear()
      : this.data.forEach((row) => this.selection.select(row));
  }

  exportExcel() {
    const rows = this.selection.selected.length ? this.selection.selected : this.data;
    const ws = XLSX.utils.json_to_sheet(rows);
    const wb = XLSX.utils.book_new();
    XLSX.utils.book_append_sheet(wb, ws, 'History');
    XLSX.writeFile(wb, 'history.xlsx');
  }

  exportPdf() {
    // простой вариант: печать в PDF средствами браузера
    window.print();
  }

  openUpload() {
    this.dialog.open(CsvUploadDialogComponent, { width: '720px' });
  }
}
