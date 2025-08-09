import pytest
from backend.bolsa import BolsaValores


def test_negociacao_basica():
    bolsa = BolsaValores()
    comprador = bolsa.registrar_usuario(1000)
    vendedor = bolsa.registrar_usuario(0)
    bolsa.carteiras[vendedor]['ABC'] = 10

    _, neg1 = bolsa.enviar_ordem(comprador, 'ABC', 5, 10, 'compra')
    assert neg1 == []

    _, neg2 = bolsa.enviar_ordem(vendedor, 'ABC', 5, 9, 'venda')
    assert len(neg2) == 1
    neg = neg2[0]
    assert neg[0] == comprador and neg[1] == vendedor
    assert neg[3] == 5 and neg[4] == 9

    assert bolsa.carteiras[comprador]['ABC'] == 5
    assert bolsa.carteiras[vendedor]['ABC'] == 5
    assert bolsa.usuarios[comprador] == pytest.approx(1000 - 5 * 9)
    assert bolsa.usuarios[vendedor] == pytest.approx(5 * 9)

    assert len(bolsa.blockchain.cadeia) == 2
    assert bolsa.blockchain.cadeia[-1].transacoes == neg2


def test_nao_pode_vender_sem_acoes():
    bolsa = BolsaValores()
    vendedor = bolsa.registrar_usuario(0)
    with pytest.raises(ValueError):
        bolsa.enviar_ordem(vendedor, 'XYZ', 1, 10, 'venda')
