"""Construtores de geometrias procedurais e adaptador de carga OFF via malha.py."""

from pathlib import Path

import glm
import numpy as np

import malha


def criar_piso(meio_lado: float = 12.0, rep: float = 12.0) -> np.ndarray:
    """Plano em y = 0 com normal +Y e UVs repetidas (formato '3f 3f 2f')."""
    L = float(meio_lado)
    R = float(rep)
    verts = [
        # Triangulo 1 (CCW visto de cima)
        (-L, 0.0, -L, 0.0, 1.0, 0.0, 0.0, R),
        (-L, 0.0,  L, 0.0, 1.0, 0.0, 0.0, 0.0),
        ( L, 0.0,  L, 0.0, 1.0, 0.0, R,   0.0),
        # Triangulo 2 (CCW visto de cima)
        (-L, 0.0, -L, 0.0, 1.0, 0.0, 0.0, R),
        ( L, 0.0,  L, 0.0, 1.0, 0.0, R,   0.0),
        ( L, 0.0, -L, 0.0, 1.0, 0.0, R,   R),
    ]
    return np.array(verts, dtype="f4")


def criar_cubo() -> np.ndarray:
    """
    Cubo unitario [-0.5, 0.5]^3 com normal por face e UV 0..1 ('3f 3f 2f').
    (normal, [p0, p1, p2, p3] em sentido anti-horario visto de fora).
    """
    h = 0.5
    faces = [
        (( 0.0,  0.0,  1.0), [(-h, -h,  h), ( h, -h,  h), ( h,  h,  h), (-h,  h,  h)]),  # +Z
        (( 0.0,  0.0, -1.0), [( h, -h, -h), (-h, -h, -h), (-h,  h, -h), ( h,  h, -h)]),  # -Z
        (( 1.0,  0.0,  0.0), [( h, -h,  h), ( h, -h, -h), ( h,  h, -h), ( h,  h,  h)]),  # +X
        ((-1.0,  0.0,  0.0), [(-h, -h, -h), (-h, -h,  h), (-h,  h,  h), (-h,  h, -h)]),  # -X
        (( 0.0,  1.0,  0.0), [(-h,  h,  h), ( h,  h,  h), ( h,  h, -h), (-h,  h, -h)]),  # +Y
        (( 0.0, -1.0,  0.0), [(-h, -h, -h), ( h, -h, -h), ( h, -h,  h), (-h, -h,  h)]),  # -Y
    ]
    uvs = [(0.0, 0.0), (1.0, 0.0), (1.0, 1.0), (0.0, 1.0)]

    dados = []
    for normal, pts in faces:
        for idx in (0, 1, 2, 0, 2, 3):
            dados.append((*pts[idx], *normal, *uvs[idx]))

    return np.array(dados, dtype="f4")


def carregar_off(
    caminho: Path | str,
    altura_alvo: float = 1.8,
) -> tuple[np.ndarray, np.ndarray, glm.mat4]:
    """Carrega malha OFF via malha.py sem alterar as coordenadas originais.

    Devolve (vertices '3f 3f 2f', indices uint32, matriz_enquadramento):
    - coordenadas originais preservadas intactas no VBO;
    - normais suaves por vertice ponderadas por area;
    - mapeamento cilindrico em Y com costura UV tratada por duplicacao;
    - matriz de enquadramento S(escala) * T(-centro_base) apoiada em y = 0.
    """
    m = malha.Malha(caminho)
    dados_tex, indices = m.texturada(tipo="cilindrico", eixo="y", costurar=True)
    vertices = np.ascontiguousarray(dados_tex[:, :8], dtype="f4")
    indices_u32 = np.ascontiguousarray(indices, dtype="u4")

    minimo = m.vertices.min(axis=0)
    maximo = m.vertices.max(axis=0)
    altura_orig = max(float(maximo[1] - minimo[1]), malha.EPS)
    escala = float(altura_alvo) / altura_orig
    m_enq = (
        glm.scale(glm.mat4(1.0), glm.vec3(escala))
        * glm.translate(
            glm.mat4(1.0),
            glm.vec3(-float(m.centro[0]), -float(minimo[1]), -float(m.centro[2])),
        )
    )
    return vertices, indices_u32, m_enq


def criar_onda_eletrica(
    raio: float = 0.35,
    amp: float = 0.06,
    picos: int = 6,
    pontos: int = 64,
) -> np.ndarray:
    """Anel senoidal ao redor do eixo Y para LINE_LOOP (formato '3f')."""
    t = np.linspace(0.0, 2.0 * np.pi, pontos, endpoint=False)
    x = raio * np.cos(t)
    y = amp * np.sin(picos * t)
    z = raio * np.sin(t)
    return np.column_stack((x, y, z)).astype("f4")


def criar_segmento_aresta(subdivisoes: int = 16) -> np.ndarray:
    """Segmento unitario de (0,0,0) ate (0,0,1) subdividido para LINE_STRIP ('3f')."""
    z = np.linspace(0.0, 1.0, max(2, subdivisoes), dtype="f4")
    zeros = np.zeros_like(z)
    return np.column_stack((zeros, zeros, z)).astype("f4")


def criar_quad() -> np.ndarray:
    """Quadrado unitario [0, 1]^2 no plano z = 0, em ordem anti-horaria (formato '3f').

    Os mesmos 4 vertices servem para TRIANGLE_FAN (preenchido) e LINE_LOOP (contorno).
    """
    return np.array(
        [(0.0, 0.0, 0.0), (1.0, 0.0, 0.0), (1.0, 1.0, 0.0), (0.0, 1.0, 0.0)],
        dtype="f4",
    )
