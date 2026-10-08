# Sobremesas: brownie, petit gâteau, pudim, churros, sorvete e mousse.
#
# Além das peças de estilo.py, este módulo traz um "motor 3D" mínimo (Vista e
# Prisma) para desenhar sólidos simples em 3/4 — caixas, cunhas, cilindros —
# com sombreamento automático pela direção da luz (do alto, à esquerda).
# especiais.py reaproveita essas peças.
import math

from .estilo import (Arte, fundo, sombra, realce, suave, bolha, rng, n, CX)

# ---------------------------------------------------------------- cores

QUENTE = '#fff4e2'      # luz principal (branco quente)
ARO = '#ffd9a0'         # luz de contorno (à direita)


def _rgb(c):
    c = c.lstrip('#')
    if len(c) == 3:
        c = ''.join(ch * 2 for ch in c)
    return tuple(int(c[i:i + 2], 16) for i in (0, 2, 4))


def mix(c1, c2, t):
    """Mistura duas cores hex (t=0 → c1, t=1 → c2)."""
    t = max(0.0, min(1.0, t))
    a, b = _rgb(c1), _rgb(c2)
    return '#' + ''.join(f'{round(x + (y - x) * t):02x}' for x, y in zip(a, b))


def tom(c, k, escuro='#160700'):
    """Clareia (k>0, rumo à luz quente) ou escurece (k<0, rumo a um marrom profundo)."""
    return mix(c, QUENTE, k) if k > 0 else mix(c, escuro, -k)


def poly(pts):
    return 'M' + ' L'.join(f'{n(x)},{n(y)}' for x, y in pts) + 'Z'


def linha(pts):
    return 'M' + ' L'.join(f'{n(x)},{n(y)}' for x, y in pts)


def pontos(lista, cor, larg, op=1):
    """Muitos pontinhos num só <path> (traço de comprimento zero com ponta redonda)."""
    if not lista:
        return ''
    d = ''.join(f'M{n(x)},{n(y)}h0' for x, y in lista)
    o = '' if op == 1 else f' stroke-opacity="{n(op)}"'
    return f'<path d="{d}" stroke="{cor}" stroke-width="{n(larg)}" stroke-linecap="round"{o}/>'


def tracos(lista, cor, larg, op=1, extra=''):
    """Vários segmentos (x0,y0,x1,y1) num só <path>."""
    if not lista:
        return ''
    d = ''.join(f'M{n(x0)},{n(y0)}L{n(x1)},{n(y1)}' for x0, y0, x1, y1 in lista)
    o = '' if op == 1 else f' stroke-opacity="{n(op)}"'
    return f'<path d="{d}" stroke="{cor}" stroke-width="{n(larg)}" stroke-linecap="round" fill="none"{o}{extra}/>'


# ---------------------------------------------------------------- 3D simples

LUZ = (-0.62, -0.5)     # componente horizontal da luz (vem da esquerda e da frente)


class Vista:
    """Projeção ortográfica em 3/4: x à direita, y para o fundo, z para cima."""

    def __init__(self, cx, cy, yaw=0, elev=24):
        self.cx, self.cy = cx, cy
        r = math.radians(yaw)
        self.c, self.s = math.cos(r), math.sin(r)
        e = math.radians(elev)
        self.ce, self.se = math.cos(e), math.sin(e)

    def rot(self, x, y):
        return (x * self.c - y * self.s, x * self.s + y * self.c)

    def p(self, x, y, z=0):
        xr, yr = self.rot(x, y)
        return (self.cx + xr, self.cy - yr * self.se - z * self.ce)


def _normal(p, q):
    dx, dy = q[0] - p[0], q[1] - p[1]
    L = math.hypot(dx, dy) or 1
    return (dy / L, -dx / L)


def subdividir(pts, passo=8, fechado=True):
    out = []
    k = len(pts)
    for i in range(k if fechado else k - 1):
        p, q = pts[i], pts[(i + 1) % k]
        m = max(1, int(math.hypot(q[0] - p[0], q[1] - p[1]) / passo))
        for j in range(m):
            out.append((p[0] + (q[0] - p[0]) * j / m, p[1] + (q[1] - p[1]) * j / m))
    if not fechado:
        out.append(pts[-1])
    return out


def ret_arredondado(w, h, r, seg=3):
    """Retângulo de cantos arredondados (no chão), sentido anti-horário."""
    pts = []
    for cx, cy, a0 in ((w / 2 - r, -h / 2 + r, -90), (w / 2 - r, h / 2 - r, 0),
                       (-w / 2 + r, h / 2 - r, 90), (-w / 2 + r, -h / 2 + r, 180)):
        for j in range(seg + 1):
            t = math.radians(a0 + 90 * j / seg)
            pts.append((cx + r * math.cos(t), cy + r * math.sin(t)))
    return pts


def circulo(r, seg=48, rx=None):
    return [((rx or r) * math.cos(2 * math.pi * i / seg), r * math.sin(2 * math.pi * i / seg)) for i in range(seg)]


class Prisma:
    """Sólido de base `base` (polígono anti-horário no chão) extrudado em z.

    `afina` estreita o topo (0.1 = topo 10% menor), para bolinhos e potes."""

    def __init__(self, v, base, afina=0.0, altura=1.0):
        self.v = v
        self.base = base
        self.afina = afina
        self.altura = altura
        k = len(base)
        self.nrm = [_normal(base[i], base[(i + 1) % k]) for i in range(k)]
        self.vis = [v.rot(*nn)[1] < -0.03 for nn in self.nrm]

    def P(self, i, z):
        x, y = self.base[i % len(self.base)]
        f = 1 - self.afina * z / self.altura
        return self.v.p(x * f, y * f, z)

    def trechos(self):
        """Sequências de vértices cujas arestas estão voltadas para quem olha."""
        k = len(self.base)
        if all(self.vis):
            return [list(range(k + 1))]
        ini = [i for i in range(k) if self.vis[i] and not self.vis[i - 1]]
        out = []
        for i in ini:
            seq = [i]
            j = i
            while self.vis[j % k]:
                j += 1
                seq.append(j)
            out.append(seq)
        return out

    def _z(self, z, i):
        return z[i % len(self.base)] if isinstance(z, (list, tuple)) else z

    def faixa(self, seq, z0, z1):
        cima = [self.P(i, self._z(z1, i)) for i in seq]
        baixo = [self.P(i, self._z(z0, i)) for i in reversed(seq)]
        return cima + baixo

    def luz(self, i):
        nx, ny = self.v.rot(*self.nrm[i % len(self.base)])
        b = max(0.0, nx * LUZ[0] + ny * LUZ[1])
        aro = max(0.0, nx - 0.6) / 0.4
        return b, aro

    def cor_face(self, cor, i, ganho=1.0):
        b, aro = self.luz(i)
        c = tom(cor, (-0.5 + 0.72 * b) * ganho)
        return mix(c, ARO, .3 * aro) if aro else c

    def degrade(self, a, seq, cor, ganho=1.0):
        """Degradê horizontal que sombreia cada face pela sua normal (quinas ficam nítidas)."""
        xs = [self.P(i, 0)[0] for i in seq]
        x0, x1 = min(xs), max(xs)
        span = (x1 - x0) or 1
        k = len(self.base)
        stops = []
        for j, i in enumerate(seq):
            off = (xs[j] - x0) / span
            antes, depois = (i - 1) % k, i % k
            ca = self.cor_face(cor, antes, ganho)
            cd = self.cor_face(cor, depois, ganho)
            if j == 0:
                stops.append((off, cd))
            elif j == len(seq) - 1:
                stops.append((off, ca))
            else:
                na, nd = self.nrm[antes], self.nrm[depois]
                if na[0] * nd[0] + na[1] * nd[1] < 0.9:      # quina: troca de cor seca
                    stops += [(off, ca), (off, cd)]
                else:
                    stops.append((off, mix(ca, cd, .5)))
        # offsets crescentes e no máximo ~10 paradas
        limpo = []
        ult = -1
        for off, c in stops:
            off = max(off, ult)
            limpo.append((round(off, 3), c))
            ult = off
        if len(limpo) > 10:
            passo = len(limpo) / 9
            limpo = [limpo[min(len(limpo) - 1, round(i * passo))] for i in range(10)]
        return a.linear(limpo, x0, 0, x1, 0, user=True)

    def lados(self, a, camadas, ganho=1.0, textura=None):
        """camadas: [(z0, z1, cor)] de baixo para cima. Devolve (svg, contorno de cada trecho)."""
        s = ''
        contornos = []
        for seq in self.trechos():
            for z0, z1, cor in camadas:
                pts = self.faixa(seq, z0, z1)
                tx = f' filter="{a.textura(textura)}"' if textura else ''
                s += f'<path d="{poly(pts)}" fill="{self.degrade(a, seq, cor, ganho)}"{tx}/>'
            contornos.append(self.faixa(seq, camadas[0][0], camadas[-1][1]))
        return s, contornos

    def topo(self, z):
        return [self.P(i, self._z(z, i)) for i in range(len(self.base))]


def elipse_vista(v, x, y, z, r):
    """Elipse de um círculo horizontal de raio r visto pela Vista."""
    cx, cy = v.p(x, y, z)
    return cx, cy, r, r * v.se


# ---------------------------------------------------------------- louça

