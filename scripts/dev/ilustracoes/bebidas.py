# Bebidas: lata, garrafas PET, água, copos de vidro com gelo e condensação,
# milk-shake e açaí (copo e tigela).
#
# Refrigerantes são da casa (sem marca real): grafite + amarelo, bolhas e o selo "D".
# Componentes reutilizáveis (combos e kids) desenham em volta de `cx`, apoiados em
# `base`, sem fundo nem sombra no chão:
#   lata(a, cx, base, escala)            garrafa_pet(a, cx, base, escala, litros)
#   copo_refri(a, cx, base, escala)      caixinha_suco(a, cx, base, escala, cor)
import math

from .estilo import (Arte, fundo, sombra, realce, sombra_contato, suave, bolha, rng, n, selo_marca, MARCA)

GRAFITE = '#232327'
ROXO = '#a855f7'
AZUL = '#7cc4ff'

# sombreamento cilíndrico (sobreposto à cor): luz principal à esquerda, luz de recorte à direita
METAL = [(0, '#000', .62), (.05, '#000', .3), (.14, '#fff', .04), (.22, '#fff', .52), (.27, '#fff', .14),
         (.36, '#000', 0), (.6, '#000', .16), (.8, '#000', .4), (.89, '#fff', .1), (.94, '#ffe9c2', .34), (1, '#000', .55)]
PAPEL = [(0, '#000', .38), (.08, '#000', .12), (.24, '#fff', .2), (.38, '#fff', .04), (.62, '#000', .08),
         (.84, '#000', .28), (.93, '#ffe9c2', .14), (1, '#000', .4)]
VIDRO = [(0, '#fff', .34), (.04, '#fff', .1), (.14, '#fff', .02), (.5, '#fff', .01), (.86, '#fff', .03),
         (.96, '#fff', .12), (1, '#fff', .38)]


def _g(cx, base, escala, corpo):
    esc = '' if escala == 1 else f' scale({n(escala)})'
    return f'<g transform="translate({n(cx)},{n(base)}){esc}">{corpo}</g>'


def _arco_frente(x, y, rx, ry):
    """Metade da frente de uma elipse (de -rx a +rx, passando por baixo)."""
    return f'M{n(x - rx)},{n(y)} A{n(rx)} {n(ry)} 0 0 0 {n(x + rx)},{n(y)}'


def _faixa_curva(rx0, y0, rx1, y1, ry0=None, ry1=None):
    """Faixa em volta de um cilindro/cone: bordas de cima e de baixo curvas (vista de cima)."""
    ry0 = rx0 * .14 if ry0 is None else ry0
    ry1 = rx1 * .14 if ry1 is None else ry1
    return (f'M{n(-rx0)},{n(y0)} A{n(rx0)} {n(ry0)} 0 0 0 {n(rx0)},{n(y0)} L{n(rx1)},{n(y1)} '
            f'A{n(rx1)} {n(ry1)} 0 0 1 {n(-rx1)},{n(y1)} Z')


def _tira(larg, f0, f1, y0, y1, passos=6):
    """Polígono que acompanha um perfil: x = larg(y) * f, entre y0 e y1."""
    ys = [y0 + (y1 - y0) * i / passos for i in range(passos + 1)]
    pts = [(larg(y) * f0, y) for y in ys] + [(larg(y) * f1, y) for y in reversed(ys)]
    return 'M' + ' L'.join(f'{n(x)},{n(y)}' for x, y in pts) + 'Z'


def _interp(perfil):
    """Meia-largura em função de y a partir de pontos (x, y) do lado direito."""
    pts = sorted(perfil, key=lambda p: p[1])

    def f(y):
        if y <= pts[0][1]:
            return pts[0][0]
        for (xa, ya), (xb, yb) in zip(pts, pts[1:]):
            if ya <= y <= yb:
                return xa + (xb - xa) * (y - ya) / ((yb - ya) or 1)
        return pts[-1][0]
    return f


def gotas(a, r, pontos, rmin=.7, rmax=2.3, escorrer=0):
    """Gotas de condensação: corpo translúcido, borda escura, brilho e cáustica."""
    corpo = a.radial([(0, '#fff', .02), (.55, '#fff', .1), (.85, '#000', .18), (1, '#000', .4)], cx=.45, cy=.4)
    cs, ss, ks = [], [], []
    for x, y in pontos:
        rr = r.uniform(rmin, rmax)
        cs.append(f'<circle cx="{n(x)}" cy="{n(y)}" r="{n(rr)}"/>')
        ss.append(f'<circle cx="{n(x - rr * .35)}" cy="{n(y - rr * .38)}" r="{n(max(rr * .3, .35))}"/>')
        if rr > 1.3:
            ks.append(f'<path d="M{n(x - rr * .5)},{n(y + rr * .45)} Q{n(x)},{n(y + rr * .85)} {n(x + rr * .55)},{n(y + rr * .3)}" '
                      f'stroke-width="{n(rr * .28)}"/>')
    s = f'<g fill="{corpo}">{"".join(cs)}</g>'
    s += f'<g fill="none" stroke="#fff" stroke-opacity=".45" stroke-linecap="round">{"".join(ks)}</g>'
    s += f'<g fill="#fff" opacity=".9">{"".join(ss)}</g>'
    for i in range(escorrer):
        x, y = pontos[r.randrange(len(pontos))]
        L = r.uniform(10, 22)
        s += (f'<path d="M{n(x)},{n(y)} q{n(r.uniform(-1, 1))},{n(L / 2)} {n(r.uniform(-1.5, 1.5))},{n(L)}" fill="none" stroke="#fff" '
              f'stroke-opacity=".22" stroke-width="1.8" stroke-linecap="round"/>'
              f'<circle cx="{n(x)}" cy="{n(y + L)}" r="1.9" fill="{corpo}"/><circle cx="{n(x - .6)}" cy="{n(y + L - .7)}" r=".6" fill="#fff" opacity=".9"/>')
    return s


def _pontos_area(r, qtd, larg, y0, y1, margem=.86, dist=4.2):
    """Pontos espalhados (sem sobreposição) numa área de perfil larg(y)."""
    pts = []
    tent = 0
    while len(pts) < qtd and tent < qtd * 60:
        tent += 1
        y = r.uniform(y0, y1)
        w = larg(y) * margem
        x = r.uniform(-w, w)
        if all((x - px) ** 2 + (y - py) ** 2 > dist ** 2 for px, py in pts):
            pts.append((x, y))
    return pts


def bolhas_gas(a, r, larg, y0, y1, qtd, cor='#ffd9b0', op=.55):
    """Bolhinhas de gás espalhadas no líquido (menores perto da superfície)."""
    s = ''
    for i in range(qtd):
        y = r.uniform(y0 + 4, y1)
        x = r.uniform(-.8, .8) * larg(y)
        rr = r.uniform(.5, 1.4) * (1 if y > (y0 + y1) / 2 else .8)
        s += f'<circle cx="{n(x)}" cy="{n(y)}" r="{n(rr)}"/>'
    return f'<g fill="#fff" fill-opacity=".14" stroke="{cor}" stroke-opacity="{n(op)}" stroke-width=".55">{s}</g>'


def gelo(a, x, y, s, rot=0, op=1.0, semente=1):
    """Cubo de gelo arredondado em 3/4, translúcido e azulado."""
    r = rng(semente)
    h = s / 2
    pts = [(-h, -h * .5), (-h * .12, -h * 1.02), (h, -h * .7), (h * .98, h * .52), (h * .06, h), (-h * .98, h * .6)]
    pts = [(px + r.uniform(-.05, .05) * s, py + r.uniform(-.05, .05) * s) for px, py in pts]
    c = (h * .02 + r.uniform(-.04, .04) * s, -h * .24)
    d = suave(pts, t=.62)
    clip = a.recorte(d)
    P = lambda q: f'{n(q[0])},{n(q[1])}'
    topo = f'M{P(pts[0])} L{P(pts[1])} L{P(pts[2])} L{P(c)}Z'
    esq = f'M{P(pts[0])} L{P(c)} L{P(pts[4])} L{P(pts[5])}Z'
    dir_ = f'M{P(c)} L{P(pts[2])} L{P(pts[3])} L{P(pts[4])}Z'
    t = f'translate({n(x)},{n(y)})' + (f' rotate({n(rot)})' if rot else '')
    o = f' opacity="{n(op)}"' if op != 1 else ''
    out = f'<g transform="{t}"{o}>'
    out += f'<path d="{d}" fill="{a.linear([(0, "#f2fbff", .62), (.55, "#bfe4ff", .36), (1, "#7fbfee", .42)], 0, 0, 1, 1)}"/>'
    out += f'<g clip-path="{clip}">'
    out += f'<path d="{topo}" fill="{a.linear([(0, "#fff", .75), (1, "#fff", .35)], 0, 0, 1, 1)}"/>'
    out += f'<path d="{esq}" fill="{a.linear([(0, "#fff", .32), (1, "#fff", .04)], 0, 0, 1, 1)}"/>'
    out += f'<path d="{dir_}" fill="{a.linear([(0, "#2a6fa8", .12), (1, "#164a7a", .38)], 0, 0, 1, 1)}"/>'
    out += f'<ellipse cx="{n(-h * .05)}" cy="{n(h * .12)}" rx="{n(h * .42)}" ry="{n(h * .3)}" fill="#fff" opacity=".42" filter="{a.desfoque(max(s * .08, .8))}"/>'
    out += (f'<path d="M{P(pts[4])} L{P(c)} L{P(pts[0])} M{P(c)} L{P(pts[2])}" fill="none" stroke="#fff" stroke-opacity=".8" '
            f'stroke-width="{n(max(s * .045, .7))}" stroke-linejoin="round"/>')
    out += f'<path d="M{P(pts[3])} L{P(pts[4])} L{P(pts[5])}" fill="none" stroke="#e6f6ff" stroke-opacity=".9" stroke-width="{n(max(s * .06, .8))}" stroke-linejoin="round" filter="{a.desfoque(.5)}"/>'
    out += f'<circle cx="{n(h * .42)}" cy="{n(h * .18)}" r="{n(s * .045)}" fill="#fff" opacity=".7"/>'
    out += f'<circle cx="{n(-h * .4)}" cy="{n(h * .38)}" r="{n(s * .03)}" fill="#fff" opacity=".6"/>'
    out += '</g>'
    out += f'<path d="{d}" fill="none" stroke="#fff" stroke-opacity=".7" stroke-width="{n(max(s * .04, .7))}"/>'
    out += f'<ellipse cx="{n(-h * .42)}" cy="{n(-h * .46)}" rx="{n(h * .3)}" ry="{n(h * .09)}" fill="#fff" transform="rotate(-27 {n(-h * .42)} {n(-h * .46)})"/>'
    out += f'<circle cx="{n(h * .62)}" cy="{n(-h * .5)}" r="{n(s * .035)}" fill="#fff"/>'
    return out + '</g>'


def gelo_mesa(a, x, base, s, rot=0, semente=1):
    """Cubo de gelo sobre a mesa, com sombra azulada e uma pocinha de água."""
    out = f'<ellipse cx="{n(x + 2)}" cy="{n(base - .5)}" rx="{n(s * .55)}" ry="{n(s * .11)}" fill="#000" opacity=".5" filter="{a.desfoque(1.6)}"/>'
    out += f'<ellipse cx="{n(x + 1)}" cy="{n(base + .6)}" rx="{n(s * .78)}" ry="{n(s * .15)}" fill="#cfeaff" opacity=".1"/>'
    out += f'<path d="M{n(x - s * .7)},{n(base + .8)} q{n(s * .7)},{n(s * .2)} {n(s * 1.45)},-.2" fill="none" stroke="#fff" stroke-opacity=".3" stroke-width=".8" stroke-linecap="round"/>'
    out += f'<ellipse cx="{n(x + s * .3)}" cy="{n(base + .2)}" rx="{n(s * .22)}" ry="{n(s * .05)}" fill="#bfe4ff" opacity=".35" filter="{a.desfoque(1)}"/>'
    out += gelo(a, x, base - s * .5, s, rot, semente=semente)
    return out


def _bolhas_marca(r, larg, y0, y1, fluxos=(-.66, .5, .8), tam=(1.4, 4.6), livre=None):
    """Padrão abstrato da casa: colunas de bolhas que diminuem ao subir (de y1 até y0)."""
    s = ''
    for k, f in enumerate(fluxos):
        y = y1 - r.uniform(0, 4)
        fase = r.uniform(0, 6)
        while y > y0 + 3:
            t = (y1 - y) / (y1 - y0)
            raio = tam[1] - (tam[1] - tam[0]) * t + r.uniform(-.5, .5)
            x = f * larg(y) + math.sin(fase + y * .12) * 3
            if not (livre and livre(x, y)):
                s += f'<circle cx="{n(x)}" cy="{n(y)}" r="{n(max(raio, .9))}"/>'
            y -= raio * 2.2 + r.uniform(1.5, 4.5)
    return s


def palha(a, x, y, ang, comp, larg=6.5, cor='#ffffff', listra=None, n_listras=7, op=1.0):
    """Canudo reto: base em (x, y), inclinado `ang` graus a partir da vertical."""
    o = f' opacity="{n(op)}"' if op != 1 else ''
    s = f'<g transform="translate({n(x)},{n(y)}) rotate({n(ang)})"{o}>'
    d = f'M{n(-larg / 2)},0 V{n(-comp)} H{n(larg / 2)} V0Z'
    s += f'<path d="{d}" fill="{cor}"/>'
    if listra:
        s += f'<g clip-path="{a.recorte(d)}" fill="{listra}">'
        passo = comp / n_listras
        for i in range(n_listras + 1):
            yy = -i * passo
            s += f'<path d="M{n(-larg)},{n(yy)} l{n(larg * 2)},{n(-larg * 1.2)} v{n(-passo * .42)} l{n(-larg * 2)},{n(larg * 1.2)}Z"/>'
        s += '</g>'
    s += f'<path d="{d}" fill="{a.linear([(0, "#000", .35), (.25, "#fff", .45), (.4, "#fff", .1), (.75, "#000", .12), (1, "#000", .4)], 0, 0, 1, 0)}"/>'
    s += f'<ellipse cx="0" cy="{n(-comp)}" rx="{n(larg / 2)}" ry="{n(larg * .2)}" fill="#3a3a3a"/>'
    s += f'<path d="M{n(-larg / 2)},{n(-comp)} A{n(larg / 2)} {n(larg * .2)} 0 0 0 {n(larg / 2)},{n(-comp)}" fill="none" stroke="{cor}" stroke-width=".9"/>'
    return s + '</g>'


