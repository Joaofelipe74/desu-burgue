# Acompanhamentos: batatas, mandioca, onion rings, nuggets, iscas, porção mista e molhos.
#
# Além das ilustrações do cardápio, expõe componentes reutilizáveis (combos e kids):
#   caixa_batata(a, cx, base, escala=1.0, cheddar=False)   batatas na caixinha de papel kraft
#   nuggets_grupo(a, cx, base, escala=1.0, qtd=6)           montinho de nuggets (sem prato)
#   pote_molho(a, cx, base, escala=1.0, molho='maionese')   potinho de molho
# Os componentes desenham centrados em `cx`, apoiados na linha do chão `base`,
# sem fundo e sem sombra no chão (quem monta a cena desenha a sombra).
import math
import re

from .estilo import (Arte, fundo, sombra, realce, suave, rng, n, selo_marca, CX, MARCA, KRAFT)

CHAO = 252


# ---------------------------------------------------------------- utilitários

def _num1(m):
    v = round(float(m.group(0)), 1)
    t = f'{v:.1f}'.rstrip('0').rstrip('.')
    return '0' if t in ('-0', '') else t


def _svg(a, corpo):
    """Fecha o SVG arredondando os caminhos (d="...") para 1 casa decimal: mesmo desenho, menos bytes."""
    svg = a.svg(corpo)
    return re.sub(r' d="([^"]*)"', lambda m: ' d="' + re.sub(r'-?\d+\.\d+', _num1, m.group(1)) + '"', svg)


def _grupo(cx, base, escala, corpo):
    t = f'translate({n(cx)},{n(base)})' + (f' scale({n(escala)})' if escala != 1 else '')
    return f'<g transform="{t}">{corpo}</g>'


def _ref(a, d, furado=False):
    """Guarda um caminho nos <defs> para reusar com <use> (economiza bytes). Devolve o id."""
    extra = ' fill-rule="evenodd" clip-rule="evenodd"' if furado else ''
    d = re.sub(r'-?\d+\.\d+', _num1, d)
    return a._def(('ref', d, furado), 'p', lambda i: f'<path id="{i}" d="{d}"{extra}/>')


def _use(i, **at):
    return f'<use href="#{i}"' + ''.join(f' {k.replace("_", "-")}="{v}"' for k, v in at.items()) + '/>'


def _recorte_ref(a, i):
    """clipPath que reusa um caminho guardado com _ref."""
    def c(cid):
        return f'<clipPath id="{cid}"><use href="#{i}"/></clipPath>'
    return f'url(#{a._def(("clipref", i), "c", c)})'


CROSTAS = {
    # frequência do ruído, relevo, k1 (multiplica), k2 (cor original)
    'empanado': ('.24', 1.6, .66, .36),
    'anel': ('.26', 1.6, .66, .36),
    'gomo': ('.22', 1.2, .64, .38),
    'mandioca': ('.18', .8, .6, .42),
}


def _crosta(a, tipo='empanado'):
    """Relevo de empanado: ruído iluminado de cima à esquerda, multiplicado sobre a cor."""
    freq, relevo, k1, k2 = CROSTAS[tipo]

    def c(i):
        return (f'<filter id="{i}" x="-5%" y="-5%" width="110%" height="110%" color-interpolation-filters="sRGB">'
                f'<feTurbulence type="fractalNoise" baseFrequency="{freq}" numOctaves="3" seed="7" result="n"/>'
                f'<feDiffuseLighting in="n" surfaceScale="{n(relevo)}" diffuseConstant="1.2" lighting-color="#fff" result="l">'
                f'<feDistantLight azimuth="225" elevation="60"/></feDiffuseLighting>'
                f'<feComposite in="SourceGraphic" in2="l" operator="arithmetic" k1="{n(k1)}" k2="{n(k2)}" k3="0" k4="0"/></filter>')
    return f'url(#{a._def(("crosta", tipo), "e", c)})'


def _forma(cx, cy, rx, ry, pontos=10, var=.12, semente=1, giro=0, curva=0, crocante=False):
    """Contorno orgânico em volta de uma elipse girada `giro` graus (curva = arqueamento)."""
    r = rng(semente)
    g = math.radians(giro)
    cg, sg = math.cos(g), math.sin(g)
    pts = []
    for i in range(pontos):
        t = 2 * math.pi * i / pontos
        if crocante:
            f = 1 + r.uniform(.25, 1) * var * (1 if i % 2 else -1)
        else:
            f = 1 + r.uniform(-var, var)
        x = math.cos(t) * rx * f
        y = math.sin(t) * ry * f + curva * ((x / rx) ** 2 - .4)
        pts.append((cx + x * cg - y * sg, cy + x * sg + y * cg))
    return suave(pts)


def _elipse_irregular(cx, cy, rx, ry, giro, var, r, pontos=22):
    g = math.radians(giro)
    cg, sg = math.cos(g), math.sin(g)
    pts = []
    for i in range(pontos):
        t = 2 * math.pi * i / pontos
        f = 1 + r.uniform(-var, var)
        x, y = math.cos(t) * rx * f, math.sin(t) * ry * f
        pts.append((cx + x * cg - y * sg, cy + x * sg + y * cg))
    return suave(pts)


# ---------------------------------------------------------------- batata frita

FRITAS = (
    [(0, '#fff5c4'), (.16, '#ffe07a'), (.5, '#fcc844'), (.54, '#eeab2c'), (1, '#c0781a')],
    [(0, '#ffeca2'), (.16, '#fed35c'), (.5, '#f5b838'), (.54, '#e09624'), (1, '#a86414')],
    [(0, '#ffe08c'), (.18, '#f7bd4a'), (.5, '#e99d2c'), (.54, '#cf7f1e'), (1, '#8e4c0e')],
)


def _frita_def(a, tom):
    """Palito-modelo (12 x 100, base em y=0) guardado nos <defs>; cada batata é um <use> escalado."""
    corpo = a.linear(FRITAS[tom], 0, 0, 1, 0)
    ponta = a.linear([(0, '#8a4610', .6), (1, '#8a4610', 0)])
    sombra_f = a.desfoque(1.5)

    def c(i):
        return (f'<g id="{i}">'
                f'<rect x="-4" y="-98" width="12" height="100" rx="3.6" fill="#3a1600" opacity=".34" filter="{sombra_f}"/>'
                f'<rect x="-6" y="-100" width="12" height="100" rx="3.6" fill="{corpo}"/>'
                f'<rect x="-6" y="-100" width="12" height="17" rx="3.6" fill="{ponta}"/>'
                f'<rect x="-4.3" y="-97" width="1.4" height="92" rx=".7" fill="#fff" opacity=".32"/></g>')
    return a._def(('frita', tom), 'b', c)


def _frita(a, x, y, comp, larg, ang, tom=0):
    """Palito de batata. (x, y) = ponta de baixo; cresce para cima, girado `ang` graus."""
    return _use(_frita_def(a, tom), transform=f'translate({n(x)},{n(y)}) rotate({n(ang)}) scale({n(larg / 12)},{n(comp / 100)})')


def _frita_centro(a, x, y, comp, larg, ang, tom=0):
    t = math.radians(ang)
    return _frita(a, x - comp / 2 * math.sin(t), y + comp / 2 * math.cos(t), comp, larg, ang, tom)


def _frita_solta(a, x, y, comp, ang, larg=12, tom=1):
    """Batata caída na mesa, com sombra própria."""
    t = math.radians(ang)
    dx, dy = math.sin(t) * comp / 2, -math.cos(t) * comp / 2
    s = (f'<path d="M{n(x - dx)},{n(y - dy + 3)} L{n(x + dx)},{n(y + dy + 3)}" stroke="#000" stroke-width="{n(larg * .9)}" '
         f'stroke-linecap="round" opacity=".6" filter="{a.desfoque(2.4)}"/>')
    return s + _frita_centro(a, x, y, comp, larg, ang, tom)


