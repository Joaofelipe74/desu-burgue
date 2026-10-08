# Base visual compartilhada pelas ilustrações do Desu Burguer.
#
# Estilo: ilustração vetorial com volume (degradês), sombras suaves, brilhos e
# textura leve, sobre um fundo escuro de "estúdio". Tudo em atributos SVG
# (sem <style> e sem scripts), para funcionar como <img> com a CSP do site.
#
# Uso:
#   a = Arte('Ilustração de ...', brilho='#ffb703')
#   corpo = fundo(a) + sombra(a, ...) + '...'
#   svg = a.svg(corpo)
import math
import random

W, H = 400, 300
CX = 200

MARCA = '#ffb703'        # amarelo da marca
MARCA_ESCURO = '#1b1b1b'
KRAFT = ('#d9b78c', '#c39a69', '#9c7448')   # papel kraft: claro, médio, escuro


def n(v):
    """Formata números de forma compacta."""
    if isinstance(v, int):
        return str(v)
    s = f'{v:.2f}'.rstrip('0').rstrip('.')
    return '0' if s in ('-0', '') else s


def _stops(stops):
    out = []
    for st in stops:
        off, cor = st[0], st[1]
        op = st[2] if len(st) > 2 else 1
        extra = '' if op == 1 else f' stop-opacity="{n(op)}"'
        out.append(f'<stop offset="{n(off)}" stop-color="{cor}"{extra}/>')
    return ''.join(out)


class Arte:
    """Uma ilustração: guarda os <defs> (degradês, filtros, recortes) com ids únicos."""

    def __init__(self, titulo, brilho=MARCA, fundo=True):
        self.titulo = titulo
        self.brilho = brilho
        self.com_fundo = fundo
        self._defs = {}
        self._ordem = []
        self._n = 0

    def _def(self, chave, prefixo, construir):
        if chave not in self._defs:
            self._n += 1
            i = f'{prefixo}{self._n}'
            self._defs[chave] = i
            self._ordem.append(construir(i))
        return self._defs[chave]

    # ---- degradês ----
    def linear(self, stops, x1=0, y1=0, x2=0, y2=1, user=False):
        """Degradê linear. Padrão: de cima (0) para baixo (1) no objeto."""
        chave = ('lin', tuple(tuple(s) for s in stops), x1, y1, x2, y2, user)

        def c(i):
            u = ' gradientUnits="userSpaceOnUse"' if user else ''
            return (f'<linearGradient id="{i}" x1="{n(x1)}" y1="{n(y1)}" x2="{n(x2)}" y2="{n(y2)}"{u}>'
                    f'{_stops(stops)}</linearGradient>')
        return f'url(#{self._def(chave, "g", c)})'

    def radial(self, stops, cx=.5, cy=.5, r=.5, fx=None, fy=None, user=False):
        chave = ('rad', tuple(tuple(s) for s in stops), cx, cy, r, fx, fy, user)

        def c(i):
            u = ' gradientUnits="userSpaceOnUse"' if user else ''
            foco = ''
            if fx is not None:
                foco += f' fx="{n(fx)}"'
            if fy is not None:
                foco += f' fy="{n(fy)}"'
            return (f'<radialGradient id="{i}" cx="{n(cx)}" cy="{n(cy)}" r="{n(r)}"{foco}{u}>'
                    f'{_stops(stops)}</radialGradient>')
        return f'url(#{self._def(chave, "r", c)})'

    # ---- filtros ----
    def desfoque(self, sd):
        def c(i):
            return (f'<filter id="{i}" x="-60%" y="-60%" width="220%" height="220%">'
                    f'<feGaussianBlur stdDeviation="{n(sd)}"/></filter>')
        return f'url(#{self._def(("blur", sd), "f", c)})'

    def textura(self, tipo):
        """Textura granulada aplicada por cima da cor do objeto.

        tipos: 'pao', 'carne', 'frito', 'fino' (granulado leve para molhos, papel, copos).
        """
        presets = {
            # (cor escura rgb, freq, k, b, semente) e (cor clara rgb, freq, k, b, semente)
            'pao': (((.45, .24, .08), .7, 1.9, -1.25, 3), ((1, .93, .78), 1.1, 1.8, -1.3, 9)),
            'carne': (((.10, .04, .02), .55, 3.0, -1.4, 5), ((.92, .62, .45), 1.2, 2.4, -1.6, 11)),
            'frito': (((.42, .20, .04), .6, 3.0, -1.5, 7), ((1, .92, .62), 1.2, 3.0, -1.8, 13)),
            'fino': (((0, 0, 0), 1.6, 1.6, -1.0, 17), ((1, 1, 1), 1.9, 1.6, -1.05, 19)),
        }
        escuro, claro = presets[tipo]

        def camada(spec, nome):
            (r, g, b), freq, k, bb, seed = spec
            return (f'<feTurbulence type="fractalNoise" baseFrequency="{n(freq)}" numOctaves="2" seed="{seed}" result="{nome}n"/>'
                    f'<feColorMatrix in="{nome}n" type="matrix" values="0 0 0 0 {n(r)} 0 0 0 0 {n(g)} 0 0 0 0 {n(b)} {n(k)} 0 0 0 {n(bb)}" result="{nome}c"/>'
                    f'<feComposite in="{nome}c" in2="SourceAlpha" operator="in" result="{nome}"/>')

        def c(i):
            return (f'<filter id="{i}" x="0" y="0" width="100%" height="100%" color-interpolation-filters="sRGB">'
                    + camada(escuro, 'e') + camada(claro, 'c') +
                    '<feMerge><feMergeNode in="SourceGraphic"/><feMergeNode in="e"/><feMergeNode in="c"/></feMerge></filter>')
        return f'url(#{self._def(("tex", tipo), "t", c)})'

    def recorte(self, d):
        """clipPath a partir de um caminho; devolve url(#id)."""
        def c(i):
            return f'<clipPath id="{i}"><path d="{d}"/></clipPath>'
        return f'url(#{self._def(("clip", d), "c", c)})'

    # ---- saída ----
    def svg(self, corpo):
        defs = ''.join(self._ordem)
        return (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" role="img" aria-label="{self.titulo}">\n'
                f'<!-- Ilustração original Desu Burguer — desenho, não é foto do produto. -->\n'
                f'<defs>{defs}</defs>\n{corpo}\n</svg>\n')


