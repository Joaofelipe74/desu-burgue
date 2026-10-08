# Especiais: cachorros-quentes (3/4, com coberturas à mostra) e sanduíches (misto, natural, beirute).
#
# Reaproveita a base de estilo.py e o "motor 3D" mínimo de sobremesas.py. Os sanduíches
# desenham cada superfície plana em coordenadas locais com transform="matrix(...)"
# (ver mat_chao / mat_parede), o que mantém os arquivos pequenos.
import math

from .estilo import (Arte, fundo, sombra, realce, sombra_contato, suave, rng, n, CX, MARCA, KRAFT, selo_marca)
from .sobremesas import (Vista, Prisma, tom, poly, linha, pontos, tracos, gota, subdividir, ret_arredondado, ARO)

CROSTA = [(0, '#f6c072'), (.35, '#e39a45'), (.75, '#b86c26'), (1, '#7f4214')]
MIOLO = [(0, '#fbe9c2'), (1, '#e7c189')]


def m(v):
    """Coordenada compacta (1 casa decimal)."""
    s = f'{v:.1f}'.rstrip('0').rstrip('.')
    return '0' if s in ('-0', '') else s


def segs(lista, cor, larg, op=1):
    """Muitos segmentos (x0,y0,x1,y1) num só <path>, com coordenadas compactas."""
    if not lista:
        return ''
    d = ''.join(f'M{m(x0)} {m(y0)}L{m(x1)} {m(y1)}' for x0, y0, x1, y1 in lista)
    o = '' if op == 1 else f' stroke-opacity="{n(op)}"'
    return f'<path d="{d}" stroke="{cor}" stroke-width="{n(larg)}" stroke-linecap="round"{o}/>'


def formas(lista, **attrs):
    """Vários polígonos (listas de pontos) num só <path>."""
    d = ''.join('M' + 'L'.join(f'{m(x)} {m(y)}' for x, y in pts) + 'Z' for pts in lista)
    at = ''.join(f' {k.replace("_", "-")}="{v}"' for k, v in attrs.items())
    return f'<path d="{d}"{at}/>'


# ---------------------------------------------------------------- bandeja de papel kraft

def bandeja(a, cx=200, cy=222, larg=306, prof=92, alt=22):
    """Barquinha de papel kraft em 3/4 (cantos arredondados, paredes abertas).

    Devolve (interior_svg, frente_svg): o lanche é desenhado entre os dois."""
    v = Vista(cx, cy, elev=38)
    base = subdividir(ret_arredondado(larg, prof, 16, seg=4), 30)
    pr = Prisma(v, base, afina=-.07, altura=alt)
    boca = poly(pr.topo(alt))
    s = f'<path d="{boca}" fill="{a.linear([(0, "#a37a4c"), (.35, KRAFT[1]), (1, "#7d5a36")])}" filter="{a.textura("fino")}"/>'
    s += f'<g clip-path="{a.recorte(boca)}"><path d="{poly(pr.topo(alt * .1))}" fill="#5a3c1e" opacity=".55" filter="{a.desfoque(6)}"/></g>'
    s += f'<path d="{boca}" fill="none" stroke="#f1d6ae" stroke-opacity=".7" stroke-width="1.2"/>'
    lados, cont = pr.lados(a, [(0, alt, KRAFT[0])], ganho=.75, textura='fino')
    f = lados
    for seq in pr.trechos():
        f += f'<path d="{poly(pr.faixa(seq, alt * .42, alt * .6))}" fill="{pr.degrade(a, seq, MARCA, .6)}"/>'
        f += f'<path d="{linha([pr.P(i, alt) for i in seq])}" fill="none" stroke="#f8e6c8" stroke-width="1.6" stroke-linecap="round"/>'
    bx, by = v.p(0, -prof / 2 - 1, alt * .5)
    f += f'<circle cx="{n(bx)}" cy="{n(by + 1.2)}" r="11.5" fill="#000" opacity=".25" filter="{a.desfoque(1.2)}"/>'
    f += selo_marca(a, bx, by, 10.5)
    return s, f


# ---------------------------------------------------------------- pão, salsicha e coberturas

class Dog:
    """Medidas do cachorro-quente na tela (eixo horizontal)."""

    def __init__(self, x0=62, x1=338, topo=118, eixo=166, labio=184, base=236, abre=0):
        self.x0, self.x1 = x0, x1
        self.topo, self.eixo, self.labio, self.base = topo, eixo, labio, base
        self.abre = abre


def pao_tras(a, d):
    x0, x1, t = d.x0, d.x1, d.topo
    fora = suave([(x0 + 2, t + 56), (x0 + 6, t + 20), (x0 + 28, t + 3), (CX - 60, t), (CX + 60, t), (x1 - 28, t + 3),
                  (x1 - 6, t + 20), (x1 - 2, t + 56)], fechado=False) + f' L{n(x1 - 2)},{n(d.eixo + 10)} L{n(x0 + 2)},{n(d.eixo + 10)}Z'
    s = f'<path d="{fora}" fill="{a.linear([(0, "#f4bb70"), (.45, "#dc8e3c"), (1, "#99561f")])}" filter="{a.textura("pao")}"/>'
    s += realce(a, x0 + 70, t + 6, 50, 3.5, op=.45, blur=2.5)
    # miolo (face de dentro, voltada para cima)
    k = 15
    dentro = suave([(x0 + 14, d.eixo + 6), (x0 + 18, t + k + 10), (x0 + 38, t + k), (CX - 50, t + k - 1), (CX + 50, t + k - 1),
                    (x1 - 38, t + k), (x1 - 18, t + k + 10), (x1 - 14, d.eixo + 6)], fechado=False) + 'Z'
    s += f'<path d="{dentro}" fill="{a.linear([(0, "#fdeccb"), (.5, "#f0d09a"), (1, "#c18f52")])}" filter="{a.textura("pao")}"/>'
    s += f'<path d="{suave([(x0 + 20, t + k + 8), (x0 + 40, t + k - 1.5), (CX, t + k - 2.5), (x1 - 40, t + k - 1.5), (x1 - 20, t + k + 8)], fechado=False)}" fill="none" stroke="#fff6e0" stroke-opacity=".85" stroke-width="1.4"/>'
    return s


def salsicha(a, x0, x1, cy, r=17, semente=1):
    """Salsicha vista de lado, com brilho e ruguinhas nas pontas."""
    rr = rng(semente)
    d = (f'M{n(x0 + r)},{n(cy - r)} C{n(CX - 40)},{n(cy - r - 3)} {n(CX + 40)},{n(cy - r - 3)} {n(x1 - r)},{n(cy - r)} '
         f'C{n(x1 + r * .2)},{n(cy - r)} {n(x1 + r * .25)},{n(cy + r)} {n(x1 - r)},{n(cy + r)} '
         f'C{n(CX + 40)},{n(cy + r - 3)} {n(CX - 40)},{n(cy + r - 3)} {n(x0 + r)},{n(cy + r)} '
         f'C{n(x0 - r * .25)},{n(cy + r)} {n(x0 - r * .2)},{n(cy - r)} {n(x0 + r)},{n(cy - r)}Z')
    s = f'<path d="{d}" fill="{a.linear([(0, "#e47a50"), (.35, "#c54e2c"), (.75, "#8e2c18"), (1, "#5a170a")])}"/>'
    s += f'<g clip-path="{a.recorte(d)}">'
    s += f'<rect x="{n(x0 - 4)}" y="{n(cy - r)}" width="{n(r * 1.6)}" height="{n(2 * r)}" fill="{a.linear([(0, "#3a0c04", .55), (1, "#3a0c04", 0)], 0, 0, 1, 0)}"/>'
    s += f'<rect x="{n(x1 - r * 1.6 + 4)}" y="{n(cy - r)}" width="{n(r * 1.6)}" height="{n(2 * r)}" fill="{a.linear([(0, "#3a0c04", 0), (1, "#3a0c04", .5)], 0, 0, 1, 0)}"/>'
    rug = []
    for x in (x0 + r * .7, x0 + r * 1.1, x1 - r * .7, x1 - r * 1.1):
        rug.append((x, cy - r * .5, x + rr.uniform(-1.5, 1.5), cy + r * .3))
    s += tracos(rug, '#5a170a', 1, .45)
    s += '</g>'
    s += f'<path d="M{n(x0 + r * 1.1)},{n(cy - r * .55)} C{n(CX - 40)},{n(cy - r * .8)} {n(CX + 40)},{n(cy - r * .8)} {n(x1 - r * 1.1)},{n(cy - r * .55)}" fill="none" stroke="#fff" stroke-opacity=".45" stroke-width="2.6" stroke-linecap="round" filter="{a.desfoque(.8)}"/>'
    s += f'<path d="M{n(x0 + r * 1.3)},{n(cy - r * .62)} C{n(x0 + 34)},{n(cy - r * .78)} {n(x0 + 50)},{n(cy - r * .8)} {n(x0 + 64)},{n(cy - r * .8)}" fill="none" stroke="#fff" stroke-opacity=".85" stroke-width="1.3" stroke-linecap="round"/>'
    s += f'<path d="M{n(x1 - r * 1.3)},{n(cy - r * .4)} C{n(x1 - r * .6)},{n(cy - r * .3)} {n(x1 - r * .25)},{n(cy)} {n(x1 - r * .3)},{n(cy + r * .3)}" fill="none" stroke="{ARO}" stroke-opacity=".5" stroke-width="1.4" stroke-linecap="round"/>'
    return s


