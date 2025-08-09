from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, List, Tuple
from uuid import uuid4
import hashlib
import json


@dataclass
class Ordem:
    """Representa uma ordem de compra ou venda."""

    id: str
    usuario_id: str
    ativo: str
    quantidade: int
    preco: float
    lado: str  # 'compra' ou 'venda'
    timestamp: datetime = field(default_factory=datetime.utcnow)


@dataclass
class Bloco:
    indice: int
    timestamp: datetime
    transacoes: List[Tuple[str, str, str, int, float]]
    hash_anterior: str
    hash: str


class Blockchain:
    """Cadeia simples de blocos para registrar negociações."""

    def __init__(self) -> None:
        genesis = Bloco(0, datetime.utcnow(), [], "0", "0")
        self.cadeia: List[Bloco] = [genesis]

    def adicionar_bloco(
        self, transacoes: List[Tuple[str, str, str, int, float]]
    ) -> Bloco:
        indice = len(self.cadeia)
        hash_anterior = self.cadeia[-1].hash
        timestamp = datetime.utcnow()
        conteudo = {
            "indice": indice,
            "timestamp": timestamp.isoformat(),
            "transacoes": transacoes,
            "hash_anterior": hash_anterior,
        }
        bloco_hash = hashlib.sha256(
            json.dumps(conteudo, sort_keys=True).encode()
        ).hexdigest()
        bloco = Bloco(indice, timestamp, transacoes, hash_anterior, bloco_hash)
        self.cadeia.append(bloco)
        return bloco


class BolsaValores:
    """Sistema simples de bolsa de valores com registro em blockchain."""

    def __init__(self) -> None:
        self.usuarios: Dict[str, float] = {}
        self.carteiras: Dict[str, Dict[str, int]] = {}
        self.livros: Dict[str, Dict[str, List[Ordem]]] = {}
        self.blockchain = Blockchain()

    def registrar_usuario(self, saldo_inicial: float) -> str:
        """Registra um novo usuário com saldo inicial."""
        usuario_id = str(uuid4())
        self.usuarios[usuario_id] = saldo_inicial
        self.carteiras[usuario_id] = {}
        return usuario_id

    def registrar_ativo(self, simbolo: str) -> None:
        """Garante que o ativo esteja registrado no livro de ordens."""
        if simbolo not in self.livros:
            self.livros[simbolo] = {"compra": [], "venda": []}

    def enviar_ordem(
        self, usuario_id: str, simbolo: str, quantidade: int, preco: float, lado: str
    ) -> Tuple[str, List[Tuple[str, str, str, int, float]]]:
        """Insere uma ordem no livro e tenta casá-la."""
        if lado not in {"compra", "venda"}:
            raise ValueError("lado deve ser 'compra' ou 'venda'")
        if quantidade <= 0 or preco <= 0:
            raise ValueError("quantidade e preço devem ser positivos")

        self.registrar_ativo(simbolo)

        if lado == "venda":
            possuidas = self.carteiras[usuario_id].get(simbolo, 0)
            if possuidas < quantidade:
                raise ValueError("ações insuficientes para vender")
        else:  # compra
            if self.usuarios[usuario_id] < quantidade * preco:
                raise ValueError("saldo insuficiente")

        ordem_id = str(uuid4())
        ordem = Ordem(ordem_id, usuario_id, simbolo, quantidade, preco, lado)
        self.livros[simbolo][lado].append(ordem)
        negociacoes = self.casar_ordens(simbolo)
        if negociacoes:
            self.blockchain.adicionar_bloco(negociacoes)
        return ordem_id, negociacoes

    def casar_ordens(
        self, simbolo: str
    ) -> List[Tuple[str, str, str, int, float]]:
        """Tenta casar ordens de compra e venda para um ativo."""
        livro = self.livros[simbolo]
        compras = sorted(livro["compra"], key=lambda o: (-o.preco, o.timestamp))
        vendas = sorted(livro["venda"], key=lambda o: (o.preco, o.timestamp))
        negociacoes: List[Tuple[str, str, str, int, float]] = []

        while compras and vendas and compras[0].preco >= vendas[0].preco:
            compra = compras[0]
            venda = vendas[0]
            qtd = min(compra.quantidade, venda.quantidade)
            preco_neg = venda.preco
            custo = qtd * preco_neg

            if self.usuarios[compra.usuario_id] < custo:
                livro["compra"].remove(compra)
                compras.pop(0)
                continue

            self.usuarios[compra.usuario_id] -= custo
            self.usuarios[venda.usuario_id] += custo

            self.carteiras[compra.usuario_id][simbolo] = (
                self.carteiras[compra.usuario_id].get(simbolo, 0) + qtd
            )
            self.carteiras[venda.usuario_id][simbolo] = (
                self.carteiras[venda.usuario_id].get(simbolo, 0) - qtd
            )

            compra.quantidade -= qtd
            venda.quantidade -= qtd
            negociacoes.append(
                (compra.usuario_id, venda.usuario_id, simbolo, qtd, preco_neg)
            )

            if compra.quantidade == 0:
                livro["compra"].remove(compra)
                compras.pop(0)
            if venda.quantidade == 0:
                livro["venda"].remove(venda)
                vendas.pop(0)

        return negociacoes
