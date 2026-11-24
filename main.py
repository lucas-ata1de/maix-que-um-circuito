import sys
from pathlib import Path

import glfw
import glm
import moderngl
import numpy as np
import camera
import alg

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


def redimensionar(window,w,h):
    ctx.viewport = (0, 0, max(1,w), max(1,h))
    cam.redimensionar(max(1,w), max(1,h))





glfw.init()

glfw.window_hint(glfw.CONTEXT_VERSION_MAJOR, 4)
glfw.window_hint(glfw.CONTEXT_VERSION_MINOR, 0)
glfw.window_hint(glfw.OPENGL_PROFILE, glfw.OPENGL_CORE_PROFILE)
glfw.window_hint(glfw.OPENGL_FORWARD_COMPAT, glfw.TRUE)
glfw.window_hint(glfw.SAMPLES, 4)
glfw.window_hint(glfw.RESIZABLE, True)

cam = camera.Camera()

janela = glfw.create_window(LADO, LADO, "Maix que um circuito", None, None)

glfw.make_context_current(janela)
glfw.swap_interval(1)
ctx = moderngl.create_context()
ctx.enable(moderngl.DEPTH_TEST)
ctx.enable(moderngl.CULL_FACE)

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
    global dt
    if action != glfw.PRESS:
        return
    if key == glfw.KEY_ESCAPE:
        glfw.set_window_should_close(window, True)
    if key == glfw.KEY_C:
        ctx.disable(moderngl.CULL_FACE)
    if key == glfw.KEY_V:
        ctx.enable(moderngl.CULL_FACE)
    if key == glfw.KEY_T:
        cam.alternar_modo()
    
girando,ultimo_x,ultimo_y = False,None,None

def mouse(window, button, action, mods):
    global girando,ultimo_x,ultimo_y

    if button == glfw.MOUSE_BUTTON_RIGHT and action == glfw.RELEASE:
        girando=False
        ultimo_x, ultimo_y = None, None
    if button == glfw.MOUSE_BUTTON_RIGHT and action == glfw.PRESS:
        girando=True
        ultimo_x, ultimo_y = None, None

def cursor(window,xpos,ypos):
    global ultimo_x,ultimo_y
    if not girando:
        return

    if ultimo_x is not None and ultimo_y is not None:
        dx,dy = xpos - ultimo_x , ypos - ultimo_y
        cam.girar(dx,dy)
    ultimo_x,ultimo_y = xpos, ypos
    

def scroll(window,xoffset, yoffset):
    cam.zoom(yoffset)

glfw.set_key_callback(janela, tecla)
glfw.set_mouse_button_callback(janela,mouse)
glfw.set_cursor_pos_callback(janela,cursor)
glfw.set_scroll_callback(janela,scroll)
glfw.set_framebuffer_size_callback(janela, redimensionar)
redimensionar(janela, *glfw.get_framebuffer_size(janela))

# --------------------------------------------------------- laco principal

angulo = 0.0
t_ant = glfw.get_time()

while not glfw.window_should_close(janela):


    ctx.clear(*FUNDO)
    agora = glfw.get_time()
    dt = agora - t_ant
    t_ant = agora

    avancar = float(glfw.get_key(janela, glfw.KEY_W) == glfw.PRESS) - float(glfw.get_key(janela, glfw.KEY_S) == glfw.PRESS)
    lateral = float(glfw.get_key(janela, glfw.KEY_D) == glfw.PRESS) - float(glfw.get_key(janela, glfw.KEY_A) == glfw.PRESS)
    vertical = float(glfw.get_key(janela, glfw.KEY_E) == glfw.PRESS) - float(glfw.get_key(janela, glfw.KEY_Q) == glfw.PRESS)

    cam.mover(avancar, lateral, dt,vertical)
    prog["u_modelo"].write(M_enq.to_bytes())
    prog["u_visao"].write(cam.visao().to_bytes())
    prog["u_projecao"].write(cam.projecao().to_bytes())

    vao_torre.render(moderngl.TRIANGLES)

    glfw.swap_buffers(janela)
    glfw.poll_events()
    glfw.set_window_title(janela,"MAix que um CircUiTo")

glfw.terminate()
print("Execucao finalizada.")