def pao_frente(a, d):
    x0, x1, l, b = d.x0, d.x1, d.labio, d.base
    fora = suave([(x0 + 4, l + 12), (x0 + 14, l + 1), (x0 + 40, l - 2), (CX, l - 3), (x1 - 40, l - 2), (x1 - 14, l + 1), (x1 - 4, l + 12),
                  (x1 - 2, b - 18), (x1 - 14, b - 3), (x1 - 46, b), (x0 + 46, b), (x0 + 14, b - 3), (x0 + 2, b - 18)], t=.9)
    s = f'<path d="{fora}" fill="{a.radial(CROSTA, cx=.32, cy=.1, r=.95)}" filter="{a.textura("pao")}"/>'
    s += f'<path d="{fora}" fill="{a.linear([(0, "#000", 0), (.55, "#000", 0), (1, "#000", .3)])}"/>'
    s += f'<g clip-path="{a.recorte(fora)}">'
    s += (f'<path d="M{n(x1 - 30)},{n(l + 2)} C{n(x1 - 8)},{n(l + 6)} {n(x1 - 4)},{n(l + 20)} {n(x1 - 5)},{n(b - 14)}" fill="none" '
          f'stroke="#fff" stroke-opacity=".25" stroke-width="4" stroke-linecap="round" filter="{a.desfoque(1.5)}"/>')
    s += '</g>'
    labio = suave([(x0 + 10, l + 4), (x0 + 22, l - 2), (CX - 60, l - 4), (CX + 60, l - 4), (x1 - 22, l - 2), (x1 - 10, l + 4),
                   (x1 - 22, l + 5.5), (CX + 40, l + 3.5), (CX - 40, l + 3.5), (x0 + 22, l + 5.5)], t=.9)
    s += f'<path d="{labio}" fill="{a.linear(MIOLO)}"/>'
    s += realce(a, x0 + 84, l + 20, 52, 6, rot=-2, op=.32, blur=4)
    s += realce(a, x0 + 70, l + 16, 22, 2, rot=-2, op=.45, blur=1)
    return s


def batata_palha(a, cx, base, larg, alt, semente=1, qtd=200, soltas=()):
    """Monte de batata palha: palitos finos e dourados, em camadas (de baixo para cima)."""
    r = rng(semente)
    camadas = [('#c4842a', '#d99a38'), ('#eaa936', '#f4c050'), ('#fbd468', '#ffe596')]
    s = f'<ellipse cx="{n(cx)}" cy="{n(base - 1)}" rx="{n(larg * .5)}" ry="{n(alt * .28)}" fill="#3a1a05" opacity=".4" filter="{a.desfoque(3)}"/>'
    por = [.38, .34, .28]
    fase = r.uniform(0, 6)
    for k, (c1, c2) in enumerate(camadas):
        esc = 1 - k * .16
        todos, g1, g2 = [], [], []
        for i in range(int(qtd * por[k])):
            u = r.uniform(-1, 1)
            perfil = (1 - u * u) ** .7 * (1 + .12 * math.sin(u * 7 + fase))
            x = cx + u * larg / 2 * esc
            y = base - 2 - r.uniform(0, 1) ** .6 * alt * perfil * esc - k * 2.5
            ang = r.uniform(-1.1, 1.1) + (math.pi / 2 if r.random() < .12 else 0)
            L = r.uniform(7, 13)
            dx, dy = math.cos(ang) * L / 2, math.sin(ang) * L / 2 * .75
            sg = (x - dx, y - dy, x + dx, y + dy)
            todos.append(sg)
            (g1 if i % 2 else g2).append(sg)
        if k == 2:
            todos += list(soltas)
            g2 += list(soltas)
        s += segs(todos, '#82480f', 3, .85)
        s += segs(g1, c1, 1.8) + segs(g2, c2, 1.8)
        if k:
            s += segs([(x0, y0 - .45, (x0 + x1) / 2, (y0 + y1) / 2 - .45) for x0, y0, x1, y1 in todos[::2]], '#fffbe6', .7, .75)
    return s


def milho(a, pts, semente=1):
    r = rng(semente)
    grao = a.radial([(0, '#fff6b8'), (.5, '#f9cb36'), (1, '#d18f10')], cx=.38, cy=.3)
    sombras, graos, luz = [], [], []
    for x, y in pts:
        ang = math.radians(r.uniform(-40, 40))
        c, s_ = math.cos(ang), math.sin(ang)
        forma = [(-3.8, -1), (-3, -3.2), (0, -3.9), (3, -3.2), (3.8, -1), (3, 2.2), (0, 3.5), (-3, 2.2)]
        pts_ = [(x + px * c - py * s_, y + px * s_ + py * c) for px, py in forma]
        sombras.append([(px + .8, py + 1.4) for px, py in pts_])
        graos.append(pts_)
        luz.append((x - 1.3 * c + 1.4 * s_, y - 1.3 * s_ - 1.4 * c))
    out = formas(sombras, fill='#4a2200', opacity='.35')
    for g in graos:
        out += f'<path d="{suave(g, t=.8)}" fill="{grao}"/>'
    out += pontos(luz, '#fff', 2, .85)
    return out


def molho(a, cores, x0, x1, topo, fundo_y, semente=1, ondas=7, amp=4):
    """Camada de molho brilhante sobre a salsicha (a borda de baixo fica escondida pelo pão da frente)."""
    r = rng(semente)
    pts = []
    for i in range(ondas * 2 + 1):
        x = x0 + (x1 - x0) * i / (ondas * 2)
        y = topo + (amp if i % 2 else -amp * .4) + r.uniform(-1.5, 1.5)
        pts.append((x, y))
    contorno = suave(pts, fechado=False) + f' L{n(x1 + 4)},{n(topo + 8)} L{n(x1)},{n(fundo_y)} L{n(x0)},{n(fundo_y)} L{n(x0 - 4)},{n(topo + 8)}Z'
    s = f'<path d="{contorno}" fill="#000" opacity=".3" transform="translate(0,3)" filter="{a.desfoque(2)}"/>'
    s += f'<path d="{contorno}" fill="{a.linear(cores)}"/>'
    s += f'<path d="{suave([(x, y + 2.4) for x, y in pts[1:-1]], fechado=False)}" fill="none" stroke="#fff" stroke-opacity=".55" stroke-width="1.6" stroke-linecap="round"/>'
    return s


def pingos_labio(a, d, xs, cores, semente=1):
    """Molho escorrendo por cima do lábio do pão da frente."""
    r = rng(semente)
    s = ''
    for x in xs:
        s += gota(a, x, d.labio - 5, r.uniform(9, 19), r.uniform(7, 11), cores, brilho=.55)
    return s


def bacon_pedacos(a, pts, semente=1):
    """Bacon picado e crocante: lascas irregulares, carne avermelhada com faixa de gordura e bordas tostadas."""
    r = rng(semente)
    sombras, carnes, tostas, gord, luz = [], [], [], [], []
    for x, y in pts:
        w, h = r.uniform(12, 17), r.uniform(6.5, 9)
        ang = math.radians(r.uniform(-35, 35))
        c, s_ = math.cos(ang), math.sin(ang)
        T = lambda px, py: (x + px * c - py * s_, y + px * s_ + py * c)
        cont = [(-w / 2, -h * .3), (-w * .25, -h / 2 + r.uniform(-1, 1)), (w * .1, -h * .42), (w / 2, -h / 2 + r.uniform(0, 1.5)),
                (w * .42, h * .1), (w / 2 - 1, h / 2), (-w * .05, h * .42 + r.uniform(-1, 1)), (-w / 2 + 1, h / 2)]
        pts_ = [T(px, py) for px, py in cont]
        sombras.append([(px + 1, py + 1.8) for px, py in pts_])
        tostas.append(pts_)
        carnes.append([T(px * .8, py * .7 - .4) for px, py in cont])
        gord.append((*T(-w * .38, -h * .02), *T(w * .4, -h * .14)))
        luz.append((*T(-w * .3, -h * .3), *T(w * .05, -h * .34)))
    s = formas(sombras, fill='#1a0500', opacity='.45')
    s += formas(tostas, fill='#5a1a0a', stroke='#2e0a02', stroke_width='.8', stroke_linejoin='round')
    s += formas(carnes, fill='#a8361f')
    s += segs(gord, '#f6d0b0', 2.2)
    s += segs([(x0, y0 + 1.5, x1, y1 + 1.5) for x0, y0, x1, y1 in gord], '#d4583a', 1.3, .9)
    s += segs(luz, '#ffffff', .9, .55)
    return s


