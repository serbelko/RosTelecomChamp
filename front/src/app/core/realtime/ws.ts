// src/app/core/ws/ws.ts
import { Injectable } from '@angular/core';
import { environment } from '../../../environments/environment';
import { BehaviorSubject, Subject, Observable, timer } from 'rxjs';
import { takeUntil } from 'rxjs/operators';

export type WsStatus = 'connected' | 'disconnected' | 'reconnecting';

function joinUrl(base: string, path: string): string {
  return `${base.replace(/\/+$/, '')}/${path.replace(/^\/+/, '')}`;
}

function resolveWsUrl(base: string): string {
  // dev: base = "/ws" -> "ws://<host>/ws"
  if (base.startsWith('/')) {
    const scheme = window.location.protocol === 'https:' ? 'wss' : 'ws';
    return `${scheme}://${window.location.host}${base}`;
  }
  // prod: base = "ws://host/ws" или "http://host/ws"
  if (/^https?:\/\//i.test(base)) return base.replace(/^http/i, 'ws');
  return base;
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

  /**
   * Подключается к относительному пути WS-эндпоинта,
   * например: "notifications" (НЕ указывать "/ws/..." — префикс /ws уже в environment.wsUrl)
   */
  connect(path: string = 'notifications'): Observable<any> {
    // Закрываем прежнее подключение/таймеры
    this.disconnect();

    // База от окружения: dev -> ws://localhost:4200/ws, prod -> ws://localhost:8000/ws
    const base = resolveWsUrl(environment.wsUrl).replace(/\/+$/, '');

    // Защита от двойного "/ws": выкинем ведущий "ws/" у path, если вдруг передали
    const cleanedPath = path.replace(/^\/+/, '').replace(/^ws\/+/i, '');
    const endpoint = joinUrl(base, cleanedPath);

    const token = localStorage.getItem('auth_token') ?? '';
    const url = token ? `${endpoint}?token=${encodeURIComponent(token)}` : endpoint;

    try {
      this.socket = new WebSocket(url);
    } catch (e) {
      console.error('[WS] constructor error:', e);
      this.scheduleReconnect(path);
      return this.messages$;
    }

    this.socket.onopen = () => {
      this.statusSub.next('connected');
      this.backoffMs = 1000;
      // опционально: hello
      try {
        this.socket?.send(JSON.stringify({ type: 'hello' }));
      } catch {}
    };

    this.socket.onmessage = (ev) => {
      try {
        this.msgSub.next(JSON.parse(ev.data));
      } catch {
        this.msgSub.next(ev.data);
      }
    };

    this.socket.onerror = (ev) => {
      console.error('[WS] error', ev);
      // onerror обычно следует за onclose, но на всякий случай инициируем реконнект
    };

    this.socket.onclose = (ev) => {
      this.statusSub.next('disconnected');
      console.warn('[WS] closed', ev.code, ev.reason || '');
      if (ev.code !== 1000) this.scheduleReconnect(path);
    };

    return this.messages$;
  }

  send(msg: any): void {
    if (this.socket?.readyState === WebSocket.OPEN) {
      this.socket.send(JSON.stringify(msg));
    }
  }

  disconnect(): void {
    this.stop$.next(); // отмена таймеров реконнекта
    try {
      this.socket?.close(1000, 'client disconnect');
    } catch {}
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