def _monte_fritas(a, cx, chao, rx, alt, qtd, semente, larg=12, comp=(52, 76), fundo_y=8):
    """Monte de batatas deitadas, visto de 3/4: camadas de baixo (mais escuras) primeiro."""
    r = rng(semente)
    itens = []
    while len(itens) < qtd:
        lv = r.random()
        w = math.sqrt(1 - lv * lv)
        if r.random() > w * 1.15:
            continue
        u = r.uniform(-1, 1)
        x = cx + u * rx * w
        y = chao - lv * alt + r.uniform(-1, 1) * fundo_y * (1 - lv) + u * u * alt * .18 * (1 - lv)
        ang = 90 + r.uniform(-58, 58) + u * 18
        c = r.uniform(*comp) * (.72 + .28 * abs(math.sin(math.radians(ang))))
        tom = r.choice((1, 2, 2)) if lv < .3 else (r.choice((0, 1, 1)) if lv < .65 else r.choice((0, 0, 1)))
        itens.append((round(lv * 5), y, x, c, ang, tom))
    itens.sort(key=lambda it: (it[0], it[1]))
    return ''.join(_frita_centro(a, x, y, c, larg, ang, tom) for _, y, x, c, ang, tom in itens)


def caixa_batata(a, cx, base, escala=1.0, cheddar=False):
    """Batatas na caixinha de papel kraft da casa (caixa ~130 de largura; com as batatas ~156 x 182 em escala 1)."""
    r = rng(23)
    s = ''
    tras = 'M-61,-110 C-38,-127 38,-127 61,-110 L50,-30 H-50 Z'
    s += f'<path d="{tras}" fill="{a.linear([(0, "#8a6236"), (1, "#3e2712")])}"/>'
    s += '<path d="M-61,-110 C-38,-127 38,-127 61,-110" fill="none" stroke="#ead2aa" stroke-width="1.4" stroke-linecap="round"/>'
    for fila, (qtd, alt, abre) in enumerate([(8, 178, 47), (7, 166, 44), (6, 152, 38)]):
        for i in range(qtd):
            u = (i + .5) / qtd * 2 - 1
            x = u * abre + r.uniform(-3, 3)
            ang = u * 15 + r.uniform(-4, 4)
            topo = alt - abs(u) * 18 + r.uniform(-10, 10)
            comp = (topo - 40) / math.cos(math.radians(ang))
            tom = r.choice((0, 1, 1, 2)) if fila == 0 else r.choice((0, 0, 0, 1))
            s += _frita(a, x, -40, comp, 12.5, ang, tom)
    # sombra que a borda da frente projeta nas batatas
    s += (f'<path d="M-64,-113 C-32,-93 32,-93 64,-113 V-138 C32,-118 -32,-118 -64,-138 Z" '
          f'fill="{a.linear([(0, "#2a1000", 0), (1, "#2a1000", .45)])}"/>')
    frente = 'M-65,-113 C-32,-93 32,-93 65,-113 L50,-3 Q49,0 46,0 H-46 Q-49,0 -50,-3 Z'
    s += f'<path d="{frente}" fill="{a.linear([(0, KRAFT[0]), (.55, KRAFT[1]), (1, KRAFT[2])], 0, 0, 1, 0)}" filter="{a.textura("fino")}"/>'
    s += f'<g clip-path="{a.recorte(frente)}">'
    s += f'<rect x="-66" y="-116" width="132" height="117" fill="{a.linear([(0, "#fff", .16), (.3, "#fff", 0), (.7, "#000", 0), (1, "#000", .3)])}"/>'
    s += f'<rect x="-66" y="-42" width="132" height="43" fill="{a.linear([(0, "#2c2826"), (1, "#141211")])}"/>'
    s += f'<rect x="-66" y="-46" width="132" height="4" fill="{MARCA}"/>'
    s += '<path d="M-52,-106 L-41,-2" stroke="#fff" stroke-opacity=".28" stroke-width="1.2"/>'
    s += '<path d="M52,-106 L41,-2" stroke="#000" stroke-opacity=".22" stroke-width="1.2"/>'
    s += f'<path d="M64.5,-112 L49.5,-4" stroke="#ffe4b8" stroke-opacity=".55" stroke-width="3" filter="{a.desfoque(1.2)}"/>'
    s += '</g>'
    s += '<path d="M-65,-113 C-32,-93 32,-93 65,-113" fill="none" stroke="#f6e2bf" stroke-width="1.6" stroke-linecap="round"/>'
    s += selo_marca(a, 0, -68, 16)
    s += realce(a, -40, -76, 6, 22, rot=8, op=.14, blur=4)
    if cheddar:
        s += _cheddar_caixa(a, r)
    return _grupo(cx, base, escala, s)


# ---------------------------------------------------------------- cheddar e bacon

CHEDDAR = [(0, '#ffd877'), (.45, '#ffae2c'), (1, '#dc790b')]


def _cheddar_poca(a, pts, brilho):
    """Cobertura de cheddar: mancha com sombra, contorno e brilhos."""
    d = suave(pts, t=.85)
    s = f'<path d="{d}" fill="#5a2a00" opacity=".4" transform="translate(2,4)" filter="{a.desfoque(2.5)}"/>'
    s += f'<path d="{d}" fill="{a.radial(CHEDDAR, cx=.4, cy=.3, r=.8)}"/>'
    s += f'<path d="{d}" fill="none" stroke="#b85c00" stroke-opacity=".3" stroke-width="1"/>'
    bx, by, bw = brilho
    s += realce(a, bx, by, bw, bw * .22, rot=-10, op=.5, blur=2.5)
    s += realce(a, bx - 2, by - 1.5, bw * .4, bw * .08 + .4, rot=-10, op=.9, blur=.5)
    return s


def _cobertura(topo, y_base, pingos):
    """Contorno de calda: `topo` da esquerda p/ direita; base ondulada y_base(x) com pingos (x, compr., larg.)."""
    x0, x1 = topo[0][0], topo[-1][0]
    base = [(x1 + 3, y_base(x1))]
    for px, L, w in sorted(pingos, key=lambda p: -p[0]):
        yb = y_base(px)
        base += [(px + w + 3, yb + 1), (px + w * .6, yb + L * .65), (px, yb + L), (px - w * .6, yb + L * .65), (px - w - 3, yb + 1)]
    base += [(x0 - 3, y_base(x0))]
    return topo + base


def _cheddar_caixa(a, r):
    topo = [(-50, -126), (-38, -142), (-22, -137), (-8, -151), (8, -143), (24, -149), (38, -137), (52, -126)]
    pts = _cobertura(topo, lambda x: -106 + abs(x) * .1 - (x / 52) ** 2 * 6,
                     [(-44, 14, 4.5), (-24, 9, 4), (-6, 20, 5), (14, 12, 4.5), (34, 18, 5)])
    s = _cheddar_poca(a, pts, (-18, -134, 16))
    for x, y in ((-6, -90), (34, -92), (-44, -96)):
        s += realce(a, x - 1.2, y, 1.1, 2.8, op=.6, blur=.4)
    s += _bacon_bits(a, [(-30, -128), (-8, -138), (16, -134), (36, -124), (-18, -116), (4, -114), (26, -112), (-38, -110), (-4, -125)], r, 1)
    return s


def _bacon_bits(a, posicoes, r, k=1.0):
    """Bacon em pedacinhos: lascas angulosas, vermelho tostado, com gordura clara numa das bordas."""
    s = ''
    carne = a.linear([(0, '#c4502e'), (.5, '#922c16'), (1, '#5e190b')])
    for x, y in posicoes:
        w = r.uniform(4.2, 6.2) * k
        h = r.uniform(3, 4) * k
        g = math.radians(r.uniform(-60, 60))
        cg, sg = math.cos(g), math.sin(g)
        cantos = [(-1, -1), (-.1, -1.1), (1, -.9), (1.1, .25), (.8, 1), (-.4, 1.1), (-1.1, .3)]
        pts = []
        for u, v in cantos:
            px, py = u * w * r.uniform(.82, 1.1), v * h * r.uniform(.82, 1.1)
            pts.append((x + px * cg - py * sg, y + px * sg + py * cg))
        d = 'M' + ' L'.join(f'{n(px)},{n(py)}' for px, py in pts) + 'Z'
        s += f'<path d="{d}" fill="#2a0800" opacity=".45" transform="translate(.8,1.5)"/>'
        s += f'<path d="{d}" fill="{carne}" stroke="#3f0e04" stroke-width=".7" stroke-linejoin="round"/>'
        def meio(p, f=.4):
            return (p[0] + (x - p[0]) * f, p[1] + (y - p[1]) * f)
        gord = [pts[0], pts[1], pts[2], meio(pts[2]), meio(pts[1]), meio(pts[0])]
        s += '<path d="M' + ' L'.join(f'{n(px)},{n(py)}' for px, py in gord) + 'Z" fill="#f2c7a6" opacity=".92"/>'
    return s


