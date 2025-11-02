// src/app/core/ws/ws.ts
import { Injectable } from '@angular/core';
import { environment } from '../../../environments/environment';
import { BehaviorSubject, Subject, Observable, timer } from 'rxjs';
import { takeUntil } from 'rxjs/operators';

export type WsStatus = 'connected' | 'disconnected' | 'reconnecting';

/** Удаляет лишние слэши при склейке URL */
function joinUrl(base: string, path: string): string {
  return `${base.replace(/\/+$/, '')}/${path.replace(/^\/+/, '')}`;
}

/** Возвращает ws(s)://<host> из абсолютного http(s)://... */
function httpToWsOrigin(httpUrl: string): string {
  try {
    const u = new URL(httpUrl);
    const wsScheme = u.protocol === 'https:' ? 'wss:' : 'ws:';
    return `${wsScheme}//${u.host}`;
  } catch {
    return '';
  }
}

/**
 * Определяем базовый WS-ориджин и префикс.
 * Приоритет:
 * 1) Если environment.wsUrl абсолютный (ws:// или wss://) — используем его как базу.
 * 2) Если environment.wsUrl относительный ("/ws") — берем хост из environment.apiUrl (если он абсолютный).
 * 3) Если apiUrl относительный и фронт на :4200 — подставляем ws://localhost:8000.
 * 4) Иначе — window.location.origin с заменой схемы на ws(s).
 */
function resolveWsBase(): string {
  const wsUrl = environment.wsUrl ?? '';

  // Абсолютный ws(s)://
  if (/^wss?:\/\//i.test(wsUrl)) {
    return wsUrl.replace(/\/+$/, '');
  }

  // Попробуем опереться на apiUrl, если он абсолютный http(s)://
  const apiUrl = environment.apiUrl ?? '';
  if (/^https?:\/\//i.test(apiUrl)) {
    const origin = httpToWsOrigin(apiUrl);
    // если wsUrl относительный — приклеим его, иначе используем /ws по умолчанию
    const wsPrefix = wsUrl && wsUrl.startsWith('/') ? wsUrl : '/ws';
    return joinUrl(origin, wsPrefix).replace(/\/+$/, '');
  }

  // Фронт на dev-сервере :4200, а apiUrl относительный — считаем, что бек на :8000
  const isDev4200 = window.location.hostname === 'localhost' && window.location.port === '4200';
  if (isDev4200) {
    const origin = `ws://localhost:8000`;
    const wsPrefix = wsUrl && wsUrl.startsWith('/') ? wsUrl : '/ws';
    return joinUrl(origin, wsPrefix).replace(/\/+$/, '');
  }

  // Fallback: текущий хост (может быть прод), заменяем схему
  const scheme = window.location.protocol === 'https:' ? 'wss' : 'ws';
  const origin = `${scheme}://${window.location.host}`;
  const wsPrefix = wsUrl && wsUrl.startsWith('/') ? wsUrl : '/ws';
  return joinUrl(origin, wsPrefix).replace(/\/+$/, '');
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
   * Подключается к относительному пути WS-эндпоинта (без ведущего /ws),
   * например: "notifications".
   * Итоговый URL будет: <wsBase>/notifications?token=...
   */
  connect(path: string = 'notifications'): Observable<any> {
    // Закроем предыдущее подключение/таймеры
    this.disconnect();

    const base = resolveWsBase(); // напр., ws://localhost:8000/ws
    const cleanedPath = path.replace(/^\/+/, '').replace(/^ws\/+/i, '');
    const endpoint = joinUrl(base, cleanedPath);

    const token = localStorage.getItem('auth_token') ?? '';
    // В браузере нельзя добавить заголовок Authorization в WebSocket-конструктор,
    // поэтому прокидываем токен через query-параметр (?token=...).
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
      // необязательное "hello", чтобы проверить канал
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
      // onerror часто следует за onclose; реконнект — в onclose
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
