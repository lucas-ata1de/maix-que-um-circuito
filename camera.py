import math
import glm

FOVY = 45.0
NEAR = 0.1
FAR = 150.0
PITCH_MAX = math.radians(85.0)
ALTURA_AEREA_MIN = 4.0
ALTURA_AEREA_MAX = 60.0


class Camera:
    def __init__(self, pos=(0.0, 2.5, 5.0), altura_aerea=18.0):
        self.pos = glm.vec3(*pos)
        self.yaw = -math.pi / 2.0
        self.pitch = -0.3
        self.cima = glm.vec3(0.0, 1.0, 0.0)

        self.modo = "livre"
        self.altura_aerea = float(altura_aerea)
        self.centro_aereo = glm.vec3(0.0, 0.0, 0.0)

        self.velocidade = 6.0
        self.sensibilidade = 0.005

        self.aspecto = 1.0
        self.fovy = glm.radians(FOVY)
        self.near = NEAR
        self.far = FAR
        self.perspectiva = True

    def frente(self) -> glm.vec3:
        return glm.normalize(glm.vec3(
            math.cos(self.pitch) * math.cos(self.yaw),
            math.sin(self.pitch),
            math.cos(self.pitch) * math.sin(self.yaw),
        ))

    def direita(self) -> glm.vec3:
        return glm.normalize(glm.cross(self.frente(), self.cima))

    def redimensionar(self, largura: int, altura: int) -> None:
        self.aspecto = float(largura) / float(max(altura, 1))

    def alternar_modo(self) -> str:
        self.modo = "aerea" if self.modo == "livre" else "livre"
        return self.modo

    def mover(self, avancar: float, lateral: float, dt: float, vertical: float = 0.0) -> None:
        if self.modo != "livre":
            return
        desloc = (
            self.frente() * avancar
            + self.direita() * lateral
            + self.cima * vertical
        )
        if glm.length(desloc) > 1e-6:
            self.pos += glm.normalize(desloc) * (self.velocidade * dt)

    def girar(self, dx: float, dy: float) -> None:
        if self.modo != "livre":
            return
        self.yaw += dx * self.sensibilidade
        self.pitch = max(-PITCH_MAX, min(PITCH_MAX, self.pitch - dy * self.sensibilidade))

    def zoom(self, yoffset: float) -> None:
        if self.modo == "livre":
            self.pos += self.frente() * (yoffset * 0.8)
        else:
            self.altura_aerea = max(
                ALTURA_AEREA_MIN,
                min(ALTURA_AEREA_MAX, self.altura_aerea - yoffset * 1.2),
            )

    def visao(self) -> glm.mat4:
        if self.modo == "livre":
            return glm.lookAt(self.pos, self.pos + self.frente(), self.cima)
        olho_aereo = self.centro_aereo + glm.vec3(0.0, self.altura_aerea, 0.01)
        return glm.lookAt(olho_aereo, self.centro_aereo, self.cima)

    def projecao(self) -> glm.mat4:
        if self.perspectiva:
            return glm.perspective(self.fovy, self.aspecto, self.near, self.far)
        dist = self.altura_aerea if self.modo == "aerea" else max(1.0, glm.length(self.pos))
        t = dist * math.tan(self.fovy / 2.0)
        r = t * self.aspecto
        return glm.ortho(-r, r, -t, t, self.near, self.far)
