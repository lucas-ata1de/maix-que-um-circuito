"""Materiais e fontes de luz em espaco linear (adaptado do Visualizador).

Este modulo manipula apenas estruturas de dados puras (sem dependencia de
moderngl), mantendo a logica do jogo desacoplada da camada de renderizacao.
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
    """Propriedades oticas Blinn-Phong em luz linear e textura opcional."""

    ka: glm.vec3
    kd: glm.vec3
    ks: glm.vec3
    shininess: float = 32.0
    textura: Optional[str] = None  # None -> textura branca 1x1 automatica


@dataclass
class LuzDirecional:
    """Fonte de luz direcional (raios paralelos) no espaco do mundo."""

    direcao: glm.vec3 = field(default_factory=lambda: glm.vec3(-0.4, -1.0, -0.35))
    cor: glm.vec3 = field(default_factory=lambda: glm.vec3(0.85, 0.88, 0.92))
    fator_amb: float = 0.22
    ativa: bool = True


@dataclass
class LuzPontual:
    """Fonte de luz pontual com atenuacao fisica (kc, kl, kq)."""

    posicao: glm.vec3 = field(default_factory=lambda: glm.vec3(0.0, 3.5, 0.0))
    cor: glm.vec3 = field(default_factory=lambda: glm.vec3(1.0, 0.78, 0.45))
    fator_amb: float = 0.08
    kc: float = 1.0
    kl: float = 0.09
    kq: float = 0.032
    ativa: bool = True


@dataclass
class CenaLuzes:
    """Conjunto de luzes ativas da cena (1 direcional + ate 4 pontuais)."""

    direcional: LuzDirecional = field(default_factory=LuzDirecional)
    pontuais: list[LuzPontual] = field(default_factory=list)


# Presets para 'Maix que um Circuito' (coeficientes ja em espaco linear)
MAT_PISO = Material(
    ka=glm.vec3(0.30, 0.30, 0.30),
    kd=glm.vec3(0.85, 0.85, 0.85),
    ks=glm.vec3(0.08, 0.08, 0.08),
    shininess=12.0,
    textura="piso",
)

MAT_TORRE_A = Material(
    ka=glm.vec3(0.10, 0.22, 0.42),
    kd=glm.vec3(0.22, 0.55, 0.95),
    ks=glm.vec3(0.75, 0.82, 0.90),
    shininess=96.0,
    textura="metal_torre",
)

MAT_TORRE_B = Material(
    ka=glm.vec3(0.42, 0.10, 0.12),
    kd=glm.vec3(0.95, 0.24, 0.26),
    ks=glm.vec3(0.88, 0.75, 0.72),
    shininess=96.0,
    textura="metal_torre",
)

MAT_PEDESTAL = Material(
    ka=glm.vec3(0.14, 0.15, 0.18),
    kd=glm.vec3(0.38, 0.42, 0.48),
    ks=glm.vec3(0.32, 0.34, 0.38),
    shininess=32.0,
    textura=None,
)