# ---------------------------------------------------------------- cena

def fundo(a):
    """Fundo escuro de estúdio: luz quente atrás do produto, mesa e vinheta."""
    if not a.com_fundo:
        return ''
    base = a.linear([(0, '#26201b'), (1, '#110d0a')])
    luz = a.radial([(0, a.brilho, .32), (.5, a.brilho, .1), (1, a.brilho, 0)], cx=.5, cy=.44, r=.6)
    mesa = a.radial([(0, '#5a4636', .55), (.6, '#3a2d23', .25), (1, '#3a2d23', 0)])
    vinheta = a.radial([(.55, '#000', 0), (1, '#000', .6)], r=.72)
    return (f'<rect width="{W}" height="{H}" fill="{base}"/>'
            f'<rect width="{W}" height="{H}" fill="{luz}"/>'
            f'<ellipse cx="200" cy="258" rx="230" ry="52" fill="{mesa}"/>'
            f'<rect width="{W}" height="{H}" fill="{vinheta}"/>')


def sombra(a, cx=200, cy=252, rx=120, ry=10, forca=1.0):
    """Sombra no chão: uma difusa e uma de contato, mais escura."""
    return (f'<ellipse cx="{n(cx)}" cy="{n(cy)}" rx="{n(rx * 1.05)}" ry="{n(ry * 1.5)}" fill="#000" opacity="{n(.5 * forca)}" filter="{a.desfoque(7)}"/>'
            f'<ellipse cx="{n(cx)}" cy="{n(cy - 1)}" rx="{n(rx * .82)}" ry="{n(ry * .55)}" fill="#000" opacity="{n(.55 * forca)}" filter="{a.desfoque(2.5)}"/>')