# ---------------------------------------------------------------- recipientes

def _tigela(a, cx, borda, rx, ry, h, rx_pe, esp, corpo_cores, interior_cores, aro_cores):
    """Vasilha de 3/4: devolve (atrás, frente). `borda` é o y do centro do aro; o pé fica em borda + h."""
    base = borda + h
    rxi, ryi = rx - esp, ry * (rx - esp) / rx
    atras = f'<ellipse cx="{n(cx)}" cy="{n(borda)}" rx="{n(rx)}" ry="{n(ry)}" fill="{a.linear(aro_cores)}"/>'
    atras += f'<ellipse cx="{n(cx)}" cy="{n(borda + .6)}" rx="{n(rxi)}" ry="{n(ryi)}" fill="{a.linear(interior_cores)}"/>'
    corpo = (f'M{n(cx - rx)},{n(borda)} C{n(cx - rx)},{n(borda + h * .72)} {n(cx - rx_pe - (rx - rx_pe) * .35)},{n(base)} {n(cx - rx_pe)},{n(base)} '
             f'H{n(cx + rx_pe)} C{n(cx + rx_pe + (rx - rx_pe) * .35)},{n(base)} {n(cx + rx)},{n(borda + h * .72)} {n(cx + rx)},{n(borda)} '
             f'A{n(rx)},{n(ry)} 0 0 1 {n(cx - rx)},{n(borda)} Z')
    frente = f'<path d="{corpo}" fill="{a.linear(corpo_cores, 0, 0, 1, 0)}"/>'
    frente += f'<g clip-path="{a.recorte(corpo)}">'
    frente += f'<rect x="{n(cx - rx)}" y="{n(borda)}" width="{n(2 * rx)}" height="{n(h)}" fill="{a.linear([(0, "#000", 0), (.55, "#000", 0), (1, "#000", .35)])}"/>'
    frente += realce(a, cx - rx * .55, borda + ry + (h - ry) * .38, rx * .12, (h - ry) * .3, rot=-14, op=.2, blur=4)
    frente += (f'<path d="M{n(cx + rx - 1)},{n(borda + 2)} C{n(cx + rx - 1)},{n(borda + h * .6)} {n(cx + rx_pe + 10)},{n(base - 3)} {n(cx + rx_pe - 6)},{n(base - 1)}" '
               f'stroke="#ffd9a0" stroke-opacity=".35" stroke-width="3" fill="none" filter="{a.desfoque(1.2)}"/>')
    frente += '</g>'
    aro = (f'M{n(cx - rx)},{n(borda)} A{n(rx)},{n(ry)} 0 0 0 {n(cx + rx)},{n(borda)} '
           f'L{n(cx + rxi)},{n(borda + .6)} A{n(rxi)},{n(ryi)} 0 0 1 {n(cx - rxi)},{n(borda + .6)} Z')
    frente += f'<path d="{aro}" fill="{a.linear(aro_cores, 0, 0, 1, 0)}"/>'
    frente += (f'<path d="M{n(cx - rx * .8)},{n(borda + ry * .6)} A{n(rx)},{n(ry)} 0 0 0 {n(cx - rx * .1)},{n(borda + ry)}" '
               f'stroke="#fff" stroke-opacity=".5" stroke-width="1.4" fill="none" stroke-linecap="round"/>')
    return atras, frente


CERAMICA_ESCURA = dict(corpo_cores=[(0, '#4a4542'), (.3, '#2e2b29'), (.75, '#1a1817'), (1, '#36302c')],
                       interior_cores=[(0, '#141211'), (1, '#2c2826')],
                       aro_cores=[(0, '#5d5753'), (.5, '#3a3633'), (1, '#24211f')])
FERRO = dict(corpo_cores=[(0, '#3c3c3e'), (.3, '#232325'), (.75, '#141415'), (1, '#2c2c2e')],
             interior_cores=[(0, '#0f0f10'), (1, '#262628')],
             aro_cores=[(0, '#5a5a5d'), (.5, '#333336'), (1, '#1c1c1e')])


def _papel_cesta(a, cx, borda, rx, ry):
    """Folha de papel kraft forrando a cesta: pontas de trás (atrás) e abas caídas na frente (frente)."""
    atras = suave([(cx - rx + 6, borda + 2), (cx - rx * .78, borda - ry - 14), (cx - rx * .55, borda - ry - 30),
                   (cx - rx * .28, borda - ry - 12), (cx, borda - ry - 6), (cx + rx * .3, borda - ry - 13),
                   (cx + rx * .58, borda - ry - 28), (cx + rx * .8, borda - ry - 12), (cx + rx - 6, borda + 2),
                   (cx + rx * .5, borda + ry * .7), (cx - rx * .5, borda + ry * .7)], t=.8)
    s = f'<path d="{atras}" fill="{a.linear([(0, KRAFT[0]), (.6, KRAFT[1]), (1, KRAFT[2])])}" filter="{a.textura("fino")}"/>'
    for px, py, qx in ((cx - rx * .55, borda - ry - 28, cx - rx * .45), (cx + rx * .58, borda - ry - 26, cx + rx * .48)):
        s += f'<path d="M{n(px)},{n(py)} L{n(qx)},{n(borda)}" stroke="#7a5530" stroke-opacity=".45" stroke-width="1.2"/>'
        s += f'<path d="M{n(px + 1.5)},{n(py + 1)} L{n(qx + 3)},{n(borda)}" stroke="#fff3dc" stroke-opacity=".4" stroke-width="1"/>'
    s += f'<path d="{atras}" fill="none" stroke="#f3dfbd" stroke-opacity=".6" stroke-width="1"/>'
    frente = ''
    for lado in (-1, 1):
        x0 = cx + lado * rx * .95
        x1 = cx + lado * rx * .42
        y0 = borda + ry * .3
        y1 = borda + ry * .9
        tip = (cx + lado * rx * .78, borda + ry + 30)
        d = suave([(x0, y0), (x1, y1), (tip[0] + lado * -6, tip[1] - 8), tip, (x0 + lado * 4, y0 + 18)], t=.6)
        frente += f'<path d="{d}" fill="#000" opacity=".35" transform="translate(2,4)" filter="{a.desfoque(2.5)}"/>'
        frente += f'<path d="{d}" fill="{a.linear([(0, "#e6c8a0"), (.5, KRAFT[0]), (1, KRAFT[1])])}" filter="{a.textura("fino")}"/>'
        frente += f'<path d="M{n(x0)},{n(y0)} L{n(x1)},{n(y1)}" stroke="#fff3dc" stroke-opacity=".7" stroke-width="1.2" stroke-linecap="round"/>'
    return s, frente


def _cesta(a, cx, borda, rx=116, ry=24, h=62, rx_pe=92):
    """Cesta grafite forrada com papel kraft. Devolve (atrás, frente)."""
    atras, frente = _tigela(a, cx, borda, rx, ry, h, rx_pe, 5, **FERRO)
    pa, pf = _papel_cesta(a, cx, borda, rx, ry)
    frente += selo_marca(a, cx, borda + ry + (h - ry) * .48, 13)
    return atras + pa, frente + pf


