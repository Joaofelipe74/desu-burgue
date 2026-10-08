# Combos, kids e arte da home: cenas montadas com os componentes de
# lanches.py, acompanhamentos.py e bebidas.py (que não são alterados aqui).
#
# Regras da composição (tela 400 x 300):
#   - luz principal de cima à esquerda, luz de recorte à direita (já nos componentes);
#   - fileira de trás mais alta e menor, fileira da frente mais baixa e maior,
#     desenhadas de trás para frente, cada peça com a sua sombra no chão;
#   - o lanche é o protagonista; batata e bebida dão apoio;
#   - a arte da home (hero) não tem fundo: fica sobre a seção escura do site.
import math
import re

from .estilo import Arte, fundo, sombra, suave, n, CX, MARCA
from .lanches import hamburguer, C, carne, queijo, alface, tomate
from .acompanhamentos import caixa_batata, nuggets_grupo, pote_molho
from .bebidas import lata, garrafa_pet, copo_refri, caixinha_suco

CHAO = 252          # linha do chão em que os componentes de lanches.py são montados
SUCO_UVA = '#8e4fc3'
SUCO_LARANJA = '#f08a12'


# ---------------------------------------------------------------- utilitários

def _num1(m):
    v = round(float(m.group(0)), 1)
    t = f'{v:.1f}'.rstrip('0').rstrip('.')
    return '0' if t in ('-0', '') else t


def _arred(texto):
    return re.sub(r'-?\d+\.\d+', _num1, texto)


_GEOM = re.compile(r' (cx|cy|r|rx|ry|x|y|width|height)="(-?[\d.]+)"')


def _caminho(d):
    """Caminho em 1 casa decimal e sem separadores dispensáveis ("3,-4" -> "3-4", "5 C" -> "5C")."""
    d = re.sub(r'[ ,](?=-)', '', _arred(d))
    return re.sub(r' (?=[A-Za-z])', '', d)


_ZERO = re.compile(r'(^|[\s,A-Za-z"(])(-?)0\.(\d)')


def _svg(a, corpo):
    """Fecha o SVG com menos bytes e o mesmo desenho.

    Coordenadas de caminhos e formas básicas em 1 casa decimal (degradês e opacidades
    ficam intactos), deslocamentos em 1 casa e números sem o zero à esquerda (0.45 -> .45).
    """
    svg = a.svg(corpo)
    svg = re.sub(r' d="([^"]*)"', lambda m: ' d="' + _caminho(m.group(1)) + '"', svg)
    svg = re.sub(r'translate\(([^)]*)\)', lambda m: f'translate({_arred(m.group(1))})', svg)
    svg = re.sub(r'<(?:ellipse|circle|rect)\b[^>]*>', lambda m: _GEOM.sub(lambda g: f' {g.group(1)}="{_arred(g.group(2))}"', m.group(0)), svg)
    return _ZERO.sub(r'\1\2.\3', svg)


# gergelim do pão de lanches.py: cada semente é um <g> com 3 elipses (~250 bytes)
_SEMENTE = re.compile(
    r'<g transform="translate\((-?[\d.]+),(-?[\d.]+)\) rotate\((-?[\d.]+)\)">'
    r'<ellipse cx="\.9" cy="1\.4" rx="([\d.]+)" ry="2\.3" fill="#3a1a06" opacity="\.3"/>'
    r'<ellipse rx="[\d.]+" ry="2\.3" fill="(url\(#\w+\))"/>'
    r'<ellipse cx="-?[\d.]+" cy="-\.8" rx="[\d.]+" ry="\.8" fill="#fff" opacity="\.85"/></g>')


