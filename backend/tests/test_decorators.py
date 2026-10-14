"""
Decorators de permissão: o que é erro de autorização e o que é erro da rota.
"""

import pytest
from flask_jwt_extended import create_access_token, jwt_required

from app import create_app
from app.extensions import db
from app.models import User, UserRole
from app.utils.decorators import admin_required


class TestDecorators:
    def test_erro_dentro_da_rota_nao_vira_erro_de_autorizacao(self):
        app = create_app('testing')

        @app.route('/teste/quebra')
        @jwt_required()
        @admin_required
        def quebra():
            raise ValueError('falha da propria rota')

        with app.app_context():
            db.create_all()
            admin = User(name='Admin', email='admin@example.com', role=UserRole.ADMIN, is_active=True)
            admin.set_password('adminpass123')
            db.session.add(admin)
            db.session.commit()
            token = create_access_token(identity=str(admin.id))

        # Em TESTING o Flask propaga a exceção: antes ela era engolida pelo
        # decorator e devolvida como 500 "Erro interno de autorização".
        with pytest.raises(ValueError, match='falha da propria rota'):
            app.test_client().get('/teste/quebra', headers={'Authorization': f'Bearer {token}'})

    def test_usuario_comum_continua_barrado(self):
        app = create_app('testing')

        @app.route('/teste/so-admin')
        @jwt_required()
        @admin_required
        def so_admin():
            return {'ok': True}

        with app.app_context():
            db.create_all()
            user = User(name='Comum', email='comum@example.com', role=UserRole.USER, is_active=True)
            user.set_password('userpass123')
            db.session.add(user)
            db.session.commit()
            token = create_access_token(identity=str(user.id))

        resposta = app.test_client().get('/teste/so-admin', headers={'Authorization': f'Bearer {token}'})
        assert resposta.status_code == 403
