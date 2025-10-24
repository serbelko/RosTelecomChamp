import { HttpErrorResponse, HttpInterceptorFn } from '@angular/common/http';
import { inject } from '@angular/core';
import { MatSnackBar } from '@angular/material/snack-bar';
import { catchError, throwError } from 'rxjs';

export const errorInterceptor: HttpInterceptorFn = (req, next) => {
  const snack = inject(MatSnackBar);
  return next(req).pipe(
    catchError((err: HttpErrorResponse) => {
      const message = err.error?.message || err.statusText || 'Network error';
      snack.open(message, 'OK', { duration: 4000 });
      return throwError(() => err);
    })
  );
};
