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
    pathRewrite: (path, req) => {
      const { URL } = require('url');
      const u = new URL(path, 'http://localhost'); // /ws/notifications?token=...
      const token = u.searchParams.get('token');
      if (token) {
        req.headers = req.headers || {};
        req.headers['authorization'] = `Bearer ${token}`;
      }
      return u.pathname; // "/ws/notifications" — query срезаем
    },
  },
];