def _prato(a, cx, borda, rx=150, ry=34):
    """Prato raso de cerâmica branca (fica todo atrás do conteúdo)."""
    s = f'<ellipse cx="{n(cx)}" cy="{n(borda + 7)}" rx="{n(rx * .7)}" ry="{n(ry * .62)}" fill="#8f877c"/>'
    s += f'<ellipse cx="{n(cx)}" cy="{n(borda + 2.5)}" rx="{n(rx)}" ry="{n(ry)}" fill="{a.linear([(0, "#d9d3c8"), (1, "#a59d90")])}"/>'
    s += f'<ellipse cx="{n(cx)}" cy="{n(borda)}" rx="{n(rx)}" ry="{n(ry)}" fill="{a.linear([(0, "#ffffff"), (.6, "#f1ede5"), (1, "#d6cfc3")], 0, 0, 1, 0)}"/>'
    s += f'<ellipse cx="{n(cx)}" cy="{n(borda + 1.5)}" rx="{n(rx * .72)}" ry="{n(ry * .7)}" fill="{a.linear([(0, "#d7d0c4"), (.4, "#ece7de"), (1, "#faf8f3")])}"/>'
    s += (f'<path d="M{n(cx - rx * .9)},{n(borda + ry * .42)} A{n(rx)},{n(ry)} 0 0 0 {n(cx - rx * .2)},{n(borda + ry * .98)}" '
          f'stroke="#fff" stroke-width="1.6" fill="none" stroke-linecap="round" opacity=".9"/>')
    s += realce(a, cx - rx * .55, borda - ry * .4, rx * .2, ry * .14, rot=-6, op=.6, blur=3)
    return s


def _madeira(a, d, cores):
    return f'<path d="{d}" fill="{a.linear(cores)}" filter="{a.textura("fino")}"/>'


def _tabua_redonda(a, cx, topo, rx=138, ry=32, esp=11):
    lado = (f'M{n(cx - rx)},{n(topo)} A{n(rx)},{n(ry)} 0 0 0 {n(cx + rx)},{n(topo)} V{n(topo + esp)} '
            f'A{n(rx)},{n(ry)} 0 0 1 {n(cx - rx)},{n(topo + esp)} Z')
    s = f'<path d="{lado}" fill="{a.linear([(0, "#9a6534"), (.4, "#7a4a22"), (1, "#3d2310")], 0, 0, 1, 0)}" filter="{a.textura("fino")}"/>'
    face = f'M{n(cx - rx)},{n(topo)} A{n(rx)},{n(ry)} 0 1 0 {n(cx + rx)},{n(topo)} A{n(rx)},{n(ry)} 0 1 0 {n(cx - rx)},{n(topo)} Z'
    s += _madeira(a, face, [(0, '#a8713c'), (1, '#cf9a5e')])
    s += f'<g clip-path="{a.recorte(face)}">'
    for i in range(5):
        k = .3 + i * .17
        s += f'<ellipse cx="{n(cx + 8)}" cy="{n(topo + 2)}" rx="{n(rx * k)}" ry="{n(ry * k)}" fill="none" stroke="#7a4a1e" stroke-opacity=".28" stroke-width=".9"/>'
    s += f'<rect x="{n(cx - rx)}" y="{n(topo - ry)}" width="{n(rx * 2)}" height="{n(ry * 2)}" fill="{a.linear([(0, "#fff", .12), (.5, "#fff", 0), (.8, "#000", 0), (1, "#000", .25)], 0, 0, 1, 0)}"/>'
    s += '</g>'
    s += (f'<path d="M{n(cx - rx + 1)},{n(topo + 1)} A{n(rx)},{n(ry)} 0 0 0 {n(cx + rx - 1)},{n(topo + 1)}" '
          f'stroke="#f0cc95" stroke-opacity=".55" stroke-width="1.2" fill="none"/>')
    return s


def _tabua_retangular(a, cx, topo, larg=330, prof=78, esp=11):
    x0, x1 = cx - larg / 2, cx + larg / 2
    ins = 14
    face = (f'M{n(x0 + ins + 12)},{n(topo)} H{n(x1 - ins - 12)} Q{n(x1 - ins)},{n(topo)} {n(x1 - ins + 1)},{n(topo + 8)} '
            f'L{n(x1)},{n(topo + prof - 10)} Q{n(x1 + 1)},{n(topo + prof)} {n(x1 - 12)},{n(topo + prof)} H{n(x0 + 12)} '
            f'Q{n(x0 - 1)},{n(topo + prof)} {n(x0)},{n(topo + prof - 10)} L{n(x0 + ins - 1)},{n(topo + 8)} Q{n(x0 + ins)},{n(topo)} {n(x0 + ins + 12)},{n(topo)} Z')
    frente = (f'M{n(x0)},{n(topo + prof - 10)} Q{n(x0 - 1)},{n(topo + prof)} {n(x0 + 12)},{n(topo + prof)} H{n(x1 - 12)} '
              f'Q{n(x1 + 1)},{n(topo + prof)} {n(x1)},{n(topo + prof - 10)} V{n(topo + prof - 10 + esp)} '
              f'Q{n(x1 + 1)},{n(topo + prof + esp)} {n(x1 - 12)},{n(topo + prof + esp)} H{n(x0 + 12)} '
              f'Q{n(x0 - 1)},{n(topo + prof + esp)} {n(x0)},{n(topo + prof - 10 + esp)} Z')
    s = _madeira(a, frente, [(0, '#8a5a2e'), (1, '#45290f')])
    s += _madeira(a, face, [(0, '#a06a36'), (1, '#cf9a5e')])
    s += f'<g clip-path="{a.recorte(face)}">'
    for i in range(6):
        yy = topo + 8 + i * (prof - 12) / 5
        s += (f'<path d="M{n(x0 - 10)},{n(yy)} q{n(larg * .3)},{n(-2 + i % 2 * 3)} {n(larg * .6)},0 t{n(larg * .5)},0" '
              f'stroke="#7a4a1e" stroke-opacity=".3" stroke-width=".9" fill="none"/>')
    s += f'<rect x="{n(x0)}" y="{n(topo)}" width="{n(larg)}" height="{n(prof)}" fill="{a.linear([(0, "#fff", .1), (.5, "#fff", 0), (.8, "#000", 0), (1, "#000", .22)], 0, 0, 1, 0)}"/>'
    s += '</g>'
    s += f'<path d="M{n(x0 + 10)},{n(topo + prof + .5)} H{n(x1 - 10)}" stroke="#f0cc95" stroke-opacity=".55" stroke-width="1.1"/>'
    return s


def _frigideira(a, cx, borda, rx=120, ry=30, h=50):
    """Frigideira de ferro com cabo à direita. Devolve (atrás, frente)."""
    atras, frente = _tigela(a, cx, borda, rx, ry, h, rx - 10, 7, **FERRO)
    x = cx + rx
    cabo = (f'M{n(x - 6)},{n(borda + 4)} L{n(x + 58)},{n(borda - 10)} Q{n(x + 72)},{n(borda - 12)} '
            f'{n(x + 72)},{n(borda - 4)} Q{n(x + 72)},{n(borda + 3)} {n(x + 58)},{n(borda + 3)} '
            f'L{n(x - 4)},{n(borda + 18)} Z')
    s = f'<path d="{cabo}" fill="#000" opacity=".4" transform="translate(2,6)" filter="{a.desfoque(3)}"/>'
    s += f'<path d="{cabo}" fill="{a.linear([(0, "#4f4f52"), (.45, "#29292b"), (1, "#111112")])}"/>'
    s += f'<ellipse cx="{n(x + 61)}" cy="{n(borda - 3.5)}" rx="4.5" ry="2.6" fill="#0a0a0b"/>'
    s += f'<path d="M{n(x)},{n(borda + 5)} L{n(x + 58)},{n(borda - 9)}" stroke="#9a9aa0" stroke-opacity=".55" stroke-width="1" fill="none"/>'
    return atras, s + frente


# ---------------------------------------------------------------- empanados

NUGGET = [(0, '#ffe196'), (.45, '#f7ad3c'), (1, '#c4661a')]
NUGGET_LADO = [(0, '#d07a1e'), (1, '#723606')]
ISCA = [(0, '#ffdf92'), (.45, '#f4a93a'), (1, '#b85e15')]
ISCA_LADO = [(0, '#c8721c'), (1, '#663005')]


