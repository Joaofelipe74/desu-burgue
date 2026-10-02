// Ilustrações próprias (desenhos SVG em public/img/ilustracoes/), usadas quando
// o produto ainda não tem foto. Sempre exibidas com o selo "Imagem ilustrativa".
export const ILLUSTRATIONS = {
  hamburguer: 'Hambúrguer clássico',
  'hamburguer-bacon': 'Hambúrguer com bacon',
  'hamburguer-salada': 'Hambúrguer com salada',
  'hamburguer-ovo': 'Hambúrguer com ovo',
  'hamburguer-tudo': 'Hambúrguer completo',
  'smash-duplo': 'Smash duplo',
  frango: 'Sanduíche de frango',
  veggie: 'Hambúrguer vegetariano',
  combo: 'Combo (lanche, batata e bebida)',
  'combo-familia': 'Combo família',
  batata: 'Batata frita',
  'batata-cheddar': 'Batata com cheddar',
  'onion-rings': 'Anéis de cebola',
  nuggets: 'Nuggets',
  'refrigerante-lata': 'Refrigerante lata',
  'refrigerante-2l': 'Refrigerante garrafa',
  suco: 'Suco',
  agua: 'Água',
  milkshake: 'Milk-shake',
  brownie: 'Brownie',
  'petit-gateau': 'Petit gâteau',
  pudim: 'Pudim',
};

export const illustrationList = () => Object.entries(ILLUSTRATIONS).map(([key, label]) => ({ key, label }));
