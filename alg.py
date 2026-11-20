import random

class Graph:
    def __init__(self,n,m=0,X=[]) -> None:
        self.n=n
        self.m=m
        self.adj=[[] for _ in range(n)]
        self.X = [0]*n if not X else X
    
    def add_edge(self,u,v):
        self.adj[u].append(v)
        self.adj[v].append(u)
        self.m+=1

    def get_n(self):
        return self.n

    def get_m(self):
        return self.m
    
    def get_adj(self):
        return self.adj
    
    def get_X(self):
        return self.X

    def set_X(self,X: list):
        self.X=X
    
    def printG(self):
        for i in range(self.get_n()):
            for j in self.get_adj()[i]:
                if(i>j):
                    print(i,j)

    def troca_xi(self,xi):
        self.X[xi] = not self.X[xi]

    def ta_no_corte(self,u,v):
        return (self.X[u] ^ self.X[v] == 1)



def sorteia_postes(n): #retorna uma lista de 0's e 1's, dizendo se o i-esimo poste está incluso
    lista = []
    for i in range(n):
        xi = random.randint(0,1)
        lista.append(xi)
    return lista

def conta_do_corte(grafo):
    adj = grafo.get_adj()
    n = grafo.get_n()
    qtd=0
    for i in range(n):
        for j in adj[i]:
            qtd+= 1 if grafo.ta_no_corte(i,j) else 0

    return qtd//2 #contamos cada aresta 2 vezes, lema do aperto de mãos
def sorteia_ate_meioaprox(grafo):
    n,m = grafo.get_n(),grafo.get_m()
    while conta_do_corte(grafo) < m/2:
        grafo.set_X(sorteia_postes(n))
    return grafo

def sorteia_grafo(n: int, p=0.5 ) -> Graph: #retorna um grafo aleatorio com distribuição de probabilidade p de sucesso e (1-p) de fracasso
    grafo = Graph(n)
    for i in range(n):
        for j in  range(i+1,n):
            xi = random.choices([0,1],weights=[1-p,p])[0] #isso sorteia xi da lista [0,1] com a distribuição [1-p,p]
            if xi==1:
                grafo.add_edge(i,j)
    return grafo



grafo = sorteia_grafo(4)
grafo.printG()