def bacon_tira(a, x0, y0, L, ang, semente=1):
    """Tira curta de bacon crocante e ondulada."""
    r = rng(semente)
    c, s_ = math.cos(math.radians(ang)), math.sin(math.radians(ang))
    fase = r.uniform(0, 3)

    def lin(dy):
        pts = []
        for i in range(9):
            t = L * i / 8
            yy = dy + 3.2 * math.sin(t / 7 + fase)
            pts.append((x0 + t * c - yy * s_, y0 + t * s_ + yy * c))
        return suave(pts, fechado=False)
    s = f'<path d="{lin(1.2)}" fill="none" stroke="#000" stroke-opacity=".4" stroke-width="11" stroke-linecap="round" filter="{a.desfoque(1.4)}"/>'
    s += f'<path d="{lin(0)}" fill="none" stroke="#3e0f05" stroke-width="10.5" stroke-linecap="round"/>'
    s += f'<path d="{lin(0)}" fill="none" stroke="#9e3119" stroke-width="8.5" stroke-linecap="round"/>'
    s += f'<path d="{lin(-1.9)}" fill="none" stroke="#cf5f3a" stroke-width="3" stroke-linecap="round"/>'
    s += f'<path d="{lin(1.2)}" fill="none" stroke="#f3c09c" stroke-width="2" stroke-linecap="round"/>'
    s += f'<path d="{lin(3.1)}" fill="none" stroke="#5e1a0a" stroke-width="1.4" stroke-linecap="round"/>'
    s += f'<path d="{lin(-3.3)}" fill="none" stroke="#fff" stroke-opacity=".4" stroke-width=".9" stroke-linecap="round"/>'
    return s


def fatia_queijo(a, x, topo, labio, w, L, semente=1):
    """Fatia de queijo derretida, caindo por cima da salsicha e do lábio do pão."""
    r = rng(semente)
    q = suave([(x - w / 2, topo + 3), (x - w * .2, topo - 1), (x + w * .25, topo - 1.5), (x + w / 2, topo + 2),
               (x + w / 2 - 2, labio + L * .45), (x + w * .18, labio + L * .55), (x + 2, labio + L), (x - w * .15, labio + L * .5),
               (x - w / 2 + 2, labio + L * .3)], t=.8)
    s = f'<path d="{q}" fill="#000" opacity=".3" transform="translate(1,2.5)" filter="{a.desfoque(1.5)}"/>'
    s += f'<path d="{q}" fill="{a.linear([(0, "#ffe68a"), (.5, "#ffd04a"), (1, "#eda61a")])}"/>'
    s += f'<path d="{q}" fill="none" stroke="#b97a08" stroke-opacity=".35" stroke-width=".8"/>'
    s += f'<path d="M{n(x - w * .36)},{n(topo + 2.5)} Q{n(x)},{n(topo - 1)} {n(x + w * .36)},{n(topo + 2)}" fill="none" stroke="#fff" stroke-opacity=".75" stroke-width="1.4" stroke-linecap="round"/>'
    s += realce(a, x - 2, labio + L * .35, 1.4, L * .2, op=.6, blur=.4)
    return s


def pure_monte(a, x0, x1, topo, fundo_y, semente=1, ondas=10):
    """Purê de batata cremoso sobre as salsichas: cristas de colher, pontas arredondadas."""
    r = rng(semente)
    cristas = []
    for i in range(ondas + 1):
        x = x0 + 14 + (x1 - x0 - 28) * i / ondas
        cristas.append((x, topo + (-6 if i % 2 else 2.5) + r.uniform(-1.5, 1.5)))
    cont = [(x0 + 2, fundo_y), (x0 - 2, topo + 14), (x0 + 4, topo + 4)] + cristas + [(x1 - 4, topo + 4), (x1 + 2, topo + 14), (x1 - 2, fundo_y)]
    d = curva(cont, t=.85)
    s = f'<path d="{d}" fill="#2a1500" opacity=".35" transform="translate(1 4)" filter="{a.desfoque(2.5)}"/>'
    s += f'<path d="{d}" fill="{a.linear([(0, "#fffef9"), (.3, "#fbf2da"), (.7, "#ecd4a0"), (1, "#c49f62")])}" stroke="#a8824a" stroke-opacity=".55" stroke-width="1"/>'
    s += f'<g clip-path="{a.recorte(d)}">'
    # marcas da espátula: cristas longas e interrompidas ao longo do monte
    cristas_d = ''
    for k, y in enumerate((topo + 9, topo + 18, topo + 27)):
        fase = r.uniform(0, 6)
        xa = x0 + 12 + r.uniform(0, 20)
        while xa < x1 - 30:
            xb = min(x1 - 10, xa + r.uniform(40, 70))
            xm = (xa + xb) / 2
            cristas_d += f'M{m(xa)} {m(y)}Q{m((xa + xm) / 2)} {m(y - 3)} {m(xm)} {m(y)}T{m(xb)} {m(y)}'
            xa = xb + r.uniform(10, 22)
    s += f'<path d="{cristas_d}" fill="none" stroke="#a8824a" stroke-opacity=".45" stroke-width="2.8" stroke-linecap="round" filter="{a.desfoque(.9)}"/>'
    s += f'<path d="{cristas_d}" fill="none" stroke="#fff" stroke-opacity=".9" stroke-width="1.3" stroke-linecap="round" transform="translate(0 -2)"/>'
    s += f'<rect x="{m(x0 - 4)}" y="{m(topo + 8)}" width="{m(x1 - x0 + 8)}" height="{m(fundo_y - topo)}" fill="{a.linear([(0, "#000", 0), (1, "#5a3a10", .3)])}"/>'
    s += f'<path d="M{m(x1 - 6)} {m(topo + 2)}Q{m(x1 + 2)} {m(topo + 10)} {m(x1 - 1)} {m(fundo_y - 4)}" fill="none" stroke="{ARO}" stroke-opacity=".6" stroke-width="1.6"/>'
    s += '</g>'
    return s


def graos_milho(a, pts, semente=1):
    """Grãos de milho graúdos e amarelos (cantos arredondados, com brilho), em montinhos."""
    r = rng(semente)
    cor = a.linear([(0, '#fff3a8'), (.45, '#ffd43c'), (1, '#e59a0a')])
    sombras, corpo, luz = [], '', []
    for x, y in pts:
        ang = r.uniform(-50, 50)
        c, s_ = math.cos(math.radians(ang)), math.sin(math.radians(ang))
        sombras.append([(x + px * c - py * s_ + 1, y + px * s_ + py * c + 2) for px, py in ((-3.4, -4), (3.4, -4), (3, 4.2), (-3, 4.2))])
        corpo += (f'<rect x="-3.6" y="-4.6" width="7.2" height="8.8" rx="3" transform="translate({m(x)} {m(y)}) rotate({m(ang)})" '
                  f'fill="{cor}" stroke="#b97606" stroke-opacity=".5" stroke-width=".6"/>')
        luz.append((x - 1.2 * c + 1.8 * s_, y - 1.2 * s_ - 1.8 * c))
    return formas(sombras, fill='#3a1e00', opacity='.35') + corpo + pts_m(luz, '#fff', 2.2, .9)


# ---------------------------------------------------------------- cachorros-quentes

VERMELHO = [(0, '#f25c3c'), (.4, '#d42e1c'), (1, '#8a1408')]
CHEDDAR = [(0, '#ffc54e'), (.45, '#f39314'), (1, '#c25f04')]
PURE = [(0, '#fffbea'), (.5, '#f7e8bc'), (1, '#dcc58c')]


