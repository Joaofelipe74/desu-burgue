// Selos que podem aparecer nos produtos (lista fechada, validada no servidor).
export const TAGS = {
  novo: 'Novo',
  vegetariano: 'Vegetariano',
  picante: 'Picante',
  compartilhar: 'Para compartilhar',
};

export const tagList = () => Object.entries(TAGS).map(([key, label]) => ({ key, label }));

/** Lê o JSON salvo no banco, ignorando valores que não estão na lista. */
export function parseTags(json) {
  try {
    const arr = JSON.parse(json || '[]');
    return Array.isArray(arr) ? arr.filter((t) => TAGS[t]) : [];
  } catch {
    return [];
  }
}
