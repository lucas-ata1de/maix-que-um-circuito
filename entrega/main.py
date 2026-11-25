"""Maix que um Circuito — Jogo 3D interativo em OpenGL 4.0 Core / ModernGL.

Execucao:
    python main.py
    (ou via Makefile: `make setup && make run`)

Controles de Teclado:
    W / A / S / D       Movimentacao horizontal da camera (modo livre)
    Espaco / L-Shift    Subir / descer a camera (modo livre)
    T                   Alternar modo de camera ('livre' <-> 'aerea')
    1                   Ligar / desligar luz direcional
    2                   Ligar / desligar luz pontual movel (orbitante)
    3                   Ligar / desligar luz de todos os choques (torres + arestas)
    4                   Ligar / desligar apenas luz dos choques das torres
    5                   Ligar / desligar apenas luz dos choques entre torres
    Y                   Ligar / desligar VSync (FPS exibido na barra de titulo)
    C / V               Desativar / ativar descarte de faces traseiras (CULL_FACE)
    Enter               Iniciar partida (a partir do estado START)
    P                   Pausar / retomar partida (congela animacoes e tempo)
    R                   Reiniciar fase com novo grafo aleatorio
    Esc                 Fechar janela

Controles de Mouse:
    Botao Esquerdo (clique)    Selecionar torre por raycasting e inverter particao
    Botao Direito + Arrastar   Girar orientacao da camera (yaw/pitch no modo livre)
    Roda do Mouse (Scroll)     Zoom (aproximar/afastar nos modos livre e aereo)
"""

from dataclasses import dataclass
import math
from pathlib import Path
from typing import Any

import glfw
import glm
import moderngl

import camera
import geometria as geo
import jogo
from material import (
    CenaLuzes,
    ConfigLuzesChoque,
    LuzChoqueAresta,
    LuzChoqueTorre,
    LuzDirecional,
    LuzPontual,
    MAT_BORDA,
    MAT_PISO,
    MAT_TORRE_A,
    MAT_TORRE_B,
    srgb_para_linear,
)
from renderizador import Renderizador

RAIZ = Path(__file__).parent
SHADERS = RAIZ / "shaders"
TEXTURAS = RAIZ / "texturas"
CAMINHO_TORRE = RAIZ / "modelos" / "torre.off"

TITULO_JANELA = "Maix que um Circuito"
LADO = 700
FUNDO = (0.10, 0.11, 0.13, 1.0)
INTERVALO_FPS = 0.25
VERSAO_OPENGL = (4, 0)
AMOSTRAS_MSAA = 4
ALTURA_ALVO_MODELO = 1.8
ALTURA_LUZ_TORRE = ALTURA_ALVO_MODELO + 0.25
DT_MAX = 0.05
RAIO_CAMERA = 0.5
MEIA_LARG_TORRE = 0.25 * ALTURA_ALVO_MODELO  # caixa da torre: usada no clique e na colisao
ALTURA_CAIXA_TORRE = ALTURA_ALVO_MODELO + 0.1

COR_COROA_A = srgb_para_linear((0.15, 0.55, 1.00))
COR_COROA_B = srgb_para_linear((1.00, 0.20, 0.25))
COR_ARESTA_CORTE = srgb_para_linear((1.00, 0.90, 0.10))
COR_ARESTA_FORA = srgb_para_linear((0.38, 0.40, 0.45))
COR_PLACAR_FUNDO = srgb_para_linear((0.15, 0.16, 0.19))
COR_PLACAR_MOLDURA = srgb_para_linear((0.85, 0.85, 0.85))
COR_PLACAR_META = srgb_para_linear((0.20, 1.00, 0.40))
COR_PLACAR_TEMPO = srgb_para_linear((0.30, 0.75, 1.00))

# Layout do placar em pixels (origem no canto inferior esquerdo da janela)
PLACAR_MARGEM = 20.0
PLACAR_LARGURA = 300.0
PLACAR_ALTURA = 18.0
PLACAR_ESPACO = 12.0


def retangulo(x: float, y: float, largura: float, altura: float) -> glm.mat4:
    """Matriz de modelo que leva o quadrado unitario [0,1]^2 ao retangulo (x, y, largura, altura)."""
    return glm.translate(glm.mat4(1.0), glm.vec3(x, y, 0.0)) * glm.scale(
        glm.mat4(1.0), glm.vec3(largura, altura, 1.0)
    )

LUZ_CHOQUE_TORRE_A = glm.vec3(0.40, 1.00, 2.25)
LUZ_CHOQUE_TORRE_B = glm.vec3(1.75, 0.36, 0.38)