def hotdog_svg(titulo, tipo):
    a = Arte(titulo)
    corpo = fundo(a) + sombra(a, cy=256, rx=168, ry=10)
    dentro_b, frente_b = bandeja(a)
    corpo += dentro_b
    d = Dog() if tipo != 'especial' else Dog(topo=112, eixo=162, labio=188)
    corpo += pao_tras(a, d)
    r = rng(7)
    if tipo == 'especial':
        corpo += salsicha(a, 42, 348, d.eixo - 9, r=15, semente=2)
        corpo += sombra_contato(a, 60, 336, d.eixo + 5, alt=6, op=.4)
        corpo += salsicha(a, 52, 358, d.eixo + 9, r=16, semente=3)
    else:
        corpo += salsicha(a, 38, 362, d.eixo, r=18, semente=1)
    if tipo == 'tradicional':
        corpo += molho(a, VERMELHO, 82, 318, d.eixo - 16, d.labio + 6, semente=3)
        pedac = [(r.uniform(90, 310), d.eixo - r.uniform(4, 14)) for _ in range(20)]
        corpo += pontos(pedac, '#ff8f6c', 3.4, .85) + pontos([(x - .9, y - .9) for x, y in pedac], '#fff', 1.1, .7)
        corpo += pao_frente(a, d)
        corpo += pingos_labio(a, d, (100, 142, 246, 296), VERMELHO, semente=2)
        corpo += milho(a, [(98, 166), (114, 172), (106, 158), (288, 166), (304, 160), (276, 174), (316, 170), (132, 166),
                           (262, 162), (86, 170), (150, 174), (246, 174), (204, 178), (126, 180), (282, 182)], semente=5)
        corpo += batata_palha(a, 200, d.eixo + 4, 150, 48, semente=4, qtd=230,
                              soltas=((90, 196, 100, 192), (314, 198, 304, 203), (176, 202, 188, 206)))
    elif tipo == 'especial':
        corpo += pure_monte(a, 76, 324, d.eixo - 19, d.labio + 6, semente=4)
        corpo += pao_frente(a, d)
        for x, w, L, sem in ((122, 40, 16, 1), (280, 42, 20, 2)):
            corpo += fatia_queijo(a, x, d.eixo - 26, d.labio, w, L, semente=sem)
        corpo += graos_milho(a, [(92, 160), (101, 152), (108, 163), (84, 168), (150, 150), (160, 158), (144, 162),
                                 (246, 148), (238, 157), (252, 160), (306, 152), (316, 161), (300, 164), (322, 150),
                                 (196, 186), (210, 190), (130, 184), (266, 186)], semente=6)
        corpo += batata_palha(a, 198, d.eixo - 6, 100, 44, semente=8, qtd=128)
    else:   # bacon & cheddar
        corpo += molho(a, CHEDDAR, 80, 320, d.eixo - 17, d.labio + 6, semente=5, ondas=6, amp=5)
        corpo += pao_frente(a, d)
        corpo += pingos_labio(a, d, (96, 136, 184, 256, 302), CHEDDAR, semente=6)
        corpo += bacon_tira(a, 84, 160, 62, 8, semente=1)
        corpo += bacon_tira(a, 260, 166, 64, -10, semente=2)
        corpo += bacon_pedacos(a, [(110, 178), (138, 170), (164, 178), (240, 176), (296, 174), (320, 168), (150, 186),
                                   (252, 186), (284, 184), (100, 186), (224, 182)], semente=9)
        corpo += batata_palha(a, 198, d.eixo + 2, 108, 42, semente=10, qtd=160)
        corpo += bacon_pedacos(a, [(176, 150), (214, 146), (196, 160), (232, 158), (162, 162)], semente=12)
    corpo += frente_b
    return a.svg(corpo)


# ---------------------------------------------------------------- planos em 3/4 (transformações afins)
#
# Cada superfície plana (topo do pão, face do corte, tampo da tábua) é desenhada
# em coordenadas locais dentro de um <g transform="matrix(...)">: formas simples
# (rect, arcos, poucas curvas), sombreamento por degradê e arquivos pequenos.

def k3(v):
    s = f'{v:.3f}'.rstrip('0').rstrip('.')
    return '0' if s in ('-0', '') else s


def mat_chao(v, z=0, ox=0, oy=0):
    """(x, y) do plano horizontal de altura z → tela (y local aponta para o fundo)."""
    x0, y0 = v.p(ox, oy, z)
    return f'matrix({k3(v.c)} {k3(-v.s * v.se)} {k3(-v.s)} {k3(-v.c * v.se)} {m(x0)} {m(y0)})'


def mat_parede(v, ox=0, oy=0, ang=0):
    """(u, y) do plano vertical por (ox, oy) na direção `ang` (graus) → tela. y local = -altura (cresce para baixo)."""
    t = math.radians(ang)
    c, s = v.rot(math.cos(t), math.sin(t))
    x0, y0 = v.p(ox, oy, 0)
    return f'matrix({k3(c)} {k3(-s * v.se)} 0 {k3(v.ce)} {m(x0)} {m(y0)})'


def curva(pts, fechado=True, t=1.0):
    """Como estilo.suave, mas com 1 casa decimal."""
    k = len(pts)
    ext = pts if fechado else [pts[0]] + list(pts) + [pts[-1]]
    ini, fim = (0, k) if fechado else (1, len(ext) - 2)
    d = f'M{m(pts[0][0])} {m(pts[0][1])}'
    for i in range(ini, fim):
        p0, p1, p2, p3 = ext[(i - 1) % len(ext)], ext[i % len(ext)], ext[(i + 1) % len(ext)], ext[(i + 2) % len(ext)]
        c1 = (p1[0] + (p2[0] - p0[0]) / 6 * t, p1[1] + (p2[1] - p0[1]) / 6 * t)
        c2 = (p2[0] - (p3[0] - p1[0]) / 6 * t, p2[1] - (p3[1] - p1[1]) / 6 * t)
        d += f'C{m(c1[0])} {m(c1[1])} {m(c2[0])} {m(c2[1])} {m(p2[0])} {m(p2[1])}'
    return d + ('Z' if fechado else '')


def pts_m(lista, cor, larg, op=1):
    """Pontinhos (traço de comprimento zero) num só <path>, coordenadas compactas."""
    if not lista:
        return ''
    d = ''.join(f'M{m(x)} {m(y)}h0' for x, y in lista)
    o = '' if op == 1 else f' stroke-opacity="{n(op)}"'
    return f'<path d="{d}" stroke="{cor}" stroke-width="{n(larg)}" stroke-linecap="round"{o}/>'


def onda(x0, x1, y, amp, k, r, fase=0.0):
    """Pontos de uma borda ondulada de x0 a x1."""
    return [(x0 + (x1 - x0) * i / k, y + amp * math.sin(i * 2.1 + fase) + r.uniform(-amp, amp) * .4) for i in range(k + 1)]


def faixa_ondulada(x0, x1, yt, yb, amp, r, k=8):
    """Faixa horizontal com as duas bordas onduladas (yt em cima, yb embaixo; y cresce para baixo)."""
    cima = onda(x0, x1, yt, amp, k, r, r.uniform(0, 6))
    baixo = onda(x1, x0, yb, amp, k, r, r.uniform(0, 6))
    return curva(cima, fechado=False) + curva(baixo, fechado=False).replace('M', 'L', 1) + 'Z', cima


# ---------------------------------------------------------------- apoios: tábua e prato

def tabua_ret(a, cx, cy, larg, prof, alt=10, elev=30, raio=16, semente=3):
    """Tábua retangular de madeira em 3/4. Devolve (svg, Vista do tampo)."""
    v = Vista(cx, cy, elev=elev)
    ret = f'x="{m(-larg / 2)}" y="{m(-prof / 2)}" width="{m(larg)}" height="{m(prof)}" rx="{m(raio)}"'
    s = f'<rect transform="{mat_chao(v, 0)}" {ret} fill="{a.linear([(0, "#7a4420"), (.4, "#5e3216"), (1, "#3a1c0a")], 0, 0, 1, 0)}"/>'
    s += f'<g transform="{mat_chao(v, alt)}">'
    s += f'<rect {ret} fill="{a.radial([(0, "#b77a46"), (.55, "#9a5f32"), (1, "#7a4422")], cx=.38, cy=.62, r=.75)}" filter="{a.textura("fino")}"/>'
    r = rng(semente)
    veios = ''
    for k in range(9):
        y = -prof / 2 + 10 + k * (prof - 20) / 8 + r.uniform(-3, 3)
        x0 = -larg / 2 + r.uniform(12, 50)
        x1 = larg / 2 - r.uniform(12, 50)
        mx = (x0 + x1) / 2 + r.uniform(-60, 60)
        veios += f'M{m(x0)} {m(y)}Q{m(mx)} {m(y + r.uniform(-7, 7))} {m(x1)} {m(y + r.uniform(-3, 3))}'
    s += f'<path d="{veios}" fill="none" stroke="#4e2a10" stroke-opacity=".35" stroke-width="1.1"/>'
    s += f'<rect {ret} fill="none" stroke="#e8b682" stroke-opacity=".6" stroke-width="1.4"/>'
    s += '</g>'
    return s, Vista(cx, cy - alt * v.ce, elev=elev)