def realce(a, cx, cy, rx, ry, rot=0, op=.35, blur=4, cor='#ffffff'):
    """Brilho suave (reflexo de luz)."""
    t = f' transform="rotate({n(rot)} {n(cx)} {n(cy)})"' if rot else ''
    f = f' filter="{a.desfoque(blur)}"' if blur else ''
    return f'<ellipse cx="{n(cx)}" cy="{n(cy)}" rx="{n(rx)}" ry="{n(ry)}" fill="{cor}" opacity="{n(op)}"{f}{t}/>'


def sombra_contato(a, x0, x1, y, alt=6, op=.4, blur=2.2):
    """Faixa escura logo abaixo de um objeto apoiado em outro."""
    return (f'<rect x="{n(x0)}" y="{n(y - alt / 2)}" width="{n(x1 - x0)}" height="{n(alt)}" rx="{n(alt / 2)}" '
            f'fill="#000" opacity="{n(op)}" filter="{a.desfoque(blur)}"/>')


# ---------------------------------------------------------------- formas

def suave(pts, fechado=True, t=1.0):
    """Curva suave (Catmull-Rom → Bézier) passando por todos os pontos."""
    k = len(pts)
    if k < 3:
        return 'M' + ' L'.join(f'{n(x)},{n(y)}' for x, y in pts)
    if fechado:
        d = f'M{n(pts[0][0])},{n(pts[0][1])}'
        for i in range(k):
            p0, p1, p2, p3 = pts[(i - 1) % k], pts[i], pts[(i + 1) % k], pts[(i + 2) % k]
            c1 = (p1[0] + (p2[0] - p0[0]) / 6 * t, p1[1] + (p2[1] - p0[1]) / 6 * t)
            c2 = (p2[0] - (p3[0] - p1[0]) / 6 * t, p2[1] - (p3[1] - p1[1]) / 6 * t)
            d += f' C{n(c1[0])},{n(c1[1])} {n(c2[0])},{n(c2[1])} {n(p2[0])},{n(p2[1])}'
        return d + 'Z'
    ext = [pts[0]] + list(pts) + [pts[-1]]
    d = f'M{n(pts[0][0])},{n(pts[0][1])}'
    for i in range(1, len(ext) - 2):
        p0, p1, p2, p3 = ext[i - 1], ext[i], ext[i + 1], ext[i + 2]
        c1 = (p1[0] + (p2[0] - p0[0]) / 6 * t, p1[1] + (p2[1] - p0[1]) / 6 * t)
        c2 = (p2[0] - (p3[0] - p1[0]) / 6 * t, p2[1] - (p3[1] - p1[1]) / 6 * t)
        d += f' C{n(c1[0])},{n(c1[1])} {n(c2[0])},{n(c2[1])} {n(p2[0])},{n(p2[1])}'
    return d


def bolha(cx, cy, rx, ry, pontos=10, var=.12, semente=1, rot=0):
    """Forma orgânica (contorno irregular) em volta de uma elipse."""
    rng = random.Random(semente)
    pts = []
    for i in range(pontos):
        ang = 2 * math.pi * i / pontos + rot
        f = 1 + rng.uniform(-var, var)
        pts.append((cx + math.cos(ang) * rx * f, cy + math.sin(ang) * ry * f))
    return suave(pts)


def rng(semente):
    return random.Random(semente)


def selo_marca(a, cx, cy, r=14, fundo_cor=MARCA, letra=MARCA_ESCURO):
    """Selo redondo com o "D" da casa (marca própria do Desu Burguer)."""
    return (f'<circle cx="{n(cx)}" cy="{n(cy)}" r="{n(r)}" fill="{fundo_cor}"/>'
            f'<circle cx="{n(cx)}" cy="{n(cy)}" r="{n(r - 1.5)}" fill="none" stroke="#000" stroke-opacity=".15" stroke-width="1"/>'
            f'<text x="{n(cx)}" y="{n(cy + r * .36)}" font-family="Arial, Helvetica, sans-serif" font-size="{n(r * 1.05)}" '
            f'font-weight="900" text-anchor="middle" fill="{letra}">D</text>')
