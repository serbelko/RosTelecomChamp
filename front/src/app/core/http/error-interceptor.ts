// src/app/core/http/error.interceptor.ts
import { HttpErrorResponse, HttpInterceptorFn } from '@angular/common/http';
import { inject } from '@angular/core';
import { catchError, throwError } from 'rxjs';
import { MatSnackBar } from '@angular/material/snack-bar';

export const errorInterceptor: HttpInterceptorFn = (req, next) => {
  const snack = inject(MatSnackBar);
  return next(req).pipe(
    catchError((err: HttpErrorResponse) => {
      const message = err.error?.message || err.statusText || 'Ошибка сети';
      snack.open(message, 'OK', { duration: 3000 });
      return throwError(() => err);
    }),
  );
};