def prato_retangular(a, cx, cy, larg, prof, alt=7, elev=30):
    """Prato retangular de cerâmica branca em 3/4. Devolve (svg, Vista da superfície)."""
    v = Vista(cx, cy, elev=elev)
    ret = f'x="{m(-larg / 2)}" y="{m(-prof / 2)}" width="{m(larg)}" height="{m(prof)}" rx="20"'
    s = f'<rect transform="{mat_chao(v, 0)}" {ret} fill="{a.linear([(0, "#e8e2d8"), (.5, "#b9b0a3"), (1, "#7c7469")], 0, 0, 1, 0)}"/>'
    s += f'<g transform="{mat_chao(v, alt)}">'
    s += f'<rect {ret} fill="{a.radial([(0, "#fffefb"), (.6, "#f1ece4"), (1, "#d6cec2")], cx=.36, cy=.64, r=.8)}"/>'
    dentro = f'x="{m(-larg / 2 + 16)}" y="{m(-prof / 2 + 14)}" width="{m(larg - 32)}" height="{m(prof - 28)}" rx="12"'
    s += f'<rect {dentro} fill="{a.linear([(0, "#fbf8f2"), (.7, "#eee8de"), (1, "#ddd5c8")])}"/>'
    s += f'<rect {dentro} fill="none" stroke="#a89f92" stroke-opacity=".35" stroke-width="2.5" transform="translate(0 1.5)" filter="{a.desfoque(1.5)}"/>'
    s += f'<rect {ret} fill="none" stroke="#fff" stroke-opacity=".9" stroke-width="1.4"/>'
    s += '</g>'
    return s, Vista(cx, cy - (alt - 1.5) * v.ce, elev=elev)


# ---------------------------------------------------------------- sanduíche de pão de forma, metade triangular

def tri_local(L, raios=(3, 3, 12)):
    """Metade de fatia cortada na diagonal: hipotenusa na frente (y=0), ponta reta no fundo; cantos arredondados."""
    A, B, C = (-L / 2, 0), (L / 2, 0), (0, L / 2)

    def em(P, Q, d):
        dx, dy = Q[0] - P[0], Q[1] - P[1]
        h = math.hypot(dx, dy)
        return P[0] + dx * d / h, P[1] + dy * d / h
    d = ''
    for i, (P, Q, R, rc) in enumerate(((A, B, C, raios[0]), (B, C, A, raios[1]), (C, A, B, raios[2]))):
        e, s_ = em(P, R, rc), em(P, Q, rc)
        d += ('M' if i == 0 else 'L') + f'{m(e[0])} {m(e[1])}Q{m(P[0])} {m(P[1])} {m(s_[0])} {m(s_[1])}'
    return d + 'Z'


PAO_BRANCO = {
    'miolo': ('#fdebc4', '#efcd92'), 'poro': '#c99a5c', 'casca': ('#8a4410', '#d08a3a'),
    'topo': [(0, '#f8cf82'), (.5, '#e6a24c'), (1, '#b56a28')], 'borda': '#7a3a12',
}
PAO_INTEGRAL = {
    'miolo': ('#dcb382', '#bf8e5a'), 'poro': '#5e3418', 'casca': ('#4a2810', '#7a4a24'),
    'topo': [(0, '#c9935c'), (.5, '#a26a38'), (1, '#6e3e1a')], 'borda': '#40200a',
}

CAMADAS = {
    # cor clara, cor escura, borda ondulada (amplitude)
    'queijo': ('#ffe27a', '#f4ae1c', .9),
    'presunto': ('#f6b4b4', '#d9727e', .8),
    'frango': ('#fff3dc', '#e0bd86', 1.1),
    'cenoura': ('#ffa040', '#e45e0a', 1.0),
    'alface': ('#b6e46e', '#4f9c2c', 1.4),
    'maionese': ('#fffdf6', '#efe6cf', .6),
    'tomate': ('#ff6a50', '#c8261a', .5),
}


