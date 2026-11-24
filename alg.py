import random
from collections import deque

class Graph:
    def __init__(self,n,m=0,X=[]) -> None:
        self.n=n
        self.m=m
        self.adj=[[] for _ in range(n)]
        self.X = sorteia_postes(self.n)
    
    def add_edge(self,u,v):
        self.adj[u].append(v)
        self.adj[v].append(u)
        self.m+=1
   
    def printG(self):
        for i in range(self.n):
            for j in self.adj[i]:
                if(i>j):
                    print(i,j)

    def troca_xi(self,xi):
        self.X[xi] ^= 1

    def ta_no_corte(self,u,v):
        return (self.X[u] ^ self.X[v] == 1)

def conecta(grafo):
    n = grafo.n
    componentes = []
    visitado = [False] * n
    for i in range(n):
        componente = []
        if visitado[i]:
            continue

        fila = deque([i])
        visitado[i]=True
        while fila:
            u=fila.popleft()
            componente.append(u)
            for v in grafo.adj[u]:
                if not visitado[v]:
                    visitado[v]=True
                    fila.append(v)
        componentes.append(componente)

    if len(componentes)<=1:
        return (grafo,False)
    
    for i in range(len(componentes)-1):
        u,v = random.choices(componentes[i])[0],random.choices(componentes[i+1])[0] # escolhe 1 vértice e cada componente e liga com outra componente
        grafo.add_edge(u,v)
    return (grafo,True)

def sorteia_postes(n): #retorna uma lista de 0's e 1's, dizendo se o i-esimo poste está incluso
    lista = []
    for i in range(n):
        xi = random.randint(0,1)
        lista.append(xi)
    return lista

def acha_opt(grafo): # algoritmo que roda 10 vezes fazendo uma escola gulosa de trocar 
    opt = 0
    X_original= list(grafo.X)
    for i in range(10):
        grafo = sorteia_ate_meioaprox(grafo)
        curr = conta_do_corte(grafo)
        trocou= True
        while trocou:
            trocou=False
            for i in range(grafo.n):
                inX,outX,X = 0,0,grafo.X
                for j in grafo.adj[i]:
                    inX+= 1 if X[j]==1 else 0
                    outX+= 1 if X[j]==0 else 0

                if (X[i]==1 and inX>outX) or (X[i]==0 and outX>inX):
                    curr+=abs(inX-outX)
                    grafo.troca_xi(i)
                    trocou=True
            
        opt = max(opt,curr)
    grafo.X= X_original
    return opt


def conta_do_corte(grafo):
    adj = grafo.adj
    n = grafo.n
    qtd=0
    for i in range(n):
        for j in adj[i]:
            qtd+= 1 if grafo.ta_no_corte(i,j) else 0

    return qtd//2 #contamos cada aresta 2 vezes, lema do aperto de mãos

def sorteia_ate_meioaprox(grafo:Graph):
    n,m = grafo.n,grafo.m
    grafo.X = sorteia_postes(n)
    while conta_do_corte(grafo) < m/2:
        grafo.X = sorteia_postes(n)
    return grafo

def sorteia_grafo(n: int,conexo=True, p=0.5 ) -> Graph: #retorna um grafo aleatorio conexo com distribuição de probabilidade p de sucesso e (1-p) de fracasso
    grafo = Graph(n)
    for i in range(n):
        for j in  range(i+1,n):
            if random.random()<p:
                grafo.add_edge(i,j)
    return conecta(grafo)[0] if conexo else grafo
    



grafo = sorteia_grafo(10,True)
grafo.printG()
print(conta_do_corte(grafo))
print(grafo.X)
print(acha_opt(grafo))





