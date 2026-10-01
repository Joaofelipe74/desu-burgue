// Apaga nome, telefone, endereço e observações de pedidos FINALIZADOS
// (concluídos ou cancelados) há mais de N dias. Valores e itens são mantidos.
// Uso: npm run purge-personal-data -- --days 90
// O prazo é uma decisão sua (LGPD: guardar só pelo tempo necessário).
import path from 'node:path';
import { buildConfig, loadEnvFile } from '../server/config.js';
import { openDatabase } from '../server/db.js';
import { purgePersonalData } from '../server/services/orders.js';

loadEnvFile();
const i = process.argv.indexOf('--days');
const days = i > 0 ? Number(process.argv[i + 1]) : NaN;
if (!Number.isInteger(days) || days < 1) {
  console.error('Informe o prazo em dias. Exemplo: npm run purge-personal-data -- --days 90');
  process.exit(1);
}
const config = buildConfig();
const db = openDatabase(path.join(config.dataDir, 'desu.db'));
const n = purgePersonalData(db, days);
db.close();
console.log(`Dados pessoais removidos de ${n} pedido(s) finalizado(s) há mais de ${days} dias.`);
