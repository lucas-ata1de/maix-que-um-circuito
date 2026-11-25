"""Materiais e fontes de luz em espaco linear (adaptado do Visualizador).

Este modulo manipula apenas estruturas de dados puras (sem dependencia de
moderngl), mantendo a logica do jogo desacoplada da camada de renderizacao.
Os presets de material estao calibrados para as texturas CC0 da Poly Haven:
piso (rubber_tiles_diff_1k.jpg), torres (rusty_metal_04_diff_1k.jpg) e bordas
(white_stucco_02_diff_1k.jpg).
"""

from dataclasses import dataclass, field
from typing import Optional

import glm


def srgb_para_linear(cor: tuple[float, float, float]) -> glm.vec3:
    """Converte cor RGB [0..1] em sRGB para luz linear (curva IEC sRGB)."""
    res = [
        c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4
        for c in cor
    ]
    return glm.vec3(res[0], res[1], res[2])


@dataclass
class Material:
    """Propriedades oticas Blinn-Phong em luz linear e textura opcional.

    Quando ``textura`` for ``None``, o renderizador vincula automaticamente
    a textura branca 1x1.
    """

    ka: glm.vec3
    kd: glm.vec3
    ks: glm.vec3
    shininess: float = 32.0
    textura: Optional[str] = None
    uv_escala: tuple[float, float] = (1.0, 1.0)


@dataclass
class LuzDirecional:
    """Fonte de luz direcional (raios paralelos) no espaco do mundo."""

    direcao: glm.vec3 = field(default_factory=lambda: glm.vec3(-0.4, -1.0, -0.35))
    cor: glm.vec3 = field(default_factory=lambda: glm.vec3(1.20, 1.22, 1.26))
    fator_amb: float = 0.28
    ativa: bool = True


@dataclass
class LuzPontual:
    """Fonte de luz pontual com atenuacao fisica (kc, kl, kq)."""

    posicao: glm.vec3 = field(default_factory=lambda: glm.vec3(0.0, 4.5, 0.0))
    cor: glm.vec3 = field(default_factory=lambda: glm.vec3(4.40, 3.45, 2.15))
    fator_amb: float = 0.12
    kc: float = 1.0
    kl: float = 0.045
    kq: float = 0.010
    ativa: bool = True


@dataclass
class LuzChoqueTorre:
    """Fonte pontual emitida pelo choque eletrico no topo de uma torre."""

    posicao: glm.vec3
    cor: glm.vec3


@dataclass
class LuzChoqueAresta:
    """Fonte linear emitida pelo arco eletrico entre duas torres (segmento AB)."""

    ponto_a: glm.vec3
    ponto_b: glm.vec3
    no_corte: bool = True
    intensidade: float = 1.0


@dataclass
class ConfigLuzesChoque:
    """Configuracao, alcance finito e emissores dos choques de torres e arestas.

    Cada choque utiliza atenuacao com janela suave de raio finito
    (``torre_raio`` e ``aresta_raio``) para iluminar a vizinhanca sem somar
    brilho excessivo sobre o restante da arena.
    """

    torres_ativas: bool = True
    arestas_ativas: bool = True
    torres: list[LuzChoqueTorre] = field(default_factory=list)
    arestas: list[LuzChoqueAresta] = field(default_factory=list)

    torre_kc: float = 1.0
    torre_kl: float = 0.30
    torre_kq: float = 0.20
    torre_fator_amb: float = 0.08
    torre_raio: float = 4.8

    aresta_kc: float = 1.0
    aresta_kl: float = 0.48
    aresta_kq: float = 0.32
    aresta_fator_amb: float = 0.03
    aresta_raio: float = 3.6

    cor_aresta_corte: glm.vec3 = field(default_factory=lambda: glm.vec3(1.25, 1.02, 0.18))
    cor_aresta_fora: glm.vec3 = field(default_factory=lambda: glm.vec3(0.12, 0.16, 0.24))

    @property
    def algum_ativo(self) -> bool:
        """Indica se ao menos um grupo de luzes de choque esta ligado."""
        return self.torres_ativas or self.arestas_ativas

    def alternar_todos(self) -> bool:
        """Liga ou desliga simultaneamente os choques das torres e das arestas."""
        novo = not self.algum_ativo
        self.torres_ativas = novo
        self.arestas_ativas = novo
        return novo


@dataclass
class CenaLuzes:
    """Conjunto de luzes ativas da cena (direcional, pontuais e choques)."""

    direcional: LuzDirecional = field(default_factory=LuzDirecional)
    pontuais: list[LuzPontual] = field(default_factory=list)
    choques: ConfigLuzesChoque = field(default_factory=ConfigLuzesChoque)


MAT_PISO = Material(
    ka=glm.vec3(1.80, 1.80, 1.80),
    kd=glm.vec3(3.60, 3.60, 3.60),
    ks=glm.vec3(0.12, 0.12, 0.14),
    shininess=32.0,
    textura="piso",
)

MAT_TORRE_A = Material(
    ka=glm.vec3(0.32, 0.65, 1.25),
    kd=glm.vec3(0.55, 1.25, 2.35),
    ks=glm.vec3(0.50, 0.60, 0.70),
    shininess=64.0,
    textura="metal_torre",
)

MAT_TORRE_B = Material(
    ka=glm.vec3(0.68, 0.24, 0.24),
    kd=glm.vec3(1.40, 0.44, 0.42),
    ks=glm.vec3(0.60, 0.50, 0.46),
    shininess=64.0,
    textura="metal_torre",
)

MAT_BORDA = Material(
    ka=glm.vec3(0.16, 0.16, 0.16),
    kd=glm.vec3(0.46, 0.46, 0.46),
    ks=glm.vec3(0.04, 0.04, 0.04),
    shininess=12.0,
    textura="borda",
    uv_escala=(20.0, 1.0),
)

MAT_PEDESTAL = Material(
    ka=glm.vec3(0.14, 0.15, 0.18),
    kd=glm.vec3(0.38, 0.42, 0.48),
    ks=glm.vec3(0.32, 0.34, 0.38),
    shininess=32.0,
    textura=None,
)
