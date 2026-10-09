# Relatório da revisão — Desu Burguer (01/10/2026)

## 1. O que existia antes

A pasta `Desu-burguer-estudo` tinha só **2 arquivos**: `index.html` e `style.css`.
Não havia servidor, banco de dados, JavaScript, imagens, documentação nem versões duplicadas.
Os originais estão preservados sem alteração em `_backup-original/` e no primeiro commit do Git
("Versão original do projeto").

Erros encontrados no `index.html` original:

| # | Problema | Efeito |
|---|---|---|
| 1 | `< html lang="pt-BR">` (espaço depois do `<`) | Tag inválida |
| 2 | `charset="UTF- 8"` | Codificação inválida; acentos podiam quebrar |
| 3 | `<meta name="viewport" ...` sem `>` | Engolia a linha seguinte (o `<title>`) |
| 4 | `<link ... hrf="style.css">` (em vez de `href`) e fora do `<head>` | **O CSS nunca era carregado** |
| 5 | `</body></html>` fechados antes do cardápio | O `<article>` ficava fora do documento |
| 6 | `</main>` sem `<main>` de abertura | HTML inválido |
| 7 | "Hambrugueria", "hora1", "cardapio" | Erros de digitação |
| 8 | "Pão, carne, queijo e **queijo** crocante" no X-Bacon | Provável erro: o X-Bacon não citava bacon (ver perguntas) |
| 9 | Preço "24,90" sem "R$" e botão "Adicionar ao carrinho" sem nenhuma ação | Não havia carrinho |
| 10 | Título "Minha Hamburgueria", diferente do nome "Desu Burguer" | Identidade inconsistente |

## 2. Decisões técnicas

- **Node.js puro, sem dependências obrigatórias.** O ambiente de trabalho não tinha acesso ao repositório npm.
  Em vez de entregar código não testado com Express e outras bibliotecas, usei só o que já vem no Node.js 22.13+:
  servidor `node:http`, banco SQLite `node:sqlite`, criptografia `node:crypto` e testes `node:test`.
  Vantagens: roda sem `npm install` e quase não há cadeia de dependências para manter (OWASP A03:2025).
- **SQLite** num arquivo (`data/desu.db`): simples de copiar e fazer backup, suficiente para uma loja.
- **Frontend em HTML, CSS e JavaScript sem build**, aproveitando a estrutura e as cores do projeto original
  (`#161616`, `#262626`, `#ffb703`).
- **Dados iniciais:** só o que existia no original, a categoria "Hambúrgueres" e o **X-Bacon a R$ 24,90**.
  Nenhum preço, produto, cupom ou taxa foi inventado. O resto é cadastrado por você no painel.

## 3. Funcionalidades implementadas

**Cliente**

- Cardápio por categorias, com foto (ou aviso "Foto em breve"), descrição, preço e selo "Indisponível".
- Personalização: adicionais com preço, quantidade e observação (ex.: "sem cebola").
- Carrinho com aumentar/diminuir/remover e subtotal. Fica salvo no navegador e sincroniza entre abas.
- Checkout:
  - nome e telefone;
  - **retirada ou entrega**, com endereço só na entrega;
  - forma de pagamento e troco;
  - cupom;
  - observações;
  - revisão com valores **calculados pelo servidor**.
- Proteções no checkout: botão desativado durante o envio, mensagens claras de erro e carregamento,
  e recálculo com aviso se o preço mudar.
- Página de acompanhamento com linha do tempo do status. Atualiza sozinha a cada 20 s.

**Painel administrativo (`/admin/`)**

- Login com proteção contra força bruta; sessão segura; logout; troca de senha.
- Pedidos:
  - lista "em aberto" ou por status, com atualização automática;
  - destaque para pedidos novos;
  - botões que só oferecem o próximo status válido;
  - cancelamento com confirmação em dois cliques.
- Cardápio: categorias (criar, renomear, ordenar, ocultar, excluir) e produtos (criar, editar, preço, ordem,
  disponibilidade com um clique, arquivar/restaurar, adicionais permitidos, foto com texto alternativo e selo de ilustrativa).
- Adicionais, cupons (percentual ou valor fixo, mínimo, limite de usos, validade) e configurações
  (loja aberta/fechada, retirada, entrega, taxa, pedido mínimo, formas de pagamento, telefone).

**Operação**

- `create-admin` (sem senha padrão), `backup`, `import-image` e `purge-personal-data` (retenção LGPD).

## 4. Testes executados e resultados

