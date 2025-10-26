// src/app/core/auth/auth.ts
import { Injectable } from '@angular/core';
import { environment } from '../../../environments/environment';
import { map, switchMap, tap } from 'rxjs/operators';
import { Observable, of } from 'rxjs';
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
  token: string;
  user?: UserProfile;
}

export interface RegisterRequest {
  name: string;
  email: string;
  password: string;
}

const LOGIN_PATH = '/api/v1/users/login';
const REGISTER_PATH = '/api/v1/users/create';
const ME_PATH = '/api/v1/users/me';

@Injectable({ providedIn: 'root' })
export class AuthService {
  private baseUrl = environment.apiUrl;

  constructor(
    private http: HttpClient,
    private store: AuthStore,
  ) {}

  // ⬇️ Метод, которого не хватало
  login(payload: LoginRequest): Observable<void> {
    return this.http
      .post<LoginResponse>(`${this.baseUrl}${LOGIN_PATH}`, {
        email: payload.email,
        password: payload.password,
      })
      .pipe(
        switchMap((res) => {
          // 1) если сервер сразу вернул user — сохраняем и всё
          if (res.user) {
            this.store.setSession(res.token, res.user);
            return of(void 0);
          }

          // 2) если user не пришёл — ДЕЛАЕМ /me С РУЧНЫМ ЗАГОЛОВКОМ
          const headers = new HttpHeaders({
            Authorization: `Bearer ${res.token}`, // важно: Bearer с большой буквы
          });

          return this.http.get<UserProfile>(`${this.baseUrl}${ME_PATH}`, { headers }).pipe(
            tap((profile) => this.store.setSession(res.token, profile)),
            map(() => void 0),
          );
        }),
      );
  }

  register(payload: RegisterRequest): Observable<boolean> {
    return this.http.post<LoginResponse>(`${this.baseUrl}${REGISTER_PATH}`, payload).pipe(
      switchMap((res) => {
        // если сервер НЕ выдал токен при регистрации — просто завершаем без /me
        if (!res.token) {
          return of(false); // токена нет
        }

        // если токен есть и user пришёл — сохраняем и выходим
        if (res.user) {
          this.store.setSession(res.token, res.user);
          return of(true);
        }

        // токен есть, user не пришёл — подтянем профиль вручную с заголовком
        const headers = new HttpHeaders({ Authorization: `Bearer ${res.token}` });
        return this.http.get<UserProfile>(`${this.baseUrl}${ME_PATH}`, { headers }).pipe(
          tap((profile) => this.store.setSession(res.token!, profile)),
          map(() => true),
        );
      }),
    );
  }

  me(): Observable<UserProfile> {
    return this.http.get<UserProfile>(`${this.baseUrl}${ME_PATH}`);
  }

  logout(): void {
    this.store.clear();
  }
}