@dataclass
class EstadoMouse:
    """Armazena o estado de arrasto do botao direito para rotacao da camera."""

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


def _atualizar_luzes_choque(
    estado_jogo: jogo.EstadoJogo,
    choques: ConfigLuzesChoque,
    tempo_anim: float,
) -> None:
    """Sincroniza as luzes emitidas pelas coroas das torres e arestas eletricas."""
    choques.torres.clear()
    if choques.torres_ativas:
        for u, (x, y, z) in enumerate(estado_jogo.posicoes):
            flicker = 0.90 + 0.10 * math.sin(tempo_anim * 7.5 + u * 1.9)
            cor_base = (
                LUZ_CHOQUE_TORRE_A
                if estado_jogo.graph.X[u] == 0
                else LUZ_CHOQUE_TORRE_B
            )
            choques.torres.append(
                LuzChoqueTorre(
                    posicao=glm.vec3(x, y + ALTURA_LUZ_TORRE, z),
                    cor=cor_base * flicker,
                )
            )

    choques.arestas.clear()
    if choques.arestas_ativas:
        for u in range(estado_jogo.n):
            ax, ay, az = estado_jogo.posicoes[u]
            p_a = glm.vec3(ax, ay + ALTURA_ALVO_MODELO, az)
            for v in estado_jogo.graph.adj[u]:
                if u >= v:
                    continue
                bx, by, bz = estado_jogo.posicoes[v]
                p_b = glm.vec3(bx, by + ALTURA_ALVO_MODELO, bz)
                no_corte = estado_jogo.graph.ta_no_corte(u, v)
                vel = 16.0 if no_corte else 5.0
                amp_f = 0.15 if no_corte else 0.06
                intens = (1.0 - amp_f) + amp_f * math.sin(
                    tempo_anim * vel + float(u * 17 + v)
                )
                choques.arestas.append(
                    LuzChoqueAresta(
                        ponto_a=p_a,
                        ponto_b=p_b,
                        no_corte=no_corte,
                        intensidade=intens,
                    )
                )