| Verificação | Resultado |
|---|---|
| `npm test`: 43 testes automáticos (cálculo, fluxo completo com banco real, adulteração de valores, duplicidade, cupons, acesso administrativo, CSRF, sessão, bloqueio de conta, limites, cabeçalhos, path traversal, uploads, erros, configuração de produção, IP atrás de proxy) | **43/43 passaram**, tanto **com** quanto **sem** o `sharp` |
| `npm run test:e2e`: Chromium em **computador (1280 px)** e **celular (390 px)** | **18/18 etapas passaram**, sem erros de JavaScript nem violações de CSP no console |
| Itens cobertos pelo E2E | Cardápio → personalização → carrinho → checkout (validação, entrega com taxa, retirada com troco) → pedido → acompanhamento → painel (login errado/certo, mudança de status vista pelo cliente, envio de imagem com selo "Imagem ilustrativa", indisponibilidade, abas, painel no celular, logout) |
| Verificações de layout no E2E | Sem rolagem horizontal, todas as imagens com `alt`, nenhuma imagem quebrada, todos os campos com rótulo |
| Modo produção com HTTPS (certificado de teste) | Inicia só com `PUBLIC_ORIGIN` https; HSTS e cookie `__Host-` com `Secure`; login, pedido e mudança de status funcionando; origem `http://localhost` recusada (403); log sem senha, token ou telefone |
| Scripts | `create-admin` (recusa senha fraca e e-mail duplicado), `backup`, `import-image` (com e sem `sharp`) e `purge-personal-data` funcionaram |
| Análise estática (ESLint 10, regras de erros e de segurança, como proibição de `innerHTML`) e `node --check` | Sem problemas (44 arquivos) |

Os testes rodaram em Linux com Node.js 22.22. As capturas de tela do E2E ficam em `test-results/e2e/` quando você roda o teste.

## 5. Pendências e o que NÃO pude verificar

- **Execução no seu Windows:** testado em Linux. O código usa caminhos e comandos compatíveis com Windows, mas rode `npm test` aí para confirmar.
- **Versão do Node no seu computador:** precisa ser **22.13 ou mais nova** (`node --version`).
- **`npm install` do `sharp` e `npm audit`:** não foi possível acessar o repositório npm daqui. Rode os dois no seu computador.
- **Imagens:** nenhuma imagem do ChatGPT estava disponível. Veja a lista exata em [`IMAGENS.md`](IMAGENS.md).
- **Navegadores:** testado em Chromium. Safari (iPhone) e Firefox não foram testados.
- **Leitor de tela:** a estrutura segue boas práticas (rótulos, `alt`, foco visível, `aria-live`, tamanho de toque de 44 px), mas não foi testada com NVDA ou VoiceOver.
- **Hospedagem real, carga/volume e notificações:** nada foi publicado. Nenhuma mensagem é enviada a clientes. Não há integração com WhatsApp nem pagamento online.
- **`node:sqlite`** é marcado como "experimental" pelo Node. O aviso fica oculto nos comandos `npm`. O acesso ao banco está isolado e testado.

## 6. Perguntas para você (decisões de negócio)

Nenhuma delas impede o sistema de funcionar. Os valores atuais podem ser mudados no painel.

1. **X-Bacon:** a descrição original dizia "queijo e queijo crocante". Troquei para "**bacon** crocante". Está certo?
2. **Grafia do nome:** "Desu **Burguer**" (com "u") é a grafia oficial?
3. **Entrega:** começa **desligada**. Qual a taxa? É fixa ou varia por bairro (hoje o sistema só tem taxa fixa)? Há área máxima de entrega?
4. **Pedido mínimo:** existe? Hoje está em R$ 0,00.
5. **Pagamento:** as três opções (dinheiro, cartão na maquininha, Pix na entrega/retirada) estão ativas. Todas valem? Deseja pagamento **online** no futuro?
6. **Retirada:** qual o endereço e o telefone de contato a exibir?
7. **Horário:** hoje a loja é aberta/fechada manualmente no painel. Quer abertura e fechamento automáticos por horário?
8. **Cardápio completo:** quais outros produtos, categorias, adicionais e preços? (podem ser cadastrados no painel)
9. **Retenção de dados:** por quantos dias guardar nome, telefone e endereço de pedidos finalizados? É preciso uma política de privacidade.
10. **Hospedagem:** onde pretende publicar? (precisa rodar Node.js e ter disco persistente)
11. **Avisos ao cliente:** deseja aviso automático (ex.: WhatsApp) quando o status mudar?

## 7. Segurança

O detalhamento está em [`SEGURANCA.md`](SEGURANCA.md). Riscos que continuam existindo:

