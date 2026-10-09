// Gera a VERSÃO DE DEMONSTRAÇÃO estática do Desu Burguer, para publicar no GitHub Pages
// (que só hospeda arquivos, sem servidor Node e sem banco de dados).
//
// O que a demonstração tem: cardápio de exemplo, busca e filtros, personalização, carrinho,
// finalização com o MESMO cálculo de preços do servidor e acompanhamento do pedido.
// O que ela NÃO tem: painel administrativo, banco de dados, envio de pedidos ou cobrança.
// Os pedidos ficam só no navegador de quem testa, e um aviso fixo deixa isso claro na tela.
//
// Uso:
//   npm run build:demo:pages   → atualiza a pasta demo/ publicada no GitHub Pages deste repositório
//   node scripts/build-demo.js --out dist-demo --base /desu-burgue/ --repo https://github.com/usuario/desu-burgue
//
// A saída é sempre igual para o mesmo código (sem datas), para dar para conferir se demo/ está atualizada.
//
//   --out   pasta de saída (padrão: dist-demo). É apagada e recriada a cada execução.
//   --base  caminho onde o site vai ficar (no GitHub Pages: /nome-do-repositorio/). Padrão: /
//   --repo  link do código, mostrado no aviso de demonstração (opcional)
import fs from 'node:fs';
import path from 'node:path';
import { ROOT_DIR } from '../server/config.js';
import { openDatabase } from '../server/db.js';
import { getPublicMenu, loadCatalog, popularProductIds } from '../server/services/menu.js';
import { STATUS_LABELS } from '../server/services/orders.js';
import { getSettings, PAYMENT_LABELS, publicSettings } from '../server/services/settings.js';

const MARCADOR = '.desu-demo-build';

function args(argv) {
  const out = { out: 'dist-demo', base: '/', repo: '' };
  for (let i = 0; i < argv.length; i++) {
    const [k, v] = [argv[i], argv[i + 1]];
    if (k === '--out' || k === '--base' || k === '--repo') {
      out[k.slice(2)] = v ?? '';
      i++;
    } else {
      throw new Error(`Opção desconhecida: ${k}`);
    }
  }
  if (!/^\/([A-Za-z0-9._-]+\/)*$/.test(out.base)) throw new Error('--base deve ser um caminho como / ou /desu-burgue/');
  if (out.repo && !/^https:\/\/[A-Za-z0-9.-]+(\/[A-Za-z0-9._~-]+)*\/?$/.test(out.repo)) {
    throw new Error('--repo deve ser um link https simples, por exemplo https://github.com/usuario/desu-burgue');
  }
  return out;
}

