// proxy.conf.js
// Работает и для HTTP, и для WebSocket.
// Для WS: клиент стучится на ws://localhost:4200/ws/notifications?token=JWT
// Прокси вырезает token из query и кладёт его в Authorization,
// затем гонит на ws://localhost:8000/ws/notifications (без query).

const { URL } = require('url');

module.exports = [
  // HTTP API -> :8000
  {
    context: ['/api'],
    target: 'http://localhost:8000',
    changeOrigin: true,
    ws: false,
    logLevel: 'debug',
  },

  // WebSocket -> :8000
  {
    context: ['/ws'],
    target: 'ws://localhost:8000',
    changeOrigin: true,
    ws: true,
    logLevel: 'debug',

    // Вешаем токен в Authorization: Bearer <jwt>
    onProxyReqWs: (proxyReq, req) => {
      // req.url вида: /ws/notifications?token=...
      const u = new URL(req.url, 'http://localhost');
      const token = u.searchParams.get('token');

      if (token) {
        proxyReq.setHeader('Authorization', `Bearer ${token}`);
      }

      // Уберём query у пути при проксировании
      const pathNoQuery = u.pathname;
      // http-proxy задаёт путь через .path
      if (proxyReq.path) proxyReq.path = pathNoQuery;
      // а для некоторых версий — через _headers:host + :path
      if (proxyReq._headers) {
        // ничего не делаем, достаточно proxyReq.path
      }
    },
  },
];
