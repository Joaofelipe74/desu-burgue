# Gera as ilustrações dos produtos (desenhos originais em SVG) em public/img/ilustracoes/.
#
# Os desenhos ficam em módulos dentro de scripts/dev/ilustracoes/:
#   estilo.py          base visual comum (fundo, sombras, brilhos, degradês, selo "D")
#   lanches.py         hambúrgueres, smash e premium
#   acompanhamentos.py batatas, porções e molhos
#   bebidas.py         refrigerantes, água, sucos, milk-shake e açaí
#   especiais.py       hot dogs e sanduíches
#   sobremesas.py      sobremesas
#   combos.py          combos, kids e a arte do topo da página (hero)
#
# Uso:  python scripts/dev/gerar-ilustracoes.py
# São desenhos ilustrativos: no site aparecem sempre com o selo "Imagem ilustrativa".
import os
import re
import sys
from xml.dom import minidom

AQUI = os.path.dirname(os.path.abspath(__file__))
RAIZ = os.path.abspath(os.path.join(AQUI, '..', '..'))
SAIDA = os.path.join(RAIZ, 'public', 'img', 'ilustracoes')
LISTA_JS = os.path.join(RAIZ, 'server', 'services', 'illustrations.js')

sys.path.insert(0, AQUI)
from ilustracoes import acompanhamentos, bebidas, combos, especiais, lanches, sobremesas  # noqa: E402

MODULOS = (lanches, acompanhamentos, bebidas, especiais, sobremesas, combos)
PROIBIDO = re.compile(r'<style|style=|<script|<image|<foreignObject|javascript:|xlink:href="(?!#)|href="(?!#)|class=', re.I)
LIMITE_BYTES = 60 * 1024


def chaves_esperadas():
    """Chaves cadastradas em server/services/illustrations.js, mais a arte do topo."""
    texto = open(LISTA_JS, encoding='utf-8').read()
    bloco = texto.split('export const ILLUSTRATIONS = {', 1)[1].split('};', 1)[0]
    chaves = re.findall(r"^\s*'?([a-z0-9-]+)'?\s*:", bloco, re.M)
    return set(chaves) | {'hero'}


def main():
    artes = {}
    for mod in MODULOS:
        for chave, svg in mod.gerar().items():
            if chave in artes:
                sys.exit(f'Ilustração repetida: {chave} ({mod.__name__})')
            artes[chave] = svg

    esperadas = chaves_esperadas()
    faltando = sorted(esperadas - artes.keys())
    sobrando = sorted(artes.keys() - esperadas)
    if faltando or sobrando:
        sys.exit(f'Lista diferente de illustrations.js. Faltando: {faltando}. Sem cadastro: {sobrando}.')

    problemas = []
    for chave, svg in artes.items():
        if PROIBIDO.search(svg):
            problemas.append(f'{chave}: contém marcação proibida pela CSP')
        if len(svg.encode('utf-8')) > LIMITE_BYTES:
            problemas.append(f'{chave}: maior que {LIMITE_BYTES // 1024} KB')
        try:
            minidom.parseString(svg)
        except Exception as erro:  # noqa: BLE001
            problemas.append(f'{chave}: SVG inválido ({erro})')
    if problemas:
        sys.exit('\n'.join(problemas))

    os.makedirs(SAIDA, exist_ok=True)
    total = 0
    for chave in sorted(artes):
        dados = artes[chave].encode('utf-8')
        total += len(dados)
        with open(os.path.join(SAIDA, chave + '.svg'), 'wb') as f:
            f.write(dados)

    extras = sorted(f for f in os.listdir(SAIDA) if f.endswith('.svg') and f[:-4] not in artes)
    print(f'{len(artes)} ilustrações geradas em {os.path.relpath(SAIDA, RAIZ)} ({total // 1024} KB no total).')
    if extras:
        print('Arquivos que não vieram do gerador (não foram apagados):', ', '.join(extras))


if __name__ == '__main__':
    main()