def _sementes(a, corpo):
    """Troca cada semente de gergelim por um <use> de uma semente-modelo, esticada na largura.

    Mesmo desenho (só a sombrinha de cada semente desloca uns décimos de unidade);
    economiza ~4 KB por pão. Se o formato do pão mudar, o texto passa sem alteração.
    """
    def troca(m):
        x, y, rot, rx, cor = m.groups()
        i = a._def(('combo-semente', cor), 's', lambda i: (
            f'<g id="{i}"><ellipse cx=".9" cy="1.4" rx="4.6" ry="2.3" fill="#3a1a06" opacity=".3"/>'
            f'<ellipse rx="4.6" ry="2.3" fill="{cor}"/>'
            f'<ellipse cx="-1.38" cy="-.8" rx="1.93" ry=".8" fill="#fff" opacity=".85"/></g>'))
        sx = float(rx) / 4.6
        esc = '' if abs(sx - 1) < .005 else f' scale({n(sx)},1)'
        return f'<use href="#{i}" transform="translate({_arred(x)},{_arred(y)}) rotate({round(float(rot))}){esc}"/>'
    return _SEMENTE.sub(troca, corpo)


def _ref(a, d):
    """Guarda um caminho nos <defs> para reusar com <use>. Devolve o id."""
    d = _arred(d)
    return a._def(('combo-ref', d), 'p', lambda i: f'<path id="{i}" d="{d}"/>')


def bacon(a, y, w, semente=7):
    """Mesmo desenho do bacon de lanches.py, com cada tira guardada uma vez nos <defs>.

    Lá cada fita é redesenhada 7 vezes (sombra, bordas, gordura, brilho) com a curva
    deslocada na vertical; aqui a curva é a mesma e o deslocamento vira translate.
    Resultado idêntico com ~1/6 dos bytes (importa nas cenas com vários lanches).
    """
    x0, x1 = CX - w / 2 - 14, CX + w / 2 + 14
    s = ''
    for base_y, fase, ini, fim in ((y - 13, 0, x0, x1), (y - 6, 2.4, x0 + 8, x1 - 4)):
        pts = []
        x = ini
        while x <= fim + .1:
            pts.append((x, base_y + 4.5 * math.sin((x - x0) / 15 + fase)))
            x += 6
        i = _ref(a, suave(pts, fechado=False))

        def fita(dy, cor, larg, extra=''):
            t = f' transform="translate(0,{n(dy)})"' if dy else ''
            return f'<use href="#{i}" stroke="{cor}" stroke-width="{n(larg)}"{extra}{t}/>'
        s += ('<g fill="none" stroke-linecap="round">'
              + fita(.6, '#000', 13, f' stroke-opacity=".35" filter="{a.desfoque(1.5)}"')
              + fita(0, '#4a1407', 12) + fita(0, '#a3361f', 10) + fita(-2.2, '#d1653f', 3.6)
              + fita(1.4, '#f5bd9b', 2.2) + fita(3.6, '#6e2210', 1.6)
              + fita(-3.8, '#fff', 1, ' stroke-opacity=".35"') + '</g>')
    return s, 16


X_BACON = [C(carne), C(queijo), C(bacon)]
X_BURGUER = [C(carne), C(queijo), C(tomate), C(alface)]
X_KIDS = [C(carne), C(queijo)]


def _lanche_def(a, nome, camadas, semente=1, pao='classico'):
    """Lanche inteiro guardado nos <defs> (cenas com vários iguais reusam com <use>)."""
    def c(i):
        corpo, _ = hamburguer(a, camadas, base=CHAO, pao=pao, semente=semente)
        return f'<g id="{i}">{_sementes(a, corpo)}</g>'
    return a._def(('combo-lanche', nome, semente, pao), 'h', c)


def _pos(cx, base, e):
    return f'translate({n(cx - CX * e)},{n(base - CHAO * e)}) scale({n(e)})'


LANCHES = {'xbacon': X_BACON, 'xburguer': X_BURGUER, 'kids': X_KIDS}

# meia-largura (na altura do chão) e altura de cada peça em escala 1
MEDIDAS = dict(lanche=(108, 157), batata=(52, 182), lata=(36, 156), pet=(37, 224), copo=(36, 196),
               suco=(29, 118), nuggets=(56, 67), pote=(34, 52))


