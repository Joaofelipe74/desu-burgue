// Testes do armazenamento de senhas.
import assert from 'node:assert/strict';
import { describe, it } from 'node:test';
import { hashPassword, needsRehash, passwordProblem, verifyPassword } from '../server/auth/passwords.js';

describe('senhas', () => {
  it('gera hash scrypt com sal aleatório e verifica corretamente', async () => {
    const pw = 'cavalo correto bateria grampo';
    const a = await hashPassword(pw);
    const b = await hashPassword(pw);
    assert.match(a, /^scrypt\$131072\$8\$1\$/);
    assert.notEqual(a, b, 'sal diferente a cada hash');
    assert.ok(!a.includes(pw));
    assert.equal(await verifyPassword(pw, a), true);
    assert.equal(await verifyPassword('senha errada qualquer coisa', a), false);
    assert.equal(await verifyPassword(pw, 'formato-invalido'), false);
    assert.equal(needsRehash(a), false);
    assert.equal(needsRehash('scrypt$16384$8$1$x$y'), true);
  });

  it('exige senha longa e recusa senhas óbvias', () => {
    assert.match(passwordProblem('curta'), /15 caracteres/);
    assert.match(passwordProblem('aaaaaaaaaaaaaaaaaaaa'), /fácil/);
    assert.match(passwordProblem('joaozinho-minha-senha-123', 'joaozinho@x.com'), /e-mail/);
    assert.equal(passwordProblem('uma frase longa que só eu sei'), null);
    assert.match(passwordProblem('x'.repeat(129)), /no máximo/);
  });
});
