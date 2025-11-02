// src/app/core/realtime/ws.ts
import { Injectable } from '@angular/core';
import { environment } from '../../../environments/environment';
import { BehaviorSubject, Subject, Observable, timer } from 'rxjs';
import { takeUntil } from 'rxjs/operators';

export type WsStatus = 'connected' | 'disconnected' | 'reconnecting';

function joinUrl(base: string, path: string): string {
  return `${base.replace(/\/+$/, '')}/${path.replace(/^\/+/, '')}`;
}

function resolveWsBase(): string {
  const wsUrl = environment.wsUrl ?? '';

  // Абсолютный ws:// или wss:// — используем как есть
  if (/^wss?:\/\//i.test(wsUrl)) {
    return wsUrl.replace(/\/+$/, '');
  }

  // Относительный путь `/ws` — всегда подключаемся к текущему хосту (через прокси)
  if (wsUrl.startsWith('/')) {
    const scheme = window.location.protocol === 'https:' ? 'wss' : 'ws';
    return `${scheme}://${window.location.host}${wsUrl}`.replace(/\/+$/, '');
  }

  // Если apiUrl абсолютный http(s):// — конвертируем в ws(s):// и добавляем /ws
  const apiUrl = environment.apiUrl ?? '';
  if (/^https?:\/\//i.test(apiUrl)) {
    return apiUrl.replace(/^http/, 'ws').replace(/\/+$/, '') + '/ws';
  }

  // Фоллбэк — текущий хост + /ws
  const scheme = window.location.protocol === 'https:' ? 'wss' : 'ws';
  return `${scheme}://${window.location.host}/ws`;
}

@Injectable({ providedIn: 'root' })
export class WsService {
  private socket?: WebSocket;
  private stop$ = new Subject<void>();

  private statusSub = new BehaviorSubject<WsStatus>('disconnected');
  readonly status$ = this.statusSub.asObservable();

  private msgSub = new Subject<any>();
  readonly messages$ = this.msgSub.asObservable();

  private backoffMs = 1000;

  connect(path: string = 'notifications'): Observable<any> {
    this.disconnect();

    const base = resolveWsBase(); // напр. ws://localhost:4200/ws
    const cleanedPath = path.replace(/^\/+/, '').replace(/^ws\/+/i, '');
    const endpoint = joinUrl(base, cleanedPath);

    const token = localStorage.getItem('auth_token') ?? '';
    // Токен кладём в query (?token=...), прокси перевесит его в Authorization
    const url = token ? `${endpoint}?token=${encodeURIComponent(token)}` : endpoint;

    try {
      this.socket = new WebSocket(url);
    } catch (e) {
      this.scheduleReconnect(path);
      throw e;
    }

    this.statusSub.next('reconnecting'); // пока не открылось

    this.socket.onopen = () => {
      this.statusSub.next('connected');
      this.backoffMs = 1000;
    };

    this.socket.onmessage = (ev) => {
      try {
        this.msgSub.next(JSON.parse(ev.data));
      } catch {
        this.msgSub.next(ev.data);
      }
    };

    this.socket.onerror = () => {
      this.statusSub.next('disconnected');
    };

    this.socket.onclose = () => {
      this.statusSub.next('disconnected');
      this.scheduleReconnect(path);
    };

    return this.messages$;
  }

  disconnect(): void {
    this.stop$.next();
    if (
      this.socket &&
      (this.socket.readyState === WebSocket.OPEN || this.socket.readyState === WebSocket.CONNECTING)
    ) {
      try {
        this.socket.close();
      } catch {}
    }
    this.socket = undefined;
    this.statusSub.next('disconnected');
  }

  private scheduleReconnect(path: string): void {
    this.statusSub.next('reconnecting');
    const delay = this.backoffMs;
    this.backoffMs = Math.min(this.backoffMs * 2, 15000);

    timer(delay)
      .pipe(takeUntil(this.stop$))
      .subscribe(() => {
        if (this.statusSub.value !== 'connected') this.connect(path);
      });
  }
}
