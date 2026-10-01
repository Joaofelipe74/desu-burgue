# Imagens do Desu Burguer

## Situação atual

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
