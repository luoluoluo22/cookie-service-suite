#!/usr/bin/env node
/**
 * 示例客户端：从本地通信服务获取任意网站 Cookie
 * 用法:
 *   node get_cookie.js bilibili.com
 *   node get_cookie.js music.163.com --json
 *   node get_cookie.js --active
 */

const http = require('http');

const target = process.argv[2] || '--active';
const isJson = process.argv.includes('--json');
const isHeader = process.argv.includes('--header');

let endpoint = '';
if (target === '--active') {
  endpoint = 'http://127.0.0.1:18888/active';
} else {
  let format = 'full';
  if (isJson) format = 'json';
  if (isHeader) format = 'header';
  endpoint = `http://127.0.0.1:18888/cookies?domain=${encodeURIComponent(target)}&format=${format}`;
}

http.get(endpoint, (res) => {
  let data = '';
  res.on('data', chunk => { data += chunk; });
  res.on('end', () => {
    try {
      if (res.statusCode !== 200) {
        console.error(`❌ 请求失败 (HTTP ${res.statusCode}):`, data);
        process.exit(1);
      }
      if (isHeader) {
        console.log(data);
      } else {
        const json = JSON.parse(data);
        console.log(JSON.stringify(json, null, 2));
      }
    } catch (e) {
      console.log(data);
    }
  });
}).on('error', (err) => {
  console.error('❌ 无法连接到本地通信服务 (http://127.0.0.1:18888)。');
  console.error('请确认 server.js 正在运行: node server.js');
  console.error('详细错误:', err.message);
});
