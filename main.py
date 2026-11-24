"""Ponto de entrada da aplicação 3D 'Maix que um Circuito' em ModernGL."""

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import glfw
import glm
import moderngl
import numpy as np

import camera

SHADERS = Path(__file__).parent / "shaders"
CAMINHO = Path(__file__).parent / "offs" / "torre.off"
TITULO_JANELA = "Maix que um Circuito"
LADO = 700
FUNDO = (0.10, 0.11, 0.13, 1.0)
VERSAO_OPENGL = (4, 0)
AMOSTRAS_MSAA = 4
ALTURA_ALVO_MODELO = 1.8
DT_MAX = 0.05


@dataclass
class EstadoMouse:
    """Armazena o estado de arrasto do botão direito para rotação da câmera."""

    girando: bool = False
    ultimo_x: float | None = None
    ultimo_y: float | None = None


def ler_off(caminho: Path) -> tuple[np.ndarray, np.ndarray]:
    """Lê uma malha triangular em formato OFF e retorna (vértices, índices)."""
    campos: list[str] = []
    for linha in Path(caminho).read_text(encoding="utf-8").splitlines():
        linha = linha.split("#")[0].strip()
        if linha:
            campos.extend(linha.split())

    n_vertices, n_faces = int(campos[1]), int(campos[2])
    p = 4
    vertices = np.array(
        campos[p:p + 3 * n_vertices],
        dtype="f4",
    ).reshape(n_vertices, 3)
    p += 3 * n_vertices

    indices = np.empty((n_faces, 3), dtype="u4")
    for i in range(n_faces):
        lados = int(campos[p])
        if lados != 3:
            raise ValueError(
                f"{caminho}: face {i} tem {lados} lados; "
                "este leitor só aceita triângulos"
            )
        indices[i] = campos[p + 1:p + 4]
        p += 1 + lados

    return vertices, indices


def preparar_malha(
    posicoes: np.ndarray,
    indices: np.ndarray,
) -> tuple[np.ndarray, glm.mat4]:
    """Calcula a matriz de enquadramento e o buffer intercalado (posição + normal)."""
    minimo = posicoes.min(axis=0)
    maximo = posicoes.max(axis=0)
    centro = (minimo + maximo) / 2.0
    escala = (1.0 / (maximo[1] - minimo[1])) * ALTURA_ALVO_MODELO
    m_enq = glm.scale(glm.mat4(1.0), glm.vec3(escala)) * glm.translate(
        glm.mat4(1.0),
        glm.vec3(-minimo[0], -minimo[1], -centro[2]),
    )

    tri_pos = posicoes[indices]
    n_face = np.cross(tri_pos[:, 1] - tri_pos[:, 0], tri_pos[:, 2] - tri_pos[:, 1])
    n_face /= np.maximum(np.linalg.norm(n_face, axis=1, keepdims=True), 1e-12)
    tri_nor = np.repeat(n_face[:, None, :], 3, axis=1)
    dados = np.concatenate([tri_pos, tri_nor], axis=2).astype("f4")

    return dados, m_enq


