// Verifica a sintaxe de todos os arquivos JavaScript do projeto (node --check).
import { execFileSync } from 'node:child_process';
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..');
const dirs = ['server', 'scripts', 'public/js', 'tests'];
const files = [];
function walk(dir) {
  for (const entry of fs.readdirSync(dir, { withFileTypes: true })) {
    const full = path.join(dir, entry.name);
    if (entry.isDirectory()) walk(full);
    else if (entry.name.endsWith('.js')) files.push(full);
  }
}
for (const d of dirs) if (fs.existsSync(path.join(root, d))) walk(path.join(root, d));

let failed = 0;
for (const f of files) {
  try {
    execFileSync(process.execPath, ['--check', f], { stdio: 'pipe' });
  } catch (err) {
    failed++;
    console.error(`Erro de sintaxe em ${path.relative(root, f)}:\n${err.stderr}`);
  }
}
console.log(`${files.length - failed}/${files.length} arquivos JavaScript sem erro de sintaxe.`);
process.exit(failed ? 1 : 0);