def _empanado(a, d, alt, cores, cores_lado, x, y, w, h, r):
    """Peça empanada com espessura: sombra, lateral (mais escura), face de cima e brilhos."""
    i = _ref(a, d)
    s = _use(i, fill='#2a1000', opacity='.5', transform=f'translate(2.5,{n(alt + 3)})', filter=a.desfoque(2.2))
    s += _use(i, fill=a.linear(cores_lado), transform=f'translate(0,{n(alt)})')
    s += _use(i, fill=a.radial(cores, cx=.36, cy=.3, r=.82))
    s += f'<g clip-path="{_recorte_ref(a, i)}">'
    s += _use(i, fill='none', stroke='#6a3000', stroke_opacity='.45', stroke_width=n(min(w, h) * .22), filter=a.desfoque(2))
    s += '</g>'
    s += realce(a, x - w * .16, y - h * .2, w * .2, h * .1, rot=-12, op=.45, blur=2)
    s += realce(a, x - w * .2, y - h * .24, w * .07, h * .04 + .5, rot=-12, op=.7, blur=.6)
    return s


def _nugget(a, x, y, w=40, h=29, giro=0, semente=1):
    r = rng(semente)
    d = _forma(x, y, w / 2, h / 2, pontos=7, var=.17, semente=semente, giro=giro)
    return _empanado(a, d, h * .32, NUGGET, NUGGET_LADO, x, y, w, h, r)


def _pos_nuggets(qtd, w=40, h=29):
    """Montinho: fileira de trás, fileira da frente e alguns por cima. Devolve [(dx, dy)] na ordem de desenho."""
    if qtd <= 3:
        filas = [(qtd, 0, 0)]
    else:
        cima = qtd // 5
        tras = (qtd - cima) // 2
        filas = [(tras, -h * .5, w * .43), (qtd - cima - tras, 0, 0), (cima, -h * .95, w * .1)]
    pos = []
    for m, dy, desloc in filas:
        for i in range(m):
            pos.append(((i - (m - 1) / 2) * w * .86 + desloc, dy - h * .5))
    return pos


def nuggets_grupo(a, cx, base, escala=1.0, qtd=6):
    """Montinho de nuggets sem prato (qtd=6: ~112 x 64 em escala 1; qtd=10: ~160 x 68)."""
    r = rng(70 + qtd)
    s = ''
    for i, (dx, dy) in enumerate(_pos_nuggets(qtd)):
        s += _nugget(a, dx + r.uniform(-2.5, 2.5), dy - 10 + r.uniform(-1.5, 1.5), r.uniform(37, 43), r.uniform(27, 31),
                     giro=r.uniform(-22, 22), semente=100 + i * 7)
    return _grupo(cx, base, escala, f'<g filter="{_crosta(a)}">{s}</g>')


def _isca(a, x, y, comp=72, larg=24, giro=0, semente=1, curva=4):
    r = rng(semente)
    d = _forma(x, y, comp / 2, larg / 2, pontos=22, var=.065, semente=semente, giro=giro, curva=curva, crocante=True)
    return _empanado(a, d, larg * .36, ISCA, ISCA_LADO, x, y, comp * .8, larg, r)


ANEL = [(0, '#ffe39c'), (.5, '#f4ab40'), (1, '#b9621a')]
ANEL_LADO = [(0, '#b8661a'), (1, '#552705')]


def _anel(a, x, y, R=34, t=18, k=.45, giro=0, semente=1):
    """Anel de cebola empanado, com volume de tubo. k = achatamento da perspectiva (1 = de frente)."""
    r = rng(semente)
    prof = t * .6 * (1 - k * .5)
    d = (_elipse_irregular(x, y, R + t / 2, (R + t / 2) * k, giro, .045, r) + ' ' +
         _elipse_irregular(x, y, R - t / 2, (R - t / 2) * k, giro, .035, r))
    i = _ref(a, d, furado=True)
    s = _use(i, fill='#2a1000', opacity='.45', transform=f'translate(2.5,{n(prof + 3)})', filter=a.desfoque(2.2))
    s += _use(i, fill=a.linear(ANEL_LADO), transform=f'translate(0,{n(prof)})')
    s += _use(i, fill=a.radial(ANEL, cx=.38, cy=.3, r=.78))
    s += f'<g clip-path="{_recorte_ref(a, i)}">'
    s += _use(i, fill='none', stroke='#5a2800', stroke_opacity='.5', stroke_width=n(t * .32), filter=a.desfoque(t * .12))
    s += (f'<ellipse cx="{n(x - t * .12)}" cy="{n(y - t * .18)}" rx="{n(R)}" ry="{n(R * k)}" fill="none" stroke="#ffd47a" '
          f'stroke-width="{n(t * .22)}" opacity=".4" filter="{a.desfoque(t * .1)}" transform="rotate({n(giro)} {n(x)} {n(y)})"/>')
    s += '</g>'
    s += realce(a, x - R * .62, y - R * k * .55, R * .22, t * .09 + .8, rot=giro - 25 * k, op=.65, blur=1)
    return s


# ---------------------------------------------------------------- batata rústica

GOMO = [(0, '#ffe8a2'), (.5, '#f7bf4f'), (1, '#dc8c26')]
CASCA = [(0, '#c07a38'), (.5, '#94532a'), (1, '#5e2f12')]


def _gomo(a, x, y, comp=90, alt=24, giro=0, semente=1, virado=False):
    """Gomo de batata com casca, deitado sobre uma face cortada.

    Mostra a outra face cortada (dourada, em meia-lua) e a casca: quando `virado`, o lado curvo
    fica para a frente e a casca aparece como uma faixa; senão, só um filete de casca no alto."""
    r = rng(semente)
    g = math.radians(giro)
    cg, sg = math.cos(g), math.sin(g)
    sinal = 1 if virado else -1

    def pt(px, py):
        return (x + px * cg - py * sg, y + px * sg + py * cg)
    curva = [pt(-comp / 2 + comp * i / 12, sinal * alt * math.sin(math.pi * i / 12) ** .8 + (r.uniform(-.6, .6) if 0 < i < 12 else 0))
             for i in range(13)]
    reta = [pt(comp / 2 - comp * i / 6, sinal * alt * .08 * math.sin(math.pi * i / 6)) for i in range(1, 6)]
    d = suave(curva + reta, t=.7)
    i = _ref(a, re.sub(r'-?\d+\.\d+', _num1, d))
    esp = alt * (.45 if virado else .2)
    lado = a.linear(CASCA) if virado else a.linear([(0, '#d18a2c'), (1, '#8a4a12')])
    s = _use(i, fill='#2a1000', opacity='.5', transform=f'translate(2.5,{n(esp + 3)})', filter=a.desfoque(2.2))
    s += _use(i, fill=lado, transform=f'translate(0,{n(esp)})')
    s += _use(i, fill=a.radial(GOMO, cx=.42, cy=.4, r=.75))
    s += f'<g clip-path="{_recorte_ref(a, i)}">'
    s += _use(i, fill='none', stroke='#a85a12', stroke_opacity='.55', stroke_width='5', filter=a.desfoque(2))
    s += '</g>'
    if not virado:
        b = _ref(a, re.sub(r'-?\d+\.\d+', _num1, suave(curva, fechado=False)))
        s += _use(b, fill='none', stroke='#7a4018', stroke_width='2.6', stroke_linecap='round')
        s += _use(b, fill='none', stroke='#c98a4a', stroke_width='.9', stroke_linecap='round', transform='translate(0,1.4)', opacity='.8')
    else:
        for k in range(3):
            px, py = pt(r.uniform(-.3, .3) * comp, alt * 1.05 + esp * .5)
            s += f'<ellipse cx="{n(px)}" cy="{n(py)}" rx="1.5" ry=".9" fill="#3d1a06" opacity=".7"/>'
    hx, hy = pt(-comp * .06, sinal * alt * .42)
    s += realce(a, hx, hy, comp * .24, 2.4, rot=giro, op=.55, blur=1.6)
    for k in range(2):
        px, py = pt(r.uniform(-.32, .32) * comp, sinal * alt * r.uniform(.2, .6))
        cor = '#fff' if k % 2 else '#2a1a10'
        s += f'<rect x="{n(px)}" y="{n(py)}" width="1.4" height="1.4" fill="{cor}" opacity=".75" transform="rotate(45 {n(px)} {n(py)})"/>'
    return s