- **Sem segundo fator (2FA)** no painel: quem obtiver a senha do administrador entra.
- **Bloqueio de conta pode ser abusado:** alguém pode errar a senha de propósito e travar o login do administrador por 15 minutos.
- **Limites de tentativas ficam na memória** do processo: zeram ao reiniciar e não funcionam com várias instâncias.
- **Proxy mal configurado:** com `TRUST_PROXY` errado, todos os clientes parecem ter o mesmo IP e o limite de pedidos (20 a cada 10 min) vale para a loja inteira.
- **Pedidos falsos:** qualquer pessoa pode fazer pedido sem conta. Há limite por IP, mas não confirmação por SMS ou WhatsApp.
- **Cópias e backups do banco contêm dados pessoais.** Proteja o servidor e os backups.
- Não houve auditoria nem teste de invasão independente.

## 8. Atualização de 02/10/2026: cardápio de exemplo, página inicial e ilustrações

Feita a pedido do dono ("o site está incompleto"; opção escolhida: exemplo com preços sugeridos).

- **Cardápio de exemplo**, aplicado uma única vez em cada banco (`server/sample-menu.js`):
  - 5 categorias e 24 produtos;
  - 7 adicionais vinculados a cada tipo de produto;
  - 4 destaques;
  - entrega ligada com taxa de R$ 6,00;
  - horário e texto "Sobre".
  
  O X-Bacon original manteve o preço e os textos. **Todos os preços são sugestões a revisar no painel.**
- **Página inicial:** banner com ilustração, destaques da casa, menu de categorias, "Como funciona", "Sobre",
  cartões de horário/entrega/retirada/pagamento, botão de WhatsApp (só aparece se configurado) e rodapé completo.
- **Celular:** no cardápio, a lista fica compacta (imagem à esquerda) e os destaques viram um carrossel.
- **Ilustrações:** 22 desenhos próprios em SVG, escolhidos no painel e exibidos sempre com o selo "Imagem ilustrativa".
  Uma foto enviada pelo painel tem prioridade.
- **Painel:**
  - produto: campos de ilustração e destaque;
  - configurações: horário, texto "Sobre" e WhatsApp (validado e transformado em link `wa.me` pelo servidor).
- **Testes:** 48 testes automáticos (5 novos sobre o cardápio de exemplo, incluindo cálculo de pedido e validação de ilustração/WhatsApp) e 18 etapas E2E passando. Nenhum erro de console/CSP.

## 9. Atualização de 06/10/2026: mais variedade, personalização e funções

Feita a pedido do dono ("mais diversidade, sem tirar o que já tem"). Nada foi removido.

- **Cardápio:** 63 produtos em 12 categorias. As novas são Smash Burgers, Artesanais Premium, Hot Dogs, Sanduíches, Kids, Açaí e Molhos.
  - Os itens anteriores continuam iguais (o X-Bacon segue a R$ 24,90).
  - A ampliação só acrescenta itens e nunca muda o que o dono já editou.
  - **Os preços continuam sendo sugestões.**
- **Personalização:**
  - grupos de opções de escolha única ou múltipla, obrigatórios ou não, com limite e preço extra;
  - exemplos: ponto da carne, tipo de pão (brioche +R$ 2,00), retirar ingredientes, sabores de bebida, molho dos nuggets, acompanhamentos do açaí (até 4) e sabores do sorvete (até 2);
  - o servidor confere tudo e soma os valores.
- **Site do cliente:**
  - busca sem diferenciar acentos;
  - filtros rápidos: Ofertas, Mais pedidos (calculado pelos pedidos reais dos últimos 30 dias), Favoritos, Novidades, Vegetarianos, Picantes e Para compartilhar;
  - ordenação por preço ou nome;
  - favoritos guardados no navegador;
  - selos nos produtos e preço promocional com o valor antigo riscado;
  - edição de itens no carrinho.
- **Painel:**
  - nova aba **Opções**, com grupos e escolhas, disponibilidade e arquivamento;
  - no produto: preço promocional, selos e grupos de opções.
- **Testes:**
  - 58 testes automáticos, 10 deles novos: preço das opções, obrigatórias, limite, opção de outro grupo, indisponível, promoção, selos, mais pedidos e ampliação sem duplicar;
  - 20 etapas E2E, incluindo busca e opção obrigatória, em celular e computador;
  - nenhum erro de console ou CSP.

## 10. Atualização de 07/10/2026: ilustrações redesenhadas

Feita a pedido do dono ("dá pra melhorar as imagens do cardápio").

- **Sem gerador de imagens por IA:** esta sessão não tinha nenhum conectado. Procurei nos conectores disponíveis e não há um.
  Por isso, os desenhos foram refeitos em código (SVG). Continuam sendo **ilustrações** e aparecem com o selo "Imagem ilustrativa".
- **Desenhos:** todos os 60 foram refeitos e a arte do topo também, num estilo único com volume, sombras, brilho e textura leve.
  - O trabalho foi dividido entre agentes de ilustração por grupo (lanches, acompanhamentos, bebidas, especiais, sobremesas e combos).
  - Cada grupo foi revisado visualmente em tamanho grande e em tamanho de cartão.
