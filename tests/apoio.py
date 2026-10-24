"""Objetos de teste do contrato; nunca usados pela aplicação ou como medições reais."""

from modelos import Paciente


class ArvoreTeste:
    """Coleção simples para verificar chamadas, sem implementar uma árvore."""

    def __init__(self):
        self.dados: dict[int, Paciente] = {}
        self.chamadas = []
        self.detalhado = False
        self.valida = True
        self.contadores = {"rotacoes_insercao": 0, "rotacoes_remocao": 0,
                           "nos_visitados_ultima_busca": 0}

    def inserir(self, paciente):
        self.chamadas.append(("inserir", paciente.prontuario))
        if paciente.prontuario in self.dados:
            return False
        self.dados[paciente.prontuario] = paciente
        self.contadores["rotacoes_insercao"] += 1
        return True

    def buscar(self, prontuario):
        self.chamadas.append(("buscar", prontuario))
        self.contadores["nos_visitados_ultima_busca"] = 2
        return self.dados.get(prontuario)

    def remover(self, prontuario):
        self.chamadas.append(("remover", prontuario))
        if prontuario not in self.dados:
            return False
        del self.dados[prontuario]
        self.contadores["rotacoes_remocao"] += 1
        return True

    def minimo(self):
        return min(self.dados.values(), key=lambda p: p.prontuario, default=None)

    def maximo(self):
        return max(self.dados.values(), key=lambda p: p.prontuario, default=None)

    def em_ordem(self):
        return sorted(self.dados.values(), key=lambda p: p.prontuario)

    def pre_ordem(self):
        return list(self.dados.values())

    def pos_ordem(self):
        return list(reversed(self.pre_ordem()))

    def altura(self):
        return 0 if self.dados else -1

    def quantidade(self):
        return len(self.dados)

    def exibir(self):
        return "Estrutura do objeto de teste"

    def validar(self):
        return self.valida

    def estatisticas(self):
        return self.contadores.copy()

    def definir_modo_detalhado(self, ativo):
        self.detalhado = ativo

    def reiniciar_estatisticas(self):
        self.contadores = dict.fromkeys(self.contadores, 0)


def fabricas_teste():
    """Retorna duas fábricas independentes e o registro das instâncias criadas."""
    instancias = {"AVL": [], "Rubro-Negra": []}

    def fabrica(nome):
        def criar():
            arvore = ArvoreTeste()
            instancias[nome].append(arvore)
            return arvore
        return criar

    return {nome: fabrica(nome) for nome in instancias}, instancias