def _alecrim(a, x, y, comp, giro):
    g = math.radians(giro)
    dx, dy = math.cos(g), math.sin(g)
    nx, ny = -dy, dx
    caule = f'M{n(x)},{n(y)} q{n(comp * .5 * dx + 3 * nx)},{n(comp * .5 * dy + 3 * ny)} {n(comp * dx)},{n(comp * dy)}'
    folhas = ''
    for i in range(16):
        t = .06 + i * .058
        px = x + dx * comp * t + nx * 1.4 * math.sin(t * math.pi)
        py = y + dy * comp * t + ny * 1.4 * math.sin(t * math.pi)
        lado = 1 if i % 2 else -1
        L = 11 * (1 - t * .45)
        ang = g + lado * math.radians(48)
        folhas += f'M{n(px)},{n(py)} l{n(math.cos(ang) * L)},{n(math.sin(ang) * L)} '
    i = _ref(a, folhas.strip())
    s = _use(i, stroke='#000', stroke_opacity='.45', stroke_width='3', stroke_linecap='round', transform='translate(1.5,2.5)', filter=a.desfoque(1.2))
    s += f'<path d="{caule}" stroke="#7a6436" stroke-width="1.8" fill="none" stroke-linecap="round"/>'
    s += _use(i, stroke='#3b6e3a', stroke_width='3', stroke_linecap='round')
    s += _use(i, stroke='#9ccf86', stroke_width='1', stroke_linecap='round', transform='translate(-.6,-.7)', opacity='.85')
    return s


def _alho(a, x, y, tam=11, giro=0):
    """Dente de alho assado, com casca fina."""
    d = (f'M0,{n(-tam)} C{n(tam * .82)},{n(-tam * .5)} {n(tam * .8)},{n(tam * .55)} 0,{n(tam * .62)} '
         f'C{n(-tam * .8)},{n(tam * .55)} {n(-tam * .82)},{n(-tam * .5)} 0,{n(-tam)} Z')
    s = f'<g transform="translate({n(x)},{n(y)}) rotate({n(giro)})">'
    s += f'<path d="{d}" fill="#000" opacity=".45" transform="translate(2,3)" filter="{a.desfoque(1.5)}"/>'
    s += f'<path d="{d}" fill="{a.radial([(0, "#fff8e2"), (.45, "#f3d9a0"), (1, "#bd8540")], cx=.36, cy=.38, r=.72)}"/>'
    s += f'<path d="M{n(-tam * .2)},{n(-tam * .85)} Q{n(tam * .35)},0 {n(tam * .12)},{n(tam * .58)}" stroke="#b08a56" stroke-width="1" fill="none" opacity=".7"/>'
    s += f'<path d="M{n(tam * .3)},{n(-tam * .6)} Q{n(tam * .75)},0 {n(tam * .4)},{n(tam * .45)}" stroke="#c9a3b8" stroke-width="1" fill="none" opacity=".6"/>'
    s += f'<path d="M0,{n(-tam)} l-1,{n(-tam * .28)}" stroke="#8a5a2a" stroke-width="2" stroke-linecap="round"/>'
    s += f'<ellipse cx="{n(-tam * .32)}" cy="{n(-tam * .15)}" rx="{n(tam * .14)}" ry="{n(tam * .32)}" fill="#fff" opacity=".75"/>'
    return s + '</g>'


# ---------------------------------------------------------------- mandioca

MANDIOCA = [(0, '#fff2c2'), (.2, '#fddc8e'), (.5, '#f4c463'), (.55, '#e4a84c'), (1, '#b2762c')]


def _mandioca(a, x, y, comp, larg, ang, semente):
    """Bastão de mandioca frita: grosso, bordas irregulares, creme dourado, ponta clara."""
    r = rng(semente)
    m = 5
    esq = [(-larg / 2 + r.uniform(-1.6, 1.6), -comp * i / m) for i in range(m + 1)]
    dir_ = [(larg / 2 + r.uniform(-1.6, 1.6), -comp * (m - i) / m) for i in range(m + 1)]
    topo = [(-larg * .22, -comp - r.uniform(1, 3.5)), (larg * .22, -comp - r.uniform(0, 2.5))]
    i = _ref(a, re.sub(r'-?\d+\.\d+', _num1, suave(esq + topo + dir_, t=.5)))
    s = f'<g transform="translate({n(x)},{n(y)}) rotate({n(ang)})">'
    s += _use(i, fill='#2a1400', opacity='.45', transform='translate(3,2)', filter=a.desfoque(2.2))
    s += f'<g filter="{_crosta(a, "mandioca")}">'
    s += _use(i, fill=a.linear(MANDIOCA, 0, 0, 1, 0))
    s += f'<g clip-path="{_recorte_ref(a, i)}">'
    for k in range(2):
        s += (f'<ellipse cx="{n(r.uniform(-.2, .25) * larg)}" cy="{n(-comp * r.uniform(.3, .75))}" rx="{n(larg * .4)}" '
              f'ry="{n(r.uniform(8, 13))}" fill="#e39c34" opacity=".5" filter="{a.desfoque(3)}"/>')
    s += _use(i, fill='none', stroke='#b8741e', stroke_opacity='.5', stroke_width='4', filter=a.desfoque(1.6))
    s += f'<rect x="{n(-larg)}" y="{n(-comp - 5)}" width="{n(larg * 2)}" height="9" fill="{a.linear([(0, "#fff8e0", .8), (1, "#fff8e0", 0)])}"/>'
    s += '</g></g>'
    s += f'<path d="M{n(-larg * .26)},{n(-comp + 9)} V{n(-comp * .35)}" stroke="#fff" stroke-opacity=".3" stroke-width="{n(larg * .08)}" stroke-linecap="round"/>'
    return s + '</g>'


# ---------------------------------------------------------------- molhos

MOLHOS = {
    'maionese': dict(sup=[(0, '#fffef8'), (.55, '#f9f0d6'), (1, '#e6d4a4')], borda='#c9ae74', alto=True, pintas=None),
    'barbecue': dict(sup=[(0, '#b84c2a'), (.5, '#7a2412'), (1, '#3e0d05')], borda='#2a0702', alto=False, pintas=None),
    'cheddar': dict(sup=[(0, '#ffd877'), (.5, '#ffa82a'), (1, '#d9730a')], borda='#b65800', alto=False, pintas=None),
    'verde': dict(sup=[(0, '#e5f3b8'), (.5, '#b2d576'), (1, '#7aa23f')], borda='#5f8530', alto=True, pintas='#2f5a1c'),
}