def prato(a, cx, cy, rx, ry, aba=.72, cor='branco'):
    """Prato raso em 3/4. (cx, cy) = centro da superfície."""
    if cor == 'branco':
        topo = [(0, '#fffdf9'), (.55, '#f2ece2'), (1, '#d5cabb')]
        lado = [(0, '#d9cfc0'), (1, '#8f8475')]
        poco = [(0, '#d6cdbf'), (.3, '#ebe4d8'), (1, '#fbf8f2')]
    else:   # ardósia
        topo = [(0, '#5a5550'), (.6, '#3e3a36'), (1, '#2a2725')]
        lado = [(0, '#2b2826'), (1, '#121110')]
        poco = [(0, '#2a2725'), (.4, '#36322f'), (1, '#45403b')]
    esp = max(3, ry * .13)
    s = f'<ellipse cx="{n(cx)}" cy="{n(cy + esp)}" rx="{n(rx * .985)}" ry="{n(ry * .98)}" fill="{a.linear(lado)}"/>'
    s += f'<ellipse cx="{n(cx)}" cy="{n(cy)}" rx="{n(rx)}" ry="{n(ry)}" fill="{a.radial(topo, cx=.38, cy=.3, r=.8)}"/>'
    # poço (fundo do prato)
    pry = ry * aba
    s += f'<ellipse cx="{n(cx)}" cy="{n(cy + ry * .05)}" rx="{n(rx * aba)}" ry="{n(pry)}" fill="{a.linear(poco)}"/>'
    clip = a.recorte(f'M{n(cx - rx * aba)},{n(cy + ry * .05)} a{n(rx * aba)},{n(pry)} 0 1,0 {n(2 * rx * aba)},0 a{n(rx * aba)},{n(pry)} 0 1,0 {n(-2 * rx * aba)},0Z')
    s += (f'<g clip-path="{clip}"><ellipse cx="{n(cx)}" cy="{n(cy + ry * .05 - pry * .35)}" rx="{n(rx * aba * 1.05)}" ry="{n(pry)}" '
          f'fill="none" stroke="#000" stroke-opacity="{".16" if cor == "branco" else ".3"}" stroke-width="{n(pry * .5)}" filter="{a.desfoque(3)}"/></g>')
    # brilhos da borda: frente-esquerda e fundo
    s += (f'<path d="M{n(cx - rx * .93)},{n(cy + ry * .2)} A{n(rx * .97)},{n(ry * .97)} 0 0,0 {n(cx - rx * .2)},{n(cy + ry * .96)}" '
          f'fill="none" stroke="#fff" stroke-opacity="{".75" if cor == "branco" else ".22"}" stroke-width="1.6" stroke-linecap="round"/>')
    s += (f'<path d="M{n(cx - rx * .6)},{n(cy - ry * .74)} A{n(rx * .95)},{n(ry * .93)} 0 0,1 {n(cx + rx * .1)},{n(cy - ry * .93)}" '
          f'fill="none" stroke="#fff" stroke-opacity="{".5" if cor == "branco" else ".16"}" stroke-width="2" stroke-linecap="round" filter="{a.desfoque(.8)}"/>')
    s += (f'<path d="M{n(cx + rx * .72)},{n(cy - ry * .66)} A{n(rx * .99)},{n(ry * .99)} 0 0,1 {n(cx + rx * .86)},{n(cy + ry * .5)}" '
          f'fill="none" stroke="{ARO}" stroke-opacity=".35" stroke-width="1.4" stroke-linecap="round"/>')
    return s


# ---------------------------------------------------------------- sorvete

SABORES = {
    # luz, cor, sombra, fundo
    'creme': ('#fffcf3', '#f9e9c0', '#e0c48e', '#a98653'),
    'morango': ('#ffe9ee', '#f8acbd', '#dc7790', '#9c3d55'),
    'chocolate': ('#b98560', '#7c4b2c', '#55301b', '#2e170b'),
}


def gota(a, x, y, L, w, cores, brilho=.6):
    """Pingo escorrendo de (x, y) para baixo, com a ponta arredondada."""
    b = w * .62
    d = (f'M{n(x - w / 2)},{n(y)} C{n(x - w / 2)},{n(y + L * .5)} {n(x - b * .55)},{n(y + L - b * 1.6)} {n(x - b)},{n(y + L - b * .9)} '
         f'A{n(b)},{n(b)} 0 1,0 {n(x + b)},{n(y + L - b * .9)} C{n(x + b * .55)},{n(y + L - b * 1.6)} {n(x + w / 2)},{n(y + L * .5)} {n(x + w / 2)},{n(y)}Z')
    s = f'<path d="{d}" fill="{a.linear(cores, 0, 0, 1, 0)}"/>'
    if brilho:
        s += f'<path d="M{n(x - w * .18)},{n(y + 1.5)} V{n(y + L - b * 1.3)}" stroke="#fff" stroke-opacity="{n(brilho)}" stroke-width="{n(max(.8, w * .16))}" stroke-linecap="round"/>'
    return s


def bola_sorvete(a, cx, base, r, sabor='creme', semente=1, pocinha=True, gotas=()):
    """Bola de sorvete apoiada em `base` (y da superfície), com a 'saia' irregular da colher.

    gotas: [(dx, comprimento, largura)] escorrendo a partir da base."""
    claro, cor, sombra_c, fundo_c = SABORES[sabor]
    rr = rng(semente)
    cy = base - r * .72
    fs = [rr.uniform(0, 2 * math.pi) for _ in range(4)]

    def ruido(t, amp):
        return amp * (.5 * math.sin(5 * t + fs[0]) + .3 * math.sin(9 * t + fs[1]) + .2 * math.sin(15 * t + fs[2]))

    s = ''
    if pocinha:   # sorvete derretendo em volta
        poca = bolha(cx + r * .08, base + r * .02, r * 1.16, r * .26, pontos=12, var=.1, semente=semente + 3)
        s += f'<path d="{poca}" fill="{a.radial([(0, claro), (.6, cor), (1, sombra_c)], cx=.42, cy=.35, r=.7)}"/>'
        s += f'<path d="{poca}" fill="none" stroke="{fundo_c}" stroke-opacity=".3" stroke-width=".8"/>'
        s += realce(a, cx - r * .62, base + r * .08, r * .3, r * .04, op=.85, blur=.5)
    for dx, L, w in gotas:
        s += gota(a, cx + dx, base - r * .05, L, w, [(0, cor), (.6, claro), (1, sombra_c)])
    pts = []
    N = 64
    for i in range(N):
        t = 2 * math.pi * i / N
        w = min(1, max(0, (math.sin(t) + .15) / .3))       # 0 no domo, 1 na saia
        f = (1 + ruido(t, .018)) * (1 - w) + (1.07 + ruido(t, .075)) * w
        pts.append((cx + math.cos(t) * r * f, cy + math.sin(t) * r * f * (1 - .38 * w)))
    d = suave(pts, t=.9)
    s += f'<ellipse cx="{n(cx)}" cy="{n(base - 1)}" rx="{n(r * .98)}" ry="{n(r * .16)}" fill="#000" opacity=".32" filter="{a.desfoque(2.5)}"/>'
    s += f'<path d="{d}" fill="{a.radial([(0, claro), (.45, cor), (.84, sombra_c), (1, fundo_c)], cx=.4, cy=.3, r=.75, fx=.36, fy=.24)}"/>'
    s += f'<g clip-path="{a.recorte(d)}">'
    # dobras suaves da colher
    for k in range(4):
        lat = -.4 + k * .24 + rr.uniform(-.05, .05)
        rx = r * math.sqrt(1 - lat * lat)
        ry = r * rr.uniform(.18, .3)
        a0 = rr.uniform(.2, 1.2)
        a1 = a0 + rr.uniform(.6, 1.2)
        ccx, ccy = cx + rr.uniform(-.06, .06) * r, cy + lat * r
        arco = [(ccx + rx * math.cos(a0 + (a1 - a0) * j / 6), ccy + ry * math.sin(a0 + (a1 - a0) * j / 6)) for j in range(7)]
        s += f'<path d="{suave(arco, fechado=False)}" fill="none" stroke="{fundo_c}" stroke-opacity=".22" stroke-width="{n(r * .07)}" stroke-linecap="round" filter="{a.desfoque(r * .03)}"/>'
        s += f'<path d="{suave([(x, y - r * .045) for x, y in arco], fechado=False)}" fill="none" stroke="#fff" stroke-opacity=".3" stroke-width="{n(r * .045)}" stroke-linecap="round" filter="{a.desfoque(r * .02)}"/>'
    # poros
    esc, cla = [], []
    for i in range(int(r * .4)):
        ang = rr.uniform(0, 2 * math.pi)
        rad = r * math.sqrt(rr.uniform(.05, .75))
        px, py = cx + math.cos(ang) * rad, cy + math.sin(ang) * rad * .8
        esc.append((px, py))
        cla.append((px + r * .018, py + r * .022))
    s += pontos(cla, '#fff', r * .035, .6) + pontos(esc, fundo_c, r * .04, .25)
    # sombra embaixo (oclusão)
    s += f'<rect x="{n(cx - r * 1.2)}" y="{n(cy)}" width="{n(r * 2.4)}" height="{n(r * .8)}" fill="{a.linear([(0, "#000", 0), (1, "#3a1d05", .3)])}"/>'
    # saia: sombra irregular logo acima da borda e lascas claras
    sulco = []
    for j in range(17):
        t = math.pi * (.03 + .94 * j / 16)
        f = .97 + ruido(t, .05)
        sulco.append((cx + math.cos(t) * r * f, cy + math.sin(t) * r * .62 * .72 + ruido(t + 1, .05) * r))
    s += f'<path d="{suave(sulco, fechado=False)}" fill="none" stroke="{fundo_c}" stroke-opacity=".42" stroke-width="{n(r * .075)}" stroke-linecap="round" filter="{a.desfoque(r * .03)}"/>'
    lascas = []
    for j in range(7):
        t = math.pi * rr.uniform(.12, .88)
        x0 = cx + math.cos(t) * r * 1.0
        y0 = cy + math.sin(t) * r * .62 * .86 + ruido(t, .06) * r
        lascas.append((x0 - r * .07, y0, x0 + r * .07, y0 + r * .01))
    s += tracos(lascas, claro, r * .05, .3, extra=f' filter="{a.desfoque(r * .02)}"')
    # luz de contorno à direita
    s += (f'<path d="M{n(cx + r * .4)},{n(cy - r * .88)} A{n(r)},{n(r)} 0 0,1 {n(cx + r * .99)},{n(cy + r * .12)}" fill="none" '
          f'stroke="{ARO}" stroke-opacity=".55" stroke-width="{n(r * .07)}" filter="{a.desfoque(r * .03)}"/>')
    s += '</g>'
    s += realce(a, cx - r * .38, cy - r * .5, r * .32, r * .18, rot=-30, op=.75, blur=r * .09)
    s += realce(a, cx - r * .44, cy - r * .55, r * .11, r * .05, rot=-30, op=.9, blur=.6)
    return s


