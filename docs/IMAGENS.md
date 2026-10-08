# Imagens do Desu Burguer

## Atualização (07/10/2026): ilustrações redesenhadas

Cada produto do cardápio de exemplo usa uma **ilustração própria** (desenho em SVG, em `public/img/ilustracoes/`),
sempre com o selo **"Imagem ilustrativa"**. São 60 desenhos de produtos e a arte do topo da página.

- **Estilo:** os desenhos têm volume (degradês), sombras suaves, brilho, textura leve e fundo escuro de estúdio.
  O estilo é o mesmo em todo o cardápio.
- **Combos:** combos e kids mostram os itens que a descrição promete. O Combo Casal ganhou desenho próprio, com 2 lanches.
- **Embalagens:** usam só a identidade da casa (selo "D", amarelo e preto, papel kraft). Não imitam nenhuma marca real.
- **Tamanho:** os arquivos têm entre 5 e 55 KB. O servidor envia compactado (gzip), então cada um chega ao navegador
  com cerca de 3 a 13 KB.
- **Não são fotos:** não foram geradas por IA (esta sessão não tinha gerador de imagens conectado). São desenhos
  vetoriais escritos em código e não representam o produto real servido.

No painel, em **Editar produto**, você escolhe a ilustração ou envia uma foto. A foto enviada sempre tem prioridade.

Para gerar os desenhos de novo (precisa de Python 3, sem bibliotecas extras):

```bash
python scripts/dev/gerar-ilustracoes.py
```

O gerador junta os módulos de `scripts/dev/ilustracoes/` (`estilo.py` é a base visual comum; `lanches.py`,
`acompanhamentos.py`, `bebidas.py`, `especiais.py`, `sobremesas.py` e `combos.py` são os desenhos). Antes de gravar,
ele confere se a lista bate com `server/services/illustrations.js`, se cada SVG é válido e se não há nada que a
política de segurança (CSP) bloquearia, como `<script>`, `<style>` ou imagens externas.

## Situação original

Nenhuma imagem foi encontrada no projeto, nem na pasta `Desu-burguer-estudo`, nem nos arquivos anexados.
As imagens geradas em outra conversa (ChatGPT) **não ficam acessíveis automaticamente**.
Enquanto não houver imagem, o cardápio mostra um ícone neutro com o texto **"Foto em breve"**.
Esse ícone não representa o produto.

## Imagens que você precisa fornecer

| # | Para quê | Onde aparece | Obrigatória? |
|---|---|---|---|
| 1 | **X-Bacon** (único produto do projeto original) | Cartão do cardápio e janela de personalização | Sim, para o cardápio ficar completo |
| 2 | Uma imagem para **cada produto novo** que você cadastrar | Cardápio | Recomendada |
| 3 | **Logotipo** da Desu Burguer (se existir) | Cabeçalho, no lugar do círculo com "D" | Opcional: hoje o logo é um "D" em CSS. Envie o arquivo e eu faço a troca |

Especificações recomendadas:

- Formato **JPG, PNG ou WebP** (SVG não é aceito no upload por segurança; para o logotipo, envie o arquivo e ele será integrado manualmente).
- Pelo menos **1000 px** no lado maior; proporção **4:3** ou **1:1** (a imagem não é cortada nem esticada: aparece inteira).
- Até **5 MB** por arquivo. Sem o `sharp` instalado, até 3 MB.
- Fundo e enquadramento do jeito que você aprovou: o sistema **não recorta** a imagem.

## Como adicionar

**Pelo painel (recomendado):**

1. Acesse `/admin/`.
2. Abra a aba **Cardápio** e clique em **Editar** no produto.
3. Escolha o arquivo em **Enviar nova imagem**.
4. Preencha o **texto alternativo**, uma descrição curta para quem usa leitor de tela (ex.: "X-Bacon com queijo derretido e bacon").
5. Deixe **desmarcado** "É foto real deste produto" quando a imagem for gerada por IA ou ilustrativa.

**Pela linha de comando** (útil para importar várias de uma vez):

```bash
npm run import-image -- --produto 1 --arquivo "C:\Users\voce\Downloads\x-bacon.png"
# acrescente --real somente se for FOTO REAL do produto
```

## Regras aplicadas automaticamente

- **Imagem ilustrativa:** por padrão toda imagem é marcada como ilustrativa e o cardápio mostra o selo **"Imagem ilustrativa"**.
  Imagens geradas por IA (como as do ChatGPT) devem continuar assim. Só desmarque quando for uma foto real do produto servido.
- **Otimização:** com o pacote opcional `sharp` instalado (`npm install`), cada envio vira duas versões WebP,
  uma de até 1200 px e uma miniatura de até 600 px. As duas mantêm a proporção, corrigem a rotação e removem
  metadados como a localização GPS. O navegador escolhe a versão adequada (`srcset`).
  Sem o `sharp`, o arquivo original é guardado como está, depois de validado.
- **Caminhos:** as imagens ficam em `data/uploads/products/` com nome aleatório e são servidas em `/uploads/products/...`.
  O mesmo caminho funciona em desenvolvimento e produção. Faça backup dessa pasta junto com o banco.
- **Imagem ausente ou com erro:** se o arquivo sumir ou falhar ao carregar, o site volta para o ícone "Foto em breve" em vez de mostrar uma imagem quebrada.
- **Trocar imagem:** o arquivo antigo é apagado automaticamente. Imagens aprovadas não são substituídas por nenhum processo automático.