const escapeAttr = (s) => s.replace(/&/g, '&amp;').replace(/"/g, '&quot;').replace(/</g, '&lt;');

/** Apaga a pasta de saída só se ela for uma saída anterior deste script (ou estiver vazia). */
function prepararSaida(dir) {
  const real = path.resolve(dir);
  const proibidas = [ROOT_DIR, path.join(ROOT_DIR, 'public'), path.join(ROOT_DIR, 'server'), path.join(ROOT_DIR, 'data')];
  if (proibidas.some((p) => real === p || p.startsWith(real + path.sep))) throw new Error(`Pasta de saída não permitida: ${real}`);
  if (fs.existsSync(real)) {
    const vazia = fs.readdirSync(real).length === 0;
    if (!vazia && !fs.existsSync(path.join(real, MARCADOR))) {
      throw new Error(`A pasta ${real} já existe e não foi criada por este script. Escolha outra com --out.`);
    }
    fs.rmSync(real, { recursive: true, force: true });
  }
  fs.mkdirSync(real, { recursive: true });
  fs.writeFileSync(path.join(real, MARCADOR), 'Gerado por scripts/build-demo.js\n');
  return real;
}

function copiarPasta(origem, destino, ignorar = new Set()) {
  fs.mkdirSync(destino, { recursive: true });
  for (const item of fs.readdirSync(origem, { withFileTypes: true })) {
    if (ignorar.has(item.name)) continue;
    const de = path.join(origem, item.name);
    const para = path.join(destino, item.name);
    if (item.isDirectory()) copiarPasta(de, para);
    else if (item.isFile()) fs.copyFileSync(de, para);
  }
}

function arquivos(dir, ext) {
  return fs.readdirSync(dir, { recursive: true, withFileTypes: true })
    .filter((f) => f.isFile() && f.name.endsWith(ext))
    .map((f) => path.join(f.parentPath ?? f.path, f.name));
}

/** Troca caminhos que começam na raiz ("/css/...") pelo caminho base do site. */
function comBase(conteudo, base, { html }) {
  let s = conteudo;
  if (html) s = s.replace(/\b(href|src)="\/(?!\/)/g, `$1="${base}`);
  // Strings em JavaScript: '/img/...', '/pedido.html' e links "href: '/'". As chamadas
  // '/api/...' ficam como estão: quem responde é a API de demonstração.
  s = s.replace(/(['"`])\/(?=(?:img|css|js)\/|checkout\.html|pedido\.html|index\.html)/g, `$1${base}`);
  s = s.replace(/(href:\s*)(['"`])\/\2/g, `$1$2${base}$2`);
  return s;
}

function dadosDaDemo(base) {
  const db = openDatabase(':memory:', { sampleMenu: true });
  try {
    const settings = getSettings(db);
    const menu = {
      store: publicSettings(settings),
      categories: getPublicMenu(db),
      popularProductIds: popularProductIds(db),
    };
    for (const p of menu.categories.flatMap((c) => c.products)) {
      if (p.image?.src?.startsWith('/')) p.image.src = base + p.image.src.slice(1);
      if (p.image?.srcset) p.image.srcset = p.image.srcset.replace(/(^|,\s*)\//g, `$1${base}`);
    }
    const cat = loadCatalog(db);
    // Datas de criação/edição não entram no cálculo; tirar deixa a saída igual a cada execução.
    const semDatas = (lista) => lista.map((o) => Object.fromEntries(Object.entries(o).filter(([k]) => !k.endsWith('_at'))));
    const catalog = {
      products: semDatas([...cat.products.values()]),
      addons: semDatas([...cat.addons.values()]),
      links: [...cat.links.entries()].map(([pid, ids]) => [pid, [...ids]]),
      options: {
        groups: semDatas([...cat.options.groups.values()]),
        choices: semDatas([...cat.options.choices.values()]),
        productGroups: [...cat.options.productGroups.entries()],
      },
    };
    return { menu, settings, catalog, paymentLabels: PAYMENT_LABELS, statusLabels: STATUS_LABELS };
  } finally {
    db.close();
  }
}

const CSP = [
  "default-src 'self'",
  "script-src 'self'",
  "style-src 'self'",
  "img-src 'self' data: blob:",
  "connect-src 'self'",
  "object-src 'none'",
  "base-uri 'none'",
  "form-action 'self'",
].join('; ');

const CSS_DEMO = `
/* ---------- Versão de demonstração (gerado por scripts/build-demo.js) ---------- */
.demo-banner {
  background: #ffb703;
  color: #1b1b1b;
  text-align: center;
  padding: 8px 16px;
  font-size: 0.9rem;
  line-height: 1.4;
}
.demo-banner a {
  color: inherit;
  font-weight: 700;
  text-decoration: underline;
}
`;

function main() {
  const opt = args(process.argv.slice(2));
  const out = prepararSaida(opt.out);
  const pub = path.join(ROOT_DIR, 'public');

  // 1. Telas do cliente (o painel administrativo precisa do servidor e fica de fora).
  copiarPasta(pub, out, new Set(['admin']));
  fs.rmSync(path.join(out, 'js', 'admin'), { recursive: true, force: true });

  // 2. Dados do cardápio de exemplo e o cálculo de preços do servidor (o mesmo código).
  const demo = path.join(out, 'demo');
  fs.mkdirSync(demo);
  fs.writeFileSync(path.join(demo, 'dados.json'), JSON.stringify(dadosDaDemo(opt.base)));
  fs.copyFileSync(path.join(ROOT_DIR, 'server', 'services', 'pricing.js'), path.join(demo, 'pricing.js'));
  fs.copyFileSync(path.join(ROOT_DIR, 'server', 'services', 'option-rules.js'), path.join(demo, 'option-rules.js'));
  fs.copyFileSync(path.join(ROOT_DIR, 'scripts', 'demo', 'api.js'), path.join(demo, 'api.js'));

  // 3. Páginas: modo demonstração, caminhos com a base, política de segurança e aviso.
  const link = opt.repo ? ` <a href="${escapeAttr(opt.repo)}" rel="noopener">Ver o código no GitHub</a>` : '';
  const aviso =
    '<div class="demo-banner" role="note"><strong>Versão de demonstração.</strong> ' +
    'Os pedidos ficam só neste navegador: nada é enviado nem cobrado, e o andamento do pedido avança sozinho.' +
    `${link}</div>`;
  for (const file of arquivos(out, '.html')) {
    let s = fs.readFileSync(file, 'utf8');
    if (!s.includes('<html lang="pt-BR">') || !/<body>/.test(s) || !s.includes('<meta charset="UTF-8" />')) {
      throw new Error(`Estrutura inesperada em ${path.relative(out, file)}`);
    }
    s = s.replace('<html lang="pt-BR">', '<html lang="pt-BR" data-demo="1">');
    s = s.replace('<meta charset="UTF-8" />', `<meta charset="UTF-8" />\n    <meta http-equiv="Content-Security-Policy" content="${CSP}" />`);
    // O aviso entra antes do cabeçalho (depois do link "Pular para o cardápio", que deve ser o primeiro).
    s = s.includes('<header') ? s.replace('<header', `${aviso}\n    <header`) : s.replace('<body>', `<body>\n    ${aviso}`);
    fs.writeFileSync(file, comBase(s, opt.base, { html: true }));
  }

  // 4. Scripts do navegador: caminhos com a base.
  for (const file of arquivos(path.join(out, 'js'), '.js')) {
    fs.writeFileSync(file, comBase(fs.readFileSync(file, 'utf8'), opt.base, { html: false }));
  }
  fs.appendFileSync(path.join(out, 'css', 'style.css'), CSS_DEMO);
  fs.writeFileSync(path.join(out, '.nojekyll'), '');

  // 5. Conferência: nenhum caminho pode continuar apontando para a raiz do domínio.
  const sobras = [];
  for (const file of [...arquivos(out, '.html'), ...arquivos(path.join(out, 'js'), '.js')]) {
    const s = fs.readFileSync(file, 'utf8');
    const rx = file.endsWith('.html')
      ? /\b(?:href|src)="\/(?!\/)[^"]*"/g
      : /(['"`])\/(?:(?:img|css|js)\/|checkout\.html|pedido\.html|index\.html)[^'"`]*\1|href:\s*(['"`])\/\2/g;
    for (const m of s.matchAll(rx)) if (!m[0].includes(`="${opt.base}`)) sobras.push(`${path.relative(out, file)}: ${m[0]}`);
  }
  if (opt.base !== '/' && sobras.length) throw new Error(`Caminhos sem a base:\n${sobras.join('\n')}`);

  const total = JSON.parse(fs.readFileSync(path.join(demo, 'dados.json'), 'utf8')).menu.categories.flatMap((c) => c.products).length;
  console.log(`Demonstração gerada em ${out} (base ${opt.base}, ${total} produtos).`);
}

main();
