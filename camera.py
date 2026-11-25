"""Controle de câmera 3D (modos livre e aéreo) para a cena ModernGL."""

import math

import glm

FOVY = 45.0
NEAR = 0.1
FAR = 150.0
PITCH_MAX = math.radians(85.0)
ALTURA_AEREA_MIN = 4.0
ALTURA_AEREA_MAX = 60.0

POSICAO_INICIAL = (0.0, 2.5, 5.0)
ALTURA_AEREA_INICIAL = 18.0
YAW_INICIAL = -math.pi / 2.0
PITCH_INICIAL = -0.3
VELOCIDADE_PADRAO = 6.0
SENSIBILIDADE_MOUSE = 0.005
PASSO_ZOOM_LIVRE = 0.8
PASSO_ZOOM_AEREO = 1.2
EPSILON = 1e-6
OFFSET_Z_AEREO = 0.2


class Camera:
    """Câmera 3D com navegação livre (FPS) e visão aérea."""

    def __init__(
        self,
        pos: tuple[float, float, float] = POSICAO_INICIAL,
        altura_aerea: float = ALTURA_AEREA_INICIAL,
    ) -> None:
        self.pos = glm.vec3(*pos)
        self.yaw = YAW_INICIAL
        self.pitch = PITCH_INICIAL
        self.cima = glm.vec3(0.0, 1.0, 0.0)

        self.modo = "livre"
        self.altura_aerea = float(altura_aerea)
        self.centro_aereo = glm.vec3(0.0, 0.0, 0.0)

        self.velocidade = VELOCIDADE_PADRAO
        self.sensibilidade = SENSIBILIDADE_MOUSE

        self.aspecto = 1.0
        self.fovy = glm.radians(FOVY)
        self.near = NEAR
        self.far = FAR
        self.perspectiva = True

    def frente(self) -> glm.vec3:
        """Retorna o vetor unitário na direção para onde a câmera aponta."""
        return glm.normalize(
            glm.vec3(
                math.cos(self.pitch) * math.cos(self.yaw),
                math.sin(self.pitch),
                math.cos(self.pitch) * math.sin(self.yaw),
            )
        )

    def direita(self) -> glm.vec3:
        """Retorna o vetor unitário à direita da direção atual da câmera."""
        return glm.normalize(glm.cross(self.frente(), self.cima))

    def redimensionar(self, largura: int, altura: int) -> None:
        """Atualiza a razão de aspecto conforme o tamanho do framebuffer."""
        self.aspecto = float(largura) / float(max(altura, 1))

    def alternar_modo(self) -> str:
        """Alterna entre os modos 'livre' e 'aerea' e retorna o modo ativo."""
        self.modo = "aerea" if self.modo == "livre" else "livre"
        return self.modo

    def mover(
        self,
        avancar: float,
        lateral: float,
        dt: float,
        vertical: float = 0.0,
    ) -> None:
        """Desloca a câmera no modo livre usando deslocamento normalizado."""
        if self.modo != "livre":
            return
        direcao_frente = self.frente()
        desloc = (
            glm.vec3(direcao_frente.x, 0.0, direcao_frente.z) * avancar
            + self.direita() * lateral
            + self.cima * vertical
        )
        if glm.length(desloc) > EPSILON:
            self.pos += glm.normalize(desloc) * (self.velocidade * dt)

    def girar(self, dx: float, dy: float) -> None:
        """Atualiza yaw e pitch no modo livre com limite vertical de pitch."""
        if self.modo != "livre":
            return
        self.yaw += dx * self.sensibilidade
        novo_pitch = self.pitch - dy * self.sensibilidade
        self.pitch = max(-PITCH_MAX, min(PITCH_MAX, novo_pitch))

    def zoom(self, yoffset: float) -> None:
        """Aproxima ou afasta a câmera conforme o modo ativo."""
        if self.modo == "livre":
            self.pos += self.frente() * (yoffset * PASSO_ZOOM_LIVRE) 
        else:
            nova_altura = self.altura_aerea - yoffset * PASSO_ZOOM_AEREO
            self.altura_aerea = max(
                ALTURA_AEREA_MIN,
                min(ALTURA_AEREA_MAX, nova_altura),
            )

    def visao(self) -> glm.mat4:
        """Calcula e retorna a matriz de visão (view)."""
        if self.modo == "livre":
            return glm.lookAt(self.pos, self.pos + self.frente(), self.cima)
        olho_aereo = self.centro_aereo + glm.vec3(
            0.0, self.altura_aerea, OFFSET_Z_AEREO
        )
        return glm.lookAt(olho_aereo, self.centro_aereo, self.cima)

    def projecao(self) -> glm.mat4:
        """Calcula e retorna a matriz de projeção (perspectiva ou ortográfica)."""
        if self.perspectiva:
            return glm.perspective(self.fovy, self.aspecto, self.near, self.far)
        dist = (
            self.altura_aerea
            if self.modo == "aerea"
            else max(1.0, glm.length(self.pos))
        )
        topo = dist * math.tan(self.fovy / 2.0)
        direita = topo * self.aspecto
        return glm.ortho(-direita, direita, -topo, topo, self.near, self.far)
    
    def raio(self, mx: float, my: float, largura: int, altura: int) -> tuple[glm.vec3, glm.vec3]:
        """Raio no mundo que passa pelo ponto (mx, my) da janela."""
        x = 2.0 * mx / largura - 1.0          # pixel -> NDC
        y = 1.0 - 2.0 * my / altura           # GLFW tem y para baixo; NDC tem y para cima
        inv = glm.inverse(self.projecao() * self.visao())
        perto = inv * glm.vec4(x, y, -1.0, 1.0)   # ponto no plano near
        longe = inv * glm.vec4(x, y, 1.0, 1.0)    # ponto no plano far
        perto = glm.vec3(perto) / perto.w         # divisão perspectiva, agora ao contrário
        longe = glm.vec3(longe) / longe.w
        return perto, glm.normalize(longe - perto)


if __name__ == "__main__":
    cam = Camera()
    cam.redimensionar(800, 600)
    cam.mover(1.0, 0.0, 0.1)
    cam.girar(10.0, -5.0)
    cam.zoom(1.0)
    assert cam.alternar_modo() == "aerea"
    cam.zoom(1.0)
    _ = cam.visao()
    _ = cam.projecao()
    print("Camera: validação básica concluída com sucesso.")