# ---------------------------------------------------------------- lata

def lata(a, cx, base, escala=1.0):
    """Lata 350 ml genérica da casa. ~76 de largura x 156 de altura acima da base (escala 1)."""
    R, H = 38, 150
    rt = R - 6.5          # raio do topo (pescoço)
    yt = -(H - 2)         # centro da tampa
    ys = -(H - 16)        # início do ombro
    corpo = (f'M{-R},-12 V{ys} C{-R},{ys - 6} {-rt},{yt + 6} {-rt},{yt} H{rt} C{rt},{yt + 6} {R},{ys - 6} {R},{ys} V-12 '
             f'C{R},-8 {R - 2},-6.5 {R - 5},-5.5 A{R - 5} 5.5 0 0 1 {-(R - 5)},-5.5 C{-(R - 2)},-6.5 {-R},-8 {-R},-12Z')
    clip = a.recorte(corpo)
    s = f'<path d="{corpo}" fill="{a.linear([(0, "#d4d6dc"), (.5, "#a4a7b0"), (1, "#7d8089")])}"/>'
    s += f'<g clip-path="{clip}">'
    # ombro: alumínio voltado para cima recebe mais luz
    s += f'<path d="M{-R},{ys + 1} C{-R},{ys - 6} {-rt},{yt + 6} {-rt},{yt} H{rt} C{rt},{yt + 6} {R},{ys - 6} {R},{ys + 1}Z" fill="#fff" opacity=".22"/>'
    # área impressa
    y0, y1 = ys + 1, -14
    impresso = _faixa_curva(R + 1, y0, R + 1, y1)
    s += f'<path d="{impresso}" fill="{a.linear([(0, "#3a3a41"), (.5, "#25252a"), (1, "#18181b")])}"/>'
    # faixa amarela larga + filetes
    fy0, fy1 = -80, -42
    s += f'<path d="{_faixa_curva(R + 1, fy0, R + 1, fy1)}" fill="{a.linear([(0, "#ffd24a"), (1, "#f29e00")])}"/>'
    for yy, esp in ((fy0 - 6, 2.4), (fy1 + 6, 1.8), (fy1 + 11, 1)):
        s += f'<path d="{_arco_frente(0, yy, R + 1, (R + 1) * .14)}" fill="none" stroke="{MARCA}" stroke-width="{esp}"/>'
    # bolhas subindo (padrão abstrato da linha de refrigerantes da casa)
    r = rng(41)
    bs = _bolhas_marca(r, lambda y: R, y0 + 4, fy0 - 10, fluxos=(-.72, -.3, .42, .78), tam=(1.2, 4.4))
    s += f'<g fill="none" stroke="{MARCA}" stroke-opacity=".85" stroke-width="1.2">{bs}</g>'
    yc = (fy0 + fy1) / 2 + 1.5
    s += f'<circle cx="0" cy="{n(yc)}" r="18.6" fill="{GRAFITE}"/>'
    s += selo_marca(a, 0, yc, 15.5, fundo_cor=MARCA, letra=GRAFITE)
    # sombreamento metálico e brilhos
    s += f'<path d="{corpo}" fill="{a.linear(METAL, 0, 0, 1, 0)}"/>'
    s += f'<rect x="{-R * .6}" y="{ys - 8}" width="3.2" height="{-ys - 4}" fill="#fff" opacity=".8" filter="{a.desfoque(.7)}"/>'
    s += f'<rect x="{-R * .4}" y="{ys}" width="1.2" height="{-ys - 16}" fill="#fff" opacity=".3"/>'
    s += f'<rect x="{R * .74}" y="{ys - 4}" width="2.6" height="{-ys - 8}" fill="#ffe9c2" opacity=".5" filter="{a.desfoque(.8)}"/>'
    # névoa gelada e condensação
    s += f'<path d="{corpo}" fill="{a.linear([(0, "#dff2ff", 0), (.5, "#dff2ff", .05), (1, "#dff2ff", .14)])}"/>'
    r = rng(43)
    s += gotas(a, r, _pontos_area(r, 42, lambda y: R, ys + 2, -16, .94, 6.6), rmin=.8, rmax=2.6, escorrer=3)
    # frisos do ombro e do fundo
    s += f'<path d="{_arco_frente(0, ys + 1, R, R * .14)}" fill="none" stroke="#fff" stroke-opacity=".5" stroke-width="1"/>'
    s += f'<path d="{_arco_frente(0, -12, R, R * .14)}" fill="none" stroke="#000" stroke-opacity=".4" stroke-width="1.2"/>'
    s += f'<path d="{_arco_frente(0, -10.4, R, R * .14)}" fill="none" stroke="#fff" stroke-opacity=".4" stroke-width=".8"/>'
    s += '</g>'
    # tampa: borda enrolada, painel rebaixado, anel de abertura
    s += f'<ellipse cx="0" cy="{yt}" rx="{rt + .6}" ry="5.6" fill="{a.linear([(0, "#8e9098"), (.35, "#f2f3f6"), (.7, "#c9cbd2"), (1, "#7b7d85")], 0, 0, 1, 0)}"/>'
    s += f'<ellipse cx="0" cy="{yt + .8}" rx="{rt - 2.6}" ry="4.1" fill="{a.linear([(0, "#6f7179"), (.45, "#b9bbc2"), (1, "#e2e3e8")])}"/>'
    s += f'<path d="M-10,{yt + 2.6} q10,3.2 20,0 q-2.5,-3.2 -10,-3.2 q-7.5,0 -10,3.2Z" fill="#9c9ea6" stroke="#55575e" stroke-opacity=".6" stroke-width=".7"/>'
    s += f'<path d="M-6.5,{yt - 3.4} h13 a2.6,2.6 0 0 1 0,5.2 h-13 a2.6,2.6 0 0 1 0,-5.2Z" fill="{a.linear([(0, "#ffffff"), (1, "#a7a9b1")])}" stroke="#6c6e75" stroke-opacity=".5" stroke-width=".5"/>'
    s += f'<ellipse cx="-1.5" cy="{yt - .8}" rx="2.6" ry="1.1" fill="#5d5f66"/>'
    s += f'<circle cx="3.6" cy="{yt - .8}" r="1.1" fill="#d9dbe0" stroke="#6c6e75" stroke-width=".4"/>'
    s += f'<path d="{_arco_frente(0, yt, rt + .6, 5.6)}" fill="none" stroke="#fff" stroke-opacity=".85" stroke-width=".9"/>'
    s += realce(a, -rt * .5, yt - 1.6, 7, 1.3, op=.8, blur=.7)
    return _g(cx, base, escala, s)


# ---------------------------------------------------------------- garrafa PET

def _perfil_pet(litros):
    if litros == 2:
        return dict(
            R=40, tampa=(13.5, -224, -205), anel=(15.5, -200.5, -197.5), nivel=-162, rotulo=(-128, -74),
            lado=[(11.6, -199), (12.2, -191), (15.5, -182), (22, -173), (30, -164), (36.5, -154), (39.6, -143), (40, -132),
                  (40, -100), (40, -66), (40, -40), (39.6, -24), (38, -14), (35, -7)],
            pes=[(27, -1.6), (14, -5.4), (0, 0)], sulcos=[-138, -64, -34])
    return dict(
        R=27, tampa=(12, -170, -155), anel=(14, -151.5, -149), nivel=-126, rotulo=(-96, -58),
        lado=[(10.2, -150), (10.8, -144), (14, -136), (19.5, -127), (24.5, -117), (26.8, -107), (27, -100), (25, -88),
              (24, -77), (25, -66), (27, -54), (27, -36), (26.6, -20), (25.4, -11), (23, -5)],
        pes=[(17, -1.2), (9, -4.2), (0, 0)], sulcos=[-104, -50])


def _contorno(lado, pes):
    pts = list(lado) + list(pes) + [(-x, y) for x, y in reversed(pes) if x != 0] + [(-x, y) for x, y in reversed(lado)]
    return suave(pts)


def _tampa_rosca(a, raio, y0, y1, cor=('#ffd45e', MARCA, '#b77900')):
    """Tampa plástica com ranhuras e lacre."""
    claro, medio, escuro = cor
    d = f'M{n(-raio)},{n(y0 + 2)} Q{n(-raio)},{n(y0)} {n(-raio + 2)},{n(y0)} H{n(raio - 2)} Q{n(raio)},{n(y0)} {n(raio)},{n(y0 + 2)} V{n(y1)} H{n(-raio)}Z'
    s = f'<path d="{d}" fill="{a.linear([(0, escuro), (.22, claro), (.45, medio), (.8, escuro), (.92, medio), (1, escuro)], 0, 0, 1, 0)}"/>'
    s += f'<g clip-path="{a.recorte(d)}" stroke="#000" stroke-opacity=".22" stroke-width=".8">'
    k = int(raio * 2 / 2.3)
    for i in range(1, k):
        x = -raio + i * 2 * raio / k
        s += f'<path d="M{n(x)},{n(y0 + 1.5)} V{n(y1 - 4.5)}"/>'
    s += '</g>'
    s += f'<path d="M{n(-raio)},{n(y1 - 4)} H{n(raio)}" stroke="#000" stroke-opacity=".35" stroke-width="1"/>'
    s += f'<ellipse cx="0" cy="{n(y0 + .6)}" rx="{n(raio - 1.2)}" ry="{n(raio * .16)}" fill="{claro}" opacity=".85"/>'
    s += f'<rect x="{n(-raio * .62)}" y="{n(y0 + 2)}" width="{n(raio * .2)}" height="{n(y1 - y0 - 6)}" fill="#fff" opacity=".4" filter="{a.desfoque(.6)}"/>'
    return s


