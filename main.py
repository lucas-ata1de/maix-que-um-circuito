"""Ponto de entrada da aplicação 3D 'Maix que um Circuito' em ModernGL."""

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import glfw
import math
import glm
import moderngl
import numpy as np
import geometria as geo
import camera
import jogo

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
    estado_jogo = jogo.EstadoJogo()

    glfw.make_context_current(janela)
    glfw.swap_interval(int(estado_ctx.vsync))

    ctx = moderngl.create_context()
    ctx.enable(moderngl.DEPTH_TEST)
    ctx.enable(moderngl.CULL_FACE)

    cam = camera.Camera(pos=(0.0,9.0,18.0),altura_aerea=28)
    dados,  m_enq = geo.carregar_off(CAMINHO)

    prog = ctx.program(
        vertex_shader=(SHADERS / "shader.vert").read_text(encoding="utf-8"),
        fragment_shader=(SHADERS / "shader.frag").read_text(encoding="utf-8"),
    )

    vbo_torre = ctx.buffer(dados.tobytes())
    vao_torre = ctx.vertex_array(prog, [(vbo_torre, "3f 3f 2x4", "vPosition", "vNorm")])

    vbo_piso = ctx.buffer(geo.criar_piso(estado_jogo.meio_lado).tobytes())
    vao_piso = ctx.vertex_array(prog, [(vbo_piso, "3f 3f 2x4", "vPosition", "vNorm")])

    vbo_cubo = ctx.buffer(geo.criar_cubo().tobytes())
    vao_cubo = ctx.vertex_array(prog, [(vbo_cubo, "3f 3f 2x4", "vPosition", "vNorm")])
    
    prog_linha = ctx.program(
        vertex_shader=(SHADERS / "linha.vert").read_text(encoding="utf-8"),
        fragment_shader=(SHADERS / "linha.frag").read_text(encoding="utf-8"),
    )
    vbo_onda = ctx.buffer(geo.criar_onda_eletrica().tobytes())
    vao_onda = ctx.vertex_array(prog_linha, [(vbo_onda, "3f", "vPosition")])

    vbo_aresta = ctx.buffer(geo.criar_segmento_aresta().tobytes())
    vao_aresta = ctx.vertex_array(prog_linha, [(vbo_aresta, "3f", "vPosition")])

    L = estado_jogo.meio_lado
    I = glm.mat4(1.0)

    bordas = [
        glm.translate(I, glm.vec3(0.0, 0.2,  L)) * glm.scale(I, glm.vec3(2 * L + 0.4, 0.4, 0.4)),
        glm.translate(I, glm.vec3(0.0, 0.2, -L)) * glm.scale(I, glm.vec3(2 * L + 0.4, 0.4, 0.4)),
        glm.translate(I, glm.vec3( L, 0.2, 0.0)) * glm.scale(I, glm.vec3(0.4, 0.4, 2 * L - 0.4)),
        glm.translate(I, glm.vec3(-L, 0.2, 0.0)) * glm.scale(I, glm.vec3(0.4, 0.4, 2 * L - 0.4)),
    ]

    def atualizar_titulo() -> None:
        vsync_txt = "ON" if estado_ctx.vsync else "OFF"
        cull_txt = "ON" if estado_ctx.cull_face else "OFF"
        cam_txt = getattr(cam, "modo", "?")
        titulo = (

            f"{TITULO_JANELA} | {estado_ctx.fps:6.1f} FPS"
            f" | VSync: {vsync_txt} | Corte Atual: {estado_jogo.tam_corte_atual / estado_jogo.graph.m:.0%} Meta: {estado_jogo.meta / estado_jogo.graph.m:.0%} | {estado_jogo.tempo_restante:4.1f}s"
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
        elif key == glfw.KEY_ENTER and estado_jogo.estado == "START":
            estado_jogo.estado = "PLAYING"
        elif key == glfw.KEY_P and estado_jogo.estado in ("PAUSED","PLAYING"):
            estado_jogo.estado = "PAUSED" if estado_jogo.estado == "PLAYING" else "PLAYING"
        elif key == glfw.KEY_R:
            estado_jogo.iniciar_fase(estado_jogo.n)

    def mouse(window: Any, button: int, action: int, _mods: int) -> None:
        if button == glfw.MOUSE_BUTTON_LEFT and action == glfw.PRESS:
            mx, my = glfw.get_cursor_pos(window)
            w, h = glfw.get_window_size(window)
            origem, direcao = cam.raio(mx, my, w, h)
            u = estado_jogo.torre_no_raio(origem, direcao)
            if u is not None:
                estado_jogo.inverter_torre(u)
                atualizar_titulo()
                return
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
    tempo_anim=0.0

    while not glfw.window_should_close(janela):
        ctx.clear(*FUNDO)
        agora = glfw.get_time()
        dt_real = agora - t_ant
        t_ant = agora
        dt = min(DT_MAX, dt_real)
        if estado_jogo.estado != "PAUSED":
            tempo_anim += dt

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
        vertical = float(glfw.get_key(janela, glfw.KEY_SPACE) == glfw.PRESS) - float(
            glfw.get_key(janela, glfw.KEY_LEFT_SHIFT) == glfw.PRESS
        )
        avancar *= int(estado_jogo.estado in ("START","PLAYING"))
        lateral *= int(estado_jogo.estado in ("START","PLAYING"))
        vertical *= int(estado_jogo.estado in ("START","PLAYING"))

        cam.mover(avancar, lateral, dt, vertical)
        estado_jogo.atualizar(dt)
        
        #projeto e renderiza a camera
        prog["u_visao"].write(cam.visao().to_bytes())
        prog["u_projecao"].write(cam.projecao().to_bytes())
        prog["u_modelo"].write(I.to_bytes())
        vao_piso.render(moderngl.TRIANGLES)

        #projeto e renderiza cubicos
        for m_borda in bordas:
            prog["u_modelo"].write(m_borda.to_bytes())
            vao_cubo.render(moderngl.TRIANGLES)

        #projeto e renderiza torres
        for x, y, z in estado_jogo.posicoes:
            m_torre = glm.translate(I, glm.vec3(x, y, z)) * m_enq
            prog["u_modelo"].write(m_torre.to_bytes())
            vao_torre.render(moderngl.TRIANGLES)

        # ---- linhas: outro programa, então visão/projeção vão de novo ----
        prog_linha["u_visao"].write(cam.visao().to_bytes())
        prog_linha["u_projecao"].write(cam.projecao().to_bytes())
        prog_linha["u_tempo"].value = tempo_anim

        # coroas girando no topo (u_amp = 0: o shader não entorta a onda)
        prog_linha["u_amp"].value = 0.0
        prog_linha["u_vel"].value = 0.0
        prog_linha["u_seed"].value = 0.0
        for u, (x, y, z) in enumerate(estado_jogo.posicoes):
            cor = (0.15, 0.55, 1.0) if estado_jogo.graph.X[u] == 0 else (1.0, 0.20, 0.25)
            m_onda = (glm.translate(I, glm.vec3(x, y + ALTURA_ALVO_MODELO, z))
                * glm.rotate(I, tempo_anim * 2.2 + u * 0.7, glm.vec3(0, 1, 0)))
            prog_linha["u_cor"].value = cor
            prog_linha["u_modelo"].write(m_onda.to_bytes())
            vao_onda.render(moderngl.LINE_LOOP)

        # arestas: segmento (0,0,0)->(0,0,1) girado em Y e esticado em Z até ir de A a B
        for u in range(estado_jogo.n):
            ax, ay, az = estado_jogo.posicoes[u]
            A = glm.vec3(ax, ay + ALTURA_ALVO_MODELO, az)
            for v in estado_jogo.graph.adj[u]:
                if u >= v:          # cada aresta aparece em adj[u] e adj[v]; desenha uma vez só
                    continue
                bx, by, bz = estado_jogo.posicoes[v]
                d = glm.vec3(bx, by + ALTURA_ALVO_MODELO, bz) - A
                comp = glm.length(d)
                if comp < 1e-5:
                    continue
                m_aresta = (glm.translate(I, A)
                    * glm.rotate(I, math.atan2(d.x, d.z), glm.vec3(0, 1, 0))
                    *glm.scale(I, glm.vec3(1.0, 1.0, comp)))
                no_corte = estado_jogo.graph.ta_no_corte(u, v)
                prog_linha["u_cor"].value = (1.0, 0.90, 0.10) if no_corte else (0.38, 0.40, 0.45)
                prog_linha["u_amp"].value = 0.2 if no_corte else 0.03
                prog_linha["u_vel"].value = 20.0 if no_corte else 5.0
                prog_linha["u_seed"].value = float(u * 17 + v)
                prog_linha["u_modelo"].write(m_aresta.to_bytes())
                vao_aresta.render(moderngl.LINE_STRIP)

        glfw.swap_buffers(janela)
        glfw.poll_events()

    glfw.terminate()
    print("Execução finalizada.")


if __name__ == "__main__":
    main()
