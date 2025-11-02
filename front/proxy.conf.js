// front/proxy.conf.js
module.exports = [
  // Все REST под /api уходит на бекенд без переписывания
  {
    context: ['/api', '/docs', '/openapi.json'],
    target: 'http://localhost:8000',
    changeOrigin: true,
    ws: false,
    logLevel: 'debug',
  },

  // WebSocket под /ws (перекладываем ?token= в Authorization)
  {
    context: ['/ws'],
    target: 'http://localhost:8000',
    changeOrigin: true,
    ws: true,
    logLevel: 'debug',
    pathRewrite: (path, req) => {
      const { URL } = require('url');
      const u = new URL(path, 'http://localhost'); // /ws/notifications?token=...
      const token = u.searchParams.get('token');
      if (token) {
        req.headers = { ...(req.headers || {}), authorization: `Bearer ${token}` };
      }
      return u.pathname; // оставляем путь /ws/notifications
    },
  },
];