def garrafa_pet(a, cx, base, escala=1.0, litros=2, liquido='cola'):
    """Garrafa PET transparente com refrigerante. 2 L: ~84 x 224; 600 ml: ~56 x 170 (escala 1)."""
    p = _perfil_pet(2 if litros >= 1 else .6)
    R, lado, pes = p['R'], p['lado'], p['pes']
    larg = _interp(lado + [(x, y) for x, y in pes])
    d = _contorno(lado, pes)
    clip = a.recorte(d)
    sem = 50 + int(litros * 10)
    r = rng(sem)
    s = ''
    # interior vazio (pescoço): plástico contra o fundo
    s += f'<path d="{d}" fill="#fff" fill-opacity=".05" stroke="#fff" stroke-opacity=".14" stroke-width=".7"/>'
    caixa = f'x="{-R}" y="{lado[0][1]}" width="{2 * R}" height="{-lado[0][1]}"'
    # líquido
    dentro = _contorno([(x - 2.3, y) for x, y in lado], [(x * .9, y - 2.6) for x, y in pes])
    nv = p['nivel']
    wl = larg(nv) - 2.3
    s += f'<g clip-path="{a.recorte(f"M-60,{nv} H60 V10 H-60Z")}">'
    if liquido == 'cola':
        cor_liq = [(0, '#3a1206'), (.07, '#7d3412'), (.16, '#3f1407'), (.5, '#200903'), (.78, '#361105'),
                   (.88, '#8e3d15'), (.95, '#d07332'), (1, '#4a1907')]
    s += f'<path d="{dentro}" fill="{a.linear(cor_liq, 0, 0, 1, 0)}"/>'
    s += bolhas_gas(a, r, lambda y: larg(y) - 4, nv, -8, 26 if litros >= 1 else 18)
    s += '</g>'
    # superfície com espuma fina
    ryl = wl * .16
    s += f'<ellipse cx="0" cy="{nv}" rx="{n(wl)}" ry="{n(ryl)}" fill="{a.radial([(0, "#9a5228"), (1, "#5a2309")], cx=.4, cy=.4)}"/>'
    s += f'<ellipse cx="0" cy="{nv}" rx="{n(wl)}" ry="{n(ryl)}" fill="none" stroke="#f3d2a8" stroke-opacity=".35" stroke-width=".9"/>'
    esp = ''
    for i in range(16):
        t = r.uniform(.05, .95) * math.pi
        esp += f'<circle cx="{n(math.cos(t) * wl * .96)}" cy="{n(nv + math.sin(t) * ryl * .9)}" r="{n(r.uniform(.5, 1.1))}"/>'
    s += f'<g fill="#fff3e0" opacity=".75">{esp}</g>'
    # plástico: bordas, sulcos e brilhos
    s += f'<g clip-path="{clip}">'
    s += f'<rect {caixa} fill="{a.linear(VIDRO, 0, 0, 1, 0)}"/>'
    s += f'<rect x="{-R}" y="{nv}" width="{2 * R}" height="{-nv}" fill="{a.linear([(0, "#000", 0), (.6, "#000", .05), (1, "#000", .45)])}"/>'
    for ys in p['sulcos']:
        w = larg(ys)
        s += f'<path d="{_arco_frente(0, ys, w, w * .15)}" fill="none" stroke="#000" stroke-opacity=".35" stroke-width="1.3"/>'
        s += f'<path d="{_arco_frente(0, ys + 1.6, w, w * .15)}" fill="none" stroke="#fff" stroke-opacity=".3" stroke-width=".9"/>'
    ytopo = lado[0][1]
    s += f'<path d="{_tira(larg, -.74, -.56, ytopo + 10, -14)}" fill="#fff" opacity=".2" filter="{a.desfoque(1.6)}"/>'
    s += f'<path d="{_tira(larg, -.83, -.78, ytopo + 6, -12)}" fill="#fff" opacity=".85" filter="{a.desfoque(.4)}"/>'
    s += f'<path d="{_tira(larg, .8, .88, ytopo + 16, -12)}" fill="#ffe9c2" opacity=".42" filter="{a.desfoque(.7)}"/>'
    s += f'<path d="{_tira(larg, .44, .48, ytopo + 20, -20)}" fill="#fff" opacity=".18" filter="{a.desfoque(.6)}"/>'
    s += '</g>'
    # rótulo da casa
    y0, y1 = p['rotulo']
    w0, w1 = larg(y0) + .6, larg(y1) + .6
    ladod = [(larg(y) + .6, y) for y in [y0 + (y1 - y0) * i / 8 for i in range(9)]]
    rot = (f'M{n(-w0)},{n(y0)} A{n(w0)} {n(w0 * .15)} 0 0 0 {n(w0)},{n(y0)} '
           + ''.join(f'L{n(x)},{n(y)} ' for x, y in ladod[1:])
           + f'A{n(w1)} {n(w1 * .15)} 0 0 1 {n(-w1)},{n(y1)} '
           + ''.join(f'L{n(-x)},{n(y)} ' for x, y in reversed(ladod[:-1])) + 'Z')
    s += f'<path d="{rot}" fill="{a.linear([(0, "#34343a"), (1, "#17171a")])}"/>'
    s += f'<g clip-path="{a.recorte(rot)}">'
    hh = y1 - y0
    fy0, fy1 = y0 + hh * .5, y1 - hh * .12
    s += f'<path d="{_faixa_curva(R + 2, fy0, R + 2, fy1)}" fill="{a.linear([(0, "#ffcf3f"), (1, "#f29e00")])}"/>'
    s += f'<path d="{_arco_frente(0, y0 + 3.5, R + 2, (R + 2) * .15)}" fill="none" stroke="{MARCA}" stroke-width="1.6"/>'
    s += f'<path d="{_arco_frente(0, y1 - 2.5, R + 2, (R + 2) * .15)}" fill="none" stroke="{MARCA}" stroke-width="1.2"/>'
    bs = ''
    for i in range(10 if litros >= 1 else 7):
        bx = r.uniform(-R * .9, R * .9)
        by = r.uniform(y0 + 8, fy0 - 5)
        if abs(bx) < R * .32:
            continue
        bs += f'<circle cx="{n(bx)}" cy="{n(by)}" r="{n(r.uniform(1.2, 3.4))}"/>'
    s += f'<g fill="none" stroke="{MARCA}" stroke-opacity=".7" stroke-width="1">{bs}</g>'
    sr = min(hh * .34, R * .42)
    s += selo_marca(a, 0, (y0 + y1) / 2 + 2, sr, fundo_cor=GRAFITE, letra=MARCA)
    s += f'<circle cx="0" cy="{n((y0 + y1) / 2 + 2)}" r="{n(sr + 1.6)}" fill="none" stroke="{MARCA}" stroke-width="1"/>'
    s += f'<path d="{rot}" fill="{a.linear(PAPEL, 0, 0, 1, 0)}"/>'
    s += f'<path d="{_tira(larg, -.62, -.54, y0 + 2, y1 - 2, 2)}" fill="#fff" opacity=".35" filter="{a.desfoque(.8)}"/>'
    s += '</g>'
    # condensação (garrafa gelada)
    r3 = rng(sem + 3)
    s += f'<g clip-path="{clip}">' + gotas(a, r3, _pontos_area(r3, 30 if litros >= 1 else 22, lambda y: larg(y), nv + 4, -10, .9, 7),
                                           rmin=.7, rmax=2.2, escorrer=2) + '</g>'
    # gargalo: anel de suporte e tampa
    ra, ya0, ya1 = p['anel']
    s += (f'<rect x="{n(-ra)}" y="{n(ya0)}" width="{n(2 * ra)}" height="{n(ya1 - ya0)}" rx="1.4" '
          f'fill="{a.linear([(0, "#fff", .25), (.25, "#fff", .7), (.6, "#fff", .2), (1, "#fff", .45)], 0, 0, 1, 0)}"/>')
    rt, yt0, yt1 = p['tampa']
    s += f'<rect x="{n(-rt + 2)}" y="{n(yt1 - 1)}" width="{n(2 * rt - 4)}" height="{n(ya0 - yt1 + 1.5)}" fill="#fff" opacity=".22"/>'
    s += _tampa_rosca(a, rt, yt0, yt1)
    return _g(cx, base, escala, s)


# ---------------------------------------------------------------- copo de papel (combos)

def copo_refri(a, cx, base, escala=1.0):
    """Copo de papel da casa com tampa e canudo. ~96 de largura x 196 de altura (escala 1)."""
    yt, wt, wb = -136, 45, 33
    ryt, ryb = wt * .13, wb * .13
    corpo = (f'M{-wt},{yt} L{-wb},{n(-ryb)} A{wb} {n(ryb)} 0 0 0 {wb},{n(-ryb)} L{wt},{yt} '
             f'A{wt} {n(ryt)} 0 0 0 {-wt},{yt}Z')
    larg = lambda y: wb + (wt - wb) * (y / yt)
    s = f'<path d="{corpo}" fill="{a.linear([(0, "#ffffff"), (1, "#ebe7df")])}"/>'
    s += f'<g clip-path="{a.recorte(corpo)}">'
    # faixa grafite com filetes amarelos e base amarela
    f0, f1 = -94, -48
    s += f'<path d="{_faixa_curva(larg(f0) + 1, f0, larg(f1) + 1, f1, larg(f0) * .13, larg(f1) * .13)}" fill="{a.linear([(0, "#36363c"), (1, "#1a1a1d")])}"/>'
    s += f'<path d="{_faixa_curva(larg(-34) + 1, -34, wb + 2, 2, larg(-34) * .13, ryb)}" fill="{a.linear([(0, "#ffcf3f"), (1, "#f09a00")])}"/>'
    for yy, e in ((f0 - 5, 2), (f1 + 5, 2)):
        s += f'<path d="{_arco_frente(0, yy, larg(yy) + 1, larg(yy) * .13)}" fill="none" stroke="{MARCA}" stroke-width="{e}"/>'
    r = rng(61)
    bs = ''
    for i in range(14):
        by = r.uniform(-128, f0 - 12)
        bx = r.uniform(-.85, .85) * larg(by)
        if abs(bx) < 12 and by > -118:
            continue
        bs += f'<circle cx="{n(bx)}" cy="{n(by)}" r="{n(r.uniform(1.6, 4.4))}"/>'
    s += f'<g fill="none" stroke="{MARCA}" stroke-width="1.3">{bs}</g>'
    s += selo_marca(a, 0, (f0 + f1) / 2 + 1, 15.5)
    # dobra do fundo
    s += f'<path d="{_arco_frente(0, -7, wb + .5, ryb)}" fill="none" stroke="#000" stroke-opacity=".25" stroke-width="1.2"/>'
    s += f'<path d="{corpo}" fill="{a.linear(PAPEL, 0, 0, 1, 0)}"/>'
    s += f'<path d="{_tira(larg, -.62, -.5, yt + 6, -10, 2)}" fill="#fff" opacity=".3" filter="{a.desfoque(1.4)}"/>'
    s += '</g>'
    # tampa plástica
    yl, wl, rl = yt - 6.5, 40.5, 5.4
    tampa = (f'M{-wt - 2.5},{yt} L{-wl},{yl} A{wl} {rl} 0 0 1 {wl},{yl} L{wt + 2.5},{yt} '
             f'A{wt + 2.5} {n(ryt + .6)} 0 0 1 {-wt - 2.5},{yt}Z')
    s += sombra_contato(a, -wt, wt, yt + 3, alt=4, op=.35, blur=1.5)
    s += f'<path d="{tampa}" fill="{a.linear([(0, "#c9c6c0"), (.2, "#ffffff"), (.55, "#ecebe7"), (.85, "#bdb9b2"), (1, "#8e8a84")], 0, 0, 1, 0)}"/>'
    s += f'<path d="{_arco_frente(0, yt, wt + 2.5, ryt + .6)}" fill="none" stroke="#fff" stroke-width="1.2"/>'
    s += f'<path d="{_arco_frente(0, yt + 2.4, wt + 1.5, ryt + .3)}" fill="none" stroke="#000" stroke-opacity=".18" stroke-width="1"/>'
    s += f'<ellipse cx="0" cy="{yl}" rx="{wl}" ry="{rl}" fill="{a.radial([(0, "#ffffff"), (.7, "#f1efea"), (1, "#d2cfc8")], cx=.4, cy=.4)}"/>'
    s += f'<ellipse cx="0" cy="{yl + .4}" rx="{wl - 7}" ry="{n(rl - 1.4)}" fill="none" stroke="#a8a49c" stroke-opacity=".55" stroke-width=".9"/>'
    s += f'<path d="M1,{yl - 1.6} l6,2.4 M7,{yl - 1.6} l-6,2.4" stroke="#8a867f" stroke-width=".9"/>'
    # canudo
    s += f'<ellipse cx="4.6" cy="{yl + .3}" rx="5.2" ry="1.6" fill="#000" opacity=".25" filter="{a.desfoque(.8)}"/>'
    s += palha(a, 4, yl + .6, 11, 54, larg=7.4, cor='#ffffff', listra=MARCA, n_listras=6)
    return _g(cx, base, escala, s)


# ---------------------------------------------------------------- caixinha de suco (kids)

def _mistura(c1, c2, t):
    a1 = [int(c1[i:i + 2], 16) for i in (1, 3, 5)]
    a2 = [int(c2[i:i + 2], 16) for i in (1, 3, 5)]
    return '#' + ''.join(f'{round(x + (y - x) * t):02x}' for x, y in zip(a1, a2))


def caixinha_suco(a, cx, base, escala=1.0, cor='#8e4fc3'):
    """Caixinha de suco infantil com canudo. ~58 de largura x 118 de altura (escala 1)."""
    claro, escuro = _mistura(cor, '#ffffff', .35), _mistura(cor, '#000000', .38)
    x0, x1, x2 = -28.5, 15.5, 28.5
    h, dy = 76, 6
    frente = f'M{x0 + 2},0 H{x1} V{-h} H{x0 + 2} Q{x0},{-h} {x0},{-h + 2} V-2 Q{x0},0 {x0 + 2},0Z'
    lado = f'M{x1},0 L{x2 - 1},{-dy + .6} Q{x2},{-dy} {x2},{-dy - 1.5} V{-h - dy + 1.5} L{x1},{-h}Z'
    topo = f'M{x0 + 1.5},{-h} H{x1} L{x2},{-h - dy} H{x0 + 13 + 1.5} Q{x0 + 13},{-h - dy} {x0 + 12},{-h - dy + .6}Z'
    s = f'<path d="{lado}" fill="{a.linear([(0, escuro), (1, _mistura(escuro, "#000000", .3))], 0, 0, 1, 0)}"/>'
    s += f'<path d="{topo}" fill="{a.linear([(0, claro), (1, cor)], 0, 0, 1, 0)}"/>'
    s += f'<path d="M{x0 + 6},{-h - 2.8} H{x1 + 6}" stroke="#fff" stroke-opacity=".35" stroke-width="1.2"/>'
    s += f'<path d="{frente}" fill="{a.linear([(0, claro), (.45, cor), (1, _mistura(cor, "#000000", .15))], 0, 0, 1, 1)}"/>'
    s += f'<g clip-path="{a.recorte(frente)}">'
    fx = (x0 + x1) / 2
    # onda clara na parte de baixo
    s += f'<path d="M{x0},-24 C{x0 + 12},-30 {x1 - 16},-16 {x1},-22 V0 H{x0}Z" fill="#fff" opacity=".2"/>'
    s += f'<path d="M{x0},-14 C{x0 + 14},-20 {x1 - 14},-6 {x1},-12 V0 H{x0}Z" fill="{escuro}" opacity=".35"/>'
    # fruta estilizada (abstrata, sem texto)
    s += f'<circle cx="{n(fx)}" cy="-44" r="15" fill="#fff" opacity=".92"/>'
    s += f'<circle cx="{n(fx)}" cy="-43" r="10" fill="{a.radial([(0, claro), (1, escuro)], cx=.35, cy=.35)}"/>'
    s += f'<circle cx="{n(fx - 3.5)}" cy="-46.5" r="2.6" fill="#fff" opacity=".75"/>'
    s += f'<path d="M{n(fx + 1)},-53 q5,-6 10,-3 q-4,6 -10,3Z" fill="#5fae3c"/>'
    s += f'<path d="M{n(fx)},-52 q.5,-3 2.5,-5" stroke="#4a3a20" stroke-width="1.2" fill="none" stroke-linecap="round"/>'
    s += selo_marca(a, x0 + 9, -h + 9, 6)
    s += f'<rect x="{x0}" y="{-h}" width="{x1 - x0}" height="{h}" fill="{a.linear([(0, "#fff", .1), (.5, "#fff", 0), (1, "#000", .18)])}"/>'
    s += f'<rect x="{x0}" y="{-h}" width="8" height="{h}" fill="#fff" opacity=".22" filter="{a.desfoque(2)}"/>'
    s += f'<rect x="{x1 - 5}" y="{-h}" width="5" height="{h}" fill="#000" opacity=".12" filter="{a.desfoque(1.5)}"/>'
    s += '</g>'
    # aba dobrada na lateral e aba de vedação no topo
    s += f'<path d="M{x1 + .8},{-h - .4} L{x2 - .6},{-h - dy + .4} L{x1 + 7},{-h + 10}Z" fill="{escuro}" stroke="#fff" stroke-opacity=".18" stroke-width=".6" stroke-linejoin="round"/>'
    s += f'<path d="M{x1 + 2},{-h + 1} L{x1 + 7},{-h + 10}" stroke="#000" stroke-opacity=".25" stroke-width=".8"/>'
    s += f'<path d="M{x0 + 13},{-h - dy - .2} L{x2 - 1},{-h - dy - .2} L{x2 - 3},{-h - dy - 2.6} L{x0 + 15},{-h - dy - 2.6}Z" fill="{claro}"/>'
    s += f'<path d="M{x1},{-h + 1} V-1" stroke="#fff" stroke-opacity=".35" stroke-width=".8"/>'
    s += f'<path d="M{x0 + 2},{-h + .5} H{x1}" stroke="#fff" stroke-opacity=".5" stroke-width=".8"/>'
    s += sombra_contato(a, x0 + 2, x2 - 2, -1, alt=3, op=.25, blur=1)
    # canudo dobrável
    px, py = 6, -h - 3
    s += f'<ellipse cx="{px}" cy="{py}" rx="3.6" ry="1.4" fill="#d9dce3"/>'
    c = f'M{px},{py} V{py - 24} Q{px},{py - 30} {px - 5},{py - 33} L{px - 11},{py - 37}'
    s += f'<path d="{c}" fill="none" stroke="#c4c7ce" stroke-width="5" stroke-linecap="round" stroke-linejoin="round"/>'
    s += f'<path d="{c}" fill="none" stroke="#ffffff" stroke-width="3.6" stroke-linecap="round" stroke-linejoin="round"/>'
    s += f'<path d="M{px - 1},{py - 2} V{py - 23}" stroke="#fff" stroke-width="1" fill="none"/>'
    for k in range(4):
        yy = py - 24.5 - k * 1.6
        s += f'<path d="M{px - 2.4 - k * 1.1},{n(yy)} l4.4,{n(1 + k * .3)}" stroke="#a9adb5" stroke-width=".6"/>'
    s += f'<path d="M{px - 1.2},{py - 2} V{py - 22}" stroke="#000" stroke-opacity=".12" stroke-width="1.2" transform="translate(2.4,0)"/>'
    return _g(cx + 2, base, escala, s)


