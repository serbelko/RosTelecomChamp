import { Injectable } from '@angular/core';
import { webSocket, WebSocketSubject } from 'rxjs/webSocket';
import { BehaviorSubject, filter, retry, shareReplay } from 'rxjs';
import { environment } from '../../../environments/environment';

export type WsStatus = 'connected' | 'disconnected' | 'reconnecting';

@Injectable({ providedIn: 'root' })
export class WsService {
  private statusSub = new BehaviorSubject<WsStatus>('disconnected');
  status$ = this.statusSub.asObservable();

  private socket?: WebSocketSubject<unknown>;

  connect(path = '/ws/robots') {
    const url = `${environment.wsUrl}${path}`;
    this.statusSub.next('reconnecting');

    this.socket = webSocket({
      url,
      openObserver: { next: () => this.statusSub.next('connected') },
      closeObserver: { next: () => this.statusSub.next('disconnected') },
    });

    return this.socket.pipe(retry({ delay: 2000 }), shareReplay({ bufferSize: 1, refCount: true }));
  }

  send(msg: unknown) {
    this.socket?.next(msg);
  }
}
