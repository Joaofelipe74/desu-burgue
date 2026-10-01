// Cria uma cópia de segurança consistente do banco em data/backups/.
// Uso: npm run backup
import fs from 'node:fs';
import path from 'node:path';
import { DatabaseSync } from 'node:sqlite';
import { buildConfig, loadEnvFile } from '../server/config.js';

loadEnvFile();
const config = buildConfig();
const source = path.join(config.dataDir, 'desu.db');
if (!fs.existsSync(source)) {
  console.error('Banco não encontrado. Inicie o sistema ao menos uma vez (npm start).');
  process.exit(1);
}
const dir = path.join(config.dataDir, 'backups');
fs.mkdirSync(dir, { recursive: true });
const stamp = new Date().toISOString().replace(/[:.]/g, '-');
const target = path.join(dir, `desu-${stamp}.db`);
const db = new DatabaseSync(source);
db.prepare('VACUUM INTO ?').run(target);
db.close();
console.log(`Backup criado em: ${target}`);
console.log('Guarde cópias fora deste computador (o arquivo contém dados de clientes — proteja-o).');