# ---------------------------------------------------------------- frutas

CITRICOS = {
    'laranja': dict(casca=[(0, '#ffb23a'), (.7, '#f07f00'), (1, '#b85400')], borda='#c86000', albedo='#fff1cf',
                    polpa=[(0, '#ffe08a'), (.6, '#ffb52e'), (1, '#f39200')], gomo='#ffcf5a'),
    'limao': dict(casca=[(0, '#8fd14f'), (.7, '#4f9e2a'), (1, '#2c6714')], borda='#2f6e17', albedo='#eff8d2',
                  polpa=[(0, '#e4f5a6'), (.6, '#bfe36a'), (1, '#93c63e')], gomo='#d6f08c'),
}


def rodela(a, x, y, raio, tipo='laranja', rot=0, gomos=9):
    """Rodela de fruta cítrica vista de frente, com espessura (casca) do lado direito."""
    c = CITRICOS[tipo]
    t = f' transform="rotate({n(rot)} {n(x)} {n(y)})"' if rot else ''
    s = f'<g{t}>'
    s += f'<circle cx="{n(x + raio * .07)}" cy="{n(y + raio * .03)}" r="{n(raio)}" fill="{a.linear([(0, c["borda"]), (1, "#000")], 0, 0, 1, 1)}"/>'
    s += f'<circle cx="{n(x)}" cy="{n(y)}" r="{n(raio)}" fill="{a.radial(c["casca"], cx=.38, cy=.35)}"/>'
    s += f'<circle cx="{n(x)}" cy="{n(y)}" r="{n(raio * .88)}" fill="{c["albedo"]}"/>'
    s += f'<circle cx="{n(x)}" cy="{n(y)}" r="{n(raio * .8)}" fill="{a.radial(c["polpa"], cx=.42, cy=.4)}"/>'
    # membranas entre os gomos
    g = ''
    for i in range(gomos):
        ang = 2 * math.pi * i / gomos + .2
        g += f'M{n(x)},{n(y)} L{n(x + math.cos(ang) * raio * .8)},{n(y + math.sin(ang) * raio * .8)} '
    s += f'<path d="{g}" stroke="{c["albedo"]}" stroke-width="{n(raio * .07)}" stroke-linecap="round" opacity=".95"/>'
    # vesículas de suco
    r = rng(int(raio * 10) + len(tipo))
    v = ''
    for i in range(gomos * 2):
        ang = 2 * math.pi * (i / 2 + r.uniform(.25, .75)) / gomos + .2
        rr = r.uniform(.3, .65) * raio
        v += f'<ellipse cx="{n(x + math.cos(ang) * rr)}" cy="{n(y + math.sin(ang) * rr)}" rx="{n(raio * .09)}" ry="{n(raio * .035)}" transform="rotate({n(math.degrees(ang))} {n(x + math.cos(ang) * rr)} {n(y + math.sin(ang) * rr)})"/>'
    s += f'<g fill="{c["gomo"]}" opacity=".9">{v}</g>'
    s += f'<circle cx="{n(x)}" cy="{n(y)}" r="{n(raio * .1)}" fill="{c["albedo"]}"/>'
    s += f'<circle cx="{n(x)}" cy="{n(y)}" r="{n(raio)}" fill="{a.radial([(0, "#fff", 0), (.75, "#fff", 0), (1, "#000", .25)])}"/>'
    s += realce(a, x - raio * .35, y - raio * .38, raio * .3, raio * .14, rot=-35, op=.55, blur=1.2)
    s += f'<circle cx="{n(x - raio * .42)}" cy="{n(y - raio * .2)}" r="{n(raio * .05)}" fill="#fff" opacity=".9"/>'
    return s + '</g>'


def fatia_pessego(a, x, y, s, rot=0):
    """Fatia de pêssego (gomo grosso em meia-lua): polpa dourada, casca rubra, centro avermelhado."""
    d = (f'M{n(-s)},0 C{n(-s * .78)},{n(-s * .95)} {n(s * .78)},{n(-s * .95)} {n(s)},0 '
         f'C{n(s * .55)},{n(-s * .1)} {n(-s * .55)},{n(-s * .1)} {n(-s)},0Z')
    pele = f'M{n(-s * .98)},{n(-.3)} C{n(-s * .78)},{n(-s * .95)} {n(s * .78)},{n(-s * .95)} {n(s * .98)},{n(-.3)}'
    out = f'<g transform="translate({n(x)},{n(y)}) rotate({n(rot)})">'
    out += f'<path d="{d}" fill="{a.linear([(0, "#ffb347"), (.45, "#ffcb62"), (.85, "#ffaa45"), (1, "#f58a35")])}"/>'
    out += f'<g clip-path="{a.recorte(d)}">'
    out += f'<ellipse cx="0" cy="{n(-s * .02)}" rx="{n(s * .55)}" ry="{n(s * .16)}" fill="#e2502a" opacity=".55" filter="{a.desfoque(s * .09)}"/>'
    out += f'<path d="{pele}" fill="none" stroke="#ff8a3a" stroke-opacity=".7" stroke-width="{n(s * .2)}" filter="{a.desfoque(s * .05)}"/>'
    out += '</g>'
    out += f'<path d="{pele}" fill="none" stroke="{a.linear([(0, "#c22a1a"), (.5, "#e5452a"), (1, "#b8261a")], 0, 0, 1, 0)}" stroke-width="{n(s * .09)}" stroke-linecap="round"/>'
    out += realce(a, -s * .22, -s * .45, s * .32, s * .07, rot=-10, op=.75, blur=.7)
    out += f'<path d="M{n(-s * .6)},{n(-s * .1)} C{n(-s * .2)},{n(-s * .17)} {n(s * .2)},{n(-s * .17)} {n(s * .6)},{n(-s * .1)}" fill="none" stroke="#fff" stroke-opacity=".35" stroke-width=".8"/>'
    return out + '</g>'


# ---------------------------------------------------------------- copo de vidro

def copo_vidro(a, wt=58, wb=45, h=168, bt=14, g=3.2, nivel=24, liq=None, sup=None, menisco='#fff', liq_op=1.0,
               textura=None, submerso='', dentro='', flutuante='', frio=True, semente=1, k=.15, gotas_qtd=46, escurecer=.3, nevoa=.1):
    """Copo de vidro transparente (local: base em y=0). Callbacks recebem `info`."""
    T = -h
    larg = lambda y: wt + (wb - wt) * ((y - T) / (0 - T))
    lin = lambda y: larg(y) - g
    ryt, ryb = wt * k, wb * k
    sil = (f'M{-wt},{T} L{-wb},{n(-ryb)} A{wb} {n(ryb)} 0 0 0 {wb},{n(-ryb)} L{wt},{T} '
           f'A{wt} {n(ryt)} 0 0 0 {-wt},{T}Z')
    L = T + nivel
    wl, wib = lin(L), lin(-bt)
    ryl, ryib = wl * k, wib * k
    liquido = (f'M{n(-wl)},{n(L)} L{n(-wib)},{-bt} A{n(wib)} {n(ryib)} 0 0 0 {n(wib)},{-bt} L{n(wl)},{n(L)} '
               f'A{n(wl)} {n(ryl)} 0 0 0 {n(-wl)},{n(L)}Z')
    info = dict(T=T, L=L, larg=larg, lin=lin, wl=wl, ryl=ryl, bt=bt, k=k)
    clip = a.recorte(sil)
    s = f'<path d="{sil}" fill="#fff" opacity=".04"/>'
    s += f'<path d="M{-wt},{T} A{wt} {n(ryt)} 0 0 1 {wt},{T}" fill="none" stroke="#fff" stroke-opacity=".35" stroke-width="1"/>'
    s += submerso(a, info) if callable(submerso) else submerso
    o = f' opacity="{n(liq_op)}"' if liq_op != 1 else ''
    tx = f' filter="{a.textura(textura)}"' if textura else ''
    s += f'<g{o}><path d="{liquido}" fill="{a.linear(liq, 0, 0, 1, 0)}"{tx}/>'
    s += f'<path d="{liquido}" fill="{a.linear([(0, "#fff", .1), (.3, "#000", 0), (1, "#000", escurecer)])}"/></g>'
    s += dentro(a, info) if callable(dentro) else dentro
    s += f'<ellipse cx="0" cy="{n(L)}" rx="{n(wl)}" ry="{n(ryl)}" fill="{a.radial(sup, cx=.42, cy=.38, r=.6)}"/>'
    s += f'<path d="{_arco_frente(0, L, wl, ryl)}" fill="none" stroke="{menisco}" stroke-opacity=".75" stroke-width="1.3"/>'
    s += f'<path d="M{n(-wl)},{n(L)} A{n(wl)} {n(ryl)} 0 0 1 {n(wl)},{n(L)}" fill="none" stroke="#000" stroke-opacity=".18" stroke-width="1"/>'
    s += flutuante(a, info) if callable(flutuante) else flutuante
    # vidro: espessura, fundo grosso, reflexos
    s += f'<g clip-path="{clip}">'
    s += f'<path d="{sil}" fill="{a.linear(VIDRO, 0, 0, 1, 0)}"/>'
    wbi = larg(-bt)
    fundo_d = (f'M{n(-wbi)},{-bt} L{-wb},{n(-ryb)} A{wb} {n(ryb)} 0 0 0 {wb},{n(-ryb)} L{n(wbi)},{-bt} '
               f'H{n(wib)} A{n(wib)} {n(ryib)} 0 0 1 {n(-wib)},{-bt}Z')
    s += f'<path d="{fundo_d}" fill="{a.linear(liq, 0, 0, 1, 0)}" opacity="{n(.55 * liq_op)}"/>'
    s += f'<path d="{fundo_d}" fill="{a.linear([(0, "#fff", .25), (.5, "#000", .2), (1, "#fff", .15)])}"/>'
    s += f'<path d="{_arco_frente(0, -bt, wib, ryib)}" fill="none" stroke="#fff" stroke-opacity=".55" stroke-width="1"/>'
    s += f'<path d="{_arco_frente(0, -ryb - 2.5, wb - 1.5, ryb)}" fill="none" stroke="#fff" stroke-opacity=".3" stroke-width="2.2" filter="{a.desfoque(.8)}"/>'
    s += f'<path d="{_tira(larg, -.78, -.6, T + 8, -bt - 4)}" fill="#fff" opacity=".2" filter="{a.desfoque(2.2)}"/>'
    s += f'<path d="{_tira(larg, -.86, -.82, T + 6, -bt - 2)}" fill="#fff" opacity=".85" filter="{a.desfoque(.45)}"/>'
    s += f'<path d="{_tira(larg, -.5, -.47, T + 14, L + 30)}" fill="#fff" opacity=".35" filter="{a.desfoque(.5)}"/>'
    s += f'<path d="{_tira(larg, .82, .9, T + 10, -bt)}" fill="#ffe9c2" opacity=".45" filter="{a.desfoque(.9)}"/>'
    s += f'<path d="{_tira(larg, .62, .65, T + 16, -bt - 8)}" fill="#fff" opacity=".18" filter="{a.desfoque(.6)}"/>'
    if frio:
        s += f'<path d="M{-wt},{n(L + 4)} H{wt} V0 H{-wt}Z" fill="{a.linear([(0, "#eaf6ff", nevoa * .3), (1, "#eaf6ff", nevoa)])}"/>'
        r = rng(semente * 7 + 3)
        s += gotas(a, r, _pontos_area(r, gotas_qtd, larg, L + 6, -bt - 4, .93, 5.6), rmin=.7, rmax=2.4, escorrer=3)
    s += '</g>'
    # borda do copo
    s += f'<ellipse cx="0" cy="{T}" rx="{wt}" ry="{n(ryt)}" fill="none" stroke="#fff" stroke-opacity=".45" stroke-width="1.2"/>'
    s += f'<ellipse cx="0" cy="{n(T + .8)}" rx="{n(wt - g)}" ry="{n((wt - g) * k)}" fill="none" stroke="#fff" stroke-opacity=".18" stroke-width=".8"/>'
    s += (f'<path d="{_arco_frente(0, T, wt, ryt)}" fill="none" stroke="{a.linear([(0, "#fff", .3), (.3, "#fff", .95), (.75, "#fff", .5), (1, "#fff", .8)], 0, 0, 1, 0)}" '
          f'stroke-width="1.5"/>')
    s += realce(a, -wt * .55, T + ryt * .7, wt * .22, 1.2, op=.8, blur=.6)
    s += f'<path d="{sil}" fill="none" stroke="#fff" stroke-opacity=".14" stroke-width=".8"/>'
    return s, info


