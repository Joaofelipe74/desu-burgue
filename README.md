# Desu Burguer

Sistema de pedidos da hamburgueria **Desu Burguer**: cardápio online, personalização de lanches,
carrinho, finalização com entrega ou retirada, acompanhamento do pedido e painel administrativo.

- **Cliente:** escolhe produtos e adicionais, ajusta quantidades e informa entrega/retirada e forma de pagamento. Depois acompanha o pedido por um link.
- **Loja (painel `/admin/`):** recebe e atualiza pedidos e cuida de categorias, produtos, fotos, disponibilidade, adicionais, cupons, taxa de entrega e horário aberto/fechado.
- **Pagamento:** feito **na entrega ou na retirada** (dinheiro, cartão na maquininha ou Pix). O site **não cobra nada online**.

> A versão original (2 arquivos) está preservada em `_backup-original/` e também no primeiro commit do Git.

> **Cardápio de exemplo:** na primeira vez que o sistema abre, ele cadastra um cardápio de exemplo
> (24 itens em 5 categorias, adicionais, destaques, taxa de entrega de R$ 6,00 e horário "Terça a domingo, das 18h às 23h").
> Os **preços são sugestões**: revise tudo no painel (`/admin/` → Cardápio, Adicionais e Configurações) antes de atender clientes reais.
> O X-Bacon original mantém o preço de R$ 24,90. Os produtos usam **ilustrações próprias** (desenhos) com o selo
> "Imagem ilustrativa" até você enviar as fotos.

---

## Jeito mais fácil (Windows)

Dê **dois cliques** em `INICIAR-DESU-BURGUER.bat`. Ele confere o Node.js, pede para criar o login do painel
(só na primeira vez), inicia o sistema e abre <http://localhost:3000>. Para desligar, feche a janela preta.

## Como rodar no seu computador (Windows, macOS ou Linux)

### 1. Instale o Node.js

Baixe a versão **LTS** em <https://nodejs.org> (precisa ser **22.13 ou mais nova**).
Para conferir, abra o terminal (no Windows: *Prompt de Comando* ou *PowerShell*) e digite:

```bash
node --version
```

### 2. Abra o terminal na pasta do projeto

```bash
cd "C:\Users\SEU_USUARIO\Downloads\Desu-burguer-estudo"
```

### 3. (Opcional, recomendado) Instale a otimização de imagens

```bash
npm install
```

O sistema funciona sem esse passo. Ele instala só o `sharp`, que deixa as fotos mais leves.

### 4. Crie o primeiro administrador

```bash
npm run create-admin
```

Informe e-mail, nome e uma senha de **pelo menos 15 caracteres**. Uma frase funciona bem.
**Não existe usuário ou senha padrão.**

### 5. Inicie o sistema

```bash
npm start
```

Abra no navegador:

- Cardápio: <http://localhost:3000>
- Painel: <http://localhost:3000/admin/>

Para parar, pressione `Ctrl + C` no terminal.

---

## Comandos disponíveis

| Comando | O que faz |
|---|---|
| `npm start` | Inicia o sistema |
| `npm run dev` | Inicia e reinicia sozinho quando o código do servidor muda |
| `npm run create-admin` | Cria um administrador (`-- --reset` redefine a senha de um existente) |
| `npm test` | Roda os testes automáticos (43 testes) |
| `npm run test:e2e` | Teste no navegador, em tamanho de celular e de computador (precisa do Playwright, veja abaixo) |
| `npm run check` | Confere a sintaxe de todos os arquivos e roda os testes |
| `npm run import-image -- --produto 1 --arquivo foto.png` | Associa uma imagem a um produto |
| `npm run backup` | Copia o banco para `data/backups/` |
| `npm run purge-personal-data -- --days 90` | Apaga dados pessoais de pedidos finalizados há mais de 90 dias |

Teste no navegador (opcional):

```bash
npm install --no-save playwright
npx playwright install chromium
npm run test:e2e
```

As capturas de tela ficam em `test-results/e2e/`.

---

## Colocar no ar (produção)

> Nada foi publicado. Esta seção explica o que é preciso para publicar quando você decidir.

O sistema tem servidor e banco de dados. Por isso **não funciona em hospedagem só de arquivos estáticos**.
É preciso um serviço que rode **Node.js 22+**, mantenha o processo ligado e tenha **disco persistente**
para a pasta `data/` (banco e fotos).

1. Copie `.env.example` para `.env` e ajuste:
   ```ini
   NODE_ENV=production
   PUBLIC_ORIGIN=https://www.seudominio.com.br
   TRUST_PROXY=1        # quantos proxies/balanceadores ficam na frente (0 se nenhum)
   ```
   O sistema **se recusa a iniciar** em produção sem HTTPS, de propósito.
2. Configure o HTTPS na hospedagem ou num proxy (Nginx, Caddy, Cloudflare).
   Também é possível usar `TLS_CERT_FILE`/`TLS_KEY_FILE` direto no Node.
3. Rode `npm install --omit=dev`, depois `npm run create-admin`, depois `npm start`.
   Use o gerenciador de processos da hospedagem (ou `pm2`/`systemd`) para manter o sistema ligado.
4. Agende `npm run backup` (por exemplo, diariamente) e guarde as cópias **fora** do servidor.
5. Rode **uma única instância** do sistema. O banco SQLite e os limites de tentativas ficam no próprio processo.

Antes de publicar, siga o checklist de [`docs/SEGURANCA.md`](docs/SEGURANCA.md).

---

## Estrutura

```
server/            servidor (Node.js puro, sem frameworks)
  app.js           segurança comum, API e arquivos estáticos
  db.js            banco SQLite, estrutura e dados iniciais
  routes/          rotas públicas e do painel
  services/        regras: cardápio, preços, pedidos, cupons, imagens, configurações
  auth/            senhas (scrypt) e sessões
  http/            roteador, leitura segura de requisições, cabeçalhos, limites
public/            telas (HTML, CSS e JavaScript do navegador)
  index.html       cardápio + carrinho
  checkout.html    finalização do pedido
  pedido.html      acompanhamento
  admin/           painel administrativo
scripts/           administrador, backup, importação de imagens, retenção de dados
tests/             testes automáticos (API, segurança, cálculo, navegador)
docs/              segurança, imagens e relatório da revisão
data/              (criada ao rodar) banco e fotos enviadas, fora do Git
_backup-original/  arquivos originais, intocados
```

## Documentação

- [`docs/RELATORIO-REVISAO.md`](docs/RELATORIO-REVISAO.md): o que foi corrigido, testes, pendências e perguntas em aberto
- [`docs/SEGURANCA.md`](docs/SEGURANCA.md): guia reutilizável de revisão de segurança (OWASP Top 10:2025)
- [`docs/IMAGENS.md`](docs/IMAGENS.md): quais imagens enviar e como
