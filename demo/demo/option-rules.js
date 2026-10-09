// Regras de conferência das opções de personalização de um item.
// Módulo puro (sem banco e sem Node): usado pelo cálculo do pedido no servidor
// e pela versão de demonstração estática, que roda só no navegador.

/**
 * Confere as escolhas de um item. Devolve { options, extraCents, issues }.
 * Regras: a escolha precisa pertencer a um grupo do produto; grupo de escolha única
 * aceita no máximo 1; múltipla respeita o máximo; grupo obrigatório precisa de escolha.
 */
export function resolveItemOptions(product, optionIds, cat, index) {
  const issues = [];
  const byGroup = new Map();
  const allowed = new Set(cat.productGroups.get(product.id) || []);
  for (const cid of optionIds) {
    const choice = cat.choices.get(cid);
    const group = choice && cat.groups.get(choice.group_id);
    if (!choice || choice.archived || !group || group.archived || !allowed.has(group.id)) {
      issues.push({ index, code: 'opcao_invalida', message: `Uma opção de ${product.name} não está mais disponível.` });
      continue;
    }
    if (!choice.available) {
      issues.push({ index, code: 'opcao_indisponivel', message: `A opção "${choice.name}" está indisponível no momento.` });
    }
    if (!byGroup.has(group.id)) byGroup.set(group.id, []);
    byGroup.get(group.id).push(choice);
  }
  const options = [];
  for (const gid of cat.productGroups.get(product.id) || []) {
    const group = cat.groups.get(gid);
    if (!group || group.archived) continue;
    const hasChoices = [...cat.choices.values()].some((c) => c.group_id === gid && !c.archived);
    const chosen = byGroup.get(gid) || [];
    const max = group.kind === 'single' ? 1 : group.max_choices;
    if (group.required && hasChoices && chosen.length === 0) {
      issues.push({ index, code: 'opcao_obrigatoria', message: `Escolha "${group.name}" para ${product.name}.` });
    }
    if (max && chosen.length > max) {
      issues.push({ index, code: 'opcao_excesso', message: `Em "${group.name}" escolha no máximo ${max}.` });
    }
    for (const c of chosen) options.push({ groupName: group.name, choiceId: c.id, name: c.name, priceCents: c.price_cents });
  }
  const extraCents = options.reduce((s, o) => s + o.priceCents, 0);
  return { options, extraCents, issues };
}