def _cubos(a, info, lista, op_dentro=.5):
    """Gelo dentro do copo: (x, y, tamanho, rotação, semente).

    Devolve (dentro, flutuante): o cubo inteiro, translúcido, sobre o líquido; e a parte que
    passa da superfície, redesenhada inteira por cima."""
    L = info['L']
    den, flu = '', ''
    acima = a.recorte(f'M-90,-400 H90 V{n(L)} H-90Z')
    for x, y, t, rot, sem in lista:
        cubo = gelo(a, x, y, t, rot, semente=sem)
        den += f'<g opacity="{n(op_dentro)}">{cubo}</g>'
        if y - t * .5 < L:
            flu += f'<g clip-path="{acima}">{cubo}</g>'
    return den, flu


def cena_copo(titulo, brilho, cor_luz, corpo_fn, rx_sombra=62, extras=None):
    a = Arte(titulo, brilho=brilho)
    s = fundo(a) + sombra(a, cx=204, cy=251, rx=rx_sombra, ry=8)
    if cor_luz:
        s += f'<ellipse cx="212" cy="255" rx="{n(rx_sombra * .6)}" ry="4.5" fill="{cor_luz}" opacity=".3" filter="{a.desfoque(3)}"/>'
    s += corpo_fn(a)
    if extras:
        s += extras(a)
    return a.svg(s)


SUCO = [(0, '#b44a00'), (.07, '#ec8200'), (.2, '#ffb52e'), (.36, '#ffa61c'), (.62, '#f28a00'), (.84, '#d66a00'),
        (.93, '#ffb547'), (1, '#9c3f00')]
LIMONADA = [(0, '#9fb562'), (.08, '#d5e3a2'), (.24, '#f4f8de'), (.5, '#e9f1c6'), (.8, '#cddd94'), (.92, '#eef5cf'), (1, '#8ea552')]
CHA = [(0, '#4e1803'), (.07, '#a2440b'), (.2, '#e48a2c'), (.4, '#d47722'), (.65, '#b85a14'), (.85, '#a64c10'),
       (.93, '#f0a24e'), (1, '#461603')]


def _suco(a):
    def flu(a, i):
        L = i['L']
        s = f'<g clip-path="{a.recorte(f"M-90,-400 H90 V{n(L)} H-90Z")}">'
        s += palha(a, -14, -20, -13, 196, larg=7.4, cor='#ffffff', listra='#ff9a1a', n_listras=12)
        s += '</g>'
        r = rng(5)
        esp = ''
        for j in range(26):
            t = r.uniform(.04, .96) * math.pi
            rr = r.uniform(.75, 1)
            esp += f'<circle cx="{n(math.cos(t) * i["wl"] * rr * .97)}" cy="{n(L + math.sin(t) * i["ryl"] * rr * .9)}" r="{n(r.uniform(.6, 1.5))}"/>'
        s += f'<g fill="#fff4d6" opacity=".7">{esp}</g>'
        s += rodela(a, 45, -169, 24, 'laranja', rot=8)
        return s
    def polpa(a, i):
        r = rng(14)
        pts = ''
        for j in range(40):
            y = r.uniform(i['L'] + 8, -18)
            x = r.uniform(-.85, .85) * i['lin'](y)
            pts += f'<ellipse cx="{n(x)}" cy="{n(y)}" rx="{n(r.uniform(1, 2.6))}" ry="{n(r.uniform(.35, .7))}" transform="rotate({n(r.uniform(-40, 40))} {n(x)} {n(y)})"/>'
        return f'<g fill="#ffe2a0" opacity=".4">{pts}</g>'
    corpo, info = copo_vidro(a, wt=56, wb=44, h=166, nivel=26, liq=SUCO, sup=[(0, '#ffd786'), (.7, '#ffb640'), (1, '#f39400')],
                             menisco='#fff0c4', dentro=polpa, flutuante=flu, semente=1)
    return _g(196, 252, 1, corpo)


def _limonada(a):
    def flu(a, i):
        L = i['L']
        s = f'<g clip-path="{a.recorte(f"M-90,-400 H90 V{n(L)} H-90Z")}">'
        s += palha(a, 16, -20, 12, 194, larg=7.4, cor='#ffffff', listra='#7cc242', n_listras=12)
        s += '</g>'
        # espuma cremosa no topo
        r = rng(9)
        wl, ryl = i['wl'], i['ryl']
        esp = ''
        for j in range(40):
            t = r.uniform(0, 2 * math.pi)
            rr = r.uniform(0, .95)
            esp += f'<circle cx="{n(math.cos(t) * wl * rr)}" cy="{n(L + math.sin(t) * ryl * rr)}" r="{n(r.uniform(.7, 1.9))}"/>'
        lin, k = i['lin'], i['k']
        y2 = L + 8
        w2 = lin(y2)
        baixo = [(w2 * math.cos(t), y2 + w2 * k * math.sin(t) + r.uniform(-1, 1.2)) for t in [j * math.pi / 14 for j in range(15)]]
        banda = f'M{n(-wl)},{n(L)} A{n(wl)} {n(ryl)} 0 0 0 {n(wl)},{n(L)} ' + ' '.join(f'L{n(x)},{n(y)}' for x, y in baixo) + 'Z'
        s += f'<path d="{banda}" fill="{a.linear([(0, "#ffffff", .95), (1, "#f3f7df", .85)])}"/>'
        s += f'<g fill="none" stroke="#c9d88f" stroke-opacity=".6" stroke-width=".6">{esp}</g>'
        s += rodela(a, -45, -169, 23, 'limao', rot=-8)
        return s

    def casca(a, i):
        """Pontinhos verdes da casca do limão batido."""
        r = rng(12)
        pts = ''
        for j in range(34):
            y = r.uniform(i['L'] + 8, -20)
            x = r.uniform(-.8, .8) * i['lin'](y)
            pts += f'<ellipse cx="{n(x)}" cy="{n(y)}" rx="{n(r.uniform(.5, 1.1))}" ry="{n(r.uniform(.3, .6))}"/>'
        return f'<g fill="#6e9a2c" opacity=".45">{pts}</g>'

    corpo, info = copo_vidro(a, wt=56, wb=44, h=166, nivel=24, liq=LIMONADA, sup=[(0, '#ffffff'), (.6, '#f7faea'), (1, '#e3ecc0')],
                             menisco='#ffffff', dentro=casca, flutuante=flu, semente=2)
    return _g(204, 252, 1, corpo)


def _cha(a):
    cubos = [(-21, -137, 30, -12, 21), (15, -136, 29, 16, 22), (-3, -106, 27, 34, 23), (-22, -72, 26, 8, 24), (19, -62, 25, -20, 25)]

    def den(a, i):
        d, _ = _cubos(a, i, cubos, op_dentro=.42)
        return d

    def flu(a, i):
        _, f = _cubos(a, i, cubos)
        return f + fatia_pessego(a, 40, i['T'] + 5, 25, 22)
    corpo, info = copo_vidro(a, wt=52, wb=46, h=170, bt=15, nivel=30, liq=CHA, sup=[(0, '#f7b86a'), (.7, '#e08a33'), (1, '#b8601a')],
                             menisco='#ffd49a', dentro=den, flutuante=flu, semente=3, escurecer=.25, nevoa=.05)
    return _g(198, 252, 1, corpo)


# ---------------------------------------------------------------- milk-shake

def morango(a, x, y, s, rot=0, folhas=True, semente=1):
    """Morango inteiro, de pé, com sementinhas e folhas."""
    r = rng(semente)
    d = (f'M0,{n(-s * .55)} C{n(s * .55)},{n(-s * .75)} {n(s * .75)},{n(-s * .2)} {n(s * .45)},{n(s * .25)} '
         f'C{n(s * .25)},{n(s * .55)} {n(s * .08)},{n(s * .72)} 0,{n(s * .75)} C{n(-s * .08)},{n(s * .72)} {n(-s * .25)},{n(s * .55)} {n(-s * .45)},{n(s * .25)} '
         f'C{n(-s * .75)},{n(-s * .2)} {n(-s * .55)},{n(-s * .75)} 0,{n(-s * .55)}Z')
    out = f'<g transform="translate({n(x)},{n(y)})' + (f' rotate({n(rot)})' if rot else '') + '">'
    out += f'<path d="{d}" fill="{a.radial([(0, "#ff6b6b"), (.55, "#e3263a"), (1, "#9e0f22")], cx=.38, cy=.32, r=.75)}"/>'
    sem = ''
    for i in range(16):
        u, v = r.uniform(-.55, .55), r.uniform(-.35, .6)
        if abs(u) > .62 - v * .5:
            continue
        sem += f'<ellipse cx="{n(u * s)}" cy="{n(v * s)}" rx="{n(s * .035)}" ry="{n(s * .055)}"/>'
    out += f'<g fill="#ffd95a" opacity=".9">{sem}</g>'
    out += realce(a, -s * .22, -s * .22, s * .16, s * .26, rot=20, op=.55, blur=s * .05)
    if folhas:
        f = ''
        for ang in (-70, -30, 10, 50, 90):
            t = math.radians(ang - 90)
            f += f'<path d="M0,{n(-s * .5)} q{n(math.cos(t) * s * .25 - s * .08)},{n(math.sin(t) * s * .2)} {n(math.cos(t) * s * .42)},{n(math.sin(t) * s * .22 - s * .02)} q{n(-math.cos(t) * s * .1)},{n(s * .12)} {n(-math.cos(t) * s * .42)},{n(-math.sin(t) * s * .22 + s * .02)}Z"/>'
        out += f'<g fill="{a.linear([(0, "#7fcf4a"), (1, "#2f7a1c")])}">{f}</g>'
        out += f'<path d="M0,{n(-s * .55)} q{n(s * .05)},{n(-s * .2)} {n(s * .18)},{n(-s * .28)}" stroke="#3f7d22" stroke-width="{n(s * .08)}" fill="none" stroke-linecap="round"/>'
    return out + '</g>'


def _chantili(a, cx, cy, larg, alt, semente=3):
    """Chantili em nuvem: gomos fofos sobrepostos (de cima para baixo) e a pontinha enrolada."""
    r = rng(semente)
    cor = a.radial([(0, '#ffffff'), (.45, '#fefbf5'), (.78, '#f1e7d6'), (1, '#d9c9ae')], cx=.38, cy=.3, r=.78)
    fileiras = [(.2, -.74, 2), (.42, -.55, 3), (.64, -.36, 4), (.84, -.16, 5), (1.0, .04, 6)]
    s = ''
    py = cy - alt
    ponta = (f'M{n(-larg * .2)},{n(py + alt * .3)} C{n(-larg * .24)},{n(py + alt * .1)} {n(-larg * .06)},{n(py + alt * .02)} {n(larg * .04)},{n(py - alt * .04)} '
             f'C{n(larg * .02)},{n(py + alt * .06)} {n(larg * .18)},{n(py + alt * .1)} {n(larg * .22)},{n(py + alt * .3)}Z')
    massa = suave([(-larg * .92, cy + alt * .1), (-larg * .78, cy - alt * .16), (-larg * .5, cy - alt * .42), (-larg * .24, cy - alt * .64),
                   (0, cy - alt * .74), (larg * .24, cy - alt * .64), (larg * .5, cy - alt * .42), (larg * .78, cy - alt * .16),
                   (larg * .92, cy + alt * .1), (0, cy + alt * .22)], t=.9)
    s += f'<path d="{massa}" fill="{a.linear([(0, "#f3eadb"), (1, "#cdb999")])}"/>'
    s += f'<path d="{ponta}" fill="{cor}"/>'
    s += f'<path d="M{n(-larg * .1)},{n(py + alt * .2)} Q{n(-larg * .02)},{n(py + alt * .06)} {n(larg * .04)},{n(py)}" fill="none" stroke="#d9c7aa" stroke-opacity=".6" stroke-width="1"/>'
    for fw, fy, qtd in fileiras:
        w = larg * fw
        y = cy + alt * fy
        rr = larg * (.21 if qtd > 2 else .19)
        for i in range(qtd):
            t = (i + .5) / qtd * 2 - 1 if qtd > 1 else 0
            gx = t * (w - rr * .7)
            gy = y - (1 - t * t) * alt * .03 + r.uniform(-1, 1)
            gx += r.uniform(-2, 2)
            rx = rr * r.uniform(.98, 1.18)
            ry = rr * r.uniform(.78, .92)
            d = bolha(gx, gy, rx, ry, pontos=8, var=.05, semente=r.randint(1, 999))
            s += f'<path d="{d}" fill="{cor}" stroke="#d6c3a5" stroke-opacity=".3" stroke-width=".7"/>'
            s += realce(a, gx - rx * .28, gy - ry * .36, rx * .36, ry * .18, rot=-20, op=.7, blur=1.2)
    return f'<g transform="translate({n(cx)},0)">{s}</g>'