- **Combo Casal:** ganhou desenho próprio, com 2 lanches. Antes usava o do Combo Família, que tem 4.
  - Em bancos que já existiam, a troca só acontece se o produto ainda estiver com o desenho original do exemplo.
- **Desempenho:** o servidor passou a enviar HTML, CSS, JS e SVG compactados com gzip quando o navegador aceita.
  As ilustrações somam cerca de 1,7 MB sem compactar e cerca de 400 KB compactadas.
- **Visual:** o fundo atrás das imagens no cartão e na janela do produto passou para o mesmo tom escuro das ilustrações.
- **Testes:**
  - 60 testes automáticos; os 2 novos cobrem a compactação gzip e a troca do Combo Casal;
  - as 20 etapas E2E continuam passando;
  - a página com o cardápio de exemplo completo não teve erro de console nem imagem quebrada;
  - no celular, nenhum conteúdo passou da largura da tela.
- **Limitação:** alguns detalhes das descrições não aparecem no desenho. O exemplo mais visível é o presunto do X-Tudo.
  Como são imagens ilustrativas, o texto do produto é o que vale. Fotos reais podem ser enviadas pelo painel a qualquer momento.

## 11. Atualização de 08/10/2026: demonstração online no GitHub Pages

- **Problema:** o link do portfólio (`joaofelipe74.github.io/desu-burgue`) parou de mostrar o site.
  Isso aconteceu quando a versão nova foi enviada ao repositório. O GitHub Pages só hospeda arquivos e não roda o servidor
  Node, então passou a exibir o README.
- **Solução:** uma versão de demonstração estática, gerada por `scripts/build-demo.js` na pasta `demo/`.
  O `index.html` da raiz redireciona o GitHub Pages para ela, e por isso não foi preciso mudar nenhuma configuração do GitHub.
  - **O que tem:** cardápio de exemplo, busca, filtros, favoritos, personalização, carrinho, finalização e acompanhamento.
  - **Cálculo:** é o mesmo do servidor. `pricing.js` e `option-rules.js` são copiados sem alteração, e um teste confere que o
    orçamento da demonstração é idêntico ao do servidor.
  - **O que fica de fora:** painel, banco, envio de pedidos e cobrança. Um aviso fixo no topo diz isso.
  - **Pedidos:** ficam só no navegador, sem telefone nem sobrenome. O andamento avança sozinho para mostrar o acompanhamento.
- **Mudanças no código do sistema:**
  - a regra das opções foi para `server/services/option-rules.js`, sem dependências;
  - `public/js/lib.js` só usa a API de demonstração quando a página está marcada com `data-demo="1"`, o que nunca acontece
    no sistema real.
- **Testes:**
  - 64 testes automáticos, 4 deles novos sobre a demonstração (um confere se `demo/` está atualizada);
  - o E2E da demonstração (`npm run test:e2e:demo`) foi servido em `/desu-burgue/` como no GitHub Pages e passou nos 9 passos;
  - o E2E do sistema continua passando nos 20 passos.
- **Ao mudar telas ou o cardápio de exemplo:** rode `npm run build:demo:pages` e envie a pasta `demo/` junto.

### 11.1 Painel na demonstração (09/10/2026)

- **O que tem:** a demonstração ganhou o painel em `/desu-burgue/demo/admin/`, com as mesmas telas do sistema real.
  - **Pedidos:** os pedidos feitos na loja de demonstração aparecem no painel, junto com 4 pedidos de exemplo
    de clientes fictícios. A mudança de status segue as mesmas regras do servidor e o cliente vê o novo status no acompanhamento.
  - **Cardápio, adicionais e opções:** dá para ligar e desligar a disponibilidade, e a loja passa a recusar o item.
    As outras edições mostram um aviso de que só funcionam rodando o projeto.
  - **Cupons:** os cupons criados valem no checkout, calculados pelo mesmo `pricing.js` do servidor.
  - **Configurações:** abrir e fechar a loja, taxa, entrega e retirada se refletem na loja.
- **Como os dados são gerados:** as listas do painel saem, no build, dos mesmos serviços do servidor (`listProducts`,
  `listOptionGroups` etc.).
- **Sem senha:** o painel de demonstração abre sem senha, e o aviso fixo deixa isso claro.
  Não é controle de acesso; no sistema real, login, sessão, CSRF e permissões continuam no servidor.
- **Testes:** os testes cobrem status, transições inválidas, disponibilidade, cupom, loja fechada e edições bloqueadas.
  O E2E da demonstração abre o painel, muda o status e confere no acompanhamento do cliente.
