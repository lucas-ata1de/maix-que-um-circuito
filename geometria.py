from pathlib import Path

import glm
import numpy as np


def criar_piso(meio_lado: float = 12.0, rep: float = 8.0) -> np.ndarray:
    """Plano em y = 0 com normal +Y e UVs repetidas (formato '3f 3f 2f')."""
    L = float(meio_lado)
    R = float(rep)
    verts = [
        # Triangulo 1 (CCW visto de cima)
        (-L, 0.0, -L,  0.0, 1.0, 0.0,  0.0, R),
        (-L, 0.0,  L,  0.0, 1.0, 0.0,  0.0, 0.0),
        ( L, 0.0,  L,  0.0, 1.0, 0.0,  R,   0.0),
        # Triangulo 2
        (-L, 0.0, -L,  0.0, 1.0, 0.0,  0.0, R),
        ( L, 0.0,  L,  0.0, 1.0, 0.0,  R,   0.0),
        ( L, 0.0, -L,  0.0, 1.0, 0.0,  R,   R),
    ]
    return np.array(verts, dtype="f4")


def criar_cubo() -> np.ndarray:
    """Cubo unitario [-0.5, 0.5]^3 com normal por face e UV 0..1 ('3f 3f 2f')."""
    h = 0.5
    faces = [
        # (normal, [p0, p1, p2, p3] em sentido anti-horario visto de fora)
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
        p0, p1, p2 = np.array(pts[0]), np.array(pts[1]), np.array(pts[2])
        for idx in (0, 1, 2, 0, 2, 3):
            dados.append((*pts[idx], *normal, *uvs[idx]))

    return np.array(dados, dtype="f4")


def carregar_off(caminho: Path | str, altura_alvo: float = 1.8) -> tuple[np.ndarray, glm.mat4]:
    """Le OFF triangular sem alterar coordenadas e devolve (dados '3f 3f 2f', M_enq)."""
    campos = []
    for linha in Path(caminho).read_text(encoding="utf-8").splitlines():
        linha = linha.split("#")[0].strip()
        if linha:
            campos.extend(linha.split())

    if campos[0].upper() != "OFF":
        raise ValueError(f"{caminho}: nao comeca com OFF")

    n_vertices, n_faces = int(campos[1]), int(campos[2])
    p = 4
    posicoes = np.array(campos[p:p + 3 * n_vertices], dtype="f4").reshape(n_vertices, 3)
    p += 3 * n_vertices

    indices = np.empty((n_faces, 3), dtype="u4")
    for i in range(n_faces):
        lados = int(campos[p])
        indices[i] = campos[p + 1:p + 4]
        p += 1 + lados

    minimo, maximo = posicoes.min(axis=0), posicoes.max(axis=0)
    centro = 0.5 * (minimo + maximo)
    escala = float(altura_alvo) / float(maximo[1] - minimo[1])
    m_enq = (
        glm.scale(glm.mat4(1.0), glm.vec3(escala))
            * glm.translate(glm.mat4(1.0), glm.vec3(-float(centro[0]), -float(minimo[1]), -float(centro[2])))
    )

    # Normal por face (facetada, sem EBO)
    tri_pos = posicoes[indices]  # (F, 3, 3)
    n_face = np.cross(tri_pos[:, 1] - tri_pos[:, 0], tri_pos[:, 2] - tri_pos[:, 1])
    n_face /= np.maximum(np.linalg.norm(n_face, axis=1, keepdims=True), 1e-12)
    tri_nor = np.repeat(n_face[:, None, :], 3, axis=1)

    # Mapeamento cilindrico em torno do eixo Y
    rel = tri_pos - centro
    u = np.arctan2(rel[:, :, 0], rel[:, :, 2]) / (2.0 * np.pi) + 0.5
    v = (tri_pos[:, :, 1] - minimo[1]) / max(float(maximo[1] - minimo[1]), 1e-6)
    tri_uv = np.stack([u, v], axis=2)

    dados = np.concatenate([tri_pos, tri_nor, tri_uv], axis=2).astype("f4")
    return dados, m_enq


def criar_onda_eletrica(raio: float = 0.35, amp: float = 0.06, picos: int = 6, pontos: int = 64) -> np.ndarray:
    """Anel senoidal ao redor do eixo Y para LINE_LOOP (formato '3f')."""
    t = np.linspace(0.0, 2.0 * np.pi, pontos, endpoint=False)
    x = raio * np.cos(t)
    y = amp * np.sin(picos * t)
    z = raio * np.sin(t)
    return np.column_stack((x, y, z)).astype("f4")


def criar_segmento_aresta(subdivisoes: int = 2) -> np.ndarray:
    """Segmento unitario de (0,0,0) ate (0,0,1) para LINE_STRIP (formato '3f')."""
    z = np.linspace(0.0, 1.0, subdivisoes, dtype="f4")
    zeros = np.zeros_like(z)
    return np.column_stack((zeros, zeros, z)).astype("f4")
