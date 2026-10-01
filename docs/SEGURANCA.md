# Guia de revisão de segurança — Desu Burguer

> **O que é este guia:** uma lista reutilizável de práticas e verificações de segurança para este projeto
> (e para projetos web parecidos), baseada em orientações públicas do OWASP.
>
> **O que ele NÃO é:** não é certificação, não garante "segurança total" e **não substitui** controles técnicos
> no servidor e na hospedagem, nem uma auditoria ou teste de invasão feito por profissionais independentes.
> Nenhuma "skill de segurança" estava disponível no ambiente em que este guia foi escrito. Por isso ele foi criado
> como documento do repositório.

Referências usadas (consultadas em outubro de 2026):

- OWASP Top 10:2025 — <https://owasp.org/Top10/2025/>
- OWASP ASVS 5.0 (Application Security Verification Standard)
- OWASP Cheat Sheets: Password Storage, Session Management, Cross-Site Request Forgery Prevention,
  Input Validation, Cross Site Scripting Prevention, File Upload, Logging, HTTP Headers, Authentication

Como usar: antes de cada publicação (ou a cada mudança importante), percorra a lista, marque o que foi verificado
e rode `npm test` e `npm run test:e2e`. Itens marcados com **[pendente]** dependem de decisão ou ambiente seu.

---

## 1. Controle de acesso (A01:2025 — Broken Access Control)

| Verificação | Como está neste projeto | Onde |
|---|---|---|
| Toda rota de administração exige sessão válida **no servidor** | `requireAdmin` em todas as rotas `/api/admin/*` (exceto login); teste percorre todas e espera 401 | `server/routes/admin.js`, `tests/admin-security.test.js` |
| Cliente não acessa dados de outros clientes | Não há conta de cliente; o pedido é consultado por um **código secreto aleatório de 192 bits** (não por número sequencial) e a resposta traz só o primeiro nome | `server/services/orders.js` (`trackOrder`) |
| Mudanças de status seguem regras definidas no servidor | Máquina de estados + checagem do status atual (evita duas pessoas mudarem ao mesmo tempo) | `nextStatuses`, `updateOrderStatus` |
| Preços, descontos e taxas não vêm do navegador | O servidor recalcula tudo; campos extras como `price` ou `totalCents` são **recusados** (400) | `server/services/pricing.js`, `onlyKeys` |
| Separação administrador × cliente | Clientes não têm sessão; o papel `admin` é verificado em cada requisição | `requireAdmin` |

Revise: ao criar rota nova no painel, inclua `requireAdmin` e adicione a rota à lista do teste `ADMIN_ROUTES`.

## 2. Configuração segura (A02:2025 — Security Misconfiguration)

| Verificação | Como está |
|---|---|
| Cabeçalhos de segurança | CSP sem `unsafe-inline`/`unsafe-eval`, `X-Content-Type-Options: nosniff`, `X-Frame-Options: DENY`, `frame-ancestors 'none'`, `Referrer-Policy`, `Permissions-Policy`, COOP/CORP; HSTS em produção (`server/http/security.js`) |
| CORS | **Não habilitado**: o navegador bloqueia leitura por outros sites. Não adicione `Access-Control-Allow-Origin: *` |
| Produção exige HTTPS | O servidor **não inicia** em produção sem `PUBLIC_ORIGIN` com `https://` (`server/config.js`) |
| Sem credenciais padrão | Não existe usuário/senha inicial; o administrador é criado com `npm run create-admin` |
| Mensagens de erro | Erros internos devolvem mensagem genérica + código da requisição; o detalhe fica só no log |
| Arquivos sensíveis fora do ar | Só `public/` e `data/uploads/products/` são servidos; caminhos com `..`, arquivos ocultos (`.env`, `.git`), código e banco retornam 404 (testado) |
| **[pendente]** Proxy reverso | Se houver Nginx/Cloudflare/hospedagem na frente, defina `TRUST_PROXY` com o número de proxies. Sem isso, todos os clientes parecem ter o mesmo IP e o limite de pedidos vale para a loja inteira |

## 3. Cadeia de suprimentos de software (A03:2025 — Software Supply Chain Failures)

