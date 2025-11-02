// src/app/core/auth/auth.ts
import { Injectable } from '@angular/core';
import { HttpClient, HttpHeaders } from '@angular/common/http';
import { environment } from '../../../environments/environment';
import { Observable, of, throwError } from 'rxjs';
import { catchError, map, switchMap, tap } from 'rxjs/operators';
import { AuthStore } from './auth.store';
import { joinUrl } from '../http/url.util';

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

// роуты бэка: /api/auth/*
const LOGIN_PATH = 'auth/login';
const REGISTER_PATH = 'auth/create';
const ME_PATH = 'auth/me';

@Injectable({ providedIn: 'root' })
export class AuthService {
  private readonly baseUrl = environment.apiUrl; // '/api'

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
      .post<LoginResponse>(joinUrl(this.baseUrl, LOGIN_PATH), {
        email: payload.email,
        password: payload.password,
      })
      .pipe(
        switchMap((res) => {
          const token = res.token;
          if (!token) return throwError(() => new Error('No token returned from /api/auth/login'));
          try {
            localStorage.setItem('auth_token', token);
          } catch {}
          const fallbackUser: UserProfile = {
            id: 'me',
            name: payload.email?.split('@')[0] || 'user',
            role: 'operator',
          };
          return this.http.get<any>(joinUrl(this.baseUrl, ME_PATH), this.authHeaders(token)).pipe(
            map((raw) => ({
              id: raw?.user_id ?? 'me',
              name: raw?.claims?.email ?? fallbackUser.name,
              role: 'operator' as const,
            })),
            tap((profile) => this.store.setSession(token, profile)),
            map(() => void 0),
            catchError(() => {
              this.store.setSession(token, fallbackUser);
              return of(void 0);
            }),
          );
        }),
      );
  }

  register(payload: RegisterRequest): Observable<boolean> {
    const body = { email: payload.email, password: payload.password };
    return this.http.post<unknown>(joinUrl(this.baseUrl, REGISTER_PATH), body).pipe(
      switchMap(() =>
        this.login({ email: payload.email, password: payload.password }).pipe(map(() => true)),
      ),
      catchError(() => of(false)),
    );
  }

  me(): Observable<UserProfile> {
    const token = this.getToken();
    return this.http.get<any>(joinUrl(this.baseUrl, ME_PATH), this.authHeaders(token)).pipe(
      map((raw) => ({
        id: raw?.user_id ?? 'me',
        name: raw?.claims?.email ?? 'user',
        role: 'operator' as const,
      })),
    );
  }

  logout(): void {
    this.store.clear();
    try {
      localStorage.removeItem('auth_token');
    } catch {}
  }
}