def _distancia(a):
    """Fileira de trás um pouco mais apagada: separa os planos sem desfocar."""
    def c(i):
        f = '<feFuncR type="linear" slope=".84"/><feFuncG type="linear" slope=".84"/><feFuncB type="linear" slope=".86"/>'
        return (f'<filter id="{i}" x="-30%" y="-30%" width="160%" height="160%" color-interpolation-filters="sRGB">'
                f'<feComponentTransfer>{f}</feComponentTransfer></filter>')
    return f'url(#{a._def(("combo-distancia",), "f", c)})'


def peca(a, tipo, cx, base, e, atras=False, sombra_forca=1.0, **op):
    """Uma peça da cena com a sua sombra no chão. `tipo`: lanche (xbacon/xburguer/kids),
    batata, lata, pet, copo, suco, nuggets ou pote."""
    if tipo in LANCHES:
        camadas = LANCHES[tipo]
        if op.get('reuso'):
            corpo = f'<use href="#{_lanche_def(a, tipo, camadas, op.get("semente", 1))}" transform="{_pos(cx, base, e)}"/>'
        else:
            corpo, _ = hamburguer(a, camadas, base=CHAO, semente=op.get('semente', 1))
            corpo = f'<g transform="{_pos(cx, base, e)}">{_sementes(a, corpo)}</g>'
        medida = 'lanche'
    else:
        medida = tipo
        corpo = {
            'batata': lambda: caixa_batata(a, cx, base, e),
            'lata': lambda: lata(a, cx, base, e),
            'pet': lambda: garrafa_pet(a, cx, base, e, 2),
            'copo': lambda: copo_refri(a, cx, base, e),
            'suco': lambda: caixinha_suco(a, cx, base, e, op.get('cor', SUCO_UVA)),
            'nuggets': lambda: nuggets_grupo(a, cx, base, e, op.get('qtd', 6)),
            'pote': lambda: pote_molho(a, cx, base, e, op.get('molho', 'barbecue')),
        }[tipo]()
    if atras:
        corpo = f'<g filter="{_distancia(a)}">{corpo}</g>'
    rx = MEDIDAS[medida][0] * e
    return sombra(a, cx + 2 * e, base, rx, max(4, rx * .085), sombra_forca) + corpo


# silhueta aproximada do corpo de cada peça (x0, y0, x1, y1) em escala 1, relativa a (cx, base):
# é onde a sombra projetada pela peça da frente pode cair.
CORPO = dict(lata=(-38, -134, 38, -6), pet=(-40, -150, 40, -6), copo=(-44, -136, 44, -4),
             suco=(-28.5, -80, 30, 0), batata=(-62, -112, 62, 0), lanche=(-118, -126, 118, 0))


def sombra_projetada(a, alvo, x, y, rx, ry, op=.42):
    """Sombra que a peça da frente joga na de trás (luz de cima à esquerda), recortada no corpo do alvo."""
    tipo, cx, base, e = alvo
    x0, y0, x1, y1 = CORPO['lanche' if tipo in LANCHES else tipo]
    clip = a.recorte(f'M{n(cx + x0 * e)},{n(base + y0 * e)} H{n(cx + x1 * e)} V{n(base + y1 * e)} H{n(cx + x0 * e)}Z')
    return (f'<g clip-path="{clip}"><ellipse cx="{n(x)}" cy="{n(y)}" rx="{n(rx)}" ry="{n(ry)}" fill="#000" '
            f'opacity="{n(op)}" filter="{a.desfoque(6)}"/></g>')