- O sistema roda **sem dependências de terceiros obrigatórias**: só Node.js (≥ 22.13) e seus módulos nativos
  (`node:http`, `node:sqlite`, `node:crypto`). Isso reduz bastante a superfície de ataque.
- Única dependência **opcional**: `sharp` (otimização de imagens), uma biblioteca amplamente usada.
- **[pendente]** Ao rodar `npm install`, rode também `npm audit` e aplique as correções compatíveis.
  Versione o `package-lock.json` que o `npm install` gerar.
- Mantenha o Node.js numa versão LTS com suporte e atualizada.
- Observação: `node:sqlite` ainda é marcado como "experimental" pelo Node. O acesso ao banco está isolado em
  poucos arquivos e coberto por testes. Rode `npm test` ao atualizar o Node.

## 4. Criptografia (A04:2025 — Cryptographic Failures)

| Verificação | Como está |
|---|---|
| Senhas com algoritmo próprio para senhas | **scrypt** (módulo `crypto` do Node/OpenSSL) com N=2^17, r=8, p=1 e sal aleatório, exatamente o mínimo recomendado pelo OWASP quando Argon2id não está disponível. O formato salvo permite migrar depois (`needsRehash`) |
| Tokens imprevisíveis | `crypto.randomBytes` para sessão (256 bits), CSRF (256 bits) e acompanhamento de pedido (192 bits) |
| Sessão não fica legível no banco | Banco guarda só o **hash SHA-256** do identificador da sessão |
| Transporte | HTTPS obrigatório em produção, cookie `Secure` e HSTS |

## 5. Injeção (A05:2025 — Injection) e XSS

| Verificação | Como está |
|---|---|
| SQL injection | Todas as consultas usam parâmetros (`?`/`:nome`); nomes de colunas dinâmicos vêm de listas fixas do código, nunca do usuário |
| XSS | Todo texto vindo do servidor entra na página por `textContent`/`createElement` (nunca `innerHTML`); CSP bloqueia scripts inline; teste grava `<img onerror>` como nome de produto e confirma que volta só como dado |
| Validação de entrada | Tipos, tamanhos e formatos validados no servidor (`server/validation.js`); campos desconhecidos são recusados; caracteres de controle removidos |
| Upload perigoso | Só JPG/PNG/WebP **verificados pelo conteúdo** (não pelo nome/tipo informado); SVG, HTML e outros são recusados; nome do arquivo é aleatório; limite de tamanho e de dimensões; com `sharp`, a imagem é decodificada e regravada (remove metadados como GPS) |
| Path traversal | Resolução segura de caminhos com checagem de pasta raiz (testado com várias codificações de `..`) |

## 6. Design seguro (A06:2025 — Insecure Design)

- **Pedidos duplicados:** cada envio leva um identificador único (`idempotencyKey`); reenvio devolve o mesmo pedido.
- **Total confirmado:** o navegador informa o total que mostrou ao cliente; se o servidor calcular outro valor,
  o pedido é recusado e o novo total é exibido para confirmação.
- **Cupom com limite de usos:** contagem feita de forma atômica dentro da transação do pedido.
- **Limites técnicos anti-abuso:** até 30 itens diferentes, 20 unidades por item, 60 unidades por pedido.
- **Pagamento:** não há cobrança online. Nenhum dado de cartão é coletado ou armazenado.
  Veja a seção 12 antes de integrar um provedor.

## 7. Autenticação (A07:2025 — Authentication Failures)

| Verificação | Como está |
|---|---|
| Senha forte | Mínimo de 15 caracteres (frase-senha), máximo de 128; recusa senhas óbvias ou que contenham o e-mail |
| Limite de tentativas | Por IP (10 a cada 15 min no login) **e** por e-mail (5 a cada 15 min); conta bloqueada por 15 min após 5 erros |
| Sem enumeração de usuários | Mesma mensagem e tempo de resposta parecido para e-mail inexistente e senha errada |
| Sessão | Cookie `HttpOnly`, `SameSite=Strict`, `Secure` + prefixo `__Host-` em produção; expira em 12 h ou 2 h sem uso; novo identificador a cada login; logout apaga no servidor; troca de senha encerra as outras sessões |
| CSRF | Token por sessão exigido no cabeçalho `X-CSRF-Token` + verificação de `Origin`/`Sec-Fetch-Site` + JSON obrigatório |
| **[pendente]** Segundo fator (2FA) | Não implementado. Recomendado se o painel for acessado por mais pessoas ou de fora da loja |

