import { Injectable } from '@angular/core';
import { environment } from '../../../environments/environment';
import { BehaviorSubject, Subject, Observable, timer } from 'rxjs';
import { takeUntil } from 'rxjs/operators';

export type WsStatus = 'connected' | 'disconnected' | 'reconnecting';

@Injectable({ providedIn: 'root' })
export class WsService {
  private socket?: WebSocket;
  private stop$ = new Subject<void>();
  private statusSub = new BehaviorSubject<WsStatus>('disconnected');
  status$ = this.statusSub.asObservable();

  private msgSub = new Subject<any>();
  messages$ = this.msgSub.asObservable();

  connect(path: string): Observable<any> {
    this.stop$.next();

    const token = localStorage.getItem('auth_token') ?? '';
    const base = (environment.wsUrl || '').replace(/\/+$/, '');
    const p = path.startsWith('/') ? path : `/${path}`;
    // важно: ходим на :4200, чтобы сработал dev-proxy и добавил Authorization
    const url = `${base}${p}?token=${encodeURIComponent(token)}`;

    try {
      // Никаких подпротоколов — всё через proxy
      this.socket = new WebSocket(url);
    } catch (e) {
      console.error('[WS] constructor error:', e);
      this.scheduleReconnect(path);
      return this.messages$;
    }

    this.socket.onopen = () => {
      this.statusSub.next('connected');
      // опциональный hello
      try {
        this.socket?.send(JSON.stringify({ type: 'hello' }));
      } catch {}
    };

    this.socket.onmessage = (ev) => {
      try {
        const data = JSON.parse(ev.data);
        this.msgSub.next(data);
      } catch {
        this.msgSub.next(ev.data);
      }
    };

    this.socket.onclose = (ev) => {
      this.statusSub.next('disconnected');
      if (ev.code !== 1000) this.scheduleReconnect(path);
      console.warn('[WS] closed', ev.code, ev.reason);
    };

    this.socket.onerror = (ev) => {
      this.statusSub.next('disconnected');
      console.error('[WS] error', ev);
      this.scheduleReconnect(path);
    };

    return this.messages$;
  }

  send(msg: any) {
    if (this.socket?.readyState === WebSocket.OPEN) {
      this.socket.send(JSON.stringify(msg));
    }
  }

  disconnect() {
    this.stop$.next();
    try {
      this.socket?.close(1000, 'client disconnect');
    } catch {}
    this.socket = undefined;
    this.statusSub.next('disconnected');
  }

  private scheduleReconnect(path: string) {
    this.statusSub.next('reconnecting');
    timer(3000)
      .pipe(takeUntil(this.stop$))
      .subscribe(() => {
        if (this.statusSub.value !== 'connected') this.connect(path);
      });
  }
}
