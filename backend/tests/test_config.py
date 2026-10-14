"""
Configuração por ambiente: segredos de exemplo, escolha do ambiente, CORS
e rota de debug.
"""

import pytest

from app import create_app
from app.config import ProductionConfig, TestingConfig, opcoes_servidor_dev


def _producao(monkeypatch, **valores):
    """Produção com segredos próprios e banco em memória; `valores` sobrescreve."""
    base = {
        'SECRET_KEY': 'segredo-proprio-de-teste',
        'JWT_SECRET_KEY': 'jwt-proprio-de-teste',
        'ADMIN_PASSWORD': 'senha-propria-de-teste',
        'SQLALCHEMY_DATABASE_URI': 'sqlite:///:memory:',
        'CREATE_ADMIN_ON_STARTUP': False,
    }
    base.update(valores)
    for chave, valor in base.items():
        monkeypatch.setattr(ProductionConfig, chave, valor, raising=False)


class TestSegredos:
    @pytest.mark.parametrize('chave', ['SECRET_KEY', 'JWT_SECRET_KEY'])
    @pytest.mark.parametrize('valor', ['change-me', 'jwt-secret-key-change-in-production', ''])
    def test_producao_recusa_segredo_de_exemplo(self, monkeypatch, chave, valor):
        _producao(monkeypatch, **{chave: valor})
        with pytest.raises(RuntimeError, match=chave):
            create_app('production')

    def test_producao_recusa_senha_de_admin_de_exemplo(self, monkeypatch):
        _producao(monkeypatch, CREATE_ADMIN_ON_STARTUP=True, ADMIN_PASSWORD='change-me')
        with pytest.raises(RuntimeError, match='ADMIN_PASSWORD'):
            create_app('production')

    def test_producao_sobe_com_segredos_proprios(self, monkeypatch):
        _producao(monkeypatch)
        app = create_app('production')
        assert app.debug is False
        assert app.config['SQLALCHEMY_ECHO'] is False

    def test_fora_de_producao_segredo_de_exemplo_e_aceito(self):
        # TestingConfig herda os segredos padrão: avisa, mas sobe.
        app = create_app('testing')
        assert app.testing is True


class TestAmbiente:
    def test_ambiente_vem_do_flask_env(self, monkeypatch):
        _producao(monkeypatch)
        monkeypatch.setenv('FLASK_ENV', 'production')
        assert create_app().config['DEBUG'] is False

        monkeypatch.setenv('FLASK_ENV', 'testing')
        assert create_app().testing is True

    def test_ambiente_desconhecido_falha_em_vez_de_cair_em_desenvolvimento(self):
        with pytest.raises(ValueError, match='prod'):
            create_app('prod')


def _preflight(client, origem):
    return client.options('/api/auth/login', headers={
        'Origin': origem,
        'Access-Control-Request-Method': 'POST',
    })


class TestCors:
    def test_padrao_libera_todas_as_origens(self):
        client = create_app('testing').test_client()
        resposta = _preflight(client, 'http://qualquer.test')
        # O Flask-CORS devolve a própria origem quando a regra é "*".
        assert resposta.headers.get('Access-Control-Allow-Origin') == 'http://qualquer.test'

    def test_cors_origins_restringe_as_origens(self, monkeypatch):
        monkeypatch.setattr(TestingConfig, 'CORS_ORIGINS', 'http://painel.test, http://outro.test')
        client = create_app('testing').test_client()

        permitida = _preflight(client, 'http://painel.test')
        assert permitida.headers.get('Access-Control-Allow-Origin') == 'http://painel.test'

        recusada = _preflight(client, 'http://intruso.test')
        assert 'Access-Control-Allow-Origin' not in recusada.headers


class TestRotaDeDebug:
    def test_fora_de_debug_a_rota_nao_existe(self):
        client = create_app('testing').test_client()
        assert client.get('/debug/routes').status_code == 404

    def test_em_debug_a_rota_lista_as_rotas(self, monkeypatch):
        monkeypatch.setattr(TestingConfig, 'DEBUG', True, raising=False)
        client = create_app('testing').test_client()
        resposta = client.get('/debug/routes')
        assert resposta.status_code == 200
        assert any(rota['path'] == '/api/auth/login' for rota in resposta.get_json())


class TestServidorDev:
    """python run.py: só nesta máquina por padrão, sem depurador exposto na rede."""

    def test_padrao_escuta_so_nesta_maquina(self):
        assert opcoes_servidor_dev({}) == ('127.0.0.1', 5000, False)

    def test_depurador_so_liga_escutando_localmente(self):
        assert opcoes_servidor_dev({'FLASK_ENV': 'development'}) == ('127.0.0.1', 5000, True)
        assert opcoes_servidor_dev({'FLASK_ENV': 'development', 'HOST': 'localhost'})[2] is True

    def test_na_rede_o_depurador_fica_desligado(self):
        assert opcoes_servidor_dev({'FLASK_ENV': 'development', 'HOST': '0.0.0.0'}) == ('0.0.0.0', 5000, False)

    def test_porta_vem_do_ambiente(self):
        assert opcoes_servidor_dev({'PORT': '8080'})[1] == 8080
