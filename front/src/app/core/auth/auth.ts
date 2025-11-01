// src/app/core/auth/auth.ts
import { Injectable } from '@angular/core';
import { environment } from '../../../environments/environment';
import { map, switchMap, tap, catchError } from 'rxjs/operators';
import { Observable, of, throwError } from 'rxjs';
import { AuthStore } from './auth.store';
import { HttpClient, HttpHeaders } from '@angular/common/http';

export interface UserProfile {
  id: string;
  name: string;
  role: 'operator' | 'admin' | 'viewer';
}

export interface LoginRequest {
  email: string;
  password: string;
  remember?: boolean;
}

export interface LoginResponse {
  token?: string;
  user?: UserProfile;
}

export interface RegisterRequest {
  name: string;
  email: string;
  password: string;
}

// так как apiUrl уже содержит /api — оставляем относительные пути БЕЗ /api
const LOGIN_PATH = '/auth/login';
const REGISTER_PATH = '/auth/create';
const ME_PATH = '/auth/me';

@Injectable({ providedIn: 'root' })
export class AuthService {
  private readonly baseUrl = environment.apiUrl;

  constructor(
    private readonly http: HttpClient,
    private readonly store: AuthStore,
  ) {}

  private authHeaders(token: string | null): { headers?: HttpHeaders } {
    return token ? { headers: new HttpHeaders({ Authorization: `Bearer ${token}` }) } : {};
  }

  private getToken(): string | null {
    try {
      return localStorage.getItem('auth_token');
    } catch {
      return null;
    }
  }

  login(payload: LoginRequest): Observable<void> {
    return this.http
      .post<LoginResponse>(`${this.baseUrl}${LOGIN_PATH}`, {
        email: payload.email,
        password: payload.password,
      })
      .pipe(
        switchMap((res) => {
          const token = res.token;
          if (!token) {
            return throwError(() => new Error('No token returned from /auth/login'));
          }

          // временный профиль — чтобы UI не пустел, если /me вернёт 401
          const fallbackUser: UserProfile = {
            id: 'me',
            name: (payload.email && payload.email.split('@')[0]) || 'user',
            role: 'operator',
          };
          this.store.setSession(token, res.user ?? fallbackUser);

          // подтягиваем реальный профиль (если упадёт — молча игнорируем)
          return this.http
            .get<UserProfile>(`${this.baseUrl}${ME_PATH}`, this.authHeaders(token))
            .pipe(
              tap((profile) => this.store.setSession(token, profile)),
              map(() => void 0),
              catchError(() => of(void 0)),
            );
        }),
      );
  }

  register(payload: RegisterRequest): Observable<boolean> {
    // /auth/create часто не возвращает токен — после 201 сразу логинимся
    return this.http.post<unknown>(`${this.baseUrl}${REGISTER_PATH}`, payload).pipe(
      switchMap(() =>
        this.login({ email: payload.email, password: payload.password }).pipe(map(() => true)),
      ),
      catchError(() => of(false)),
    );
  }

  me(): Observable<UserProfile> {
    const token = this.getToken();
    return this.http.get<UserProfile>(`${this.baseUrl}${ME_PATH}`, this.authHeaders(token));
  }

  logout(): void {
    this.store.clear();
  }
}