def main() -> None:
    """Inicializa GLFW/ModernGL, carrega a torre e executa o laço principal."""
    if not glfw.init():
        raise RuntimeError("Não foi possível inicializar o GLFW.")

    glfw.window_hint(glfw.CONTEXT_VERSION_MAJOR, VERSAO_OPENGL[0])
    glfw.window_hint(glfw.CONTEXT_VERSION_MINOR, VERSAO_OPENGL[1])
    glfw.window_hint(glfw.OPENGL_PROFILE, glfw.OPENGL_CORE_PROFILE)
    glfw.window_hint(glfw.OPENGL_FORWARD_COMPAT, glfw.TRUE)
    glfw.window_hint(glfw.SAMPLES, AMOSTRAS_MSAA)
    glfw.window_hint(glfw.RESIZABLE, True)

    janela = glfw.create_window(LADO, LADO, TITULO_JANELA, None, None)
    if janela is None:
        glfw.terminate()
        raise RuntimeError("Não foi possível criar a janela GLFW.")

    glfw.make_context_current(janela)
    glfw.swap_interval(1)

    ctx = moderngl.create_context()
    ctx.enable(moderngl.DEPTH_TEST)
    ctx.enable(moderngl.CULL_FACE)

    cam = camera.Camera()
    estado_mouse = EstadoMouse()

    posicoes, indices = ler_off(CAMINHO)
    dados, m_enq = preparar_malha(posicoes, indices)

    prog = ctx.program(
        vertex_shader=(SHADERS / "shader.vert").read_text(encoding="utf-8"),
        fragment_shader=(SHADERS / "shader.frag").read_text(encoding="utf-8"),
    )
    vbo_torre = ctx.buffer(dados.tobytes())
    vao_torre = ctx.vertex_array(prog, [(vbo_torre, "3f 3f", "vPosition", "vNorm")])

    def redimensionar(_window: Any, largura: int, altura: int) -> None:
        largura_segura = max(1, largura)
        altura_segura = max(1, altura)
        ctx.viewport = (0, 0, largura_segura, altura_segura)
        cam.redimensionar(largura_segura, altura_segura)

    def tecla(
        window: Any,
        key: int,
        _scancode: int,
        action: int,
        _mods: int,
    ) -> None:
        if action != glfw.PRESS:
            return
        if key == glfw.KEY_ESCAPE:
            glfw.set_window_should_close(window, True)
        elif key == glfw.KEY_C:
            ctx.disable(moderngl.CULL_FACE)
        elif key == glfw.KEY_V:
            ctx.enable(moderngl.CULL_FACE)
        elif key == glfw.KEY_T:
            cam.alternar_modo()

    def mouse(_window: Any, button: int, action: int, _mods: int) -> None:
        if button != glfw.MOUSE_BUTTON_RIGHT:
            return
        if action == glfw.RELEASE:
            estado_mouse.girando = False
            estado_mouse.ultimo_x = None
            estado_mouse.ultimo_y = None
        elif action == glfw.PRESS:
            estado_mouse.girando = True
            estado_mouse.ultimo_x = None
            estado_mouse.ultimo_y = None

    def cursor(_window: Any, xpos: float, ypos: float) -> None:
        if not estado_mouse.girando:
            return
        if estado_mouse.ultimo_x is not None and estado_mouse.ultimo_y is not None:
            dx = xpos - estado_mouse.ultimo_x
            dy = ypos - estado_mouse.ultimo_y
            cam.girar(dx, dy)
        estado_mouse.ultimo_x = xpos
        estado_mouse.ultimo_y = ypos

    def scroll(_window: Any, _xoffset: float, yoffset: float) -> None:
        cam.zoom(yoffset)

    glfw.set_key_callback(janela, tecla)
    glfw.set_mouse_button_callback(janela, mouse)
    glfw.set_cursor_pos_callback(janela, cursor)
    glfw.set_scroll_callback(janela, scroll)
    glfw.set_framebuffer_size_callback(janela, redimensionar)
    redimensionar(janela, *glfw.get_framebuffer_size(janela))

    t_ant = glfw.get_time()

    while not glfw.window_should_close(janela):
        ctx.clear(*FUNDO)
        agora = glfw.get_time()
        dt = min(DT_MAX, agora - t_ant)
        t_ant = agora

        avancar = float(glfw.get_key(janela, glfw.KEY_W) == glfw.PRESS) - float(
            glfw.get_key(janela, glfw.KEY_S) == glfw.PRESS
        )
        lateral = float(glfw.get_key(janela, glfw.KEY_D) == glfw.PRESS) - float(
            glfw.get_key(janela, glfw.KEY_A) == glfw.PRESS
        )
        vertical = float(glfw.get_key(janela, glfw.KEY_E) == glfw.PRESS) - float(
            glfw.get_key(janela, glfw.KEY_Q) == glfw.PRESS
        )

        cam.mover(avancar, lateral, dt, vertical)
        prog["u_modelo"].write(m_enq.to_bytes())
        prog["u_visao"].write(cam.visao().to_bytes())
        prog["u_projecao"].write(cam.projecao().to_bytes())

        vao_torre.render(moderngl.TRIANGLES)

        glfw.swap_buffers(janela)
        glfw.poll_events()

    glfw.terminate()
    print("Execução finalizada.")


if __name__ == "__main__":
    main()