def main() -> None:
    """Inicializa GLFW/ModernGL, carrega geometrias/texturas e executa o laco principal."""
    if not glfw.init():
        raise RuntimeError("Nao foi possivel inicializar o GLFW.")

    glfw.window_hint(glfw.CONTEXT_VERSION_MAJOR, VERSAO_OPENGL[0])
    glfw.window_hint(glfw.CONTEXT_VERSION_MINOR, VERSAO_OPENGL[1])
    glfw.window_hint(glfw.OPENGL_PROFILE, glfw.OPENGL_CORE_PROFILE)
    glfw.window_hint(glfw.OPENGL_FORWARD_COMPAT, glfw.TRUE)
    glfw.window_hint(glfw.SAMPLES, AMOSTRAS_MSAA)
    glfw.window_hint(glfw.SRGB_CAPABLE, glfw.TRUE)
    glfw.window_hint(glfw.RESIZABLE, True)

    janela = glfw.create_window(LADO, LADO, TITULO_JANELA, None, None)
    if janela is None:
        glfw.terminate()
        raise RuntimeError("Nao foi possivel criar a janela GLFW.")

    estado_mouse = EstadoMouse()
    estado_ctx = EstadoCTX()
    estado_jogo = jogo.EstadoJogo()

    glfw.make_context_current(janela)
    glfw.swap_interval(int(estado_ctx.vsync))

    ctx = moderngl.create_context()
    ctx.enable(moderngl.DEPTH_TEST)
    ctx.enable(moderngl.CULL_FACE)

    cam = camera.Camera(pos=(0.0, 9.0, 11.0), altura_aerea=28.0)

    renderizador = Renderizador(
        ctx,
        pasta_shaders=SHADERS,
        usar_framebuffer_srgb=True,
    )
    renderizador.carregar_textura(
        "piso",
        TEXTURAS / "rubber_tiles_diff_1k.jpg",
        repetir=True,
    )
    renderizador.carregar_textura(
        "metal_torre",
        TEXTURAS / "rusty_metal_04_diff_1k.jpg",
        repetir=True,
    )
    renderizador.carregar_textura(
        "borda",
        TEXTURAS / "white_stucco_02_diff_1k.jpg",
        repetir=True,
    )

    luz_movel = LuzPontual(posicao=glm.vec3(8.0, 4.5, 0.0))
    cena_luzes = CenaLuzes(
        direcional=LuzDirecional(),
        pontuais=[luz_movel],
        choques=ConfigLuzesChoque(),
    )

    dados_torre, indices_torre, m_enq = geo.carregar_off(
        CAMINHO_TORRE,
        altura_alvo=ALTURA_ALVO_MODELO,
    )
    vbo_torre = ctx.buffer(dados_torre.tobytes())
    ibo_torre = ctx.buffer(indices_torre.tobytes())

    vbo_piso = ctx.buffer(geo.criar_piso(estado_jogo.meio_lado, rep=12.0).tobytes())
    vbo_cubo = ctx.buffer(geo.criar_cubo().tobytes())
    vbo_onda = ctx.buffer(geo.criar_onda_eletrica().tobytes())
    vbo_aresta = ctx.buffer(geo.criar_segmento_aresta().tobytes())
    vbo_quad = ctx.buffer(geo.criar_quad().tobytes())

    L = float(estado_jogo.meio_lado)
    I = glm.mat4(1.0)
    rot_y90 = glm.rotate(I, math.pi / 2.0, glm.vec3(0.0, 1.0, 0.0))

    bordas = [
        glm.translate(I, glm.vec3(0.0, 0.2,  L)) * glm.scale(I, glm.vec3(2 * L + 0.4, 0.4, 0.4)),
        glm.translate(I, glm.vec3(0.0, 0.2, -L)) * glm.scale(I, glm.vec3(2 * L + 0.4, 0.4, 0.4)),
        glm.translate(I, glm.vec3( L, 0.2, 0.0)) * rot_y90 * glm.scale(I, glm.vec3(2 * L - 0.4, 0.4, 0.4)),
        glm.translate(I, glm.vec3(-L, 0.2, 0.0)) * rot_y90 * glm.scale(I, glm.vec3(2 * L - 0.4, 0.4, 0.4)),
    ]

    def atualizar_titulo() -> None:
        """Atualiza a barra de titulo com FPS, estados graficos e progresso da partida."""
        if estado_jogo.estado == "GAME_OVER":
            glfw.set_window_title(janela, "GAME OVER, tente novamente aperte R")
            return
        if estado_jogo.estado == "VICTORY":
            glfw.set_window_title(
                janela,
                f"Ganhou! Tente novamente apertando R. Sobrou {estado_jogo.tempo_restante:.1f} segundos.",
            )
            return
        vsync_txt = "ON" if estado_ctx.vsync else "OFF"
        cull_txt = "ON" if estado_ctx.cull_face else "OFF"
        l1_txt = "ON" if cena_luzes.direcional.ativa else "OFF"
        l2_txt = "ON" if luz_movel.ativa else "OFF"
        ch = cena_luzes.choques
        if ch.torres_ativas and ch.arestas_ativas:
            l3_txt = "ON"
        elif ch.torres_ativas:
            l3_txt = "TORRE"
        elif ch.arestas_ativas:
            l3_txt = "ARESTA"
        else:
            l3_txt = "OFF"
        m_arestas = max(1, estado_jogo.graph.m)
        titulo = (
            f"{TITULO_JANELA} | {estado_ctx.fps:6.1f} FPS"
            f" | VSync:{vsync_txt} | Cam:{cam.modo} | Cull:{cull_txt}"
            f" | L1:{l1_txt} L2:{l2_txt} Choque:{l3_txt} | {estado_jogo.estado}"
            f" | Corte:{estado_jogo.tam_corte_atual / m_arestas:.0%}"
            f" Meta:{estado_jogo.meta / m_arestas:.0%}"
            f" | {estado_jogo.tempo_restante:4.1f}s"
        )
        glfw.set_window_title(janela, titulo)

    def redimensionar(_window: Any, largura: int, altura: int) -> None:
        """Ajusta o viewport e a razao de aspecto ao redimensionar a janela."""
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
        """Trata acoes discretas do teclado (luzes, camera, pausa, reinicio e vsync)."""
        if action != glfw.PRESS:
            return
        if key == glfw.KEY_ESCAPE:
            glfw.set_window_should_close(window, True)
        elif key == glfw.KEY_1:
            cena_luzes.direcional.ativa = not cena_luzes.direcional.ativa
            atualizar_titulo()
        elif key == glfw.KEY_2:
            luz_movel.ativa = not luz_movel.ativa
            atualizar_titulo()
        elif key == glfw.KEY_3:
            cena_luzes.choques.alternar_todos()
            atualizar_titulo()
        elif key == glfw.KEY_4:
            cena_luzes.choques.torres_ativas = not cena_luzes.choques.torres_ativas
            atualizar_titulo()
        elif key == glfw.KEY_5:
            cena_luzes.choques.arestas_ativas = not cena_luzes.choques.arestas_ativas
            atualizar_titulo()
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
            atualizar_titulo()
        elif key == glfw.KEY_P and estado_jogo.estado in ("PAUSED", "PLAYING"):
            estado_jogo.estado = "PAUSED" if estado_jogo.estado == "PLAYING" else "PLAYING"
            atualizar_titulo()
        elif key == glfw.KEY_R:
            estado_jogo.iniciar_fase(estado_jogo.n)
            atualizar_titulo()

    def mouse(window: Any, button: int, action: int, _mods: int) -> None:
        """Trata selecao de torre (botao esquerdo) e inicio/fim de giro (botao direito)."""
        if button == glfw.MOUSE_BUTTON_LEFT and action == glfw.PRESS:
            mx, my = glfw.get_cursor_pos(window)
            w, h = glfw.get_window_size(window)
            origem, direcao = cam.raio(mx, my, w, h)
            u = estado_jogo.torre_no_raio(
                origem,
                direcao,
                meia_larg=MEIA_LARG_TORRE,
                altura=ALTURA_CAIXA_TORRE,
            )
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
        """Atualiza yaw e pitch da camera enquanto o botao direito e arrastado."""
        if not estado_mouse.girando:
            return
        if estado_mouse.ultimo_x is not None and estado_mouse.ultimo_y is not None:
            dx = xpos - estado_mouse.ultimo_x
            dy = ypos - estado_mouse.ultimo_y
            cam.girar(dx, dy)
        estado_mouse.ultimo_x = xpos
        estado_mouse.ultimo_y = ypos

    def scroll(_window: Any, _xoffset: float, yoffset: float) -> None:
        """Aproxima ou afasta a camera conforme a rolagem do mouse."""
        cam.zoom(yoffset)
        cam.pos = estado_jogo.empurrar_esfera(cam.pos, RAIO_CAMERA, MEIA_LARG_TORRE, ALTURA_CAIXA_TORRE)

    glfw.set_key_callback(janela, tecla)
    glfw.set_mouse_button_callback(janela, mouse)
    glfw.set_cursor_pos_callback(janela, cursor)
    glfw.set_scroll_callback(janela, scroll)
    glfw.set_framebuffer_size_callback(janela, redimensionar)
    redimensionar(janela, *glfw.get_framebuffer_size(janela))

    atualizar_titulo()
    t_ant = glfw.get_time()
    tempo_anim = 0.0
    raio_orbita = 8.0

    try:
        while not glfw.window_should_close(janela):
            agora = glfw.get_time()
            dt_real = agora - t_ant
            t_ant = agora
            dt = min(DT_MAX, dt_real)

            if estado_jogo.estado != "PAUSED":
                tempo_anim += dt
                luz_movel.posicao = glm.vec3(
                    raio_orbita * math.cos(tempo_anim * 0.8),
                    4.5 + 0.6 * math.sin(tempo_anim * 1.6),
                    raio_orbita * math.sin(tempo_anim * 0.8),
                )

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
            pode_mover = int(estado_jogo.estado in ("START", "PLAYING"))
            avancar *= pode_mover
            lateral *= pode_mover
            vertical *= pode_mover

            cam.mover(avancar, lateral, dt, vertical)
            cam.pos = estado_jogo.empurrar_esfera(cam.pos, RAIO_CAMERA, MEIA_LARG_TORRE, ALTURA_CAIXA_TORRE)
            estado_jogo.atualizar(dt)

            _atualizar_luzes_choque(estado_jogo, cena_luzes.choques, tempo_anim)

            V = cam.visao()
            P = cam.projecao()

            renderizador.limpar_tela(FUNDO)

            renderizador.iniciar_cena_3d(V, P, cena_luzes)
            renderizador.desenhar_objeto(vbo_piso, MAT_PISO, I)

            for m_borda in bordas:
                renderizador.desenhar_objeto(vbo_cubo, MAT_BORDA, m_borda)

            for u, (x, y, z) in enumerate(estado_jogo.posicoes):
                m_torre = glm.translate(I, glm.vec3(x, y, z)) * m_enq
                mat_torre = MAT_TORRE_A if estado_jogo.graph.X[u] == 0 else MAT_TORRE_B
                renderizador.desenhar_objeto(vbo_torre, mat_torre, m_torre, ibo=ibo_torre)

            alguma_luz_global = cena_luzes.direcional.ativa or luz_movel.ativa
            choques = cena_luzes.choques
            escala_coroa = 1.0 if choques.torres_ativas else (0.14 if alguma_luz_global else 0.0)
            escala_aresta = 1.0 if choques.arestas_ativas else (0.14 if alguma_luz_global else 0.0)

            renderizador.iniciar_linhas_3d(V, P, tempo=tempo_anim)

            if escala_coroa > 0.0:
                for u, (x, y, z) in enumerate(estado_jogo.posicoes):
                    cor_coroa = (
                        COR_COROA_A if estado_jogo.graph.X[u] == 0 else COR_COROA_B
                    ) * escala_coroa
                    m_onda = (
                        glm.translate(I, glm.vec3(x, y + ALTURA_ALVO_MODELO, z))
                        * glm.rotate(
                            I,
                            tempo_anim * 2.2 + u * 0.7 if choques.torres_ativas else 0.0,
                            glm.vec3(0.0, 1.0, 0.0),
                        )
                    )
                    renderizador.desenhar_linha(
                        vbo_onda,
                        m_onda,
                        cor_coroa,
                        modo=moderngl.LINE_LOOP,
                    )

            if escala_aresta > 0.0:
                for u in range(estado_jogo.n):
                    ax, ay, az = estado_jogo.posicoes[u]
                    p_a = glm.vec3(ax, ay + ALTURA_ALVO_MODELO, az)
                    for v in estado_jogo.graph.adj[u]:
                        if u >= v:
                            continue
                        bx, by, bz = estado_jogo.posicoes[v]
                        delta = glm.vec3(bx, by + ALTURA_ALVO_MODELO, bz) - p_a
                        comp = glm.length(delta)
                        if comp < 1e-5:
                            continue
                        m_aresta = (
                            glm.translate(I, p_a)
                            * glm.rotate(I, math.atan2(delta.x, delta.z), glm.vec3(0.0, 1.0, 0.0))
                            * glm.scale(I, glm.vec3(1.0, 1.0, comp))
                        )
                        no_corte = estado_jogo.graph.ta_no_corte(u, v)
                        cor_aresta = (
                            COR_ARESTA_CORTE if no_corte else COR_ARESTA_FORA
                        ) * escala_aresta
                        renderizador.desenhar_linha(
                            vbo_aresta,
                            m_aresta,
                            cor_aresta,
                            modo=moderngl.LINE_STRIP,
                            amp=(0.12 if no_corte else 0.03) if choques.arestas_ativas else 0.0,
                            vel=(18.0 if no_corte else 5.0) if choques.arestas_ativas else 0.0,
                            seed=float(u * 17 + v),
                        )

            larg_tela, alt_tela = glfw.get_framebuffer_size(janela)
            renderizador.iniciar_placar_2d(larg_tela, alt_tela)

            m_arestas = max(1, estado_jogo.graph.m)
            frac_corte = estado_jogo.tam_corte_atual / m_arestas
            frac_meta = estado_jogo.meta / m_arestas
            frac_tempo = estado_jogo.tempo_restante / estado_jogo.tempo_total

            x = PLACAR_MARGEM
            y_corte = alt_tela - PLACAR_MARGEM - PLACAR_ALTURA
            y_tempo = y_corte - PLACAR_ESPACO - PLACAR_ALTURA

            for y, frac, cor in (
                (y_corte, frac_corte, COR_ARESTA_CORTE),
                (y_tempo, frac_tempo, COR_PLACAR_TEMPO),
            ):
                barra = retangulo(x, y, PLACAR_LARGURA, PLACAR_ALTURA)
                cheio = retangulo(x, y, PLACAR_LARGURA * frac, PLACAR_ALTURA)
                renderizador.desenhar_placar_2d(vbo_quad, barra, COR_PLACAR_FUNDO, moderngl.TRIANGLE_FAN)
                renderizador.desenhar_placar_2d(vbo_quad, cheio, cor, moderngl.TRIANGLE_FAN)
                renderizador.desenhar_placar_2d(vbo_quad, barra, COR_PLACAR_MOLDURA, moderngl.LINE_LOOP)

            x_meta = x + PLACAR_LARGURA * frac_meta
            marca = retangulo(x_meta - 1.5, y_corte - 4.0, 3.0, PLACAR_ALTURA + 8.0)
            renderizador.desenhar_placar_2d(vbo_quad, marca, COR_PLACAR_META, moderngl.TRIANGLE_FAN)

            renderizador.finalizar_placar_2d()

            glfw.swap_buffers(janela)
            glfw.poll_events()
    finally:
        renderizador.liberar()
        vbo_torre.release()
        ibo_torre.release()
        vbo_piso.release()
        vbo_cubo.release()
        vbo_onda.release()
        vbo_aresta.release()
        vbo_quad.release()
        glfw.terminate()
        print("Execucao finalizada.")


if __name__ == "__main__":
    main()
