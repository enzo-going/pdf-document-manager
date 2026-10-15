"""
Erro interno vai para o log do servidor, não para quem chamou a API.
"""

import logging

from flask_jwt_extended import create_access_token

from app import create_app
from app.extensions import db
from app.models import User, UserRole
from app.routes import analytics


class _DocumentoQueQuebra:
    """Substitui o modelo na rota: qualquer consulta estoura com texto "interno"."""

    class _Consulta:
        def __getattr__(self, nome):
            raise RuntimeError('SELECT * FROM users WHERE senha = "segredo-interno"')

    query = _Consulta()


def test_erro_interno_nao_vaza_para_a_resposta(monkeypatch, caplog):
    app = create_app('testing')
    with app.app_context():
        db.create_all()
        user = User(name='Operador', email='op@example.com', role=UserRole.USER, is_active=True)
        user.set_password('senha-teste-123')
        db.session.add(user)
        db.session.commit()
        token = create_access_token(identity=str(user.id))

    # A rota passa a consultar algo que estoura com uma mensagem "interna".
    monkeypatch.setattr(analytics, 'Document', _DocumentoQueQuebra)
    with caplog.at_level(logging.ERROR):
        resposta = app.test_client().get(
            '/api/analytics/charts/signature-status',
            headers={'Authorization': f'Bearer {token}'},
        )

    assert resposta.status_code == 500
    corpo = resposta.get_data(as_text=True)
    assert 'segredo-interno' not in corpo
    assert 'RuntimeError' not in corpo
    assert resposta.get_json()['message'] == 'Erro ao montar o gráfico de assinaturas'
    # O detalhe continua disponível para quem cuida do servidor.
    assert 'segredo-interno' in caplog.text
