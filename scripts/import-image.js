// Associa uma imagem do seu computador a um produto (alternativa ao upload pelo painel).
// Uso: npm run import-image -- --produto 1 --arquivo "C:\caminho\x-bacon.png" [--real]
//   --real  marque só se for FOTO REAL do produto. Sem isso, o site mostra "Imagem ilustrativa".
import fs from 'node:fs';
import path from 'node:path';
import { buildConfig, loadEnvFile } from '../server/config.js';
import { openDatabase } from '../server/db.js';
import { getSharp, removeImageFiles, storeProductImage } from '../server/services/images.js';
import { getProduct, setProductImage } from '../server/services/menu.js';

loadEnvFile();
const arg = (name) => {
  const i = process.argv.indexOf(name);
  return i > 0 ? process.argv[i + 1] : undefined;
};
const productId = Number(arg('--produto'));
const file = arg('--arquivo');
const isReal = process.argv.includes('--real');

if (!Number.isInteger(productId) || !file) {
  console.error('Uso: npm run import-image -- --produto <id> --arquivo <caminho da imagem> [--real]');
  process.exit(1);
}
const config = buildConfig();
const db = openDatabase(path.join(config.dataDir, 'desu.db'));
try {
  const product = getProduct(db, productId);
  const buf = fs.readFileSync(file);
  if (buf.length > config.maxImageBytes) throw new Error('Arquivo maior que o limite configurado (MAX_IMAGE_MB).');
  const dir = path.join(config.dataDir, 'uploads', 'products');
  const image = await storeProductImage(buf, dir);
  setProductImage(db, productId, image);
  db.prepare('UPDATE products SET image_is_illustrative = ? WHERE id = ?').run(isReal ? 0 : 1, productId);
  removeImageFiles(dir, product.image_file, product.image_thumb_file);
  console.log(`Imagem associada a "${product.name}" (${image.width}×${image.height}).`);
  console.log(image.optimized ? 'Otimizada para WebP.' : `Sem otimização (sharp ${getSharp() ? 'ok' : 'não instalado'}).`);
  console.log(isReal ? 'Marcada como foto real.' : 'Marcada como imagem ilustrativa.');
} catch (err) {
  console.error(`Erro: ${err.publicMessage || err.message}`);
  process.exitCode = 1;
} finally {
  db.close();
}