def _milkshake(a):
    T = -150
    lado = [(48, T), (47.2, -140), (44, -120), (38.5, -100), (31.5, -82), (25, -66), (19.5, -52), (15.5, -43), (10, -36),
            (6.6, -30), (6, -22), (6.6, -15), (9, -11.5)]
    larg = _interp(lado)
    taca = suave(lado, fechado=False) + ' ' + suave([(-x, y) for x, y in reversed(lado)], fechado=False).replace('M', 'L', 1) + 'Z'
    dentro_pts = [(x - 2.6, y) for x, y in lado if y <= -46] + [(9, -46), (0, -45)]
    dentro = suave(dentro_pts + [(-x, y) for x, y in reversed(dentro_pts) if x != 0], t=.9)
    k = .15
    s = ''
    # pé da taça
    s += f'<ellipse cx="0" cy="-4.5" rx="34" ry="6.4" fill="{a.linear([(0, "#fff", .5), (.5, "#fff", .12), (1, "#fff", .4)], 0, 0, 1, 0)}"/>'
    s += f'<path d="M-34,-4.5 A34 6.4 0 0 0 34,-4.5 V-2.6 A34 6.4 0 0 1 -34,-2.6Z" fill="#fff" opacity=".35"/>'
    s += f'<ellipse cx="0" cy="-5" rx="31" ry="5" fill="none" stroke="#fff" stroke-opacity=".5" stroke-width=".8"/>'
    s += f'<path d="M-34,-4.5 A34 6.4 0 0 0 34,-4.5" fill="none" stroke="#fff" stroke-opacity=".8" stroke-width="1"/>'
    # milk-shake (opaco) com caldas escorrendo por dentro
    shake = [(0, '#a8385c'), (.1, '#e2708f'), (.26, '#f9b6c8'), (.48, '#f49db6'), (.76, '#da6c8f'), (.9, '#f6aec4'), (1, '#9c3455')]
    s += f'<path d="{dentro}" fill="{a.linear(shake, 0, 0, 1, 0)}"/>'
    s += f'<g clip-path="{a.recorte(dentro)}">'
    s += f'<path d="{dentro}" fill="{a.linear([(0, "#fff", .12), (.5, "#000", 0), (1, "#4a0a1e", .35)])}"/>'
    calda, brilho_calda = '', ''
    for x0, desl, esp in ((-40, 34, 5), (-14, 30, 4), (14, 36, 5.5), (38, 26, 4)):
        c = f'M{x0},{T - 2} C{x0 + desl * .3},{T + 30} {x0 - desl * .5},{T + 60} {x0 + desl * .1},{T + 98}'
        calda += f'<path d="{c}" stroke-width="{esp}"/>'
        brilho_calda += f'<path d="{c}"/>'
    calda += f'<g stroke="#ff8fab" stroke-opacity=".55" stroke-width="1.1" transform="translate(-1.3,0)">{brilho_calda}</g>'
    s += f'<g fill="none" stroke="#c51d48" stroke-opacity=".8" stroke-linecap="round">{calda}</g>'
    r = rng(17)
    pts_b = ''
    for i in range(30):
        y = r.uniform(T + 4, -50)
        x = r.uniform(-.85, .85) * (larg(y) - 3)
        pts_b += f'<circle cx="{n(x)}" cy="{n(y)}" r="{n(r.uniform(.6, 1.4))}"/>'
    s += f'<g fill="#fff" opacity=".35">{pts_b}</g>'
    s += '</g>'
    # vidro da taça
    clip = a.recorte(taca)
    s += f'<path d="{taca}" fill="#fff" fill-opacity=".06" stroke="#fff" stroke-opacity=".18" stroke-width=".8"/>'
    s += f'<g clip-path="{clip}">'
    s += f'<rect x="-48" y="{T}" width="96" height="{-T - 11.5}" fill="{a.linear(VIDRO, 0, 0, 1, 0)}"/>'
    s += f'<path d="{_tira(larg, -.8, -.62, T + 8, -60)}" fill="#fff" opacity=".25" filter="{a.desfoque(2)}"/>'
    s += f'<path d="{_tira(larg, -.88, -.84, T + 6, -56)}" fill="#fff" opacity=".85" filter="{a.desfoque(.45)}"/>'
    s += f'<path d="{_tira(larg, .8, .9, T + 10, -58)}" fill="#ffe9c2" opacity=".45" filter="{a.desfoque(.9)}"/>'
    s += f'<rect x="-6" y="-46" width="12" height="36" fill="{a.linear([(0, "#fff", .55), (.3, "#fff", .1), (.7, "#fff", .05), (1, "#fff", .45)], 0, 0, 1, 0)}"/>'
    s += f'<path d="M-15,-44 Q0,-38 15,-44" fill="none" stroke="#fff" stroke-opacity=".5" stroke-width="1.2"/>'
    r = rng(19)
    s += gotas(a, r, _pontos_area(r, 34, larg, T + 6, -50, .9, 5.4), rmin=.7, rmax=2.2, escorrer=2)
    s += '</g>'
    # borda + escorridos de milk-shake por fora
    ryt = 48 * k
    s += f'<ellipse cx="0" cy="{T}" rx="48" ry="{n(ryt)}" fill="{a.radial([(0, "#fbc4d3"), (1, "#e07a99")], cx=.4, cy=.4)}"/>'
    for x0, L in ((-30, 22), (22, 32), (36, 14)):
        y0 = T + ryt * (1 - (x0 / 48) ** 2) ** .5 - 1
        s += (f'<path d="M{x0 - 5},{n(y0 - 1)} C{x0 - 4},{n(y0 + L * .5)} {x0 - 3.5},{n(y0 + L)} {x0},{n(y0 + L)} '
              f'C{x0 + 3.5},{n(y0 + L)} {x0 + 4},{n(y0 + L * .5)} {x0 + 5},{n(y0 - 1)}Z" fill="{a.linear([(0, "#f7a9bf"), (1, "#e4799a")], 0, 0, 1, 0)}"/>')
        s += realce(a, x0 - 1.6, y0 + L * .6, 1.1, L * .2, op=.7, blur=.4)
    s += f'<path d="{_arco_frente(0, T, 48, ryt)}" fill="none" stroke="#fff" stroke-opacity=".7" stroke-width="1.3"/>'
    # chantili, calda e morango
    s += _chantili(a, 0, T - 2, 50, 64)
    # calda de morango escorrendo do topo
    ty = T - 2 - 64
    poca = suave([(-14, ty + 17), (-7, ty + 10), (3, ty + 9), (13, ty + 12), (15, ty + 17), (6, ty + 20), (-6, ty + 21)], t=.9)
    escorre, gotas_c = '', ''
    for x0, y0, L, rg in ((-11, ty + 19, 15, 2.6), (1, ty + 20, 22, 3), (12, ty + 17, 11, 2.2)):
        escorre += f'M{x0 - 2.6},{n(y0 - 2)} C{x0 - 2.4},{n(y0 + L * .5)} {x0 - 1.2},{n(y0 + L * .7)} {x0 - 1.1},{n(y0 + L)} H{x0 + 1.1} C{x0 + 1.2},{n(y0 + L * .7)} {x0 + 2.4},{n(y0 + L * .5)} {x0 + 2.6},{n(y0 - 2)}Z '
        gotas_c += f'<circle cx="{x0}" cy="{n(y0 + L + rg * .5)}" r="{n(rg)}"/>'
    s += f'<g fill="#7a0a20" opacity=".3" transform="translate(1,1.4)" filter="{a.desfoque(.9)}"><path d="{escorre}"/>{gotas_c}</g>'
    s += f'<g fill="{a.linear([(0, "#f04462"), (.55, "#cc1c3f"), (1, "#9a0f2a")], 0, 0, 1, 1)}"><path d="{poca}"/><path d="{escorre}"/>{gotas_c}</g>'
    s += f'<ellipse cx="-5" cy="{n(ty + 12)}" rx="5" ry="1.2" fill="#ffb3c0" opacity=".85"/>'
    for x0, y0, L, rg in ((-11, ty + 19, 15, 2.6), (1, ty + 20, 22, 3)):
        s += f'<circle cx="{n(x0 - rg * .35)}" cy="{n(y0 + L + rg * .1)}" r="{n(rg * .3)}" fill="#fff" opacity=".8"/>'
    s += f'<ellipse cx="2" cy="{T - 60}" rx="13" ry="3.4" fill="#6b4a33" opacity=".35" filter="{a.desfoque(1.6)}"/>'
    s += morango(a, 1, T - 70, 17, rot=-8, semente=5)
    # canudo espetado no chantili
    s += palha(a, 22, T - 26, 24, 62, larg=8, cor='#ffffff', listra='#f06292', n_listras=8)
    return _g(200, 252, 1, s)


# ---------------------------------------------------------------- água

def garrafa_agua(a, cx, base, escala=1.0):
    """Garrafa de água mineral 500 ml, plástico com anéis, tampa azul."""
    lado = [(10.5, -178), (11.2, -172), (14, -165), (19, -156), (24, -146), (26.6, -136), (27, -127), (27, -100), (27, -70),
            (27, -40), (26.6, -22), (25.6, -12), (23, -5)]
    pes = [(16, -1), (8, -3.2), (0, 0)]
    larg = _interp(lado + pes)
    d = _contorno(lado, pes)
    clip = a.recorte(d)
    r = rng(71)
    nv = -152
    s = f'<path d="{d}" fill="#fff" fill-opacity=".05" stroke="#fff" stroke-opacity=".2" stroke-width=".7"/>'
    dentro = _contorno([(x - 2, y) for x, y in lado], [(x * .9, y - 2.2) for x, y in pes])
    agua = [(0, '#4a96d6', .8), (.07, '#b8e4ff', .72), (.18, '#5aa6e6', .42), (.5, '#3d86c8', .26), (.8, '#4a96d6', .36),
            (.9, '#c8ecff', .7), (.96, '#eef9ff', .85), (1, '#4a96d6', .8)]
    s += f'<g clip-path="{a.recorte(f"M-60,{nv} H60 V10 H-60Z")}">'
    s += f'<path d="{dentro}" fill="{a.linear(agua, 0, 0, 1, 0)}"/>'
    s += f'<path d="{dentro}" fill="{a.linear([(0, "#fff", .1), (1, "#06243f", .22)])}"/>'
    s += bolhas_gas(a, r, lambda y: larg(y) - 5, nv, -10, 18, cor='#e6f6ff', op=.6)
    s += '</g>'
    wl = larg(nv) - 2
    s += f'<ellipse cx="0" cy="{nv}" rx="{n(wl)}" ry="{n(wl * .16)}" fill="#cfeeff" opacity=".45"/>'
    s += f'<path d="{_arco_frente(0, nv, wl, wl * .16)}" fill="none" stroke="#fff" stroke-opacity=".85" stroke-width="1"/>'
    s += f'<g clip-path="{clip}">'
    s += f'<rect x="-27" y="-178" width="54" height="178" fill="{a.linear(VIDRO, 0, 0, 1, 0)}"/>'
    # anéis do plástico
    aneis = [-124, -118] + [-72 + i * -0 for i in range(0)] + [y for y in range(-70, -16, 8)]
    for ys in aneis:
        w = larg(ys)
        s += f'<path d="{_arco_frente(0, ys, w, w * .16)}" fill="none" stroke="#06243f" stroke-opacity=".35" stroke-width="1.6"/>'
        s += f'<path d="{_arco_frente(0, ys + 1.8, w, w * .16)}" fill="none" stroke="#fff" stroke-opacity=".45" stroke-width="1"/>'
    s += f'<path d="{_tira(larg, -.76, -.58, -168, -10)}" fill="#fff" opacity=".22" filter="{a.desfoque(1.6)}"/>'
    s += f'<path d="{_tira(larg, -.85, -.8, -170, -10)}" fill="#fff" opacity=".9" filter="{a.desfoque(.4)}"/>'
    s += f'<path d="{_tira(larg, .8, .89, -160, -10)}" fill="#e6f6ff" opacity=".55" filter="{a.desfoque(.7)}"/>'
    s += gotas(a, r, _pontos_area(r, 34, larg, nv + 4, -10, .9, 6.5), rmin=.7, rmax=2.1, escorrer=2)
    s += '</g>'
    # rótulo
    y0, y1 = -110, -80
    rot = _faixa_curva(27.6, y0, 27.6, y1, 27.6 * .16, 27.6 * .16)
    s += f'<path d="{rot}" fill="{a.linear([(0, "#ffffff"), (1, "#dcefff")])}"/>'
    s += f'<g clip-path="{a.recorte(rot)}">'
    s += f'<path d="{_faixa_curva(29, y1 - 8, 29, y1 + 2, 29 * .16, 29 * .16)}" fill="{a.linear([(0, "#5fb3f5"), (1, "#2a7fcf")])}"/>'
    s += f'<path d="{_arco_frente(0, y0 + 3.5, 29, 29 * .16)}" fill="none" stroke="#5fb3f5" stroke-width="1.4"/>'
    s += f'<path d="M-27,{y1 - 11} q7,-4 13.5,0 t13.5,0 t13.5,0 t13.5,0" fill="none" stroke="#9fd2fb" stroke-width="1.2"/>'
    s += selo_marca(a, 0, (y0 + y1) / 2 - 1.5, 10.5)
    s += f'<path d="{rot}" fill="{a.linear(PAPEL, 0, 0, 1, 0)}"/>'
    s += '</g>'
    # gargalo e tampa
    s += (f'<rect x="-14" y="-182" width="28" height="3.2" rx="1.4" '
          f'fill="{a.linear([(0, "#fff", .25), (.25, "#fff", .75), (.6, "#fff", .2), (1, "#fff", .5)], 0, 0, 1, 0)}"/>')
    s += f'<rect x="-10.5" y="-184" width="21" height="6" fill="#fff" opacity=".22"/>'
    s += _tampa_rosca(a, 12.5, -198, -184, cor=('#7cc4ff', '#2f86d6', '#16508f'))
    return _g(cx, base, escala, s)