# ---------------------------------------------------------------- brownie

def brownie():
    a = Arte('Ilustração de brownie com sorvete')
    v = Vista(200, 236, yaw=32, elev=27)
    H = 50
    r = rng(41)
    base = subdividir(ret_arredondado(116, 116, 8), 9)
    zt = [H + r.uniform(-1.2, 1.8) for _ in base]
    pr = Prisma(v, base)
    corpo = fundo(a)
    corpo += sombra(a, cy=256, rx=150, ry=9)
    corpo += prato(a, 200, 234, 156, 52)
    corpo += f'<path d="{poly([v.p(x * 1.08 + 8, y * 1.08 - 6, 0) for x, y in base])}" fill="#3a2010" opacity=".4" filter="{a.desfoque(5)}"/>'
    lados, contornos = pr.lados(a, [(0, H - 7, '#472511'), (H - 7, zt, '#5d341a')], ganho=1.0)
    corpo += lados
    for c in contornos:
        corpo += f'<g clip-path="{a.recorte(poly(c))}">'
        corpo += f'<path d="{poly(c)}" fill="#000" opacity=".01" filter="{a.textura("carne")}"/>'
        esc, cla = [], []
        for i in range(90):
            idx = r.randrange(len(base))
            if not pr.vis[idx]:
                continue
            t = r.random()
            p0, p1 = pr.P(idx, 0), pr.P(idx + 1, 0)
            z = r.uniform(3, H - 10)
            x = p0[0] + (p1[0] - p0[0]) * t
            y = p0[1] + (p1[1] - p0[1]) * t - z * v.ce
            esc.append((x, y))
            if i % 2:
                cla.append((x + .6, y + .9))
        corpo += pontos(cla, '#b07850', 1.2, .6) + pontos(esc, '#170802', 2.4, .75)
        y0, y1 = v.p(0, 0, H)[1], v.p(60, -60, 0)[1]
        corpo += f'<rect x="0" y="{n(y0 - 40)}" width="400" height="200" fill="{a.linear([(0, "#000", 0), (.6, "#000", 0), (1, "#000", .45)], 0, y0, 0, y1, user=True)}"/>'
        corpo += '</g>'
    # topo: casquinha craquelada e brilhante
    topo = pr.topo(zt)
    dt = poly(topo)
    corpo += f'<path d="{dt}" fill="{a.radial([(0, "#80502f"), (.5, "#5f361b"), (1, "#3e200d")], cx=.32, cy=.3, r=.85)}" filter="{a.textura("carne")}"/>'
    corpo += f'<g clip-path="{a.recorte(dt)}">'
    for i in range(11):
        x, y = r.uniform(-52, 52), r.uniform(-52, 52)
        pts = [v.p(x, y, H + 1)]
        ang = r.uniform(0, math.pi * 2)
        for k in range(4):
            ang += r.uniform(-.8, .8)
            x += math.cos(ang) * r.uniform(7, 13)
            y += math.sin(ang) * r.uniform(7, 13)
            pts.append(v.p(x, y, H + 1))
        corpo += f'<path d="{linha([(x, y + 1) for x, y in pts])}" fill="none" stroke="#c99470" stroke-opacity=".5" stroke-width="1"/>'
        corpo += f'<path d="{linha(pts)}" fill="none" stroke="#1b0a03" stroke-opacity=".85" stroke-width="1.3" stroke-linejoin="round"/>'
    corpo += realce(a, *v.p(-30, 20, H), 30, 7, rot=-14, op=.3, blur=4)
    corpo += realce(a, *v.p(-36, 22, H), 12, 2, rot=-14, op=.45, blur=1)
    corpo += '</g>'
    # aresta de luz nas bordas do topo voltadas para a frente
    for seq in pr.trechos():
        corpo += f'<path d="{linha([pr.P(i, zt[i % len(base)]) for i in seq])}" fill="none" stroke="#d29a70" stroke-opacity=".55" stroke-width="1.2" stroke-linejoin="round"/>'
    # migalhas
    for i, (x, y) in enumerate(((-96, -30), (78, -84), (-80, 50), (102, 6), (-30, -92))):
        px, py = v.p(x, y, 0)
        corpo += f'<path d="{bolha(px, py, 3.6 - i * .4, 2.6, pontos=6, var=.3, semente=i + 7)}" fill="#3b1d0c"/>'
        corpo += f'<circle cx="{n(px - .9)}" cy="{n(py - .9)}" r=".8" fill="#a06a48"/>'
    # sorvete derretendo sobre o brownie e escorrendo pelas faces
    bx, by = v.p(6, 6, H)
    ex, ey = v.p(-58, -58, H)       # quina da frente fica entre as duas faces
    derr = suave([(bx - 46, by - 2), (bx - 40, by + 9), (bx - 20, by + 16), (bx - 6, by + 27), (bx + 8, by + 21),
                  (bx + 30, by + 16), (bx + 48, by + 5), (bx + 40, by - 7), (bx, by - 11), (bx - 30, by - 9)], t=.9)
    corpo += f'<path d="{derr}" fill="{a.linear([(0, "#fff6dc"), (.7, "#f3dfae"), (1, "#dcc08a")])}"/>'
    corpo += realce(a, bx - 26, by + 5, 12, 2, rot=12, op=.8, blur=.6)
    for dx, dy, L, w in ((-28, 11, 20, 7), (-9, 20, 36, 9), (17, 15, 18, 7), (34, 8, 12, 6)):
        corpo += gota(a, bx + dx, by + dy, L, w, [(0, '#e6cc96'), (.45, '#fff4d6'), (1, '#dcc08a')], brilho=.75)
    corpo += bola_sorvete(a, bx, by + 2, 42, 'creme', semente=3, pocinha=False)
    return a.svg(corpo)


# ---------------------------------------------------------------- petit gâteau

LAVA = [(0, '#5e2a10'), (.45, '#3a1607'), (1, '#1d0902')]


