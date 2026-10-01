// Ponto de entrada: `npm start`
import fs from 'node:fs';
import http from 'node:http';
import https from 'node:https';
import path from 'node:path';
import { createApp } from './app.js';
import { buildConfig, loadEnvFile } from './config.js';
import { openDatabase } from './db.js';
import { createLogger } from './log.js';

loadEnvFile();

let config;
try {
  config = buildConfig();
} catch (err) {
  console.error(`\n[Desu Burguer] Configuração inválida: ${err.message}\n`);
  process.exit(1);
}

const log = createLogger(config.logLevel);
const db = openDatabase(path.join(config.dataDir, 'desu.db'));
const handler = createApp({ config, db, log });

const server = config.tlsCertFile
  ? https.createServer({ cert: fs.readFileSync(config.tlsCertFile), key: fs.readFileSync(config.tlsKeyFile) }, handler)
  : http.createServer(handler);

server.requestTimeout = 30_000;
server.headersTimeout = 15_000;
server.keepAliveTimeout = 5_000;

const admins = db.prepare('SELECT COUNT(*) AS n FROM admin_users WHERE active = 1').get().n;

server.listen(config.port, config.host, () => {
  const addr = server.address();
  log.info('server_started', { env: config.env, host: addr.address, port: addr.port, origin: config.publicOrigin });
  console.log(`\nDesu Burguer rodando em ${config.publicOrigin}`);
  console.log(`Painel administrativo: ${config.publicOrigin}/admin/`);
  if (admins === 0) {
    console.log('\nAtenção: nenhum administrador cadastrado. Rode "npm run create-admin" para criar o primeiro.');
  }
});

function shutdown(signal) {
  log.info('server_stopping', { signal });
  server.close(() => {
    db.close();
    process.exit(0);
  });
  setTimeout(() => process.exit(1), 10_000).unref();
}
process.on('SIGINT', () => shutdown('SIGINT'));
process.on('SIGTERM', () => shutdown('SIGTERM'));
process.on('unhandledRejection', (err) => log.error('unhandled_rejection', { error: err }));