# ---------------------------------------------------------------- açaí

ACAI = [(0, '#1c0624'), (.08, '#3a0f4c'), (.24, '#5f2177'), (.4, '#4c1763'), (.72, '#330b43'), (.88, '#55206a'), (.95, '#7a3a8e'), (1, '#1a0520')]


def banana(a, x, y, raio, k=.55):
    """Rodela de banana vista de cima em perspectiva (achatada por k)."""
    ry = raio * k
    s = f'<ellipse cx="{n(x + .4)}" cy="{n(y + raio * .16)}" rx="{n(raio)}" ry="{n(ry)}" fill="#d9bd6a"/>'
    s += f'<ellipse cx="{n(x)}" cy="{n(y)}" rx="{n(raio)}" ry="{n(ry)}" fill="{a.radial([(0, "#fffbe6"), (.6, "#fff0b8"), (1, "#ecd27f")], cx=.42, cy=.38)}"/>'
    s += f'<ellipse cx="{n(x)}" cy="{n(y)}" rx="{n(raio * .45)}" ry="{n(ry * .45)}" fill="none" stroke="#e6cf86" stroke-width="{n(raio * .07)}" opacity=".8"/>'
    for ang in (0, 2.1, 4.2):
        s += f'<circle cx="{n(x + math.cos(ang) * raio * .16)}" cy="{n(y + math.sin(ang) * ry * .16)}" r="{n(raio * .06)}" fill="#8a6a2a" opacity=".7"/>'
    s += f'<ellipse cx="{n(x - raio * .35)}" cy="{n(y - ry * .35)}" rx="{n(raio * .25)}" ry="{n(ry * .16)}" fill="#fff" opacity=".85"/>'
    return s


def banana_frente(a, x, y, raio):
    """Rodela de banana encostada na parede do copo (vista de frente)."""
    s = f'<circle cx="{n(x)}" cy="{n(y)}" r="{n(raio)}" fill="{a.radial([(0, "#fff8da"), (.65, "#fbe9a6"), (1, "#e3c56c")], cx=.45, cy=.42)}"/>'
    s += f'<circle cx="{n(x)}" cy="{n(y)}" r="{n(raio * .45)}" fill="none" stroke="#e8d08a" stroke-width="{n(raio * .08)}"/>'
    for ang in (.3, 2.4, 4.5):
        s += f'<circle cx="{n(x + math.cos(ang) * raio * .17)}" cy="{n(y + math.sin(ang) * raio * .17)}" r="{n(raio * .07)}" fill="#8a6a2a" opacity=".7"/>'
    return s


def _coracao(s):
    return (f'M0,{n(-s * .5)} C{n(s * .5)},{n(-s * .66)} {n(s * .66)},{n(-s * .12)} {n(s * .38)},{n(s * .26)} '
            f'C{n(s * .2)},{n(s * .52)} {n(s * .06)},{n(s * .64)} 0,{n(s * .66)} C{n(-s * .06)},{n(s * .64)} {n(-s * .2)},{n(s * .52)} {n(-s * .38)},{n(s * .26)} '
            f'C{n(-s * .66)},{n(-s * .12)} {n(-s * .5)},{n(-s * .66)} 0,{n(-s * .5)}Z')


def morango_metade(a, x, y, s, rot=0, folha=True):
    """Metade de morango com o corte voltado para a frente."""
    d = _coracao(s)
    out = f'<g transform="translate({n(x)},{n(y)})' + (f' rotate({n(rot)})' if rot else '') + '">'
    out += f'<path d="{d}" fill="#b5122a"/>'
    out += f'<path d="{d}" fill="{a.radial([(0, "#ffe2e2"), (.35, "#ffb0b4"), (.7, "#f2566a"), (.9, "#d61f3a"), (1, "#d61f3a", 0)], cx=.5, cy=.45, r=.55)}" transform="scale(.9)"/>'
    out += (f'<path d="M0,{n(-s * .36)} C{n(s * .14)},{n(-s * .1)} {n(s * .1)},{n(s * .3)} 0,{n(s * .5)} C{n(-s * .1)},{n(s * .3)} {n(-s * .14)},{n(-s * .1)} 0,{n(-s * .36)}Z" '
            f'fill="#fff4f2" opacity=".85"/>')
    for sx in (-1, 1):
        out += f'<path d="M0,{n(-s * .3)} q{n(sx * s * .26)},{n(s * .22)} {n(sx * s * .18)},{n(s * .62)}" fill="none" stroke="#fff" stroke-opacity=".55" stroke-width="{n(s * .03)}"/>'
    if folha:
        out += f'<path d="M{n(-s * .3)},{n(-s * .52)} q{n(s * .3)},{n(-s * .2)} {n(s * .6)},0 q{n(-s * .3)},{n(s * .12)} {n(-s * .6)},0Z" fill="#4f9a2c"/>'
    out += f'<ellipse cx="{n(-s * .18)}" cy="{n(-s * .2)}" rx="{n(s * .1)}" ry="{n(s * .05)}" fill="#fff" opacity=".8" transform="rotate(-30 {n(-s * .18)} {n(-s * .2)})"/>'
    return out + '</g>'


def morango_deitado(a, x, y, s, k=.5, rot=0):
    """Metade de morango deitada, corte para cima, em perspectiva (achatada por k), com a casca por baixo."""
    out = f'<g transform="translate({n(x)},{n(y)}) scale(1,{n(k)})">'
    out += f'<g transform="translate(0,{n(s * .2)}) rotate({n(rot)})"><path d="{_coracao(s)}" fill="#8e0c20"/></g>'
    out += morango_metade(a, 0, 0, s, rot, folha=False)
    return out + '</g>'


def granola(a, r, pontos, tam=3.2):
    """Granola: pedacinhos irregulares (agrupados por cor) com textura crocante e brilho."""
    cores = ['#d49a4a', '#b8732f', '#e6bb6c', '#93531f']
    grupos = {c: '' for c in cores}
    luz = ''
    for i, (x, y) in enumerate(pontos):
        t = tam * r.uniform(.65, 1.2)
        q = [(r.uniform(-1, -.5) * t, r.uniform(-.6, .2) * t), (r.uniform(-.1, .4) * t, r.uniform(-.8, -.45) * t),
             (r.uniform(.6, 1) * t, r.uniform(-.3, .3) * t), (r.uniform(-.2, .3) * t, r.uniform(.45, .8) * t)]
        grupos[cores[i % 4]] += f'M{n(x + q[0][0])},{n(y + q[0][1])} ' + ' '.join(f'l{n(b[0] - c[0])},{n(b[1] - c[1])}' for c, b in zip(q, q[1:])) + 'Z'
        if i % 3 == 0:
            luz += f'M{n(x + q[0][0] * .6)},{n(y + q[1][1] * .5)} l{n(t * .5)},{n(-t * .2)}'
    s = f'<g filter="{a.textura("frito")}" stroke-width="{n(tam * .45)}" stroke-linejoin="round">'
    for c, d in grupos.items():
        if d:
            s += f'<path d="{d}" fill="{c}" stroke="{c}"/>'
    s += '</g>'
    if luz:
        s += f'<path d="{luz}" stroke="#fff3cf" stroke-opacity=".75" stroke-width="{n(tam * .22)}" stroke-linecap="round" fill="none"/>'
    return s


def leite_condensado(a, pts, esp=3.2):
    """Fio de leite condensado: sombra, corpo cremoso e brilho."""
    c = suave(pts, fechado=False, t=.9)
    s = f'<path d="{c}" fill="none" stroke="#1a0520" stroke-opacity=".45" stroke-width="{n(esp + 1.2)}" stroke-linecap="round" transform="translate(.6,1.4)" filter="{a.desfoque(.9)}"/>'
    s += f'<path d="{c}" fill="none" stroke="#f4e2bd" stroke-width="{n(esp)}" stroke-linecap="round"/>'
    s += f'<path d="{c}" fill="none" stroke="#fffaf0" stroke-width="{n(esp * .5)}" stroke-linecap="round" transform="translate(-.3,-.5)"/>'
    return s


def _monte_acai(a, cx, y, rx, ry, alt, semente):
    """Superfície do açaí acima da borda: domo cremoso levemente irregular, com brilho."""
    r = rng(semente)
    pts = []
    for i in range(13):
        t = i / 12
        ang = math.pi * t
        bump = r.uniform(-1.2, 1.2) if 0 < i < 12 else 0
        pts.append((cx - rx * math.cos(ang), y - (ry + alt) * math.sin(ang) ** .75 + bump))
    topo = suave(pts, fechado=False, t=.9)
    d = topo + f' A{n(rx)} {n(ry)} 0 0 1 {n(cx - rx)},{n(y)}Z'
    s = f'<path d="{d}" fill="{a.radial([(0, "#8a45a3"), (.4, "#5c1f74"), (.85, "#2e0a3b"), (1, "#22062c")], cx=.4, cy=.3, r=.75)}"/>'
    s += f'<g clip-path="{a.recorte(d)}">'
    s += f'<path d="{topo}" fill="none" stroke="#b47ccc" stroke-opacity=".45" stroke-width="3" transform="translate(1.5,2.5)" filter="{a.desfoque(1.5)}"/>'
    s += f'<path d="{_arco_frente(cx, y, rx, ry)}" fill="none" stroke="#14031a" stroke-opacity=".5" stroke-width="4" filter="{a.desfoque(2)}"/>'
    s += '</g>'
    s += realce(a, cx - rx * .42, y - ry * .5 - alt * .55, rx * .2, ry * .16, rot=-20, op=.55, blur=1.2)
    return s, d


def _coberturas(a, cx, y, rx, ry, alt, semente, banan=4, moran=2, gran=26, escala=1.0):
    """Coberturas sobre o monte de açaí (de trás para a frente) e fio de leite condensado por cima."""
    r = rng(semente)
    pos = lambda u, v: (cx + u * rx, y + v * ry - alt * max(1 - u * u - v * v, 0) ** .5)
    itens = []
    for i in range(banan):
        u = -.62 + i * 1.24 / max(banan - 1, 1)
        v = (-.35 if i % 2 else .25) + r.uniform(-.08, .08)
        itens.append((v, 'b', u))
    morangos = [(.08, -.5, 1.0, 10)] if moran == 1 else [(-.3, -.52, 1.0, -16), (.34, -.2, .86, 14)]
    for u, v, esc, rot in morangos[:moran]:
        itens.append((v, 'm', (u, esc, rot)))
    gpts = []
    for i in range(gran):
        t = r.uniform(0, 6.28)
        q = r.uniform(.25, .95) ** .7
        gpts.append(pos(math.cos(t) * q * .92, math.sin(t) * q * .85))
    gpts.sort(key=lambda p: p[1])
    meio = len(gpts) // 2
    s = granola(a, r, gpts[:meio], 3.4 * escala)
    for v, tipo, u in sorted(itens, key=lambda t: t[0]):
        if tipo == 'b':
            x, yy = pos(u, v)
            s += banana(a, x, yy, 13.5 * escala, .52)
        else:
            u, esc, rot = u
            x, yy = pos(u, v)
            s += morango(a, x, yy - 10 * escala * esc, 21 * escala * esc, rot=rot, semente=int(u * 10) + 7)
    s += granola(a, r, gpts[meio:], 3.4 * escala)
    pts = [pos(-.8 + i * 1.6 / 6, (.3 if i % 2 else -.2) + r.uniform(-.05, .05)) for i in range(7)]
    s += leite_condensado(a, pts, 2.8 * escala)
    return s


def _onda(r, x0, x1, y, curva, passo=8, jit=1.5):
    """Linha ondulada que acompanha a frente de um cilindro (curva para baixo no meio)."""
    pts = []
    x = x0
    while x <= x1 + .1:
        f = max(1 - (x / max(abs(x0), abs(x1))) ** 2, 0) ** .5
        pts.append((x, y + f * curva + r.uniform(-jit, jit)))
        x += passo
    return pts