def petit_gateau():
    a = Arte('Ilustração de petit gâteau')
    corpo = fundo(a) + sombra(a, cy=256, rx=150, ry=9)
    corpo += prato(a, 200, 234, 156, 52)
    v = Vista(180, 240, yaw=0, elev=24)
    R, H = 52, 62
    pr = Prisma(v, circulo(R, 60), afina=.1, altura=H)
    corpo += f'<ellipse cx="190" cy="242" rx="62" ry="17" fill="#2a1408" opacity=".5" filter="{a.desfoque(4)}"/>'
    # sorvete atrás, à direita
    corpo += bola_sorvete(a, 276, 222, 34, 'creme', semente=8)
    # poça de chocolate no prato
    poca = suave([(146, 248), (170, 255), (204, 256), (236, 258), (264, 262), (290, 258), (296, 250), (276, 244), (244, 242), (204, 240), (160, 241)], t=.9)
    corpo += f'<path d="{poca}" fill="{a.linear([(0, "#5a2810"), (.5, "#341405"), (1, "#1a0803")])}"/>'
    corpo += f'<path d="{poca}" fill="none" stroke="#000" stroke-opacity=".3"/>'
    corpo += f'<path d="M226,248 C246,247 266,249 282,252" fill="none" stroke="#fff" stroke-opacity=".55" stroke-width="2.4" stroke-linecap="round" filter="{a.desfoque(.8)}"/>'
    corpo += realce(a, 272, 256, 8, 1.3, op=.8, blur=.4)
    lados, contornos = pr.lados(a, [(0, H, '#552a13')], ganho=1.0, textura='carne')
    corpo += lados
    c = contornos[0]
    corpo += f'<g clip-path="{a.recorte(poly(c))}">'
    corpo += f'<rect x="120" y="{n(240 - H)}" width="130" height="{n(H + 20)}" fill="{a.linear([(0, "#000", 0), (.65, "#000", 0), (1, "#000", .45)])}"/>'
    corpo += '</g>'
    # topo em domo, craquelado
    tx, ty = v.p(0, 0, H)
    rt = R * .9
    ryt = rt * v.se
    domo = f'M{n(tx - rt)},{n(ty)} A{n(rt)},{n(ryt)} 0 0,0 {n(tx + rt)},{n(ty)} C{n(tx + rt * .92)},{n(ty - ryt - 12)} {n(tx - rt * .92)},{n(ty - ryt - 12)} {n(tx - rt)},{n(ty)}Z'
    corpo += f'<path d="{domo}" fill="{a.radial([(0, "#87502f"), (.55, "#5c2d13"), (1, "#3a1a09")], cx=.36, cy=.3, r=.85)}" filter="{a.textura("carne")}"/>'
    r = rng(12)
    corpo += f'<g clip-path="{a.recorte(domo)}">'
    for i in range(7):
        x0 = tx + r.uniform(-rt * .75, rt * .45)
        y0 = ty - r.uniform(-ryt * .3, ryt + 5)
        rach = f'M{n(x0)},{n(y0)} l{n(r.uniform(5, 10))},{n(r.uniform(-3, 3))} l{n(r.uniform(4, 9))},{n(r.uniform(-3, 3))}'
        corpo += f'<path d="{rach}" fill="none" stroke="#c48a62" stroke-opacity=".45" stroke-width="1" transform="translate(0,1)"/>'
        corpo += f'<path d="{rach}" fill="none" stroke="#1d0b03" stroke-width="1.2" stroke-opacity=".85"/>'
    corpo += realce(a, tx - 16, ty - 9, 18, 5, rot=-8, op=.28, blur=3)
    corpo += '</g>'
    corpo += f'<path d="M{n(tx - rt)},{n(ty)} A{n(rt)},{n(ryt)} 0 0,0 {n(tx + rt)},{n(ty)}" fill="none" stroke="#a8714c" stroke-opacity=".45" stroke-width="1.2"/>'
    # corte da colher: abertura na frente-direita, com o recheio saindo
    ox, oy = tx + 8, ty + ryt * .5
    abertura = suave([(ox - 24, oy - 2), (ox - 14, oy - 10), (ox + 4, oy - 12), (ox + 22, oy - 7), (ox + 28, oy + 6),
                      (ox + 24, oy + 24), (ox + 6, oy + 32), (ox - 14, oy + 26), (ox - 26, oy + 10)], t=.9)
    corpo += f'<path d="{abertura}" fill="#8a5434" filter="{a.textura("carne")}" transform="translate({n(ox + 1)},{n(oy + 2)}) scale(1.08) translate({n(-ox)},{n(-oy)})"/>'
    corpo += f'<path d="{abertura}" fill="{a.radial([(0, "#4f220d"), (.7, "#26100a"), (1, "#120501")], cx=.45, cy=.35)}"/>'
    rio = suave([(ox - 18, oy + 4), (ox - 21, oy + 16), (ox - 24, oy + 30), (ox - 20, oy + 42), (ox - 26, oy + 54),
                 (ox - 14, oy + 64), (ox + 12, oy + 66), (ox + 40, oy + 64), (ox + 46, oy + 56), (ox + 32, oy + 48),
                 (ox + 28, oy + 34), (ox + 26, oy + 18), (ox + 20, oy + 4), (ox + 2, oy + 1)], t=.85)
    corpo += f'<path d="{rio}" fill="{a.linear([(0, "#7a3c1a"), (.3, "#4c1d0a"), (.75, "#2a0f04"), (1, "#170601")], 0, 0, 1, .3)}"/>'
    corpo += f'<path d="{rio}" fill="none" stroke="#000" stroke-opacity=".35"/>'
    # brilhos do chocolate derretido
    corpo += f'<path d="M{n(ox - 14)},{n(oy + 10)} C{n(ox - 16)},{n(oy + 18)} {n(ox - 18)},{n(oy + 26)} {n(ox - 16)},{n(oy + 34)}" fill="none" stroke="#fff" stroke-opacity=".75" stroke-width="2.6" stroke-linecap="round" filter="{a.desfoque(.5)}"/>'
    corpo += f'<path d="M{n(ox - 17)},{n(oy + 42)} C{n(ox - 19)},{n(oy + 48)} {n(ox - 16)},{n(oy + 54)} {n(ox - 8)},{n(oy + 58)}" fill="none" stroke="#fff" stroke-opacity=".5" stroke-width="2" stroke-linecap="round" filter="{a.desfoque(.5)}"/>'
    corpo += f'<path d="M{n(ox - 4)},{n(oy + 14)} C{n(ox - 6)},{n(oy + 26)} {n(ox - 2)},{n(oy + 40)} {n(ox + 4)},{n(oy + 50)}" fill="none" stroke="#a5653c" stroke-opacity=".35" stroke-width="5" stroke-linecap="round" filter="{a.desfoque(2)}"/>'
    corpo += f'<path d="M{n(ox + 20)},{n(oy + 14)} C{n(ox + 22)},{n(oy + 24)} {n(ox + 20)},{n(oy + 34)} {n(ox + 26)},{n(oy + 44)}" fill="none" stroke="{ARO}" stroke-opacity=".45" stroke-width="1.6" stroke-linecap="round"/>'
    corpo += realce(a, ox - 8, oy - 1, 10, 2.8, rot=-10, op=.6, blur=1)
    corpo += realce(a, ox + 2, oy + 9, 3, 1.4, op=.7, blur=.4)
    corpo += realce(a, ox + 12, oy + 58, 14, 2, op=.45, blur=1)
    return a.svg(corpo)


# ---------------------------------------------------------------- pudim

def veu(a, pr, seq, z, rr, cores, queda=(3, 8), pingos=2):
    """Calda escorrendo pela beirada de cima de uma face (lençol com pingos)."""
    topo = [pr.P(i, z) for i in seq]
    # amostra fina ao longo da aresta
    am = []
    for j in range(len(topo) - 1):
        (x0, y0), (x1, y1) = topo[j], topo[j + 1]
        m = max(1, int(abs(x1 - x0) / 3))
        for k in range(m):
            am.append((x0 + (x1 - x0) * k / m, y0 + (y1 - y0) * k / m))
    am.append(topo[-1])
    if len(am) < 4:
        return ''
    fase = rr.uniform(0, 6)
    gotas = [rr.uniform(.15, .85) for _ in range(pingos)]
    comp = [rr.uniform(10, 22) for _ in range(pingos)]
    baixo = []
    for j, (x, y) in enumerate(am):
        u = j / (len(am) - 1)
        q = queda[0] + (queda[1] - queda[0]) * (.5 + .5 * math.sin(u * 9 + fase))
        for g, c in zip(gotas, comp):
            q += c * math.exp(-((u - g) / .035) ** 2)
        baixo.append((x, y + q))
    d = linha(am) + ' ' + suave(list(reversed(baixo)), fechado=False).replace('M', 'L', 1) + 'Z'
    s = f'<path d="{d}" fill="{a.linear(cores)}" opacity=".94"/>'
    s += f'<path d="{linha(am)}" fill="none" stroke="#ffd089" stroke-opacity=".7" stroke-width="1.3"/>'
    for g, c in zip(gotas, comp):
        x, y = am[int(g * (len(am) - 1))]
        s += f'<path d="M{n(x - 1.2)},{n(y + 3)} V{n(y + c - 1)}" stroke="#ffe0a8" stroke-opacity=".7" stroke-width="1.2" stroke-linecap="round"/>'
    return s


