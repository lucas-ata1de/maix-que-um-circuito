from dataclasses import dataclass
import grafo
import math
import random

class EstadoJogo:
    """Armazena estado atual do jogo, o grafo ,corte atual etc"""
    n: int = 0 
    def __init__(self,n: int =16,meio_lado : float =12,dist_min: float = 4.0):
        self.meio_lado = meio_lado
        self.n = n
        self.dist_min = dist_min
        self.iniciar_fase(n)

    def iniciar_fase(self,n):
        self.meta = 0
        self.tam_corte_atual = 1
        self.tempo_restante = 60.0
        self.estado = "START"
        self.posicoes = sortear_posicoes(n,self.meio_lado,self.dist_min)
        while self.meta <= self.tam_corte_atual:
            self.graph = grafo.sorteia_grafo(n,True,0.35)
            grafo.sorteia_ate_meioaprox(self.graph)
            self.tam_corte_atual = grafo.conta_do_corte(self.graph)
            self.meta = grafo.acha_opt(self.graph)

    def inverter_torre(self, u: int) -> None:
        if self.estado != "PLAYING":
            return
        self.graph.troca_xi(u)
        self.tam_corte_atual = grafo.conta_do_corte(self.graph)
        if self.tam_corte_atual >= self.meta:
            self.estado = "VICTORY"

    def atualizar(self, dt: float) -> None:
        if self.estado != "PLAYING":
            return
        self.tempo_restante = max(0.0, self.tempo_restante - dt)
        if self.tempo_restante <= 0.0:
            self.estado = "GAME_OVER"

    def torre_no_raio(self, o, d, meia_larg: float = 0.45, altura: float = 4) -> int | None:
        melhor, melhor_t = None, math.inf
        for u, (x, y, z) in enumerate(self.posicoes):
            t = raio_aabb(o, d, (x - meia_larg, y, z - meia_larg),
                                (x + meia_larg, y + altura, z + meia_larg))
            if t is not None and t < melhor_t:     # a mais próxima da câmera
                melhor, melhor_t = u, t
        return melhor


def raio_aabb(o, d, bmin, bmax) -> float | None:
    """Método das faixas (slabs): t em que o raio o + t*d entra na caixa, ou None."""
    t_entra, t_sai = 0.0, math.inf
    for i in range(3):                       # eixos x, y, z
        if abs(d[i]) < 1e-9:                 # raio paralelo a esse par de planos
            if not (bmin[i] <= o[i] <= bmax[i]):
                return None
            continue
        t1 = (bmin[i] - o[i]) / d[i]
        t2 = (bmax[i] - o[i]) / d[i]
        if t1 > t2:
            t1, t2 = t2, t1
        t_entra = max(t_entra, t1)
        t_sai = min(t_sai, t2)
        if t_entra > t_sai:
            return None
    return t_entra




def distquad(x0,y0,z0,x,y,z):
    return (x0-x)**2 + (y0-y)**2 + (z0-z)**2;

def sortear_posicoes(n, meio_lado, dist_min):
    lista = []
    margem = 2.0
    limite = meio_lado - margem
    tentativas=0
    while len(lista) < n:
        x = random.uniform(-limite, limite)
        z = random.uniform(-limite, limite)
        if all(distquad(x, 0.0, z, px, py, pz) >= dist_min ** 2 for px, py, pz in lista):
            lista.append((x, 0.0, z))
            tentativas = 0
        else:
            tentativas += 1
            if tentativas > 300:
                dist_min *= 0.9
                tentativas = 0
    return lista

