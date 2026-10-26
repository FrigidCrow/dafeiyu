// THROWAWAY local supervisor. A restart replaces the actual DSH child process.
import http from 'node:http';
import { fork } from 'node:child_process';
import { readFile } from 'node:fs/promises';
import { fileURLToPath } from 'node:url';
import path from 'node:path';
const directory = path.dirname(fileURLToPath(import.meta.url));
process.chdir(directory);
const port = Number(process.env.PROTOTYPE_PORT || 4317);
let child, id = 0, queue = Promise.resolve();
const pending = new Map();
async function start() {
  child = fork(path.join(directory, 'host.mjs'), [], { stdio: ['ignore', 'inherit', 'inherit', 'ipc'] });
  await new Promise((resolve, reject) => {
    child.on('message', msg => {
      if (msg.ready) resolve();
      else { const p = pending.get(msg.id); pending.delete(msg.id); if (msg.error) p?.reject(Object.assign(new Error(msg.error), { state: msg.state })); else p?.resolve(msg.result); }
    });
    child.on('error', reject);
    child.on('exit', code => {
      if (code) reject(new Error('DSH host 启动失败：' + code));
      for (const p of pending.values()) p.reject(new Error('DSH host 已退出'));
      pending.clear();
    });
  });
}
const call = (command, action) => new Promise((resolve, reject) => {
  const seq = ++id; pending.set(seq, { resolve, reject }); child.send({ id: seq, command, action });
});
async function restart() {
  const old = child;
  const exited = new Promise(resolve => old.once('exit', resolve));
  await call('close'); await exited; await start();
  const result = await call('state');
  result.lastResult = '真实 DSH 进程已重启，从 scratch 恢复状态。旧 PID ' + old.pid + ' → 新 PID ' + child.pid;
  return result;
}
await start();
const server = http.createServer(async (req, res) => {
  const send = (status, data) => { res.writeHead(status, { 'Content-Type': 'application/json; charset=utf-8', 'Cache-Control': 'no-store' }); res.end(JSON.stringify(data)); };
  try {
    if (req.method === 'GET' && req.url === '/') {
      res.writeHead(200, { 'Content-Type': 'text/html; charset=utf-8', 'Cache-Control': 'no-store' }); res.end(await readFile(path.join(directory, 'index.html'))); return;
    }
    if (req.method === 'GET' && req.url === '/api/state') { send(200, await call('state')); return; }
    if (req.method === 'POST' && req.url === '/api/action') {
      if (req.headers.origin && req.headers.origin !== `http://127.0.0.1:${port}` && req.headers.origin !== `http://localhost:${port}`) { send(403, { error: '只允许本机原型页面操作' }); return; }
      let body = ''; for await (const chunk of req) { body += chunk; if (body.length > 20000) throw new Error('操作内容过长'); }
      const action = JSON.parse(body);
      const task = queue.then(() => action.type === 'restart' ? restart() : call('action', action));
      queue = task.catch(() => {}); send(200, await task); return;
    }
    send(404, { error: '没有此原型页面' });
  } catch (error) { send(400, { error: error.message, state: error.state }); }
});
server.listen(port, '127.0.0.1', () => console.log(`DSH 原型已启动：http://127.0.0.1:${port}（真实 DSH + 模拟 provider）`));
let stopping = false;
async function stop() { if (stopping) return; stopping = true; server.close(); await call('close').catch(() => {}); process.exit(0); }
process.on('SIGINT', stop); process.on('SIGTERM', stop);