def cena(a, pecas):
    """Peças em ordem de desenho (de trás para frente): (tipo, cx, base, escala, {opções}).

    Opções: atras=True (fileira de trás), projeta=(índices das peças de trás que recebem a
    sombra desta), reuso=True (lanches iguais desenhados uma vez só), cor, molho, qtd.
    """
    s = ''
    for p in pecas:
        tipo, cx, base, e = p[:4]
        op = dict(p[4]) if len(p) > 4 else {}
        for k in op.pop('projeta', ()):
            # a sombra cai à direita da peça, do meio da altura até o chão do alvo
            alvo = pecas[k][:4]
            meia, alt = MEDIDAS['lanche' if tipo in LANCHES else tipo]
            s += sombra_projetada(a, alvo, cx + meia * e * .98, base - alt * e * .3, 20 * e + 6, alt * e * .36)
        s += peca(a, tipo, cx, base, e, **op)
    return s


# ---------------------------------------------------------------- cenas

def _combo():
    a = Arte('Ilustração de combo com hambúrguer, batata e refrigerante')
    return _svg(a, fundo(a) + cena(a, [
        ('batata', 92, 226, .66, dict(atras=True)),
        ('lata', 318, 228, .88, dict(atras=True)),
        ('xbacon', 204, 262, .84, dict(projeta=(1,))),
    ]))


def _combo_casal():
    a = Arte('Ilustração de combo com dois hambúrgueres, batata e refrigerante 2 litros')
    return _svg(a, fundo(a) + cena(a, [
        ('batata', 86, 230, .82, dict(atras=True)),
        ('pet', 336, 230, .8, dict(atras=True)),
        ('xbacon', 162, 254, .64, dict(reuso=True)),
        ('xbacon', 252, 272, .7, dict(reuso=True, projeta=(1,))),
    ]))


def _combo_familia():
    a = Arte('Ilustração de combo família com quatro hambúrgueres, batata e refrigerante 2 litros')
    return _svg(a, fundo(a) + cena(a, [
        ('batata', 162, 214, .72, dict(atras=True)),
        ('pet', 262, 212, .72, dict(atras=True)),
        ('xburguer', 100, 236, .48, dict(reuso=True)),
        ('xburguer', 300, 236, .48, dict(reuso=True)),
        ('xburguer', 160, 272, .58, dict(reuso=True)),
        ('xburguer', 248, 274, .58, dict(reuso=True, projeta=(3,))),
    ]))


def _kids():
    a = Arte('Ilustração de combo infantil com mini hambúrguer')
    return _svg(a, fundo(a) + cena(a, [
        ('batata', 92, 226, .62, dict(atras=True)),
        ('suco', 314, 226, 1.14, dict(atras=True, cor=SUCO_UVA)),
        ('kids', 204, 262, .8, dict(projeta=(1,))),
    ]))


def _kids_nuggets():
    a = Arte('Ilustração de combo infantil com nuggets')
    return _svg(a, fundo(a) + cena(a, [
        ('batata', 86, 224, .6, dict(atras=True)),
        ('suco', 328, 226, 1.0, dict(atras=True, cor=SUCO_LARANJA)),
        ('nuggets', 194, 262, 1.6),
        ('pote', 264, 278, .8, dict(molho='barbecue')),
    ]))


def _hero():
    a = Arte('Ilustração de hambúrguer com batata frita e refrigerante', fundo=False)
    # poça de luz quente no chão: dá onde as sombras aparecerem sobre o fundo escuro da home
    luz = a.radial([(0, MARCA, .2), (.55, MARCA, .07), (1, MARCA, 0)])
    s = fundo(a) + f'<ellipse cx="203" cy="250" rx="186" ry="30" fill="{luz}"/>'
    return _svg(a, s + cena(a, [
        ('batata', 89, 226, .82),
        ('copo', 323, 226, .9),
        ('xbacon', 203, 260, .94, dict(projeta=(1,), sombra_forca=1.3)),
    ]))


def gerar():
    A = {}
    A['combo'] = _combo()
    A['combo-casal'] = _combo_casal()
    A['combo-familia'] = _combo_familia()
    A['kids'] = _kids()
    A['kids-nuggets'] = _kids_nuggets()
    A['hero'] = _hero()
    return A