def pudim():
    a = Arte('Ilustração de pudim')
    corpo = fundo(a) + sombra(a, cy=256, rx=152, ry=9)
    corpo += prato(a, 200, 234, 158, 53)
    # fatia de pudim de forma de anel: arco de fora (molde), arco de dentro (furo) e dois cortes retos
    ri, ro, span, H = 62, 168, 34, 84
    fora = [(ro * math.cos(math.radians(span * i / 12)), ro * math.sin(math.radians(span * i / 12))) for i in range(13)]
    furo = [(ri * math.cos(math.radians(span * (1 - i / 4))), ri * math.sin(math.radians(span * (1 - i / 4)))) for i in range(5)]
    mx = sum(p[0] for p in fora + furo) / 18
    my = sum(p[1] for p in fora + furo) / 18
    fora = [(x - mx, y - my) for x, y in fora]
    furo = [(x - mx, y - my) for x, y in furo]
    lado = subdividir([fora[-1], furo[0]], 12, fechado=False)[1:-1]
    corte_pts = subdividir([furo[-1], fora[0]], 12, fechado=False)[1:-1]
    base = fora + lado + furo + corte_pts
    tipos = ['molde'] * 12 + ['lado'] * (len(lado) + 1) + ['furo'] * 4 + ['corte'] * (len(corte_pts) + 1)
    v = Vista(216, 240, yaw=-26, elev=24)
    pr = Prisma(v, base)
    r = rng(9)
    # poça de caramelo, brilhante e translúcida na borda
    pcx, pcy = v.p(14, -10, 0)
    poca = bolha(pcx - 4, pcy + 6, 116, 32, pontos=13, var=.12, semente=11)
    corpo += f'<path d="{poca}" fill="#c8761c" opacity=".55" transform="translate(0,1.5)"/>'
    corpo += f'<path d="{poca}" fill="{a.radial([(0, "#8a3a06"), (.55, "#6e2a02"), (.85, "#9a4a0c"), (1, "#d48a30")], cx=.45, cy=.4, r=.62)}"/>'
    corpo += f'<path d="{poca}" fill="none" stroke="#ffcf8a" stroke-opacity=".35" stroke-width="1"/>'
    corpo += realce(a, pcx - 74, pcy + 18, 26, 2.6, rot=8, op=.7, blur=1)
    corpo += realce(a, pcx - 82, pcy + 17, 9, 1.2, rot=8, op=.95, blur=.3)
    corpo += realce(a, pcx + 70, pcy + 24, 16, 1.8, rot=-6, op=.6, blur=.6)
    corpo += realce(a, pcx + 6, pcy + 31, 34, 1.6, op=.25, blur=1.5)
    # sombra de contato da fatia
    corpo += f'<path d="{poly([v.p(x * 1.05 + 4, y * 1.05 - 4, 0) for x, y in base])}" fill="#2a0e00" opacity=".55" filter="{a.desfoque(3.5)}"/>'
    # paredes visíveis, separadas por tipo (corte = creme; molde e furo = dourados de caramelo)
    y_top, y_bot = v.p(0, 0, H)[1], v.p(0, -70, 0)[1]
    k = len(base)
    paredes = []
    for seq in pr.trechos():
        run = [seq[0]]
        for i in seq[1:]:
            if tipos[(i - 1) % k] == tipos[run[0] % k]:
                run.append(i)
            else:
                paredes.append((tipos[run[0] % k], run))
                run = [i - 1, i]
        if len(run) > 1:
            paredes.append((tipos[run[0] % k], run))
    vistos = {}
    for tipo, seq in paredes:
        vistos[tipo] = seq
        cor, ganho = ('#fad57c', .38) if tipo == 'corte' else ('#e6a446', .5)
        pts_f = pr.faixa(seq, 0, H)
        corpo += f'<path d="{poly(pts_f)}" fill="{pr.degrade(a, seq, cor, ganho)}"/>'
        corpo += f'<g clip-path="{a.recorte(poly(pts_f))}">'
        if tipo == 'corte':
            corpo += f'<rect x="0" y="{n(y_top - 40)}" width="400" height="180" fill="{a.linear([(0, "#7a3204", .75), (.08, "#c06c18", .4), (.17, "#f0b860", .1), (.26, "#000", 0), (.72, "#000", 0), (1, "#5a2a00", .3)], 0, y_top, 0, y_bot, user=True)}"/>'
            fa, fb = pr.P(seq[0], 0), pr.P(seq[-1], 0)
            gx = fa[0] + (fb[0] - fa[0]) * .3
            gy = fa[1] + (fb[1] - fa[1]) * .3
            corpo += realce(a, gx, gy - H * v.ce * .45, 13, H * v.ce * .34, op=.32, blur=7)
            corpo += realce(a, gx - 4, gy - H * v.ce * .5, 1.2, H * v.ce * .26, op=.4, blur=.6)
            furos = []
            for i in range(9):
                t = r.uniform(.08, .92)
                z = H - 13 - r.uniform(0, 14)
                furos.append((fa[0] + (fb[0] - fa[0]) * t, fa[1] + (fb[1] - fa[1]) * t - z * v.ce))
            corpo += pontos([(x + .4, y + .7) for x, y in furos], '#fff8e4', 1.3, .9) + pontos(furos, '#d4952e', 1.2, .7)
        else:
            corpo += f'<rect x="0" y="{n(y_top - 40)}" width="400" height="180" fill="{a.linear([(0, "#5a1e00", .65), (.12, "#a0480a", .3), (.28, "#000", 0), (.75, "#000", 0), (1, "#4a2000", .3)], 0, y_top, 0, y_bot, user=True)}"/>'
            if tipo == 'molde':
                xs = [pr.P(i, H) for i in seq]
                for u, w, op in ((.3, 4, .3), (.62, 1.6, .5)):
                    xa, ya = xs[int(u * (len(xs) - 1))]
                    corpo += realce(a, xa, ya + H * v.ce * .55, w, H * v.ce * .36, op=op, blur=w * .5, cor='#fff3d8')
        corpo += '</g>'
    # topo de caramelo: âmbar escuro e espelhado
    topo = poly(pr.topo(H))
    corpo += f'<path d="{topo}" fill="{a.radial([(0, "#e8a040"), (.35, "#b05a10"), (.75, "#7a3004"), (1, "#561c00")], cx=.4, cy=.55, r=.72)}"/>'
    corpo += f'<g clip-path="{a.recorte(topo)}"><path d="{topo}" fill="none" stroke="#3a1000" stroke-opacity=".5" stroke-width="5" filter="{a.desfoque(2.5)}"/></g>'
    car = [(0, '#8a3c06'), (.3, '#c8761c'), (.7, '#a85210'), (1, '#6a2804')]
    if 'corte' in vistos:
        corpo += veu(a, pr, vistos['corte'], H, r, car, queda=(4, 10), pingos=3)
    if 'molde' in vistos:
        corpo += veu(a, pr, vistos['molde'], H, r, car, queda=(5, 12), pingos=2)
    cx_, cy_ = v.p(-18, 6, H)
    corpo += realce(a, cx_, cy_, 36, 6, rot=-6, op=.45, blur=3)
    corpo += realce(a, cx_ - 12, cy_ - 1, 20, 2.2, rot=-6, op=.95, blur=.5)
    corpo += realce(a, cx_ + 34, cy_ + 5, 6, 1.5, rot=-6, op=.8, blur=.3)
    if 'molde' in vistos:
        corpo += f'<path d="{linha([pr.P(i, H) for i in vistos["molde"]])}" fill="none" stroke="{ARO}" stroke-opacity=".6" stroke-width="1.4"/>'
    return a.svg(corpo)


# ---------------------------------------------------------------- churros

def churro(a, x, y, L, t, rot, semente=1, ponta=None):
    """Mini churro estriado com açúcar e canela. (x, y) = ponta esquerda; `ponta` = trecho final coberto de doce de leite."""
    r = rng(semente)
    ond = [r.uniform(-.04, .04) * t for _ in range(6)]
    cima = [(t * .45 + (L - t * .9) * j / 5, -t / 2 + ond[j]) for j in range(6)]
    baixo = [(L - t * .45 - (L - t * .9) * j / 5, t / 2 - ond[5 - j] * .5) for j in range(6)]
    d = (suave(cima, fechado=False) + f' C{n(L - t * .1)},{n(-t / 2)} {n(L)},{n(-t * .22)} {n(L)},0 C{n(L)},{n(t * .22)} {n(L - t * .1)},{n(t / 2)} {n(L - t * .45)},{n(t / 2)}'
         + suave(baixo, fechado=False).replace('M', ' L', 1) + f' C{n(t * .1)},{n(t / 2)} 0,{n(t * .25)} 0,0 C0,{n(-t * .25)} {n(t * .1)},{n(-t / 2)} {n(t * .45)},{n(-t / 2 + ond[0])}Z')
    s = f'<g transform="translate({n(x)},{n(y)}) rotate({n(rot)})">'
    s += f'<path d="{d}" fill="#7a3a0e"/>'
    s += f'<g clip-path="{a.recorte(d)}">'
    # estrias: cada crista é um "tubinho" com luz em cima e sombra embaixo
    k = 4
    h = t / k
    s += f'<g filter="{a.textura("frito")}">'
    for j in range(k):
        y0 = -t / 2 + h * j
        q = j / (k - 1)
        luz = mix('#ffe0a0', '#d98f40', q)
        meio = mix('#f2ae55', '#b4661f', q)
        esc = mix('#c06d24', '#5e2a08', q)
        s += (f'<rect x="{n(-h * .3)}" y="{n(y0 + h * .05)}" width="{n(L + h * .6)}" height="{n(h * .9)}" rx="{n(h * .45)}" '
              f'fill="{a.linear([(0, luz), (.5, meio), (1, esc)])}"/>')
    s += '</g>'
    # açúcar (cristais) e canela (pó)
    acucar, canela = [], []
    for i in range(int(L * .9)):
        px = r.uniform(t * .15, L - t * .15)
        py = -t / 2 + t * (r.random() ** 1.3)
        (acucar if r.random() < .55 else canela).append((px, py))
    s += pontos(canela, '#5a2406', t * .05, .4) + pontos(acucar, '#fffdf6', t * .045, .85)
    s += f'<rect x="0" y="{n(t * .05)}" width="{n(L)}" height="{n(t * .45)}" fill="{a.linear([(0, "#000", 0), (1, "#200a00", .28)])}"/>'
    s += '</g>'
    if ponta:
        x0 = L - ponta
        borda = suave([(x0, -t / 2 - 2), (x0 + t * .22, -t * .15), (x0 - t * .06, t * .2), (x0 + t * .16, t / 2 + 2),
                       (L + 3, t / 2 + 2), (L + 3, -t / 2 - 2)], t=.6)
        s += f'<g clip-path="{a.recorte(d)}"><path d="{borda}" fill="#000" opacity=".35" transform="translate(-2.5,0)" filter="{a.desfoque(1.2)}"/>'
        s += f'<path d="{borda}" fill="{a.linear([(0, "#dba05a"), (.3, "#b56e2c"), (.75, "#7c3c0e"), (1, "#552403")])}"/></g>'
        s += gota(a, x0 + ponta * .38, t * .4, t * .62, t * .34, [(0, '#8a4512'), (.45, '#c88440'), (1, '#5a2804')], brilho=.6)
        s += f'<path d="M{n(x0 + t * .3)},{n(-t * .3)} H{n(L - t * .35)}" stroke="#fff3dc" stroke-opacity=".85" stroke-width="{n(t * .08)}" stroke-linecap="round"/>'
    s += realce(a, L * .45, -t * .32, L * .32, t * .07, op=.5, blur=1)
    s += '</g>'
    return s