def _pote(a, molho='maionese', pingo=False):
    """Potinho de cerâmica branca canelado com molho; origem no centro da base. ~76 x 52."""
    m = MOLHOS[molho]
    r = rng(5)
    top, rx, ry = -42, 38, 10
    rb, ryb = 33, 8
    corpo = f'M{-rx},{top} L{-rb},{-ryb} A{rb},{ryb} 0 0 0 {rb},{-ryb} L{rx},{top} A{rx},{ry} 0 0 1 {-rx},{top} Z'
    s = f'<path d="{corpo}" fill="{a.linear([(0, "#cfc9be"), (.16, "#ffffff"), (.45, "#f3efe7"), (.8, "#c9c1b3"), (.93, "#a69e90"), (1, "#d6cfc3")], 0, 0, 1, 0)}"/>'
    s += f'<g clip-path="{a.recorte(corpo)}">'
    claros, escuros = '', ''
    for k in range(-8, 9):
        th = k * math.pi / 18
        xt, xb = rx * math.sin(th), rb * math.sin(th)
        yt = top + ry * math.cos(th) + 2
        yb = -ryb + ryb * math.cos(th) - 1
        claros += f'M{n(xt - .9)},{n(yt)} L{n(xb - .8)},{n(yb)} '
        escuros += f'M{n(xt + 1)},{n(yt)} L{n(xb + .9)},{n(yb)} '
    s += f'<path d="{claros}" stroke="#fff" stroke-opacity=".75" stroke-width="1.1"/>'
    s += f'<path d="{escuros}" stroke="#8a8173" stroke-opacity=".35" stroke-width="1.1"/>'
    s += f'<rect x="{-rx}" y="{top}" width="{2 * rx}" height="{-top}" fill="{a.linear([(0, "#000", 0), (.6, "#000", 0), (1, "#000", .18)])}"/>'
    s += '</g>'
    s += f'<ellipse cx="0" cy="{top}" rx="{rx}" ry="{ry}" fill="{a.linear([(0, "#ffffff"), (1, "#e3ddd2")])}"/>'
    s += f'<ellipse cx="0" cy="{top + .4}" rx="{rx - 3.5}" ry="{n(ry - 2.2)}" fill="{a.linear([(0, "#bdb5a7"), (1, "#efe9df")])}"/>'
    sup = a.radial(m['sup'], cx=.4, cy=.35, r=.75)
    s += f'<ellipse cx="0" cy="{top + 1.6}" rx="{rx - 4.5}" ry="{n(ry - 3)}" fill="{sup}"/>'
    s += f'<ellipse cx="0" cy="{top + 1.6}" rx="{rx - 4.5}" ry="{n(ry - 3)}" fill="none" stroke="{m["borda"]}" stroke-opacity=".45" stroke-width=".8"/>'
    if m['alto']:
        monte = 'M-24,-40.5 C-20,-47 -12,-52 -4,-56 C0,-58 4,-58 6,-55 C14,-50 22,-45 25,-40.5 C12,-37 -12,-37 -24,-40.5 Z'
        s += f'<path d="{monte}" fill="{a.radial(m["sup"], cx=.38, cy=.3, r=.8)}"/>'
        s += '<path d="M-18,-43.5 C-8,-47 6,-47 18,-43" stroke="#000" stroke-opacity=".1" stroke-width="1.6" fill="none"/>'
        s += '<path d="M-11,-48.5 C-4,-52 4,-51.5 11,-48" stroke="#000" stroke-opacity=".08" stroke-width="1.4" fill="none"/>'
        s += '<path d="M-17,-44.5 C-8,-48 4,-48 14,-45.5" stroke="#fff" stroke-opacity=".7" stroke-width="1" fill="none"/>'
        s += '<path d="M-9,-49.5 C-3,-52.5 3,-52.5 8,-50" stroke="#fff" stroke-opacity=".7" stroke-width=".9" fill="none"/>'
        s += realce(a, -6, -51, 4, 1.6, rot=-20, op=.9, blur=.4)
    else:
        s += '<path d="M-14,-41 C-6,-45 8,-44.5 16,-40.5 M-6,-40.6 C-1,-42.4 5,-42 8,-40.2" stroke="#fff" stroke-opacity=".45" stroke-width="1" fill="none" stroke-linecap="round"/>'
        s += realce(a, -14, -42.4, 7, 1.5, rot=-4, op=.75, blur=.6)
    if m['pintas']:
        for k in range(14):
            px, py = r.uniform(-22, 22), r.uniform(-46, -40)
            if m['alto'] and abs(px) < 14:
                py -= r.uniform(0, 9) * (1 - abs(px) / 14)
            s += f'<ellipse cx="{n(px)}" cy="{n(py)}" rx="{n(r.uniform(.6, 1.2))}" ry=".55" fill="{m["pintas"]}" opacity=".85"/>'
    s += f'<path d="M{-rx + 3},{top - 2} A{rx},{ry} 0 0 1 -6,{top - ry + .6}" stroke="#fff" stroke-width="1.2" fill="none" stroke-linecap="round"/>'
    s += realce(a, -24, -24, 4, 12, rot=6, op=.55, blur=2)
    if pingo:
        cor = a.linear([(0, m['sup'][1][1]), (1, m['sup'][2][1])])
        s += f'<path d="M14,-34 C15,-29 13.5,-24 14.5,-20 C15,-16 19.5,-16 20,-20 C20.5,-24 19,-30 21,-35 Z" fill="{cor}"/>'
        s += '<path d="M15.7,-30 C15.6,-27 15.4,-24 15.8,-22" stroke="#fff" stroke-opacity=".7" stroke-width=".7" fill="none" stroke-linecap="round"/>'
    return s


def pote_molho(a, cx, base, escala=1.0, molho='maionese'):
    """Potinho de molho (~76 de largura x ~52 de altura em escala 1)."""
    return _grupo(cx, base, escala, _pote(a, molho))


def _sombra_pote(a, cx, base, escala):
    return (f'<ellipse cx="{n(cx + 3 * escala)}" cy="{n(base - 3 * escala)}" rx="{n(38 * escala)}" ry="{n(9 * escala)}" fill="#000" opacity=".5" '
            f'filter="{a.desfoque(3)}"/>')


# ---------------------------------------------------------------- ilustrações

def _batata():
    a = Arte('Ilustração de batata frita')
    s = fundo(a) + sombra(a, cy=CHAO, rx=78, ry=9)
    s += caixa_batata(a, CX, CHAO, 1.12)
    s += _frita_solta(a, 116, 254, 62, 76, tom=1) + _frita_solta(a, 142, 259, 54, 106, tom=0)
    s += _frita_solta(a, 284, 256, 60, 98, tom=2)
    return _svg(a, s)


def _cheddar_fluxo(a, cx, b, r):
    """Cheddar derramado sobre o monte de batatas, com pingos escorrendo."""
    topo = [(cx - 76, b - 30), (cx - 66, b - 52), (cx - 46, b - 72), (cx - 22, b - 86), (cx + 2, b - 92), (cx + 26, b - 86),
            (cx + 48, b - 72), (cx + 66, b - 52), (cx + 76, b - 30)]
    def yb(x):
        return b - 46 + ((x - cx) / 76) ** 2 * 26
    pingos = [(cx - 62, 18, 5), (cx - 40, 30, 6), (cx - 16, 20, 5.5), (cx + 8, 34, 6.5), (cx + 32, 22, 5.5), (cx + 56, 26, 5.5)]
    s = _cheddar_poca(a, _cobertura(topo, yb, pingos), (cx - 22, b - 76, 24))
    for px, L, w in pingos:
        s += realce(a, px - w * .3, yb(px) + L * .55, 1.3, L * .2, op=.65, blur=.5)
    # algumas batatas aparecendo por cima do cheddar
    for x, y, c, ang, tom in ((cx - 36, b - 70, 48, 64, 0), (cx + 36, b - 68, 46, 116, 0), (cx + 4, b - 86, 42, 98, 1), (cx - 58, b - 48, 40, 134, 1)):
        s += _frita_centro(a, x, y, c, 14, ang, tom)
    s += _cheddar_poca(a, [(cx - 26, b - 84), (cx - 8, b - 94), (cx + 14, b - 90), (cx + 22, b - 80), (cx + 4, b - 75), (cx - 18, b - 76)], (cx - 8, b - 86, 9))
    s += _cheddar_poca(a, [(cx - 44, b - 70), (cx - 30, b - 74), (cx - 22, b - 64), (cx - 34, b - 58), (cx - 46, b - 62)], (cx - 36, b - 70, 5))
    bits = [(cx - 40, b - 64), (cx - 18, b - 80), (cx + 10, b - 82), (cx + 30, b - 70), (cx - 4, b - 66), (cx + 50, b - 56),
            (cx - 56, b - 46), (cx + 18, b - 56), (cx - 26, b - 52), (cx + 2, b - 92), (cx + 40, b - 44), (cx - 8, b - 48)]
    return s + _bacon_bits(a, bits, r, 1.15)


def _batata_cheddar():
    a = Arte('Ilustração de batata com cheddar e bacon')
    cx, borda = 184, 200
    atras, frente = _frigideira(a, cx, borda)
    s = fundo(a) + sombra(a, cx=cx + 24, cy=CHAO, rx=146, ry=9)
    s += atras
    s += _monte_fritas(a, cx, borda + 14, 104, 78, 44, semente=5, larg=14, comp=(52, 74))
    s += _cheddar_fluxo(a, cx, borda, rng(9))
    s += frente
    return _svg(a, s)


