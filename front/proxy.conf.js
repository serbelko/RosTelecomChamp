// proxy.conf.js
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

    // Перекладываем ?token=JWT в Authorization и срезаем query
    onProxyReqWs: (proxyReq, req) => {
      const u = new URL(req.url, 'http://localhost'); // /ws/notifications?token=...
      const token = u.searchParams.get('token');
      if (token) proxyReq.setHeader('Authorization', `Bearer ${token}`);

      // Критично: переписываем путь апстрима без query
      req.url = u.pathname; // например "/ws/notifications"
    },
  },
];
