"""Estrutura de grafo e heurísticas probabilísticas para Max-Cut."""

import random
from collections import deque

NUM_REINICIOS_OPT = 10
PROB_ARESTA_PADRAO = 0.5


class Graph:
    """Grafo não-direcionado com partição binária X associada aos vértices."""

    def __init__(
        self,
        n: int,
        m: int = 0,
        X: list[int] | None = None,
    ) -> None:
        self.n: int = n
        self.m: int = m
        self.adj: list[list[int]] = [[] for _ in range(n)]
        self.X: list[int] = list(X) if X is not None else sorteia_postes(self.n)

    def add_edge(self, u: int, v: int) -> None:
        """Adiciona uma aresta não-direcionada entre os vértices u e v."""
        self.adj[u].append(v)
        self.adj[v].append(u)
        self.m += 1

    def printG(self) -> None:
        """Imprime todas as arestas do grafo sem duplicidade."""
        for i in range(self.n):
            for j in self.adj[i]:
                if i > j:
                    print(i, j)

    def troca_xi(self, xi: int) -> None:
        """Inverte o lado da partição (0 <-> 1) do vértice xi."""
        self.X[xi] ^= 1

    def ta_no_corte(self, u: int, v: int) -> bool:
        """Retorna True se os vértices u e v pertencem a lados opostos do corte."""
        return (self.X[u] ^ self.X[v]) == 1


def conecta(grafo: Graph) -> tuple[Graph, bool]:
    """Garante conexidade ligando componentes conexas com arestas aleatórias."""
    n = grafo.n
    componentes: list[list[int]] = []
    visitado = [False] * n

    for i in range(n):
        if visitado[i]:
            continue

        componente: list[int] = []
        fila = deque([i])
        visitado[i] = True
        while fila:
            u = fila.popleft()
            componente.append(u)
            for v in grafo.adj[u]:
                if not visitado[v]:
                    visitado[v] = True
                    fila.append(v)
        componentes.append(componente)

    if len(componentes) <= 1:
        return grafo, False

    for i in range(len(componentes) - 1):
        u = random.choices(componentes[i])[0]
        v = random.choices(componentes[i + 1])[0]
        grafo.add_edge(u, v)

    return grafo, True


def sorteia_postes(n: int) -> list[int]:
    """Sorteia uma lista binária (0 ou 1) indicando a partição de cada poste."""
    return [random.randint(0, 1) for _ in range(n)]


def conta_do_corte(grafo: Graph) -> int:
    """Conta quantas arestas atravessam o corte definido pela partição atual."""
    qtd = 0
    for i in range(grafo.n):
        for j in grafo.adj[i]:
            if grafo.ta_no_corte(i, j):
                qtd += 1
    return qtd // 2  # cada aresta é contada duas vezes (lema do aperto de mãos)


def sorteia_ate_meioaprox(grafo: Graph) -> Graph:
    """Sorteia partições aleatórias até atingir um corte de pelo menos m/2."""
    n, m = grafo.n, grafo.m
    grafo.X = sorteia_postes(n)
    while conta_do_corte(grafo) < m / 2:
        grafo.X = sorteia_postes(n)
    return grafo


def acha_opt(grafo: Graph) -> int:
    """Executa busca local gulosa com reinícios aleatórios para estimar o Max-Cut."""
    opt = 0
    x_original = list(grafo.X)

    for _ in range(NUM_REINICIOS_OPT):
        grafo = sorteia_ate_meioaprox(grafo)
        curr = conta_do_corte(grafo)
        trocou = True

        while trocou:
            trocou = False
            for i in range(grafo.n):
                in_x = 0
                out_x = 0
                x_atual = grafo.X
                for j in grafo.adj[i]:
                    if x_atual[j] == 1:
                        in_x += 1
                    else:
                        out_x += 1

                if (x_atual[i] == 1 and in_x > out_x) or (
                    x_atual[i] == 0 and out_x > in_x
                ):
                    curr += abs(in_x - out_x)
                    grafo.troca_xi(i)
                    trocou = True

        opt = max(opt, curr)

    grafo.X = x_original
    return opt


def sorteia_grafo(
    n: int,
    conexo: bool = True,
    p: float = PROB_ARESTA_PADRAO,
) -> Graph:
    """Gera um grafo aleatório G(n, p), opcionalmente forçando conexidade."""
    grafo = Graph(n)
    for i in range(n):
        for j in range(i + 1, n):
            if random.random() < p:
                grafo.add_edge(i, j)
    return conecta(grafo)[0] if conexo else grafo


if __name__ == "__main__":
    grafo = sorteia_grafo(10, True)
    grafo.printG()
    print(conta_do_corte(grafo))
    print(grafo.X)
    print(acha_opt(grafo))
