// Cria (ou redefine a senha de) um administrador.
// Uso:  npm run create-admin
//       npm run create-admin -- --reset   (redefinir senha de um e-mail existente)
// Não existe usuário/senha padrão: a senha é digitada por você e guardada só como hash.
import path from 'node:path';
import readline from 'node:readline';
import { Writable } from 'node:stream';
import { hashPassword, passwordProblem } from '../server/auth/passwords.js';
import { destroyUserSessions } from '../server/auth/sessions.js';
import { buildConfig, loadEnvFile } from '../server/config.js';
import { openDatabase } from '../server/db.js';

loadEnvFile();
const config = buildConfig();
const reset = process.argv.includes('--reset');
// --if-missing: só pergunta se ainda não existir nenhum administrador (usado pelo INICIAR-DESU-BURGUER.bat)
const onlyIfMissing = process.argv.includes('--if-missing');

// Saída "silenciável": enquanto a senha é digitada, nada aparece na tela.
let muted = false;
const output = new Writable({
  write(chunk, _enc, cb) {
    if (!muted) process.stdout.write(chunk);
    cb();
  },
});
const isTTY = Boolean(process.stdin.isTTY);
const rl = readline.createInterface({ input: process.stdin, output, terminal: isTTY });
const linesIter = rl[Symbol.asyncIterator]();

async function ask(question, hidden = false) {
  process.stdout.write(question);
  muted = hidden;
  const { value, done } = await linesIter.next();
  muted = false;
  if (hidden && isTTY) process.stdout.write('\n');
  if (done) throw new Error('Entrada encerrada antes do fim.');
  return value;
}

const db = openDatabase(path.join(config.dataDir, 'desu.db'));

if (onlyIfMissing && db.prepare('SELECT COUNT(*) AS n FROM admin_users').get().n > 0) {
  rl.close();
  db.close();
  process.exit(0);
}
if (onlyIfMissing) console.log('Primeiro acesso: crie o login do painel administrativo.\n');

try {
  const email = (await ask('E-mail do administrador: ')).trim().toLowerCase();
  if (!/^[^\s@]{1,64}@[^\s@]{1,190}\.[^\s@]{2,}$/.test(email)) throw new Error('E-mail inválido.');
  const existing = db.prepare('SELECT id FROM admin_users WHERE email = ?').get(email);
  if (existing && !reset) throw new Error('Este e-mail já está cadastrado. Para trocar a senha use: npm run create-admin -- --reset');
  if (!existing && reset) throw new Error('Não há administrador com este e-mail.');

  let name = '';
  if (!existing) {
    name = (await ask('Nome: ')).trim();
    if (name.length < 2 || name.length > 80) throw new Error('Nome deve ter entre 2 e 80 caracteres.');
  }

  console.log('Senha: mínimo de 15 caracteres. Dica: use uma frase fácil de lembrar e difícil de adivinhar.');
  const password = await ask('Senha: ', true);
  const problem = passwordProblem(password, email);
  if (problem) throw new Error(problem);
  const confirm = await ask('Repita a senha: ', true);
  if (confirm !== password) throw new Error('As senhas não conferem.');

  const hash = await hashPassword(password);
  if (existing) {
    db.prepare('UPDATE admin_users SET password_hash = ?, failed_attempts = 0, locked_until = NULL, active = 1 WHERE id = ?').run(
      hash,
      existing.id
    );
    destroyUserSessions(db, existing.id);
    console.log('\nSenha redefinida. Todas as sessões abertas desse administrador foram encerradas.');
  } else {
    db.prepare('INSERT INTO admin_users (email, name, password_hash) VALUES (?, ?, ?)').run(email, name, hash);
    console.log(`\nAdministrador criado. Acesse ${config.publicOrigin}/admin/ para entrar.`);
  }
  process.exitCode = 0;
} catch (err) {
  console.error(`\nErro: ${err.message}`);
  process.exitCode = 1;
} finally {
  rl.close();
  db.close();
}