def ramequim(a, cx, cy, R, H, recheio=None):
    """Potinho de cerâmica estriado. (cx, cy) = centro da base no chão. Devolve (svg, (x, y, rx, ry) da superfície)."""
    v = Vista(cx, cy, elev=26)
    pr = Prisma(v, circulo(R, 48), afina=-.06, altura=H)
    s = f'<ellipse cx="{n(cx + 4)}" cy="{n(cy + 2)}" rx="{n(R * 1.1)}" ry="{n(R * .36)}" fill="#000" opacity=".45" filter="{a.desfoque(4)}"/>'
    lados, cont = pr.lados(a, [(0, H, '#f3ede3')], ganho=.7)
    s += lados
    s += f'<g clip-path="{a.recorte(poly(cont[0]))}">'
    estrias = []
    for i in range(0, 48, 2):
        if pr.vis[i] or pr.vis[i - 1]:
            x0, y0 = pr.P(i, 0)
            x1, y1 = pr.P(i, H)
            estrias.append((x0, y0, x1, y1))
    s += tracos(estrias, '#8a7d6b', 1.2, .4)
    s += tracos([(x0 - 1.3, y0, x1 - 1.3, y1) for x0, y0, x1, y1 in estrias], '#fff', .9, .55)
    s += '</g>'
    ex, ey = v.p(0, 0, H)
    Rt = R * 1.06
    ry = Rt * v.se
    s += f'<ellipse cx="{n(ex)}" cy="{n(ey)}" rx="{n(Rt)}" ry="{n(ry)}" fill="{a.linear([(0, "#ddd3c5"), (1, "#fffdf8")])}"/>'
    s += f'<ellipse cx="{n(ex)}" cy="{n(ey + .6)}" rx="{n(Rt - 3)}" ry="{n(ry - 1.6)}" fill="{a.linear([(0, "#9a8f80"), (1, "#e7dfd2")])}"/>'
    sup = (ex, ey + 2.5, Rt - 3.6, ry - 2.6)
    if recheio:
        s += f'<ellipse cx="{n(sup[0])}" cy="{n(sup[1])}" rx="{n(sup[2])}" ry="{n(sup[3])}" fill="{a.radial(recheio, cx=.4, cy=.35, r=.75)}"/>'
    s += f'<path d="M{n(ex - Rt + .5)},{n(ey + 1)} A{n(Rt)},{n(ry)} 0 0,0 {n(ex + Rt - .5)},{n(ey + 1)}" fill="none" stroke="#fff" stroke-opacity=".8" stroke-width="1.2"/>'
    return s, sup


def churros():
    a = Arte('Ilustração de churros')
    corpo = fundo(a) + sombra(a, cy=256, rx=156, ry=9)
    # tábua de ardósia
    v = Vista(200, 244, yaw=-4, elev=26)
    tab = Prisma(v, subdividir(ret_arredondado(306, 124, 10, seg=4), 40))
    lados, _ = tab.lados(a, [(0, 8, '#34302d')], ganho=.8)
    corpo += lados
    top = poly(tab.topo(8))
    corpo += f'<path d="{top}" fill="{a.radial([(0, "#5c5651"), (.6, "#403c38"), (1, "#2b2826")], cx=.4, cy=.3, r=.8)}" filter="{a.textura("fino")}"/>'
    corpo += f'<path d="{linha([tab.P(i, 8) for i in tab.trechos()[0]])}" fill="none" stroke="#9a938c" stroke-opacity=".6" stroke-width="1.2"/>'
    T, L = 25, 150

    def sombra_churro(x, y, L, rot, dy=9, op=.55):
        rad = math.radians(rot)
        mx, my = x + math.cos(rad) * L / 2, y + math.sin(rad) * L / 2 + dy
        return f'<ellipse cx="{n(mx + 4)}" cy="{n(my)}" rx="{n(L / 2)}" ry="6" fill="#000" opacity="{n(op)}" filter="{a.desfoque(3)}" transform="rotate({n(rot)} {n(mx)} {n(my)})"/>'
    # dois churros embaixo, um cruzado por cima
    corpo += sombra_churro(58, 214, L, -4) + sombra_churro(70, 238, L, -2)
    corpo += churro(a, 58, 214, L, T, -4, semente=3)
    corpo += churro(a, 70, 238, L, T, -2, semente=5)
    corpo += sombra_churro(84, 196, L - 6, 12, dy=12, op=.5)
    corpo += churro(a, 84, 196, L - 6, T, 12, semente=7)
    # pote de doce de leite (à direita)
    doce = [(0, '#d69448'), (.45, '#ab5f1d'), (1, '#6c3008')]
    pote, (sx, sy, srx, sry) = ramequim(a, 304, 244, 40, 34, recheio=doce)
    corpo += pote
    corpo += f'<path d="M{n(sx - srx * .65)},{n(sy - sry * .05)} C{n(sx - srx * .35)},{n(sy - sry * .75)} {n(sx + srx * .35)},{n(sy - sry * .7)} {n(sx + srx * .55)},{n(sy - sry * .05)}" fill="none" stroke="#f0bb76" stroke-opacity=".7" stroke-width="2" stroke-linecap="round"/>'
    corpo += realce(a, sx - srx * .4, sy - sry * .3, srx * .28, sry * .18, op=.85, blur=.8)
    # churro mergulhado no doce de leite
    ang = 24
    L2 = 128
    x0 = sx + 2 - math.cos(math.radians(ang)) * (L2 - 4)
    y0 = sy + 1 - math.sin(math.radians(ang)) * (L2 - 4)
    corpo += churro(a, x0, y0, L2, T, ang, semente=11, ponta=40)
    corpo += f'<path d="{bolha(sx + 4, sy + 1.5, 15, 5.5, pontos=9, var=.18, semente=4)}" fill="{a.linear(doce)}"/>'
    corpo += realce(a, sx, sy - 1, 7, 1.5, op=.75, blur=.5)
    return a.svg(corpo)


# ---------------------------------------------------------------- sorvete na tigela

CHOCO = [(0, '#6a3418'), (.35, '#45190a'), (1, '#1c0802')]


def calda_bola(a, cx, base, r, gotas, cores=CHOCO, semente=1, a0=208, a1=328, nivel=.3):
    """Calda grossa sobre o topo de uma bola de sorvete, com pingos [(fx, comprimento)] (frações de r)."""
    cy = base - r * .72
    rr = rng(semente)
    t0, t1 = math.radians(a0), math.radians(a1)
    p0 = (cx + r * 1.02 * math.cos(t0), cy + r * 1.02 * math.sin(t0))
    p1 = (cx + r * 1.02 * math.cos(t1), cy + r * 1.02 * math.sin(t1))
    d = f'M{n(p0[0])},{n(p0[1])} A{n(r * 1.02)},{n(r * 1.02)} 0 0,1 {n(p1[0])},{n(p1[1])}'
    yb = cy - r * nivel
    xatual = p1[0]
    for fx, fl, fw in sorted(gotas, key=lambda g: -g[0]):
        w = r * fw
        b = w * .62
        xd = cx + fx * r
        L = fl * r
        yy = yb + rr.uniform(-.04, .06) * r
        d += f' Q{n((xatual + xd + w / 2) / 2)},{n(yy + r * rr.uniform(-.08, .1))} {n(xd + w / 2)},{n(yy)}'
        d += (f' C{n(xd + w / 2)},{n(yy + L * .5)} {n(xd + b * .55)},{n(yy + L - b * 1.6)} {n(xd + b)},{n(yy + L - b * .9)}'
              f' A{n(b)},{n(b)} 0 1,1 {n(xd - b)},{n(yy + L - b * .9)}'
              f' C{n(xd - b * .55)},{n(yy + L - b * 1.6)} {n(xd - w / 2)},{n(yy + L * .5)} {n(xd - w / 2)},{n(yy)}')
        xatual = xd - w / 2
    d += f' Q{n((xatual + p0[0]) / 2)},{n(yb + r * .1)} {n(p0[0])},{n(p0[1])}Z'
    s = f'<path d="{d}" fill="#000" opacity=".25" transform="translate(1.5,3)" filter="{a.desfoque(2)}"/>'
    s += f'<path d="{d}" fill="{a.linear(cores, 0, 0, .6, 1)}"/>'
    s += f'<path d="{d}" fill="none" stroke="#000" stroke-opacity=".3" stroke-width=".8"/>'
    s += f'<path d="M{n(cx - r * .74)},{n(cy - r * .4)} A{n(r * .84)},{n(r * .84)} 0 0,1 {n(cx - r * .05)},{n(cy - r * .84)}" fill="none" stroke="#fff" stroke-opacity=".3" stroke-width="{n(r * .16)}" stroke-linecap="round" filter="{a.desfoque(r * .05)}"/>'
    s += f'<path d="M{n(cx - r * .76)},{n(cy - r * .42)} A{n(r * .86)},{n(r * .86)} 0 0,1 {n(cx - r * .2)},{n(cy - r * .84)}" fill="none" stroke="#fff" stroke-opacity=".75" stroke-width="{n(r * .045)}" stroke-linecap="round"/>'
    s += realce(a, cx - r * .12, cy - r * .55, r * .12, r * .05, op=.8, blur=.5)
    for fx, fl, fw in gotas:
        xd = cx + fx * r
        w = r * fw
        s += f'<path d="M{n(xd - w * .18)},{n(yb + 4)} V{n(yb + fl * r - w * .9)}" stroke="#fff" stroke-opacity=".5" stroke-width="{n(max(1, w * .16))}" stroke-linecap="round"/>'
        s += f'<circle cx="{n(xd - w * .2)}" cy="{n(yb + fl * r - w * .55)}" r="{n(w * .12)}" fill="#fff" opacity=".7"/>'
    s += (f'<path d="M{n(cx + r * .55)},{n(cy - r * .78)} A{n(r)},{n(r)} 0 0,1 {n(cx + r * .9)},{n(cy - r * .3)}" fill="none" '
          f'stroke="{ARO}" stroke-opacity=".5" stroke-width="{n(r * .05)}"/>')
    return s


