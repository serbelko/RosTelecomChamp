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
  user: {
    id: string;
    name: string;
    role: 'operator' | 'admin' | 'viewer';
  };
}

@Injectable({ providedIn: 'root' })
export class AuthService {
  private baseUrl = environment.apiUrl;

  constructor(
    private http: HttpClient,
    private store: AuthStore
  ) {}

  login(payload: LoginRequest): Observable<void> {
    return this.http.post<LoginResponse>(`${this.baseUrl}/api/auth/login`, payload).pipe(
      tap(res => this.store.setSession(res.token, res.user)),
      map(() => void 0)
    );
  }

  logout(): void {
    this.store.clear();
  }
}
