"""Ponto de entrada da aplicação 3D 'Maix que um Circuito' em ModernGL."""

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import glfw
import glm
import moderngl
import numpy as np
import geometria as geo
import camera

SHADERS = Path(__file__).parent / "shaders"
CAMINHO = Path(__file__).parent / "modelos" / "torre.off"
TITULO_JANELA = "Maix que um Circuito"
LADO = 700
FUNDO = (0.10, 0.11, 0.13, 1.0)
INTERVALO_FPS = 0.25
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

@dataclass
class EstadoCTX:
    """Armazena o estado do contexto geral da janela e do OpenGL."""

    vsync: bool = True
    cull_face: bool = True
    fps: float = 0.0
    frames: int = 0
    tempo_acum: float = 0.0


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

    estado_mouse = EstadoMouse()
    estado_ctx = EstadoCTX()

    glfw.make_context_current(janela)
    glfw.swap_interval(int(estado_ctx.vsync))

    ctx = moderngl.create_context()
    ctx.enable(moderngl.DEPTH_TEST)
    ctx.enable(moderngl.CULL_FACE)

    cam = camera.Camera()
    dados,  m_enq = geo.carregar_off(CAMINHO)

    prog = ctx.program(
        vertex_shader=(SHADERS / "shader.vert").read_text(encoding="utf-8"),
        fragment_shader=(SHADERS / "shader.frag").read_text(encoding="utf-8"),
    )
    vbo_torre = ctx.buffer(dados.tobytes())
    vao_torre = ctx.vertex_array(prog, [(vbo_torre, "3f 3f 2x4", "vPosition", "vNorm")])

    def atualizar_titulo() -> None:
        vsync_txt = "ON" if estado_ctx.vsync else "OFF"
        cull_txt = "ON" if estado_ctx.cull_face else "OFF"
        cam_txt = getattr(cam, "modo", "?")
        titulo = (
            f"{TITULO_JANELA} | {estado_ctx.fps:6.1f} FPS"
            f" | VSync: {vsync_txt} | Câm: {cam_txt} | Cull: {cull_txt}"
        )
        glfw.set_window_title(janela, titulo)

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
            estado_ctx.cull_face = False
            atualizar_titulo()
        elif key == glfw.KEY_V:
            ctx.enable(moderngl.CULL_FACE)
            estado_ctx.cull_face = True
            atualizar_titulo()
        elif key == glfw.KEY_T:
            cam.alternar_modo()
            atualizar_titulo()
        elif key == glfw.KEY_Y:
            estado_ctx.vsync = not estado_ctx.vsync
            glfw.swap_interval(int(estado_ctx.vsync))
            estado_ctx.frames = 0
            estado_ctx.tempo_acum = 0.0
            atualizar_titulo()

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

    atualizar_titulo()
    t_ant = glfw.get_time()

    while not glfw.window_should_close(janela):
        ctx.clear(*FUNDO)
        agora = glfw.get_time()
        dt_real = agora - t_ant
        t_ant = agora
        dt = min(DT_MAX, dt_real)

        estado_ctx.frames += 1
        estado_ctx.tempo_acum += dt_real
        if estado_ctx.tempo_acum >= INTERVALO_FPS:
            estado_ctx.fps = estado_ctx.frames / estado_ctx.tempo_acum
            estado_ctx.frames = 0
            estado_ctx.tempo_acum = 0.0
            atualizar_titulo()

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