def copo_acai(a, cx, base, grande=False):
    """Copo plástico transparente de açaí, com camadas visíveis e coberturas no topo."""
    if grande:
        wt, wb, h, sem, alt = 66, 48, 168, 82, 17
        camadas = [('acai', .27), ('granola', .37), ('acai', .6), ('leite', .67), ('acai', 1.0)]
    else:
        wt, wb, h, sem, alt = 56, 42, 128, 81, 15
        camadas = [('acai', .4), ('leite', .49), ('acai', 1.0)]
    k = .2
    T = -h
    larg = lambda y: wt + (wb - wt) * ((y - T) / (0 - T))
    ryt, ryb = wt * k, wb * k
    sil = (f'M{-wt},{T} L{-wb},{n(-ryb)} A{wb} {n(ryb)} 0 0 0 {wb},{n(-ryb)} L{wt},{T} '
           f'A{wt} {n(ryt)} 0 0 0 {-wt},{T}Z')
    g = 1.6
    inner = (f'M{n(-wt + g)},{T} L{n(-wb + g)},{n(-ryb - 3)} A{n(wb - g)} {n(ryb)} 0 0 0 {n(wb - g)},{n(-ryb - 3)} L{n(wt - g)},{T} '
             f'A{n(wt - g)} {n(ryt)} 0 0 1 {n(-wt + g)},{T}Z')
    r = rng(sem)
    s = f'<path d="{inner}" fill="{a.linear(ACAI, 0, 0, 1, 0)}"/>'
    s += f'<g clip-path="{a.recorte(inner)}">'
    # cremosidade do açaí junto à parede
    lis = ''
    for i in range(int(h / 9)):
        x = r.uniform(-wt * .85, wt * .6)
        y = r.uniform(T + 6, -8)
        lis += f'M{n(x)},{n(y)} q{n(r.uniform(5, 10))},{n(r.uniform(-4, 2))} {n(r.uniform(14, 24))},{n(r.uniform(-1, 4))}'
    s += f'<path d="{lis}" fill="none" stroke="#9a58b0" stroke-opacity=".4" stroke-width="2.2" stroke-linecap="round"/>'
    yb = 0
    curva = ryt * .9
    for tipo, f in camadas:
        y1 = -h * f
        if tipo == 'acai':
            yb = y1
            continue
        y0 = yb
        topo = _onda(r, -wt - 2, wt + 2, y1, curva, jit=1.2)
        fundo_ = list(reversed(_onda(r, -wt - 2, wt + 2, y0, curva, jit=2)))
        d = suave(topo + fundo_, t=.8)
        if tipo == 'leite':
            s += f'<path d="{d}" fill="{a.linear([(0, "#fffaf0"), (.55, "#f7e6c2"), (1, "#e6c993")])}"/>'
            pingos = ''
            for x0 in (-wt * .6, -wt * .18, wt * .3, wt * .66):
                L = r.uniform(7, 15)
                yy = y0 + max(1 - (x0 / wt) ** 2, 0) ** .5 * curva - 1.5
                pingos += f'M{n(x0 - 3)},{n(yy)} C{n(x0 - 3)},{n(yy + L * .7)} {n(x0 - 1.4)},{n(yy + L)} {n(x0)},{n(yy + L)} C{n(x0 + 1.4)},{n(yy + L)} {n(x0 + 3)},{n(yy + L * .7)} {n(x0 + 3)},{n(yy)}Z'
            s += f'<path d="{pingos}" fill="#f0dbb2"/>'
            s += f'<path d="{suave(topo, fechado=False)}" fill="none" stroke="#fff" stroke-opacity=".8" stroke-width="1.3" transform="translate(0,1.6)"/>'
        else:
            s += f'<path d="{d}" fill="#8a4c1c"/>'
            gp = []
            for i in range(int(wt * 1.5)):
                x = r.uniform(-wt, wt)
                gp.append((x, r.uniform(y1 + 1, y0) + max(1 - (x / wt) ** 2, 0) ** .5 * curva))
            s += granola(a, r, gp, 3.6)
        yb = y1
    # frutas encostadas no plástico
    if grande:
        for x, y, rr in ((-36, -74, 11), (-2, -70, 12), (34, -76, 11)):
            s += banana_frente(a, x, y, rr)
        s += morango_metade(a, -24, -136, 19, rot=-12, folha=False) + morango_metade(a, 26, -140, 17, rot=10, folha=False)
    else:
        for x, y, rr in ((-28, -26, 10.5), (12, -22, 11)):
            s += banana_frente(a, x, y, rr)
        s += morango_metade(a, -8, -96, 18, rot=8, folha=False)
    s += f'<path d="{inner}" fill="{a.linear([(0, "#000", .45), (.12, "#000", .1), (.3, "#fff", .08), (.5, "#000", 0), (.85, "#000", .3), (1, "#000", .5)], 0, 0, 1, 0)}"/>'
    s += '</g>'
    # topo: monte de açaí com coberturas
    m, _ = _monte_acai(a, 0, T, wt - 1, ryt, alt, sem + 1)
    s += m
    s += _coberturas(a, 0, T, wt - 1, ryt, alt, sem + 2, banan=3 if not grande else 4, moran=1 if not grande else 2,
                     gran=26 if not grande else 34, escala=1.0 if not grande else 1.1)
    # plástico
    clip = a.recorte(sil)
    s += f'<g clip-path="{clip}">'
    s += f'<path d="{sil}" fill="{a.linear(VIDRO, 0, 0, 1, 0)}"/>'
    s += f'<path d="{_tira(larg, -.8, -.64, T + 6, -8)}" fill="#fff" opacity=".22" filter="{a.desfoque(1.8)}"/>'
    s += f'<path d="{_tira(larg, -.88, -.84, T + 6, -6)}" fill="#fff" opacity=".8" filter="{a.desfoque(.45)}"/>'
    s += f'<path d="{_tira(larg, .8, .88, T + 8, -8)}" fill="#ffe9c2" opacity=".4" filter="{a.desfoque(.8)}"/>'
    s += f'<path d="{_arco_frente(0, -4, wb - 1, ryb)}" fill="none" stroke="#fff" stroke-opacity=".35" stroke-width="1.2"/>'
    r2 = rng(sem + 5)
    s += gotas(a, r2, _pontos_area(r2, 22 if grande else 16, larg, T + 14, -8, .9, 8), rmin=.7, rmax=2.1, escorrer=1)
    s += '</g>'
    s += f'<path d="{sil}" fill="none" stroke="#fff" stroke-opacity=".2" stroke-width=".8"/>'
    # borda enrolada do copo (só a frente aparece sobre o monte)
    s += f'<path d="{_arco_frente(0, T, wt + .6, ryt + .4)}" fill="none" stroke="#e9e2f2" stroke-opacity=".75" stroke-width="2.4"/>'
    s += f'<path d="{_arco_frente(0, T - .6, wt, ryt)}" fill="none" stroke="#fff" stroke-opacity=".9" stroke-width=".9"/>'
    return _g(cx, base, 1, s)


def tigela_acai(a, cx, base):
    """Tigela de cerâmica com açaí e coberturas em faixas: granola, banana e morango."""
    rx, ry, yt = 128, 50, -84
    corpo = (f'M{-rx},{yt} C{-rx},{yt + 42} {-rx * .64},{yt + 76} {-52},{-9} L{-46},0 H46 L52,-9 '
             f'C{rx * .64},{yt + 76} {rx},{yt + 42} {rx},{yt} A{rx} {ry} 0 0 1 {-rx},{yt}Z')
    s = f'<path d="M-48,-10 L-46,0 H46 L48,-10Z" fill="{a.linear([(0, "#8f7f68"), (.3, "#cdbda3"), (1, "#7a6a54")], 0, 0, 1, 0)}"/>'
    s += f'<path d="{corpo}" fill="{a.linear([(0, "#fbf6ee"), (.55, "#efe4d3"), (1, "#cdbb9f")])}"/>'
    s += f'<g clip-path="{a.recorte(corpo)}">'
    s += f'<path d="{corpo}" fill="{a.linear([(0, "#000", .38), (.1, "#000", .08), (.28, "#fff", .3), (.42, "#fff", 0), (.72, "#000", .12), (.9, "#000", .34), (.96, "#ffe9c2", .22), (1, "#000", .35)], 0, 0, 1, 0)}"/>'
    s += realce(a, -rx * .52, yt + 38, 26, 6, rot=-28, op=.55, blur=3)
    s += f'<path d="{_arco_frente(0, yt + 2, rx, ry)}" fill="none" stroke="#fff" stroke-opacity=".35" stroke-width="3" filter="{a.desfoque(1.2)}"/>'
    s += '</g>'
    s += sombra_contato(a, -42, 42, -9, alt=3, op=.3, blur=1.2)
    # borda e parede interna
    s += f'<ellipse cx="0" cy="{yt}" rx="{rx}" ry="{ry}" fill="{a.linear([(0, "#d6c7ae"), (1, "#fffaf2")])}"/>'
    s += f'<ellipse cx="0" cy="{yt + 1.5}" rx="{rx - 6}" ry="{ry - 4.5}" fill="{a.linear([(0, "#a8967a"), (.45, "#ddd0ba"), (1, "#f6efe3")])}"/>'
    # açaí
    arx, ary, ay, dome = rx - 11, ry - 9, yt + 5, 7
    s += f'<ellipse cx="0" cy="{ay - 2}" rx="{arx + 1}" ry="{ary + 1}" fill="#1a0520" opacity=".45" filter="{a.desfoque(2)}"/>'
    s += f'<ellipse cx="0" cy="{ay}" rx="{arx}" ry="{ary}" fill="{a.radial([(0, "#7d3895"), (.5, "#561b6d"), (1, "#2a0834")], cx=.42, cy=.4, r=.62)}"/>'
    r = rng(91)
    sw = ''
    for i in range(16):
        u, v = r.uniform(-.85, .85), r.uniform(.3, .85)
        if u * u + v * v > .85:
            continue
        x0, y0 = u * arx, ay + v * ary
        sw += f'M{n(x0)},{n(y0)} q{n(r.uniform(5, 10))},{n(r.uniform(-3, -1))} {n(r.uniform(12, 20))},{n(r.uniform(-1, 1.5))}'
    s += f'<path d="{sw}" fill="none" stroke="#a066b8" stroke-opacity=".5" stroke-width="1.8" stroke-linecap="round"/>'
    s += realce(a, -arx * .45, ay + ary * .55, 20, 3.5, rot=-4, op=.35, blur=2)
    pos = lambda u, v: (u * arx, ay + v * ary - dome * max(1 - u * u - v * v, 0) ** .5)
    dentro = lambda u, v, m=.9: u * u + v * v < m
    # faixa de trás: granola
    gp = []
    for i in range(120):
        u, v = r.uniform(-.95, .95), r.uniform(-.9, -.38)
        if dentro(u, v, .86):
            gp.append(pos(u, v))
    gp.sort(key=lambda p: p[1])
    s += f'<ellipse cx="0" cy="{n(ay - ary * .58)}" rx="{n(arx * .82)}" ry="{n(ary * .26)}" fill="#3a1a0a" opacity=".35" filter="{a.desfoque(2)}"/>'
    s += granola(a, r, gp, 4.2)
    # faixa do meio: banana
    for i in range(8):
        u = -.76 + i * 1.52 / 7
        v = -.13 + (.04 if i % 2 else -.04)
        if not dentro(u, v, .88):
            continue
        x, y = pos(u, v)
        s += banana(a, x + r.uniform(-1.5, 1.5), y, 15, .5)
    # faixa da frente: morangos deitados
    for i in range(6):
        u = -.66 + i * 1.32 / 5
        v = .3 + (.04 if i % 2 else -.04)
        x, y = pos(u, v)
        s += morango_deitado(a, x + r.uniform(-2, 2), y, 25, .55, rot=180 + r.uniform(-25, 25))
    # fio de leite condensado sobre o açaí da frente
    pts = [pos(-.7 + i * 1.4 / 8, .66 + (.08 if i % 2 else -.08)) for i in range(9)]
    s += leite_condensado(a, pts, 3.4)
    s += f'<path d="{_arco_frente(0, yt, rx, ry)}" fill="none" stroke="#fff" stroke-opacity=".75" stroke-width="1.3"/>'
    return _g(cx, base, 1, s)


# ---------------------------------------------------------------- cenas

def gerar():
    A = {}

    a = Arte('Ilustração de lata de refrigerante')
    corpo = fundo(a) + sombra(a, cx=204, cy=251, rx=50, ry=8) + lata(a, 200, 252, 1.12)
    corpo += gelo_mesa(a, 136, 258, 24, -10, semente=3) + gelo_mesa(a, 159, 265, 18, 14, semente=4) + gelo_mesa(a, 262, 260, 21, 6, semente=5)
    A['refrigerante-lata'] = a.svg(corpo)

    a = Arte('Ilustração de refrigerante 600 ml')
    corpo = fundo(a) + sombra(a, cx=203, cy=251, rx=36, ry=7) + garrafa_pet(a, 200, 252, 1.1, .6)
    corpo += gelo_mesa(a, 150, 260, 21, -8, semente=6) + gelo_mesa(a, 254, 262, 19, 10, semente=7)
    A['refrigerante-600'] = a.svg(corpo)

    a = Arte('Ilustração de garrafa de refrigerante')
    corpo = fundo(a) + sombra(a, cx=203, cy=253, rx=50, ry=8) + garrafa_pet(a, 200, 255, 1.0, 2)
    A['refrigerante-2l'] = a.svg(corpo)

    A['suco'] = cena_copo('Ilustração de suco natural', MARCA, '#ff9a1a', _suco)
    A['limonada'] = cena_copo('Ilustração de limonada suíça', '#d9f07a', '#d8eb9a', _limonada)
    A['cha-gelado'] = cena_copo('Ilustração de chá gelado', '#ff9f43', '#e08a2c', _cha,
                                extras=lambda a: gelo_mesa(a, 140, 262, 20, -12, semente=8) + gelo_mesa(a, 262, 259, 17, 10, semente=9))

    A['milkshake'] = cena_copo('Ilustração de milk-shake', '#f472b6', None, _milkshake, rx_sombra=48)

    a = Arte('Ilustração de garrafa de água', brilho=AZUL)
    corpo = fundo(a) + sombra(a, cx=203, cy=251, rx=36, ry=7)
    corpo += f'<ellipse cx="210" cy="254" rx="26" ry="4" fill="#9fd4ff" opacity=".28" filter="{a.desfoque(2.5)}"/>'
    corpo += garrafa_agua(a, 200, 252, 1.12)
    A['agua'] = a.svg(corpo)

    a = Arte('Ilustração de copo de açaí', brilho=ROXO)
    A['acai'] = a.svg(fundo(a) + sombra(a, cx=203, cy=251, rx=56, ry=8) + copo_acai(a, 200, 252))
    a = Arte('Ilustração de copo grande de açaí', brilho=ROXO)
    A['acai-grande'] = a.svg(fundo(a) + sombra(a, cx=203, cy=253, rx=66, ry=8) + copo_acai(a, 200, 254, grande=True))
    a = Arte('Ilustração de tigela de açaí', brilho=ROXO)
    A['acai-tigela'] = a.svg(fundo(a) + sombra(a, cx=203, cy=252, rx=100, ry=9) + tigela_acai(a, 200, 256))
    return A