## 8. Integridade de software e dados (A08:2025)

- O site não carrega scripts de CDNs externos (CSP `script-src 'self'`).
- O banco usa transações e restrições (`CHECK`, chaves estrangeiras). O total do pedido é conferido pelo próprio banco
  (`total = subtotal − desconto + taxa`).
- **[pendente]** Faça backup periódico com `npm run backup` e guarde cópias fora do servidor (protegidas: contêm dados pessoais).

## 9. Registro e alertas (A09:2025 — Security Logging and Alerting Failures)

- Logs em JSON (uma linha por evento): login com sucesso/falha, bloqueio de conta, CSRF/origem recusados,
  limite atingido, ações administrativas (também gravadas na tabela `audit_log`) e pedidos criados (sem dados pessoais).
- Nunca são registrados: senhas, tokens, cookies, telefones, endereços. E-mails aparecem mascarados (`jo***@dominio`).
  Há teste que confere isso.
- **[pendente]** Configure na hospedagem a retenção dos logs e um alerta para muitos `login_failed`/`account_locked`.

## 10. Condições excepcionais (A10:2025 — Mishandling of Exceptional Conditions)

- Erros inesperados param a requisição com resposta genérica (falha "fechada"), sem expor detalhes.
- Transações desfazem tudo em caso de erro (nenhum pedido "pela metade").
- Tempo limite de requisição (30 s) e de cabeçalhos (15 s); corpo JSON limitado a 32 KB; imagem a 5 MB.
- Cálculo de senha limitado a 2 em paralelo (evita derrubar o servidor com muitas tentativas de login).

## 11. Privacidade e dados pessoais (LGPD)

- Dados coletados do cliente: **nome, telefone e endereço (só para entrega)**. Nada de CPF, e-mail ou data de nascimento.
- O acompanhamento do pedido mostra só o primeiro nome; não mostra telefone nem endereço.
- `npm run purge-personal-data -- --days N` apaga nome, telefone, endereço e observações de pedidos finalizados há mais de N dias.
- **[pendente]** Definir o prazo de retenção e publicar uma política de privacidade (decisão do responsável pela loja).

## 12. Pagamentos online (quando houver)

Hoje o sistema **não** cobra online. Se for integrar um provedor (Pix dinâmico, cartão etc.):

1. Use um provedor de pagamento confiável com checkout/tokenização próprios. **Nunca** receba ou guarde número de cartão.
2. Crie a cobrança no **servidor**, com o valor calculado pelo servidor (nunca o valor enviado pelo navegador).
3. Guarde as chaves do provedor só em variáveis de ambiente (`.env`), nunca no código ou no Git.
4. Valide a assinatura de cada webhook e confirme o status consultando a API do provedor antes de marcar como pago.
5. Use idempotência também na criação da cobrança e trate webhooks repetidos.
6. Teste em ambiente "sandbox" do provedor antes de cobrar de verdade.

## 13. Segredos

- O projeto **não tem segredos no código**. A configuração fica em `.env`, que está no `.gitignore`.
- Ao revisar, procure por chaves/senhas no código e no histórico do Git. Se encontrar alguma, **troque-a no serviço de origem** (apagar do código não basta).

---

## Checklist rápido antes de publicar

- [ ] `npm test` e `npm run test:e2e` passando
- [ ] `.env` com `NODE_ENV=production`, `PUBLIC_ORIGIN=https://...` e `TRUST_PROXY` corretos
- [ ] HTTPS funcionando (cadeado no navegador) e HTTP redirecionando para HTTPS na hospedagem
- [ ] Administrador criado com `npm run create-admin` (senha forte, guardada em gerenciador de senhas)
- [ ] `npm audit` sem vulnerabilidades relevantes (se instalou dependências)
- [ ] Backup automático do arquivo `data/desu.db` configurado
- [ ] Prazo de retenção de dados pessoais definido
- [ ] Imagens aprovadas enviadas e marcadas corretamente como "ilustrativa" ou "foto real"
- [ ] Revisão por terceiro/auditoria independente, se o volume de pedidos ou dados justificar