def _batata_rustica():
    a = Arte('Ilustração de batata rústica')
    cx, borda = CX, 194
    atras, frente = _tigela(a, cx, borda, 122, 26, 56, 80, 6, **CERAMICA_ESCURA)
    s = fundo(a) + sombra(a, cy=CHAO, rx=118, ry=10)
    s += atras
    r = rng(12)
    gomos = [  # dx, dy, giro, virado (de trás para frente, de baixo para cima)
        (-54, -10, -12, False), (54, -12, 14, False), (0, -16, 4, False),
        (-60, 6, 16, True), (58, 6, -18, True), (-14, 10, -6, True), (34, 12, 8, True),
        (-40, -32, -34, False), (36, -34, 30, False), (-2, -42, -4, False),
        (-24, -20, 22, True), (24, -22, -24, True), (-12, -58, -26, False), (18, -60, 28, False)]
    corpo = ''
    for i, (dx, dy, gi, vir) in enumerate(gomos):
        corpo += _gomo(a, cx + dx, borda + dy, r.uniform(84, 94), r.uniform(22, 26), gi, semente=30 + i, virado=vir)
    s += f'<g filter="{_crosta(a, "gomo")}">{corpo}</g>'
    s += _alecrim(a, cx - 74, borda - 44, 70, -20) + _alecrim(a, cx + 4, borda - 80, 66, 22)
    s += _alho(a, cx - 38, borda - 40, 11, -30) + _alho(a, cx + 50, borda - 38, 10.5, 40) + _alho(a, cx + 12, borda - 4, 11, 14)
    s += frente
    s += _alho(a, cx + 128, CHAO + 2, 12, 70) + _alho(a, cx + 112, CHAO + 10, 11, -20) + _alecrim(a, cx - 158, CHAO + 8, 58, -10)
    return _svg(a, s)


def _mandioca_svg():
    a = Arte('Ilustração de mandioca frita')
    cx, borda = CX, 194
    atras, frente = _cesta(a, cx, borda, 112, 24, 56, 88)
    s = fundo(a) + sombra(a, cy=CHAO, rx=112, ry=10)
    s += atras
    r = rng(17)
    bastoes = [  # dx na base, comprimento, ângulo, largura (de trás para frente)
        (-56, 112, -24, 24), (-20, 130, -7, 25), (22, 122, 13, 24), (58, 110, 27, 24),
        (-72, 94, -12, 25), (-34, 114, 9, 26), (8, 120, -13, 26), (44, 106, 19, 25), (74, 90, 8, 24),
        (-46, 92, -21, 27), (-8, 98, 5, 27), (30, 94, -5, 26), (60, 84, 30, 26)]
    for i, (dx, comp, ang, larg) in enumerate(bastoes):
        s += _mandioca(a, cx + dx + r.uniform(-2, 2), borda + 22, comp + 22 + r.uniform(-4, 4), larg, ang, semente=40 + i)
    s += frente
    return _svg(a, s)


def _onion_rings():
    a = Arte('Ilustração de anéis de cebola')
    cx, topo = CX, 234
    s = fundo(a) + sombra(a, cy=CHAO, rx=138, ry=10)
    s += _tabua_redonda(a, cx, topo)
    aneis = [  # dx, dy, R, k, giro (de trás para frente): 10 anéis
        (-64, -50, 31, .86, -22), (62, -52, 31, .86, 22), (0, -70, 31, .9, 3),
        (2, -6, 33, .42, 0), (0, -20, 33, .42, 4), (2, -34, 32, .42, -3),
        (-82, -4, 30, .5, -16), (84, -2, 30, .5, 16),
        (-44, 14, 31, .42, -6), (46, 14, 31, .42, 6)]
    corpo = ''.join(_anel(a, cx + dx, topo + dy, R, 18, k, g, semente=60 + i) for i, (dx, dy, R, k, g) in enumerate(aneis))
    s += f'<g filter="{_crosta(a, "anel")}">{corpo}</g>'
    return _svg(a, s)


def _nuggets_svg():
    a = Arte('Ilustração de nuggets')
    s = fundo(a) + sombra(a, cy=CHAO, rx=150, ry=10)
    s += _prato(a, CX, 230, 154, 32)
    s += nuggets_grupo(a, 160, 250, 1.2, qtd=10)
    s += _sombra_pote(a, 304, 238, 1.1) + pote_molho(a, 304, 240, 1.1, 'barbecue')
    return _svg(a, s)


def _isca_frango():
    a = Arte('Ilustração de iscas de frango')
    cx, borda = 178, 194
    atras, frente = _cesta(a, cx, borda, 112, 24, 58, 88)
    s = fundo(a) + sombra(a, cx=204, cy=CHAO, rx=162, ry=10)
    s += atras
    r = rng(21)
    iscas = [(-50, 0, -16), (46, 0, 18), (-4, 4, 4), (-56, -24, -46), (54, -24, 44), (-22, -22, -10), (22, -24, 14),
             (-28, -46, -58), (28, -46, 56), (0, -44, -2), (-2, -64, 76)]
    corpo = ''.join(_isca(a, cx + dx, borda + dy, r.uniform(68, 78), r.uniform(23, 26), g, semente=80 + i, curva=r.uniform(-4, 4))
                    for i, (dx, dy, g) in enumerate(iscas))
    s += f'<g filter="{_crosta(a)}">{corpo}</g>'
    s += frente
    s += _sombra_pote(a, 320, CHAO, 1.1) + pote_molho(a, 320, CHAO, 1.1, 'maionese')
    return _svg(a, s)


def _porcao_mista():
    a = Arte('Ilustração de porção mista')
    topo, prof = 152, 90
    s = fundo(a) + sombra(a, cy=CHAO, rx=172, ry=10)
    s += _tabua_retangular(a, CX, topo, 348, prof, 12)
    aneis = ''.join(_anel(a, CX + dx, topo + dy, 28, 16, k, g, semente=120 + i)
                    for i, (dx, dy, k, g) in enumerate([(-24, 18, .86, -14), (26, 16, .86, 14), (2, 64, .42, 0), (0, 52, .42, 4), (2, 40, .42, -2)]))
    s += f'<g filter="{_crosta(a, "anel")}">{aneis}</g>'
    s += _monte_fritas(a, 100, topo + 70, 50, 54, 30, semente=7, larg=12, comp=(40, 56), fundo_y=6)
    r = rng(33)
    iscas = ''.join(_isca(a, 300 + dx, topo + dy, r.uniform(62, 68), r.uniform(21, 23), g, semente=140 + i, curva=r.uniform(-3, 3))
                    for i, (dx, dy, g) in enumerate([(-20, 36, -34), (26, 34, 30), (-22, 70, 6), (24, 68, -10), (2, 52, 74), (0, 24, -6)]))
    s += f'<g filter="{_crosta(a)}">{iscas}</g>'
    aneis2 = ''.join(_anel(a, CX + dx, topo + dy, 26, 15, k, g, semente=130 + i)
                     for i, (dx, dy, k, g) in enumerate([(-30, 76, .48, -10), (32, 76, .48, 10)]))
    s += f'<g filter="{_crosta(a, "anel")}">{aneis2}</g>'
    return _svg(a, s)


def _molho_svg(titulo, molho):
    a = Arte(titulo)
    s = fundo(a) + sombra(a, cy=CHAO, rx=100, ry=10)
    s += _grupo(CX, CHAO, 2.7, _pote(a, molho, pingo=True))
    return _svg(a, s)


def gerar():
    A = {}
    A['batata'] = _batata()
    A['batata-cheddar'] = _batata_cheddar()
    A['batata-rustica'] = _batata_rustica()
    A['mandioca'] = _mandioca_svg()
    A['onion-rings'] = _onion_rings()
    A['nuggets'] = _nuggets_svg()
    A['isca-frango'] = _isca_frango()
    A['porcao-mista'] = _porcao_mista()
    A['molho-maionese'] = _molho_svg('Ilustração de pote de maionese', 'maionese')
    A['molho-barbecue'] = _molho_svg('Ilustração de pote de barbecue', 'barbecue')
    A['molho-cheddar'] = _molho_svg('Ilustração de pote de cheddar', 'cheddar')
    A['molho-verde'] = _molho_svg('Ilustração de pote de maionese verde', 'verde')
    return A
