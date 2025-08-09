from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, List, Tuple
from uuid import uuid4


@dataclass
class Order:
    """Representa uma ordem de compra ou venda."""

    id: str
    user_id: str
    symbol: str
    quantity: int
    price: float
    side: str  # 'buy' ou 'sell'
    timestamp: datetime = field(default_factory=datetime.utcnow)


class StockExchange:
    """Sistema simples de bolsa de valores."""

    def __init__(self) -> None:
        # Saldo de cada usuário
        self.users: Dict[str, float] = {}
        # Carteira de ações de cada usuário
        self.portfolios: Dict[str, Dict[str, int]] = {}
        # Livro de ordens por ativo
        self.order_books: Dict[str, Dict[str, List[Order]]] = {}

    def register_user(self, initial_balance: float) -> str:
        """Registra um novo usuário com saldo inicial."""
        user_id = str(uuid4())
        self.users[user_id] = initial_balance
        self.portfolios[user_id] = {}
        return user_id

    def list_stock(self, symbol: str) -> None:
        """Garante que o ativo esteja registrado no livro de ordens."""
        if symbol not in self.order_books:
            self.order_books[symbol] = {"buy": [], "sell": []}

    def place_order(
        self, user_id: str, symbol: str, quantity: int, price: float, side: str
    ) -> Tuple[str, List[Tuple[str, str, str, int, float]]]:
        """Insere uma ordem no livro e tenta casá-la."""
        if side not in {"buy", "sell"}:
            raise ValueError("side must be 'buy' or 'sell'")
        if quantity <= 0 or price <= 0:
            raise ValueError("quantity and price must be positive")

        self.list_stock(symbol)

        if side == "sell":
            owned = self.portfolios[user_id].get(symbol, 0)
            if owned < quantity:
                raise ValueError("not enough shares to sell")
        else:  # buy
            if self.users[user_id] < quantity * price:
                raise ValueError("insufficient funds")

        order_id = str(uuid4())
        order = Order(order_id, user_id, symbol, quantity, price, side)
        self.order_books[symbol][side].append(order)
        trades = self.match_orders(symbol)
        return order_id, trades

    def match_orders(
        self, symbol: str
    ) -> List[Tuple[str, str, str, int, float]]:
        """Tenta casar ordens de compra e venda para um ativo."""
        book = self.order_books[symbol]
        buys = sorted(book["buy"], key=lambda o: (-o.price, o.timestamp))
        sells = sorted(book["sell"], key=lambda o: (o.price, o.timestamp))
        trades: List[Tuple[str, str, str, int, float]] = []

        while buys and sells and buys[0].price >= sells[0].price:
            buy = buys[0]
            sell = sells[0]
            trade_qty = min(buy.quantity, sell.quantity)
            trade_price = sell.price
            cost = trade_qty * trade_price

            # Verifica saldo do comprador
            if self.users[buy.user_id] < cost:
                book["buy"].remove(buy)
                buys.pop(0)
                continue

            # Atualiza saldos
            self.users[buy.user_id] -= cost
            self.users[sell.user_id] += cost

            # Atualiza carteiras
            self.portfolios[buy.user_id][symbol] = (
                self.portfolios[buy.user_id].get(symbol, 0) + trade_qty
            )
            self.portfolios[sell.user_id][symbol] = (
                self.portfolios[sell.user_id].get(symbol, 0) - trade_qty
            )

            buy.quantity -= trade_qty
            sell.quantity -= trade_qty
            trades.append((buy.user_id, sell.user_id, symbol, trade_qty, trade_price))

            if buy.quantity == 0:
                book["buy"].remove(buy)
                buys.pop(0)
            if sell.quantity == 0:
                book["sell"].remove(sell)
                sells.pop(0)

        return trades
