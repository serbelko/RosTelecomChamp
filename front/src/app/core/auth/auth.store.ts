import { Injectable } from '@angular/core';
import { BehaviorSubject } from 'rxjs';

export interface UserProfile {
  id: string;
  name: string;
  role: 'operator' | 'admin' | 'viewer';
}

const TOKEN_KEY = 'auth_token';
const USER_KEY = 'auth_user';

@Injectable({ providedIn: 'root' })
export class AuthStore {
  private tokenSubject = new BehaviorSubject<string | null>(localStorage.getItem(TOKEN_KEY));
  private userSubject = new BehaviorSubject<UserProfile | null>(
    localStorage.getItem(USER_KEY)
      ? (JSON.parse(localStorage.getItem(USER_KEY)!) as UserProfile)
      : null,
  );

  token$ = this.tokenSubject.asObservable();
  user$ = this.userSubject.asObservable();

  get token() {
    return this.tokenSubject.value;
  }
  get user() {
    return this.userSubject.value;
  }

  setSession(token: string, user: UserProfile) {
    localStorage.setItem(TOKEN_KEY, token);
    localStorage.setItem(USER_KEY, JSON.stringify(user));
    this.tokenSubject.next(token);
    this.userSubject.next(user);
  }

  clear() {
    localStorage.removeItem(TOKEN_KEY);
    localStorage.removeItem(USER_KEY);
    this.tokenSubject.next(null);
    this.userSubject.next(null);
  }
}
