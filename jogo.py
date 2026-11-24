from dataclasses import dataclass
import grafo
import random

@dataclass
class EstadoJogo:
    """Armazena estado atual do jogo, o grafo ,corte atual etc"""
    n = 0
    graph = grafo.sorteia_grafo(n)
    corte_atual = graph.X
    meta = grafo.acha_opt(graph)
    tempo_restante = 30
    estado = "START"





def distquad(x0,y0,z0,x,y,z):
    return (x0-x)**2 + (y0-y)**2 + (z0-z)**2;

def sortear_posicoes(n, meio_lado, dist_min):
    lista = []
    margem = 2.0
    limite = meio_lado - margem
    for i in range(n):
        (x,y,z) = (random.uniform(-limite,limite),0,random.uniform(-limite,limite))
        denovo = False
        for j in range(i):
            if distquad(x,y,z,lista[j][0],lista[j][1],lista[j][2]) < dist_min**2:
                denovo=True
        if denovo:
            i-=1
        else:
            lista.append((x,y,z))

