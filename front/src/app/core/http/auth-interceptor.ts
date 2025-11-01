import { HttpInterceptorFn } from '@angular/common/http';

/**
 * Функциональный перехватчик: добавляет Authorization: Bearer <token>
 * ко всем исходящим HTTP-запросам, если токен есть в localStorage.
 */
export const authInterceptor: HttpInterceptorFn = (req, next) => {
  const token = localStorage.getItem('auth_token');
  if (!token) {
    return next(req);
  }
  const authReq = req.clone({
    setHeaders: { Authorization: `Bearer ${token}` },
  });
  return next(authReq);
};
