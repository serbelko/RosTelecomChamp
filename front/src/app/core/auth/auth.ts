// src/app/core/auth/auth.ts
import { Injectable } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { environment } from '../../../environments/environment';
import { map, tap } from 'rxjs/operators';
import { Observable } from 'rxjs';
import { AuthStore } from './auth.store';

export interface LoginRequest {
  email: string;
  password: string;
}
export interface LoginResponse {
  token: string;
  user?: { id: string; name: string; role: 'operator' | 'admin' | 'viewer' };
}

export interface RegisterRequest {
  name: string;
  email: string;
  password: string;
}

const LOGIN_PATH = '/api/v1/users/login';
const REGISTER_PATH = '/api/v1/users/create'; // при необходимости замени на свой

@Injectable({ providedIn: 'root' })
export class AuthService {
  private baseUrl = environment.apiUrl;

  constructor(
    private http: HttpClient,
    private store: AuthStore,
  ) {}

  login(payload: LoginRequest): Observable<void> {
    return this.http.post<LoginResponse>(`${this.baseUrl}${LOGIN_PATH}`, payload).pipe(
      tap((res) => {
        const user = res.user ?? { id: 'me', name: payload.email, role: 'operator' as const };
        this.store.setSession(res.token, user);
      }),
      map(() => void 0),
    );
  }

  register(payload: RegisterRequest): Observable<void> {
    return this.http.post<LoginResponse>(`${this.baseUrl}${REGISTER_PATH}`, payload).pipe(
      tap((res) => {
        // два варианта:
        // 1) сразу логиним по токену, если backend возвращает token при регистрации
        if (res.token) {
          const user = res.user ?? {
            id: 'me',
            name: payload.name || payload.email,
            role: 'operator' as const,
          };
          this.store.setSession(res.token, user);
        }
      }),
      map(() => void 0),
    );
  }

  logout(): void {
    this.store.clear();
  }
}
