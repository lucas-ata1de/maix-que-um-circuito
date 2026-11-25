"""Gera as capturas do relatorio rodando o jogo de verdade.

O script importa main.py, intercepta algumas funcoes (glfw.swap_buffers,
set_window_title, callbacks) e, em instantes fixos, aciona as mesmas teclas
que o jogador usaria, chamando os callbacks registrados pelo proprio jogo.
Cada captura e o backbuffer lido com ctx.screen.read() logo antes do swap,
com o texto da barra de titulo daquele instante desenhado acima da imagem.

Uso (de dentro de relatorio/):  python capturas.py
"""
import os
import random
import re
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
FIG = Path(__file__).resolve().parent / "figuras"
sys.path.insert(0, str(RAIZ))
os.chdir(RAIZ)

import glfw  # noqa: E402
import glm  # noqa: E402
import moderngl  # noqa: E402
from PIL import Image, ImageDraw, ImageFont  # noqa: E402

import camera  # noqa: E402
import grafo  # noqa: E402
import jogo  # noqa: E402
import main  # noqa: E402

FIG.mkdir(exist_ok=True)
ref: dict = {"titulo": "", "medidas": {}}

# ---------- interceptacoes ----------
_create_context = moderngl.create_context
_set_title = glfw.set_window_title
_set_key = glfw.set_key_callback
_swap = glfw.swap_buffers
_should_close = glfw.window_should_close


def create_context(*a, **k):
    ref["ctx"] = _create_context(*a, **k)
    return ref["ctx"]


def set_title(janela, txt):
    ref["titulo"] = txt
    _set_title(janela, txt)


def set_key(janela, cb):
    ref["tecla"] = cb
    return _set_key(janela, cb)


class EstadoJogoCapturado(jogo.EstadoJogo):
    def __init__(self, *a, **k):
        super().__init__(*a, **k)
        ref["jogo"] = self


class CameraCapturada(camera.Camera):
    def __init__(self, *a, **k):
        super().__init__(*a, **k)
        ref["cam"] = self


moderngl.create_context = create_context
glfw.set_window_title = set_title
glfw.set_key_callback = set_key
jogo.EstadoJogo = EstadoJogoCapturado
camera.Camera = CameraCapturada


# ---------- acoes ----------
def tecla(janela, key):
    ref["tecla"](janela, key, 0, glfw.PRESS, 0)


def fps_do_titulo():
    m = re.search(r"([\d.]+) FPS", ref["titulo"])
    return float(m.group(1)) if m else float("nan")


def capturar(nome):
    ctx = ref["ctx"]
    w, h = ctx.screen.width, ctx.screen.height
    img = Image.frombytes("RGB", (w, h), ctx.screen.read(components=3))
    img = img.transpose(Image.FLIP_TOP_BOTTOM).resize((720, 720 * h // w))
    try:
        fonte = ImageFont.truetype("DejaVuSans.ttf", 14)
    except OSError:
        fonte = ImageFont.load_default()
    partes = ref["titulo"].split(" | ")
    meio = (len(partes) + 1) // 2
    texto = " | ".join(partes[:meio]) + ("\n" + " | ".join(partes[meio:]) if meio < len(partes) else "")
    final = Image.new("RGB", (img.width, img.height + 46), (40, 42, 48))
    ImageDraw.Draw(final).multiline_text((8, 5), texto, fill=(235, 235, 235), font=fonte, spacing=3)
    final.paste(img, (0, 46))
    final.save(FIG / f"{nome}.jpg", quality=90)
    print("capturado:", nome, "|", ref["titulo"])


def vista_padrao():
    cam = ref["cam"]
    cam.pos = glm.vec3(0.0, 9.0, 11.0)
    cam.yaw, cam.pitch = -1.5708, -0.45


def vista_textura():
    """Aproxima a camera da torre mais perto do centro."""
    cam, e = ref["cam"], ref["jogo"]
    x, _, z = min(e.posicoes, key=lambda p: p[0] ** 2 + p[2] ** 2)
    cam.pos = glm.vec3(x + 1.0, 2.2, z + 6.0)
    cam.yaw, cam.pitch = -1.75, 0.05


def quase_vitoria_e_clique():
    """Monta uma particao a 1 inversao da meta e faz a inversao pela regra do jogo."""
    e = ref["jogo"]
    g = e.graph
    for _ in range(5000):
        g.X = [random.randint(0, 1) for _ in range(g.n)]
        melhorou = True
        while melhorou:
            melhorou = False
            for u in range(g.n):
                if sum(1 if g.X[u] == g.X[v] else -1 for v in g.adj[u]) > 0:
                    g.X[u] ^= 1
                    melhorou = True
        if grafo.conta_do_corte(g) >= e.meta:
            break
    for u in range(g.n):
        g.X[u] ^= 1
        if grafo.conta_do_corte(g) < e.meta:
            break
        g.X[u] ^= 1
    e.tam_corte_atual = grafo.conta_do_corte(g)
    e.inverter_torre(u)


def passo_inicio(j):
    vista_padrao()


def passo_vsync_off(j):
    ref["medidas"]["fps_vsync_on"] = fps_do_titulo()
    capturar("inicio")
    tecla(j, glfw.KEY_Y)


def passo_vsync_on(j):
    ref["medidas"]["fps_vsync_off"] = fps_do_titulo()
    tecla(j, glfw.KEY_Y)
    tecla(j, glfw.KEY_ENTER)


def passo_jogando(j):
    capturar("jogando")
    tecla(j, glfw.KEY_T)


def passo_aerea(j):
    capturar("camera_aerea")
    tecla(j, glfw.KEY_T)
    tecla(j, glfw.KEY_2)


def passo_luz_dir(j):
    capturar("luz_direcional")
    tecla(j, glfw.KEY_2)
    tecla(j, glfw.KEY_1)


def passo_luz_pont(j):
    capturar("luz_pontual")
    tecla(j, glfw.KEY_1)
    vista_textura()


def passo_textura(j):
    capturar("texturas")
    vista_padrao()
    tecla(j, glfw.KEY_P)


def passo_pausa(j):
    capturar("pausa")
    tecla(j, glfw.KEY_P)
    ref["jogo"].tempo_restante = 0.01


def passo_derrota(j):
    capturar("derrota")
    tecla(j, glfw.KEY_R)
    tecla(j, glfw.KEY_ENTER)


def passo_clique_vitoria(j):
    quase_vitoria_e_clique()


def passo_vitoria(j):
    capturar("vitoria")
    ref["fim"] = True


ROTEIRO = [
    (0.3, passo_inicio), (2.0, passo_vsync_off), (4.0, passo_vsync_on),
    (5.5, passo_jogando), (6.5, passo_aerea), (7.5, passo_luz_dir),
    (8.5, passo_luz_pont), (9.5, passo_textura), (10.5, passo_pausa),
    (11.5, passo_derrota), (13.5, passo_clique_vitoria), (14.0, passo_vitoria),
]


def swap(janela):
    if "t0" not in ref:
        ref["t0"], ref["i"] = glfw.get_time(), 0
    t = glfw.get_time() - ref["t0"]
    while ref["i"] < len(ROTEIRO) and t >= ROTEIRO[ref["i"]][0]:
        ROTEIRO[ref["i"]][1](janela)
        ref["i"] += 1
    _swap(janela)


glfw.swap_buffers = swap
glfw.window_should_close = lambda j: ref.get("fim", False) or _should_close(j)

if __name__ == "__main__":
    main.main()
    print("medidas:", ref["medidas"])
