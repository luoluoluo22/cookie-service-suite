#!/usr/bin/env node
/**
 * 命令行重载 Edge / Chrome 扩展
 * 用法:
 *   node reload.js
 *   npm run reload
 */

const http = require('http');

console.log('🔄 正在请求本地服务触发浏览器扩展重载...');

const req = http.get('http://127.0.0.1:18888/reload', (res) => {
  let body = '';
  res.on('data', chunk => body += chunk);
  res.on('end', () => {
    try {
      const json = JSON.parse(body);
      if (res.statusCode === 200 && json.success) {
        console.log('✅', json.message || '浏览器扩展已成功重载！');
      } else {
        console.warn('⚠️ 响应提示:', json.error || body);
      }
    } catch (e) {
      console.log(body);
    }
  });
});

req.on('error', (err) => {
  console.error('❌ 连接本地服务失败 (127.0.0.1:18888)。');
  console.error('请确认 server.js 正在运行: node server.js');
  console.error('错误详情:', err.message);
});
