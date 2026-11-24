import sys
from pathlib import Path

import glfw
import glm
import moderngl
import numpy as np

SHADERS = Path(__file__).parent / "shaders"
CAMINHO = Path(__file__).parent/"offs"/"torre.off"
LADO = 700
FUNDO = (0.10, 0.11, 0.13, 1.0)

#LEITURA DO MODELO OFF 
def ler_off(caminho):
    campos = []
    for linha in Path(caminho).read_text(encoding="utf-8").splitlines():
        linha = linha.split("#")[0].strip()    # comentario ate o fim da linha
        if linha:
            campos.extend(linha.split())

    n_vertices, n_faces = int(campos[1]), int(campos[2])
    p = 4
    vertices = np.array(campos[p:p + 3 * n_vertices],
                        dtype='f4').reshape(n_vertices, 3)
    p += 3 * n_vertices

    indices = np.empty((n_faces, 3), dtype='u4')
    for i in range(n_faces):
        lados = int(campos[p])
        if lados != 3:
            raise ValueError(f"{caminho}: face {i} tem {lados} lados; "
                             "este leitor so aceita triangulos")
        indices[i] = campos[p + 1:p + 4]
        p += 1 + lados

    return vertices, indices


# ------------------------------------------------------------ geometria


# ------------------------------------------------------------ inicializacao


glfw.init()

glfw.window_hint(glfw.CONTEXT_VERSION_MAJOR, 4)
glfw.window_hint(glfw.CONTEXT_VERSION_MINOR, 0)
glfw.window_hint(glfw.OPENGL_PROFILE, glfw.OPENGL_CORE_PROFILE)
glfw.window_hint(glfw.OPENGL_FORWARD_COMPAT, glfw.TRUE)
glfw.window_hint(glfw.SAMPLES, 4)
glfw.window_hint(glfw.RESIZABLE, False)

janela = glfw.create_window(LADO, LADO, "Maix que um circuito", None, None)
posicoes, indices = ler_off(CAMINHO)

minimo,maximo = posicoes.min(axis=0), posicoes.max(axis=0)
centro = (minimo + maximo)/2
escala = 1/(maximo[1]-minimo[1])*1.8
M_enq = (glm.scale(glm.mat4(1.0),glm.vec3(escala)) * glm.translate(glm.mat4(1.0),glm.vec3(*(-centro))))

tri_pos = posicoes[indices]
n_face = np.cross(tri_pos[:, 1] - tri_pos[:, 0], tri_pos[:, 2] - tri_pos[:, 1])
n_face /= np.maximum(np.linalg.norm(n_face, axis=1, keepdims=True), 1e-12)
tri_nor = np.repeat(n_face[:, None, :], 3, axis=1) 
dados = np.concatenate([tri_pos, tri_nor], axis=2).astype("f4")


glfw.make_context_current(janela)
glfw.swap_interval(1)
ctx = moderngl.create_context()
ctx.enable(moderngl.DEPTH_TEST)
ctx.enable(moderngl.CULL_FACE)

prog = ctx.program(
    vertex_shader=(SHADERS / "shader.vert").read_text(encoding="utf-8"),
    fragment_shader=(SHADERS / "shader.frag").read_text(encoding="utf-8"),
)

vbo_torre = ctx.buffer(dados.tobytes())
vao_torre = ctx.vertex_array(prog, [(vbo_torre,"3f 3f","vPosition","vNorm")])


visao = glm.lookAt(glm.vec3(1.5, 0.8, 2.0), glm.vec3(0.0, 0.0, 0.0), glm.vec3(0.0, 1.0, 0.0))
proj = glm.perspective(glm.radians(45.0), 1.0, 0.1, 100.0)
prog["u_visao"].write(visao.to_bytes())
prog["u_projecao"].write(proj.to_bytes())




def tecla(window, key, scancode, action, mods):
    if action != glfw.PRESS:
        return
    if key == glfw.KEY_ESCAPE:
        glfw.set_window_should_close(window, True)
    if key == glfw.KEY_C:
        ctx.disable(moderngl.CULL_FACE)
    if key == glfw.KEY_V:
        ctx.enable(moderngl.CULL_FACE)


glfw.set_key_callback(janela, tecla)

# --------------------------------------------------------- laco principal

angulo = 0.0
t_ant = glfw.get_time()

while not glfw.window_should_close(janela):


    ctx.clear(*FUNDO)
    agora = glfw.get_time()
    dt = agora - t_ant
    t_ant = agora
    angulo += 0.8 * dt

    modelo = glm.rotate(glm.mat4(1.0), angulo, glm.vec3(0.0, 1.0, 0.0)) * M_enq
    prog["u_modelo"].write(modelo.to_bytes())
    vao_torre.render(moderngl.TRIANGLES)

    glfw.swap_buffers(janela)
    glfw.poll_events()
    glfw.set_window_title(janela,"MAix que um CircUiTo")

glfw.terminate()
print("Execucao finalizada.")