def meia_fatia(a, v, L, camadas, pao, semente=1, marcas=True, extra=None, topo_extra=None):
    """Metade triangular de sanduíche em 3/4: face do corte (camadas) na frente e o topo do pão.

    v: Vista com origem no meio da hipotenusa, no apoio. camadas: [(espessura, tipo)] de baixo para cima.
    extra(H, r) → svg no plano da face (u, y com y = -altura), por cima das camadas (queijo escorrendo, folhas).
    topo_extra(L, r) → svg no plano do topo (grãos, etc.)."""
    r = rng(semente)
    H = sum(e for e, _ in camadas)
    hw = L / 2 - 1.2
    tri = tri_local(L)
    # sombra no apoio
    s = (f'<g transform="{mat_chao(v, 0)}"><path d="{tri}" fill="#1e0e04" opacity=".7" transform="translate(9 -3) scale(1.05)" '
         f'filter="{a.desfoque(5)}"/><rect x="{m(-L / 2 - 4)}" y="-6.5" width="{m(L + 12)}" height="7" rx="3.5" fill="#1e0e04" opacity=".55" '
         f'filter="{a.desfoque(2.5)}"/></g>')
    # face do corte (y local para baixo: o pão de baixo vai de -esp a 0)
    face = (f'M{m(-hw)} -2Q{m(-hw)} 0 {m(-hw + 3)} 0H{m(hw - 3)}Q{m(hw)} 0 {m(hw)} -2V{m(-H + 3)}Q{m(hw)} {m(-H)} {m(hw - 4)} {m(-H)}'
            f'H{m(-hw + 4)}Q{m(-hw)} {m(-H)} {m(-hw)} {m(-H + 3)}Z')
    s += f'<g transform="{mat_parede(v)}">'
    s += f'<path d="{face}" fill="#000" opacity=".55" transform="translate(0 1.5)" filter="{a.desfoque(1.6)}"/>'
    s += f'<g clip-path="{a.recorte(face)}">'
    z = 0
    for esp, tipo in camadas:
        yb, yt = -z, -z - esp
        z += esp
        if tipo == 'pao':
            baixo = yb == 0
            c1, c2 = pao['miolo']
            e1, e2 = pao['casca']
            st = ([(0, c2), (.64, c1), (.86, e2), (1, e1)] if baixo else [(0, e1), (.14, e2), (.36, c1), (1, c2)])
            s += f'<rect x="{m(-hw)}" y="{m(yt)}" width="{m(2 * hw)}" height="{m(esp)}" fill="{a.linear(st)}" filter="{a.textura("pao")}"/>'
            lo, hi = (yt + esp * .2, yb - esp * .3) if baixo else (yt + esp * .3, yb - esp * .2)
            poros = [(r.uniform(-hw + 5, hw - 5), r.uniform(lo, hi)) for _ in range(int(L * .2))]
            s += pts_m(poros, pao['poro'], 1.8, .5)
            # casca nas pontas da fatia
            s += f'<path d="M{m(-hw)} {m(yt)}h3.4v{m(esp)}h-3.4ZM{m(hw)} {m(yt)}h-3.4v{m(esp)}h3.4Z" fill="{e2}" opacity=".9"/>'
        else:
            claro, escuro, amp = CAMADAS[tipo]
            d, cima = faixa_ondulada(-hw - 2, hw + 2, yt - amp * .3, yb + amp * .3, amp, r, k=max(5, int(L / 26)))
            s += f'<path d="{d}" fill="{a.linear([(0, claro), (.35, claro), (1, escuro)])}"/>'
            if tipo == 'presunto':
                dobras = ''.join(f'M{m(x)} {m(yb - esp * .2)}q{m(r.uniform(-2, 2))} {m(-esp * .3)} {m(r.uniform(-1, 1))} {m(-esp * .6)}' for x in
                                 [r.uniform(-hw + 6, hw - 6) for _ in range(int(L / 30))])
                s += f'<path d="{dobras}" fill="none" stroke="#fbd6d4" stroke-width="1.2" stroke-linecap="round" stroke-opacity=".8"/>'
                s += f'<path d="{curva([(x, y + esp * .45) for x, y in cima], fechado=False)}" fill="none" stroke="#fff0ee" stroke-opacity=".5" stroke-width="1"/>'
            elif tipo == 'frango':
                fib = ''.join(f'M{m(x)} {m(y)}l{m(r.uniform(4, 9))} {m(r.uniform(-1.6, 1.6))}' for x, y in
                              [(r.uniform(-hw, hw - 6), r.uniform(yt + 1, yb - 1)) for _ in range(int(L * .2))])
                s += f'<path d="{fib}" fill="none" stroke="#c09058" stroke-width="1.3" stroke-linecap="round" stroke-opacity=".7"/>'
                fib2 = ''.join(f'M{m(x)} {m(y)}l{m(r.uniform(4, 8))} {m(r.uniform(-1.2, 1.2))}' for x, y in
                               [(r.uniform(-hw, hw - 6), r.uniform(yt + 1, yb - 1)) for _ in range(int(L * .14))])
                s += f'<path d="{fib2}" fill="none" stroke="#fffaf0" stroke-width="1.2" stroke-linecap="round" stroke-opacity=".85"/>'
            elif tipo == 'cenoura':
                fio = ''.join(f'M{m(x)} {m(y)}l{m(r.uniform(-6, 6))} {m(r.uniform(-1.5, 1.5))}' for x, y in
                              [(r.uniform(-hw, hw), r.uniform(yt + .5, yb - .5)) for _ in range(int(L * .15))])
                s += f'<path d="{fio}" fill="none" stroke="#ffcf7a" stroke-width="1.1" stroke-linecap="round" stroke-opacity=".8"/>'
            elif tipo in ('queijo', 'maionese'):
                s += f'<path d="{curva([(x, y + .9) for x, y in cima], fechado=False)}" fill="none" stroke="#fff" stroke-opacity=".7" stroke-width="1"/>'
    # luz: mais claro à esquerda, oclusão perto do apoio
    s += f'<rect x="{m(-hw)}" y="{m(-H)}" width="{m(2 * hw)}" height="{m(H)}" fill="{a.linear([(0, "#fff", .12), (.45, "#fff", 0), (1, "#2a1000", .22)], 0, 0, 1, 0)}"/>'
    s += f'<rect x="{m(-hw)}" y="{m(-H)}" width="{m(2 * hw)}" height="{m(H)}" fill="{a.linear([(.7, "#2a1000", 0), (1, "#2a1000", .4)])}"/>'
    s += '</g>'
    s += f'<path d="M{m(-hw + 4)} {m(-H + .7)}H{m(hw - 4)}" stroke="#fff3d8" stroke-opacity=".75" stroke-width="1.2" stroke-linecap="round"/>'
    if extra:
        s += extra(H, r)
    s += '</g>'
    # topo do pão
    s += f'<g transform="{mat_chao(v, H)}">'
    s += f'<path d="{tri}" fill="{a.radial(pao["topo"], cx=.42, cy=.38, r=.72)}" filter="{a.textura("pao")}"/>'
    s += f'<g clip-path="{a.recorte(tri)}">'
    s += (f'<path d="M{m(-L / 2)} 0L0 {m(L / 2)}L{m(L / 2)} 0" fill="none" stroke="{pao["borda"]}" stroke-opacity=".75" '
          f'stroke-width="9" stroke-linejoin="round" filter="{a.desfoque(2.6)}"/>')
    if marcas:
        riscos = ''.join(f'M{m(c - 60)} -10l75 75' for c in range(-L // 2 + 6, L // 2 + 30, 21))
        s += f'<path d="{riscos}" fill="none" stroke="#5a2408" stroke-opacity=".5" stroke-width="6.5" filter="{a.desfoque(1.2)}"/>'
        s += f'<path d="{riscos}" fill="none" stroke="#ffe0a6" stroke-opacity=".3" stroke-width="1.6" transform="translate(6.5 -1)"/>'
    if topo_extra:
        s += topo_extra(L, r)
    s += realce(a, -L * .14, L * .14, L * .17, L * .06, rot=8, op=.24, blur=4)
    s += '</g>'
    s += f'<path d="M{m(-L / 2 + 5)} .9H{m(L / 2 - 5)}" stroke="#ffe7bc" stroke-opacity=".7" stroke-width="1.3" stroke-linecap="round"/>'
    s += '</g>'
    return s


def pingo_mole(a, x, y, L, w, cores, brilho=.75):
    """Escorrido que afina até uma ponta redonda (sem "bolinha"), de (x, y) para baixo."""
    b = w * .3
    d = (f'M{m(x - w / 2)} {m(y)}C{m(x - w / 2)} {m(y + L * .45)} {m(x - b * 1.1)} {m(y + L * .6)} {m(x - b)} {m(y + L - b)}'
         f'A{m(b)} {m(b)} 0 0 0 {m(x + b)} {m(y + L - b)}C{m(x + b * 1.1)} {m(y + L * .6)} {m(x + w / 2)} {m(y + L * .45)} {m(x + w / 2)} {m(y)}Z')
    s = f'<path d="{d}" fill="{a.linear(cores, 0, 0, 1, 0)}"/>'
    s += f'<path d="M{m(x - w * .16)} {m(y + 1.5)}Q{m(x - w * .2)} {m(y + L * .5)} {m(x - b * .4)} {m(y + L - b * 1.4)}" fill="none" stroke="#fff" stroke-opacity="{n(brilho)}" stroke-width="{n(max(.8, w * .14))}" stroke-linecap="round"/>'
    return s


QUEIJO_LAB = ([(0, '#fff3b0'), (.4, '#ffd640'), (1, '#e8a010')], [(0, '#e89a0c'), (.35, '#ffe892'), (.65, '#ffd040'), (1, '#d98a06')], '#3a1a00')
MAIONESE_LAB = ([(0, '#ffffff'), (.5, '#fbf6e8'), (1, '#e2d6b8')], [(0, '#ddd0b0'), (.35, '#fffdf6'), (.7, '#f6efdc'), (1, '#cfc2a0')], '#3a2a10')


def labio_derretido(a, u0, u1, z, r, pingos=((.5, 14),), cores=QUEIJO_LAB, grosso=1.0):
    """No plano da face: recheio cremoso escapando do corte na altura z (lábio ondulado) e escorridos [(posição 0–1, comprimento)]."""
    lab, ping, somb = cores
    k = 6
    cima = [(u0 + (u1 - u0) * i / k, -z - (2.4 + r.uniform(0, 1)) * grosso) for i in range(k + 1)]
    baixo = [(u0 + (u1 - u0) * i / k, -z + (2 + abs(math.sin(i * 1.7 + r.uniform(0, 2))) * 4.5) * grosso) for i in range(k, -1, -1)]
    cima[0] = (u0, -z)
    cima[-1] = (u1, -z)
    d = curva(cima, fechado=False) + curva(baixo, fechado=False).replace('M', 'L', 1) + 'Z'
    s = f'<path d="{d}" fill="{somb}" opacity=".3" transform="translate(.8 2)" filter="{a.desfoque(1.2)}"/>'
    s += f'<path d="{d}" fill="{a.linear(lab)}"/>'
    s += f'<path d="M{m(u0 + 5)} {m(-z - 1.2 * grosso)}H{m(u1 - 5)}" stroke="#fff" stroke-opacity=".85" stroke-width="1.3" stroke-linecap="round"/>'
    for t, comp in pingos:
        x = u0 + (u1 - u0) * t
        s += pingo_mole(a, x, -z + 2.5 * grosso, comp, r.uniform(6.5, 8.5) * grosso, ping)
    return s


def misto_quente():
    a = Arte('Ilustração de misto quente')
    elev = 36
    corpo = fundo(a) + sombra(a, cy=246, rx=150, ry=12)
    tab, vt = tabua_ret(a, 200, 222, 300, 136, alt=11, elev=elev)
    corpo += tab
    camadas = [(13, 'pao'), (5, 'queijo'), (10, 'presunto'), (5, 'queijo'), (12, 'pao')]
    L = 178

    def derretido(H, r):
        s = labio_derretido(a, -L * .44, -L * .16, 15.5, r, pingos=((.3, 16), (.78, 9)))
        s += labio_derretido(a, L * .06, L * .34, 15.5, r, pingos=((.55, 12),))
        s += labio_derretido(a, -L * .12, L * .14, 30.5, r, pingos=((.4, 13),))
        return s
    for (bx, by, yaw, sem) in ((52, 22, -20, 2), (-56, -22, 12, 1)):
        x0, y0 = vt.p(bx, by, 0)
        corpo += meia_fatia(a, Vista(x0, y0, yaw=yaw, elev=elev), L, camadas, PAO_BRANCO, semente=sem, extra=derretido)
    return a.svg(corpo)


def babado_alface(a, u0, u1, z, r, amp=5):
    """No plano da face: folha de alface escapando do corte na altura z, com a borda crespa caindo."""
    k = int((u1 - u0) / 12)
    cima = [(u0 + (u1 - u0) * i / k, -z - 1.5 + r.uniform(-.8, .8)) for i in range(k + 1)]
    baixo = [(u0 + (u1 - u0) * i / k + r.uniform(-1.5, 1.5), -z + (amp + r.uniform(0, 2.5) if i % 2 else 1.5))
             for i in range(k, -1, -1)]
    d = curva(cima, fechado=False) + curva(baixo, fechado=False, t=.8).replace('M', 'L', 1) + 'Z'
    s = f'<path d="{d}" fill="#0e2a04" opacity=".35" transform="translate(.6 1.8)" filter="{a.desfoque(1)}"/>'
    s += f'<path d="{d}" fill="{a.linear([(0, "#d4f590"), (.4, "#86cc4c"), (1, "#3f8a24")])}"/>'
    s += f'<path d="{curva(cima, fechado=False)}" fill="none" stroke="#f2ffd6" stroke-opacity=".8" stroke-width="1.1"/>'
    return s


def sanduiche_natural():
    a = Arte('Ilustração de sanduíche natural')
    elev = 36
    corpo = fundo(a) + sombra(a, cy=246, rx=150, ry=12)
    prato, vp = prato_retangular(a, 200, 224, 304, 134, alt=8, elev=elev)
    corpo += prato
    camadas = [(11, 'pao'), (4, 'alface'), (13, 'frango'), (6, 'cenoura'), (3, 'maionese'), (11, 'pao')]
    L = 178

    def recheio(H, r):
        s = babado_alface(a, -L / 2 + 3, L / 2 - 3, 13.5, r, amp=6.5)
        fios = ''.join(f'M{m(x)} {m(-30 + r.uniform(-2, 2))}q{m(r.uniform(-3, 3))} {m(r.uniform(1, 3))} {m(r.uniform(-4, 4))} {m(r.uniform(3, 6))}'
                       for x in [r.uniform(-L * .46, L * .46) for _ in range(20)])
        s += f'<path d="{fios}" stroke="#e8680e" stroke-width="1.9" stroke-linecap="round" fill="none"/>'
        s += labio_derretido(a, -L * .42, -L * .08, 35.5, r, pingos=((.4, 9),), cores=MAIONESE_LAB, grosso=.8)
        s += labio_derretido(a, L * .12, L * .4, 35.5, r, pingos=((.6, 7),), cores=MAIONESE_LAB, grosso=.8)
        return s

    def graos(L, r):
        pts = [(r.uniform(-L * .44, L * .44), r.uniform(3, L * .44)) for _ in range(90)]
        pts = [(x, y) for x, y in pts if y < L / 2 - abs(x) - 3]
        flocos = ''.join(f'M{m(x)} {m(y)}l{m(r.uniform(2, 3.5))} {m(r.uniform(-1.5, 1.5))}' for x, y in pts[::3])
        s = f'<path d="{flocos}" stroke="#5a3010" stroke-width="3.6" stroke-linecap="round" stroke-opacity=".35" transform="translate(.5 -1)"/>'
        s += f'<path d="{flocos}" stroke="#f0d8a8" stroke-width="3" stroke-linecap="round"/>'
        s += pts_m(pts[1::3], '#2e1606', 2, .65) + pts_m(pts[2::3], '#d9b47a', 1.6, .7)
        return s
    for (bx, by, yaw, sem) in ((-56, 22, 20, 3), (52, -22, -12, 4)):
        x0, y0 = vp.p(bx, by, 0)
        corpo += meia_fatia(a, Vista(x0, y0, yaw=yaw, elev=elev), L, camadas, PAO_INTEGRAL, semente=sem, marcas=False,
                            extra=recheio, topo_extra=graos)
    return a.svg(corpo)


# ---------------------------------------------------------------- beirute

BEIRUTE = [(4, 'pita'), (4, 'queijo'), (9, 'frango'), (5, 'tomate'), (4, 'alface'), (2.5, 'molho'), (4.5, 'pita')]
COR_B = {'pita': ('#f4d7a0', '#d9a660'), 'queijo': ('#ffe68a', '#f2b322'), 'frango': ('#e2b07a', '#a8693a'),
         'tomate': ('#ff6a4e', '#c42416'), 'alface': ('#b8e872', '#4c9a2a'), 'molho': ('#f4f6dc', '#c9d3a2')}


def face_beirute(a, u0, u1, r, H, detalhe=True):
    """Camadas do recheio no plano de uma face do corte (u de u0 a u1, y = -altura)."""
    s = ''
    z = 0
    w = u1 - u0
    for esp, tipo in BEIRUTE:
        yb, yt = -z, -z - esp
        z += esp
        c1, c2 = COR_B[tipo]
        if tipo == 'pita':
            casca = [(0, '#b26a26'), (.3, c2), (1, c1)] if yt < -H + 6 else [(0, c1), (.7, c2), (1, '#b26a26')]
            s += f'<rect x="{m(u0)}" y="{m(yt)}" width="{m(w)}" height="{m(esp)}" fill="{a.linear(casca)}"/>'
            continue
        if not detalhe:
            s += f'<rect x="{m(u0)}" y="{m(yt)}" width="{m(w)}" height="{m(esp)}" fill="{c1 if tipo != "frango" else c2}"/>'
            continue
        d, cima = faixa_ondulada(u0 - 1, u1 + 1, yt - .5, yb + .5, .8, r, k=max(4, int(w / 20)))
        s += f'<path d="{d}" fill="{a.linear([(0, c1), (1, c2)])}"/>'
        if tipo == 'frango':
            pedacos = []
            x = u0 + r.uniform(-2, 2)
            while x < u1 - 4:
                lw = r.uniform(9, 17)
                y0 = yt + r.uniform(-.6, 1.2)
                y1 = yb - r.uniform(-.4, 1)
                pedacos.append([(x, y0 + r.uniform(0, 2)), (x + lw * .5, y0 - r.uniform(0, 1)), (x + lw, y0 + r.uniform(0, 2)),
                                (x + lw + r.uniform(0, 1.5), (y0 + y1) / 2), (x + lw, y1), (x + lw * .5, y1 + r.uniform(0, .8)), (x, y1),
                                (x - r.uniform(0, 1.5), (y0 + y1) / 2)])
                x += lw + r.uniform(.5, 2)
            dd = ''.join(curva(pp, t=.8) for pp in pedacos)
            s += f'<path d="{dd}" fill="{a.linear([(0, "#b06a30"), (.2, "#e9c48a"), (.6, "#f4dcb0"), (1, "#c08048")])}"/>'
            marcas = ''.join(f'M{m(r.uniform(u0 + 3, u1 - 3))} {m(yt + 1.2)}l1.6 2.2' for _ in range(int(w / 10)))
            s += f'<path d="{marcas}" stroke="#6a3010" stroke-width="1.8" stroke-linecap="round" stroke-opacity=".75"/>'
        elif tipo == 'tomate':
            sem = [(r.uniform(u0 + 2, u1 - 2), (yt + yb) / 2 + r.uniform(-.6, .6)) for _ in range(int(w / 7))]
            s += pts_m(sem, '#ffd6a0', 2.3, .85)
        elif tipo == 'molho':
            s += pts_m([(r.uniform(u0, u1), (yt + yb) / 2) for _ in range(int(w / 5))], '#3d7a26', 1.5, .9)
        elif tipo == 'queijo':
            s += f'<path d="{curva([(x, y + .8) for x, y in cima], fechado=False)}" fill="none" stroke="#fff6c8" stroke-opacity=".8" stroke-width=".9"/>'
    if detalhe:   # queijo derretido escapando do corte, por cima do pão de baixo
        for t in (r.uniform(.1, .3), r.uniform(.55, .75)):
            x = u0 + w * t
            lw = r.uniform(14, 22)
            q = f'M{m(x)} -8C{m(x + lw * .3)} -8.6 {m(x + lw * .7)} -8.6 {m(x + lw)} -8C{m(x + lw * .9)} -5 {m(x + lw * .6)} -3.2 {m(x + lw * .45)} -2.2C{m(x + lw * .3)} -3 {m(x + lw * .1)} -5 {m(x)} -8Z'
            s += f'<path d="{q}" fill="{a.linear([(0, "#fff0a0"), (.5, "#ffd23a"), (1, "#e09a0c")])}"/>'
            s += f'<path d="M{m(x + lw * .25)} -7.2H{m(x + lw * .6)}" stroke="#fff" stroke-opacity=".8" stroke-width=".9" stroke-linecap="round"/>'
    return s


def borda_beirute(a, v, ox, oy, R, t0, t1, r):
    """Parede curva (aro) da cunha, de t0 a t1 (graus, no sentido horário da tela), com as camadas à mostra."""
    def pt(t, zz, rr=R):
        return v.p(ox + rr * math.cos(math.radians(t)), oy + rr * math.sin(math.radians(t)), zz)

    def arco(t_a, t_b, zz):
        x1, y1 = pt(t_b, zz)
        return f'A{m(R)} {m(R * v.se)} 0 0 {0 if t_b > t_a else 1} {m(x1)} {m(y1)}'

    s = ''
    z = 0
    for esp, tipo in BEIRUTE:
        za, zb = z, z + esp
        z = zb
        c1, c2 = {'pita': ('#e9b878', '#a0602a'), 'frango': ('#f2d3a2', '#c8925a')}.get(tipo, COR_B[tipo])
        xa, ya = pt(t0, zb)
        xb, yb = pt(t1, za)
        d = f'M{m(xa)} {m(ya)}{arco(t0, t1, zb)}L{m(xb)} {m(yb)}{arco(t1, t0, za)}Z'
        s += f'<path d="{d}" fill="{a.linear([(0, tom(c1, .12)), (.45, c1), (1, tom(c2, -.12))], 0, 0, 1, 0)}"/>'
    # alface crespa escapando pela borda
    if abs(t1 - t0) > 30:
        k = max(3, int(abs(t1 - t0) / 8))
        fr = []
        for i in range(k + 1):
            t = t0 + (t1 - t0) * i / k
            x, y = pt(t, 24.5, R + 1.5)
            fr.append((x, y + (4 + r.uniform(0, 2) if 0 < i < k and i % 2 else 0)))
        s += f'<path d="{curva(fr, fechado=False)}" fill="none" stroke="#3f8a22" stroke-width="3.6" stroke-linecap="round"/>'
        s += f'<path d="{curva(fr, fechado=False)}" fill="none" stroke="#a6e060" stroke-width="1.4" stroke-linecap="round" transform="translate(0 -.9)"/>'
    # luz no alto da borda e oclusão perto da tábua
    xa, ya = pt(t0, z)
    s += f'<path d="M{m(xa)} {m(ya)}{arco(t0, t1, z)}" fill="none" stroke="#ffe3b0" stroke-opacity=".7" stroke-width="1.2"/>'
    xa, ya = pt(t0, 2.5)
    s += f'<path d="M{m(xa)} {m(ya)}{arco(t0, t1, 2.5)}" fill="none" stroke="#2a1000" stroke-opacity=".35" stroke-width="5" filter="{a.desfoque(1.5)}"/>'
    return s


def topo_beirute(a, v, ox, oy, R, t0, t1, H, r):
    """Tampa de pão sírio da cunha: dourada, com marcas da chapa e pintas tostadas."""
    c0, s0 = math.cos(math.radians(t0)), math.sin(math.radians(t0))
    c1, s1 = math.cos(math.radians(t1)), math.sin(math.radians(t1))
    setor = f'M0 0L{m(R * c0)} {m(R * s0)}A{m(R)} {m(R)} 0 0 1 {m(R * c1)} {m(R * s1)}Z'
    s = f'<g transform="{mat_chao(v, H, ox, oy)}">'
    s += f'<path d="{setor}" fill="{a.radial([(0, "#f4d094"), (.5, "#e6aa5c"), (.85, "#cc8a40"), (1, "#a0602a")], cx=0, cy=0, r=R, user=True)}" filter="{a.textura("pao")}"/>'
    s += f'<g clip-path="{a.recorte(setor)}">'
    riscos = ''.join(f'M{c - 200} -150l400 300' for c in range(-250, 260, 28))
    s += f'<path d="{riscos}" fill="none" stroke="#7a3c10" stroke-opacity=".34" stroke-width="7" filter="{a.desfoque(1.8)}"/>'
    s += f'<path d="{riscos}" fill="none" stroke="#fff0cc" stroke-opacity=".2" stroke-width="1.3" transform="translate(6.5 0)"/>'
    for _ in range(5):
        tt = math.radians(r.uniform(t0 + 12, t1 - 12))
        rr = R * r.uniform(.3, .85)
        s += f'<ellipse cx="{m(rr * math.cos(tt))}" cy="{m(rr * math.sin(tt))}" rx="{m(r.uniform(6, 11))}" ry="{m(r.uniform(4, 7))}" fill="#8a4410" opacity="{n(r.uniform(.3, .45))}" filter="{a.desfoque(2)}"/>'
    s += f'<path d="{setor}" fill="none" stroke="#fff6e0" stroke-opacity=".4" stroke-width="2" transform="translate(-1 1)" filter="{a.desfoque(1)}"/>'
    s += '</g></g>'
    return s


def beirute():
    a = Arte('Ilustração de beirute')
    elev, giro = 28, 25
    corpo = fundo(a) + sombra(a, cy=246, rx=150, ry=13)
    # tábua redonda de madeira
    cy_t = 186
    vt = Vista(200, cy_t, elev=elev)
    Rb, alt = 152, 10
    ry_b = Rb * vt.se
    corpo += f'<ellipse cx="200" cy="{cy_t}" rx="{Rb}" ry="{m(ry_b)}" fill="{a.linear([(0, "#7a4420"), (.4, "#5e3216"), (1, "#3a1c0a")], 0, 0, 1, 0)}"/>'
    ty = cy_t - alt * vt.ce
    topo_t = f'M{200 - Rb} {m(ty)}a{Rb} {m(ry_b)} 0 1 0 {2 * Rb} 0a{Rb} {m(ry_b)} 0 1 0 {-2 * Rb} 0Z'
    corpo += f'<path d="{topo_t}" fill="{a.radial([(0, "#bf8250"), (.6, "#9e6234"), (1, "#7a4422")], cx=.4, cy=.38, r=.7)}" filter="{a.textura("fino")}"/>'
    rv = rng(5)
    veios = ''
    for k in range(9):
        y = ty - ry_b + 10 + k * (2 * ry_b - 20) / 8
        meia = Rb * math.sqrt(max(0, 1 - ((y - ty) / ry_b) ** 2)) - 14
        veios += f'M{m(200 - meia)} {m(y)}Q{m(200 + rv.uniform(-50, 50))} {m(y + rv.uniform(-4, 4))} {m(200 + meia)} {m(y + rv.uniform(-2, 2))}'
    corpo += f'<path d="{veios}" fill="none" stroke="#4e2a10" stroke-opacity=".35" stroke-width="1"/>'
    corpo += f'<path d="M{200 - Rb} {m(ty)}a{Rb} {m(ry_b)} 0 0 0 {2 * Rb} 0" fill="none" stroke="#e8b682" stroke-opacity=".6" stroke-width="1.4"/>'
    # pão sírio recheado em 4 cunhas: três no lugar e uma puxada para a frente, virada com o corte para quem olha
    R = 108
    H = sum(e for e, _ in BEIRUTE)
    r = rng(17)
    vb = Vista(200, ty, elev=elev)
    v = Vista(*vb.p(30, 10), yaw=giro, elev=elev)
    corpo += f'<ellipse cx="{m(v.cx + 4)}" cy="{m(v.cy + 4)}" rx="{R + 8}" ry="{m((R + 8) * v.se)}" fill="#1e0c02" opacity=".55" filter="{a.desfoque(6)}"/>'
    g = 3

    def cunha(v, ox, oy, t0, t1, detalhe_faces=(), sombra_propria=False):
        def visivel(t):   # parede cuja normal aponta para t (graus, local) está de frente?
            return math.sin(math.radians(t + v_giro[0])) < -.05
        v_giro = [math.degrees(math.atan2(v.s, v.c))]
        out = ''
        if sombra_propria:
            setor = f'M0 0L{m(R * math.cos(math.radians(t0)))} {m(R * math.sin(math.radians(t0)))}A{R} {R} 0 0 1 {m(R * math.cos(math.radians(t1)))} {m(R * math.sin(math.radians(t1)))}Z'
            out += f'<g transform="{mat_chao(v, 0, ox, oy)}"><path d="{setor}" fill="#1e0c02" opacity=".65" transform="translate(5 -4) scale(1.04)" filter="{a.desfoque(4)}"/></g>'
        for ang, normal in ((t0, t0 - 90), (t1, t1 + 90)):
            if not visivel(normal):
                continue
            out += f'<g transform="{mat_parede(v, ox, oy, ang)}">' + face_beirute(a, 0, R, r, H, detalhe=ang in detalhe_faces)
            out += f'<rect x="0" y="{m(-H)}" width="{R}" height="{m(H)}" fill="{a.linear([(.6, "#2a1000", 0), (1, "#2a1000", .35)])}"/>'
            out += f'<path d="M2 {m(-H + .6)}H{R - 2}" stroke="#fff0cc" stroke-opacity=".6" stroke-width="1"/></g>'
        vis = [t for t in range(t0, t1 + 1) if visivel(t)]
        if len(vis) > 2:
            out += borda_beirute(a, v, ox, oy, R, vis[-1], vis[0], r)
        out += topo_beirute(a, v, ox, oy, R, t0, t1, H, r)
        return out
    pecas = []
    for t0 in (45, 135, 315):
        meio = math.radians(t0 + 45)
        ox, oy = g * math.cos(meio), g * math.sin(meio)
        prof = v.rot(ox + .5 * R * math.cos(meio), oy + .5 * R * math.sin(meio))[1]
        pecas.append((prof, ox, oy, t0, t0 + 90))
    for prof, ox, oy, t0, t1 in sorted(pecas, reverse=True):
        corpo += cunha(v, ox, oy, t0, t1, detalhe_faces=(225, 315))
    # a cunha que saiu: girada 90° para mostrar o corte de frente
    vc = Vista(*vb.p(-130, -62), yaw=giro + 90, elev=elev)
    corpo += cunha(vc, 0, 0, 225, 315, detalhe_faces=(225,), sombra_propria=True)
    return a.svg(corpo)


def gerar():
    return {
        'hotdog': hotdog_svg('Ilustração de cachorro-quente', 'tradicional'),
        'hotdog-especial': hotdog_svg('Ilustração de cachorro-quente especial', 'especial'),
        'hotdog-bacon': hotdog_svg('Ilustração de cachorro-quente com bacon e cheddar', 'bacon'),
        'misto-quente': misto_quente(),
        'sanduiche-natural': sanduiche_natural(),
        'beirute': beirute(),
    }