def sorvete():
    a = Arte('Ilustração de sorvete')
    corpo = fundo(a) + sombra(a, cy=254, rx=104, ry=9)
    se = math.sin(math.radians(17))
    ce = math.cos(math.radians(17))
    cx, cy = 200, 252
    perfil = [(0, 46), (4, 48), (9, 42), (14, 44), (22, 62), (34, 80), (48, 94), (62, 102), (72, 105)]
    zr, R = perfil[-1]
    ry = R * se
    rim_y = cy - zr * ce
    esq = [(cx - rad, cy - z * ce) for z, rad in perfil]
    dir_ = [(cx + rad, cy - z * ce) for z, rad in perfil]
    parede = (suave(list(reversed(esq)), fechado=False)
              + f' A{n(perfil[0][1])},{n(perfil[0][1] * se)} 0 0,0 {n(dir_[0][0])},{n(dir_[0][1])}'
              + suave(dir_, fechado=False).replace('M', ' L', 1)
              + f' A{n(R)},{n(ry)} 0 0,1 {n(esq[-1][0])},{n(esq[-1][1])}Z')
    # boca da tigela (interior)
    corpo += f'<ellipse cx="{n(cx)}" cy="{n(rim_y)}" rx="{n(R)}" ry="{n(ry)}" fill="{a.linear([(0, "#c8bba9"), (.5, "#efe8dc"), (1, "#fffdf8")])}"/>'
    corpo += f'<ellipse cx="{n(cx)}" cy="{n(rim_y + 4)}" rx="{n(R - 12)}" ry="{n(ry - 6)}" fill="#6a4a2a" opacity=".45" filter="{a.desfoque(4)}"/>'
    # bolas: morango atrás (dir.), creme na frente (esq.)
    b1, b2 = rim_y + 16, rim_y + 24
    corpo += bola_sorvete(a, 238, b1, 50, 'morango', semente=22, pocinha=False)
    corpo += calda_bola(a, 238, b1, 50, [(-.5, .5, .2), (-.08, .78, .17), (.36, .42, .15)], semente=4, a0=206, a1=322)
    corpo += bola_sorvete(a, 164, b2, 52, 'creme', semente=21, pocinha=False)
    corpo += calda_bola(a, 164, b2, 52, [(-.55, .42, .16), (-.12, .95, .19), (.32, .62, .17), (.66, .3, .14)], semente=6, a0=204, a1=330)
    # parede de fora (cobre a base das bolas), com faixa amarela da casa
    corpo += f'<path d="{parede}" fill="{a.linear([(0, "#fbf7f0"), (.3, "#efe8dc"), (.72, "#bdb1a0"), (.92, "#8a7f70"), (1, "#c9a988")], 0, 0, 1, 0)}"/>'
    corpo += f'<g clip-path="{a.recorte(parede)}">'
    corpo += f'<path d="M{n(cx - R)},{n(rim_y + 8)} A{n(R)},{n(ry)} 0 0,0 {n(cx + R)},{n(rim_y + 8)}" fill="none" stroke="#ffb703" stroke-width="4.5"/>'
    corpo += f'<path d="M{n(cx - R)},{n(rim_y + 6.2)} A{n(R)},{n(ry)} 0 0,0 {n(cx + R)},{n(rim_y + 6.2)}" fill="none" stroke="#fff" stroke-opacity=".35" stroke-width="1"/>'
    corpo += f'<rect x="90" y="{n(rim_y)}" width="220" height="{n(cy - rim_y + 10)}" fill="{a.linear([(0, "#000", 0), (.5, "#000", .04), (1, "#000", .45)])}"/>'
    fy = rim_y + ry + 10
    corpo += f'<path d="M{n(cx - R * .66)},{n(fy)} C{n(cx - R * .64)},{n(fy + 10)} {n(cx - 48)},{n(cy - 22)} {n(cx - 34)},{n(cy - 14)}" fill="none" stroke="#fff" stroke-opacity=".8" stroke-width="7" stroke-linecap="round" filter="{a.desfoque(3)}"/>'
    corpo += f'<path d="M{n(cx - R * .64)},{n(fy + 1)} C{n(cx - R * .62)},{n(fy + 10)} {n(cx - 50)},{n(cy - 24)} {n(cx - 38)},{n(cy - 17)}" fill="none" stroke="#fff" stroke-opacity=".9" stroke-width="1.6" stroke-linecap="round"/>'
    corpo += '</g>'
    corpo += f'<path d="M{n(cx - R)},{n(rim_y)} A{n(R)},{n(ry)} 0 0,0 {n(cx + R)},{n(rim_y)}" fill="none" stroke="#fff" stroke-opacity=".95" stroke-width="2"/>'
    corpo += f'<path d="M{n(cx + R * .55)},{n(rim_y + ry * .84)} A{n(R)},{n(ry)} 0 0,0 {n(cx + R)},{n(rim_y)}" fill="none" stroke="{ARO}" stroke-opacity=".6" stroke-width="2"/>'
    return a.svg(corpo)


# ---------------------------------------------------------------- mousse

def sementes_maracuja(a, pts, r, escala=1.0):
    """Sementes pretas de maracujá, cada uma no seu arilo de gel claro, com brilho."""
    s = pontos(pts, '#ffe9a0', 7.5 * escala, .55)
    for x, y in pts:
        s += f'<ellipse cx="{n(x)}" cy="{n(y)}" rx="{n(2.7 * escala)}" ry="{n(1.8 * escala)}" fill="#1c1006" transform="rotate({n(r.uniform(-40, 40))} {n(x)} {n(y)})"/>'
    s += pontos([(x - .9 * escala, y - .6 * escala) for x, y in pts], '#fff', 1.1 * escala, .85)
    return s


def maracuja_metade(a, cx, cy, rx, r):
    """Meio maracujá cortado, de lado: casca roxa enrugada, entrecasca branca e polpa com sementes."""
    ry = rx * .42
    s = f'<ellipse cx="{n(cx + 3)}" cy="{n(cy + rx * .62)}" rx="{n(rx * 1.05)}" ry="{n(rx * .2)}" fill="#000" opacity=".55" filter="{a.desfoque(3)}"/>'
    casca = f'M{n(cx - rx)},{n(cy)} A{n(rx)},{n(ry)} 0 0,1 {n(cx + rx)},{n(cy)} C{n(cx + rx)},{n(cy + rx * .55)} {n(cx + rx * .5)},{n(cy + rx * .72)} {n(cx)},{n(cy + rx * .72)} C{n(cx - rx * .5)},{n(cy + rx * .72)} {n(cx - rx)},{n(cy + rx * .55)} {n(cx - rx)},{n(cy)}Z'
    s += f'<path d="{casca}" fill="{a.radial([(0, "#8a4a6a"), (.5, "#5a2442"), (1, "#2a0a1c")], cx=.35, cy=.45, r=.7)}"/>'
    s += f'<path d="M{n(cx - rx * .7)},{n(cy + rx * .3)} q{n(rx * .2)},{n(rx * .12)} {n(rx * .4)},{n(rx * .08)} M{n(cx + rx * .1)},{n(cy + rx * .5)} q{n(rx * .2)},{n(-rx * .04)} {n(rx * .38)},{n(-rx * .16)}" fill="none" stroke="#1e0612" stroke-opacity=".6" stroke-width="1.2" stroke-linecap="round"/>'
    s += realce(a, cx - rx * .5, cy + rx * .3, rx * .25, rx * .08, rot=20, op=.35, blur=1.5)
    s += f'<ellipse cx="{n(cx)}" cy="{n(cy)}" rx="{n(rx)}" ry="{n(ry)}" fill="#f6ecd2"/>'
    s += f'<ellipse cx="{n(cx)}" cy="{n(cy + .6)}" rx="{n(rx * .84)}" ry="{n(ry * .8)}" fill="{a.radial([(0, "#ffd860"), (.6, "#f5a623"), (1, "#c8700a")], cx=.42, cy=.4, r=.62)}"/>'
    pts = []
    for i in range(14):
        t = r.uniform(0, 2 * math.pi)
        k = math.sqrt(r.uniform(.05, .85))
        pts.append((cx + math.cos(t) * rx * .74 * k, cy + .6 + math.sin(t) * ry * .68 * k))
    s += sementes_maracuja(a, pts, r, .8)
    s += realce(a, cx - rx * .3, cy - ry * .3, rx * .22, ry * .12, op=.8, blur=.6)
    s += f'<path d="M{n(cx - rx)},{n(cy)} A{n(rx)},{n(ry)} 0 0,0 {n(cx + rx)},{n(cy)}" fill="none" stroke="#fff" stroke-opacity=".6" stroke-width="1"/>'
    return s


