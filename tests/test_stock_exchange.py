import pytest
from backend.stock_exchange import StockExchange


def test_basic_trade():
    exchange = StockExchange()
    buyer = exchange.register_user(1000)
    seller = exchange.register_user(0)
    exchange.portfolios[seller]['ABC'] = 10

    # ordem de compra não casa sozinha
    _, trades1 = exchange.place_order(buyer, 'ABC', 5, 10, 'buy')
    assert trades1 == []

    # ordem de venda casa com a compra existente
    _, trades2 = exchange.place_order(seller, 'ABC', 5, 9, 'sell')
    assert len(trades2) == 1
    trade = trades2[0]
    assert trade[0] == buyer and trade[1] == seller
    assert trade[3] == 5 and trade[4] == 9

    assert exchange.portfolios[buyer]['ABC'] == 5
    assert exchange.portfolios[seller]['ABC'] == 5
    assert exchange.users[buyer] == pytest.approx(1000 - 5 * 9)
    assert exchange.users[seller] == pytest.approx(5 * 9)


def test_cannot_sell_without_shares():
    exchange = StockExchange()
    seller = exchange.register_user(0)
    with pytest.raises(ValueError):
        exchange.place_order(seller, 'XYZ', 1, 10, 'sell')