def mousse():
    a = Arte('Ilustração de mousse de maracujá')
    corpo = fundo(a)
    r = rng(5)
    cx, y0, R, RY = 184, 98, 94, 22        # boca da taça
    k = RY / R
    fy = 244                                 # pé
    corpo += sombra(a, cx=cx + 4, cy=fy + 6, rx=62, ry=7)
    corpo += f'<ellipse cx="{cx + 6}" cy="{fy + 5}" rx="64" ry="9" fill="#ffb21a" opacity=".22" filter="{a.desfoque(6)}"/>'
    # maracujá cortado ao lado (discreto, atrás à direita)
    corpo += maracuja_metade(a, 306, 226, 30, r)
    # pé e haste de vidro
    vid = lambda o1, o2: a.linear([(0, '#ffffff', o1), (.3, '#ffffff', o2), (.8, '#ffffff', o2 * .5), (1, '#ffffff', o1 * .8)], 0, 0, 1, 0)
    corpo += f'<ellipse cx="{cx}" cy="{fy}" rx="56" ry="10.5" fill="{vid(.4, .1)}"/>'
    corpo += f'<ellipse cx="{cx}" cy="{fy - 2.5}" rx="50" ry="8" fill="none" stroke="#fff" stroke-opacity=".35" stroke-width="1"/>'
    corpo += f'<path d="M{cx - 56},{fy} A56,10.5 0 0,0 {cx + 56},{fy}" fill="none" stroke="#fff" stroke-opacity=".75" stroke-width="1.4"/>'
    haste = (f'M{cx - 10},204 C{cx - 7},211 {cx - 13},215 {cx - 10},220 C{cx - 7},225 {cx - 7},{fy - 10} {cx - 14},{fy - 4} '
             f'L{cx + 14},{fy - 4} C{cx + 7},{fy - 10} {cx + 7},225 {cx + 10},220 C{cx + 13},215 {cx + 7},211 {cx + 10},204Z')
    corpo += f'<path d="{haste}" fill="{vid(.55, .16)}"/>'
    corpo += f'<path d="M{cx - 4},{fy - 7} V209" stroke="#fff" stroke-opacity=".75" stroke-width="1.3" stroke-linecap="round"/>'
    corpo += f'<path d="M{cx + 6},{fy - 9} C{cx + 4},228 {cx + 5},222 {cx + 8},216" fill="none" stroke="{ARO}" stroke-opacity=".6" stroke-width="1.1"/>'
    # taça (silhueta de fora e parede de dentro)
    taca = (f'M{cx - R},{y0} A{R},{RY} 0 0,1 {cx + R},{y0} C{cx + R - 1},{y0 + 52} {cx + R - 20},188 {cx + 32},201 '
            f'Q{cx},208 {cx - 32},201 C{cx - R + 20},188 {cx - R + 1},{y0 + 52} {cx - R},{y0}Z')
    Ri = R - 4
    dentro = (f'M{cx - Ri},{y0} A{Ri},{RY - 1} 0 0,1 {cx + Ri},{y0} C{cx + Ri - 1},{y0 + 50} {cx + Ri - 20},184 {cx + 30},196 '
              f'Q{cx},202 {cx - 30},196 C{cx - Ri + 20},184 {cx - Ri + 1},{y0 + 50} {cx - Ri},{y0}Z')
    corpo += f'<path d="{taca}" fill="#fff" opacity=".04"/>'
    # parede de trás, por dentro, acima do creme
    corpo += f'<path d="M{cx - Ri},{y0} A{Ri},{RY - 1} 0 0,1 {cx + Ri},{y0}" fill="none" stroke="#fff" stroke-opacity=".28" stroke-width="1.2"/>'
    # mousse: corpo aerado, visto pelo vidro
    L0 = y0 + 9
    rl = Ri - 1.5
    ryl = rl * k
    corpo_m = f'M{n(cx - rl)},{L0} A{n(rl)},{n(ryl)} 0 0,1 {n(cx + rl)},{L0} V214 H{n(cx - rl)}Z'
    corpo += f'<g clip-path="{a.recorte(dentro)}">'
    corpo += f'<path d="{corpo_m}" fill="{a.linear([(0, "#d29a2a"), (.16, "#f3d070"), (.42, "#fcebae"), (.72, "#f3d47e"), (1, "#bf8a20")], 0, 0, 1, 0)}"/>'
    corpo += f'<rect x="{cx - R}" y="{L0}" width="{2 * R}" height="110" fill="{a.linear([(0, "#fff", 0), (.4, "#000", 0), (1, "#6a4000", .38)])}"/>'
    claras = [(cx + r.uniform(-.9, .9) * rl * .95, r.uniform(L0 + ryl + 4, 196)) for _ in range(66)]
    corpo += pontos(claras[::3], '#fffbe8', 2.6, .6) + pontos(claras[1::3], '#fff6d0', 1.5, .7) + pontos(claras[2::3], '#a87a1a', 1.7, .3)
    # calda escorrendo pela parede de dentro (véu translúcido na frente do creme, com alguns fios mais longos)
    beira, veu_b = [], []
    fios = ((-.62, 26), (-.18, 15), (.3, 34), (.66, 12))
    for i in range(29):
        u = -1 + 2 * i / 28
        x = cx + u * rl
        y = L0 + ryl * math.sqrt(max(0, 1 - u * u))
        beira.append((x, y - 2))
        q = 4 + 2.5 * math.sin(i * 1.3) + sum(c * math.exp(-((u - f) / .045) ** 2) for f, c in fios)
        veu_b.append((x, y + q))
    veu = linha(beira) + ' ' + suave(list(reversed(veu_b)), fechado=False).replace('M', 'L', 1) + 'Z'
    corpo += f'<path d="{veu}" fill="{a.linear([(0, "#f59c12"), (.5, "#ffb52a"), (1, "#e68a0a")])}" opacity=".78"/>'
    corpo += f'<path d="{suave([(x, y - 1.5) for x, y in veu_b[2:-2]], fechado=False)}" fill="none" stroke="#a85000" stroke-opacity=".3" stroke-width="1"/>'
    for f, c in fios:
        x = cx + f * rl - 1.5
        y = L0 + ryl * math.sqrt(1 - f * f)
        corpo += f'<path d="M{n(x)},{n(y + 3)} V{n(y + c - 1)}" stroke="#fff3cf" stroke-opacity=".7" stroke-width="1.3" stroke-linecap="round"/>'
    corpo += '</g>'
    # topo: aro de creme e calda generosa por cima, com sementes
    corpo += f'<ellipse cx="{cx}" cy="{L0}" rx="{n(rl)}" ry="{n(ryl)}" fill="{a.radial([(0, "#fff8dc"), (.75, "#f8e4a2"), (1, "#e2bf62")], cx=.4, cy=.4, r=.65)}"/>'
    calda = bolha(cx + 2, L0 + .5, rl * .9, ryl * .84, pontos=14, var=.06, semente=7)
    corpo += f'<path d="{calda}" fill="#9a4a00" opacity=".4" transform="translate(1,2)" filter="{a.desfoque(1.5)}"/>'
    corpo += f'<path d="{calda}" fill="{a.radial([(0, "#ffe27a"), (.35, "#ffc131"), (.75, "#f59c12"), (1, "#d6780a")], cx=.42, cy=.4, r=.62)}"/>'
    corpo += f'<g clip-path="{a.recorte(calda)}">'
    sem = []
    for _ in range(140):
        x = cx + 2 + r.uniform(-1, 1) * rl * .82
        y = L0 + r.uniform(-1, 1) * ryl * .76
        if ((x - cx - 2) / (rl * .84)) ** 2 + ((y - L0) / (ryl * .78)) ** 2 < 1 and all((x - p) ** 2 + ((y - q) * 2.4) ** 2 > 105 for p, q in sem):
            sem.append((x, y))
    corpo += sementes_maracuja(a, sem, r)
    corpo += f'<ellipse cx="{cx + 6}" cy="{L0 + 9}" rx="{n(rl * .8)}" ry="8" fill="#a85000" opacity=".22" filter="{a.desfoque(4)}"/>'
    corpo += '</g>'
    corpo += f'<path d="{calda}" fill="none" stroke="#c46a00" stroke-opacity=".55" stroke-width=".9"/>'
    corpo += realce(a, cx - 30, L0 - 8, 28, 3, rot=-3, op=.85, blur=1)
    corpo += realce(a, cx - 44, L0 - 7, 9, 1.3, rot=-3, op=.95, blur=.3)
    corpo += realce(a, cx + 40, L0 + 7, 14, 1.6, rot=-4, op=.55, blur=.6)
    # vidro: reflexos, espessura da boca e luz de contorno
    corpo += f'<path d="{taca}" fill="{a.linear([(0, "#ffffff", .2), (.14, "#ffffff", .05), (.5, "#ffffff", 0), (.88, "#ffffff", .04), (1, "#ffffff", .16)], 0, 0, 1, 0)}"/>'
    corpo += f'<path d="M{cx - R + 9},{y0 + 26} C{cx - R + 10},{y0 + 62} {cx - R + 24},{176} {cx - 50},{192}" fill="none" stroke="#fff" stroke-opacity=".6" stroke-width="7" stroke-linecap="round" filter="{a.desfoque(2.4)}"/>'
    corpo += f'<path d="M{cx - R + 11},{y0 + 28} C{cx - R + 12},{y0 + 60} {cx - R + 25},{172} {cx - 54},{188}" fill="none" stroke="#fff" stroke-opacity=".95" stroke-width="1.4" stroke-linecap="round"/>'
    corpo += f'<path d="M{cx + R - 16},{y0 + 34} C{cx + R - 18},{y0 + 60} {cx + R - 30},{172} {cx + 44},{186}" fill="none" stroke="#fff" stroke-opacity=".3" stroke-width="3" stroke-linecap="round" filter="{a.desfoque(1.4)}"/>'
    corpo += f'<path d="M{cx + R - 2},{y0 + 8} C{cx + R - 2},{y0 + 54} {cx + R - 20},{184} {cx + 30},{199}" fill="none" stroke="{ARO}" stroke-opacity=".65" stroke-width="2" stroke-linecap="round"/>'
    corpo += f'<path d="M{cx - 26},{199} Q{cx},{205} {cx + 26},{199}" fill="none" stroke="#fff" stroke-opacity=".55" stroke-width="2.2" stroke-linecap="round"/>'
    corpo += f'<ellipse cx="{cx}" cy="{y0}" rx="{R}" ry="{RY}" fill="none" stroke="#fff" stroke-opacity=".5" stroke-width="1.2"/>'
    corpo += f'<path d="M{cx - R},{y0} A{R},{RY} 0 0,0 {cx + R},{y0}" fill="none" stroke="#fff" stroke-opacity=".9" stroke-width="1.8"/>'
    corpo += f'<path d="M{cx - R + 3},{y0 + 1} A{R - 3},{RY - 1.5} 0 0,0 {cx + R - 3},{y0 + 1}" fill="none" stroke="#fff" stroke-opacity=".3" stroke-width="1"/>'
    corpo += realce(a, cx - R * .55, y0 + RY * .78, 16, 1.6, rot=12, op=.9, blur=.5)
    return a.svg(corpo)


def gerar():
    return {
        'brownie': brownie(),
        'petit-gateau': petit_gateau(),
        'pudim': pudim(),
        'churros': churros(),
        'sorvete': sorvete(),
        'mousse': mousse(),
    }
