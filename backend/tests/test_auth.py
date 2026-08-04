"""
Testes de autenticação JWT

O contrato exercitado aqui é o de `app/routes/auth.py`, que é o blueprint
registrado em `/api/auth`: respostas planas (`message`, `user`, `access_token`,
`error`), sem envelope `success`/`data`.
"""

import json

import pytest

from app import create_app
from app.extensions import db
from app.models import User, UserRole


@pytest.fixture
def app_test():
    """Aplicação de teste com banco em memória e dois usuários conhecidos."""
    app = create_app('testing')

    with app.app_context():
        db.create_all()

        user = User(
            name='Teste User',
            email='test@example.com',
            role=UserRole.USER,
            is_active=True
        )
        user.set_password('testpass123')
        db.session.add(user)

        admin = User(
            name='Admin User',
            email='admin@example.com',
            role=UserRole.ADMIN,
            is_active=True
        )
        admin.set_password('adminpass123')
        db.session.add(admin)

        db.session.commit()

        yield app

        db.session.remove()
        db.drop_all()


@pytest.fixture
def client_test(app_test):
    """Cliente de teste"""
    return app_test.test_client()


def _login(client, email, password):
    response = client.post('/api/auth/login',
                           json={'email': email, 'password': password})
    return response, json.loads(response.data)


@pytest.fixture
def user_token(client_test):
    """Access token de usuário comum"""
    _, data = _login(client_test, 'test@example.com', 'testpass123')
    return data['access_token']


@pytest.fixture
def admin_token(client_test):
    """Access token de administrador"""
    _, data = _login(client_test, 'admin@example.com', 'adminpass123')
    return data['access_token']


class TestLogin:
    """POST /api/auth/login"""

    def test_login_success(self, client_test):
        response, data = _login(client_test, 'test@example.com', 'testpass123')
        assert response.status_code == 200
        assert 'access_token' in data
        assert 'refresh_token' in data
        assert data['user']['email'] == 'test@example.com'
        assert data['user']['role'] == UserRole.USER.value
        assert 'password_hash' not in data['user']

    def test_login_invalid_email(self, client_test):
        response, data = _login(client_test, 'wrong@example.com', 'testpass123')
        assert response.status_code == 401
        assert 'error' in data

    def test_login_invalid_password(self, client_test):
        response, data = _login(client_test, 'test@example.com', 'wrongpassword')
        assert response.status_code == 401
        assert 'error' in data

    def test_login_missing_fields(self, client_test):
        response = client_test.post('/api/auth/login', json={'email': 'test@example.com'})
        assert response.status_code == 400
        assert 'error' in json.loads(response.data)

    def test_login_inactive_user(self, client_test, app_test):
        with app_test.app_context():
            user = User.query.filter_by(email='test@example.com').first()
            user.is_active = False
            db.session.commit()

        response, data = _login(client_test, 'test@example.com', 'testpass123')
        assert response.status_code == 403
        assert 'error' in data


class TestCurrentUser:
    """GET /api/auth/me"""

    def test_me_with_token(self, client_test, user_token):
        response = client_test.get('/api/auth/me',
                                   headers={'Authorization': f'Bearer {user_token}'})
        assert response.status_code == 200
        assert json.loads(response.data)['email'] == 'test@example.com'

    def test_me_without_token(self, client_test):
        response = client_test.get('/api/auth/me')
        assert response.status_code == 401

    def test_me_with_invalid_token(self, client_test):
        response = client_test.get('/api/auth/me',
                                   headers={'Authorization': 'Bearer nao-e-um-token'})
        assert response.status_code == 422


class TestUserManagement:
    """/api/auth/users — só admin"""

    def test_create_user_as_admin(self, client_test, admin_token):
        response = client_test.post('/api/auth/users',
                                    json={
                                        'name': 'New User',
                                        'email': 'new@example.com',
                                        'password': 'newpass123',
                                        'role': 'user'
                                    },
                                    headers={'Authorization': f'Bearer {admin_token}'})
        assert response.status_code == 201
        data = json.loads(response.data)
        assert data['user']['email'] == 'new@example.com'
        assert data['user']['role'] == UserRole.USER.value

    def test_create_user_as_regular_user(self, client_test, user_token):
        response = client_test.post('/api/auth/users',
                                    json={
                                        'name': 'New User',
                                        'email': 'new2@example.com',
                                        'password': 'newpass123',
                                        'role': 'user'
                                    },
                                    headers={'Authorization': f'Bearer {user_token}'})
        assert response.status_code == 403
        assert 'error' in json.loads(response.data)

    def test_create_user_duplicate_email(self, client_test, admin_token):
        response = client_test.post('/api/auth/users',
                                    json={
                                        'name': 'Outro',
                                        'email': 'test@example.com',
                                        'password': 'newpass123',
                                        'role': 'user'
                                    },
                                    headers={'Authorization': f'Bearer {admin_token}'})
        assert response.status_code == 409

    def test_list_users_as_admin(self, client_test, admin_token):
        response = client_test.get('/api/auth/users',
                                   headers={'Authorization': f'Bearer {admin_token}'})
        assert response.status_code == 200
        data = json.loads(response.data)
        assert isinstance(data['users'], list)
        assert data['total'] == len(data['users']) == 2

    def test_list_users_as_regular_user(self, client_test, user_token):
        response = client_test.get('/api/auth/users',
                                   headers={'Authorization': f'Bearer {user_token}'})
        assert response.status_code == 403


class TestRefreshAndLogout:
    """POST /api/auth/refresh e /api/auth/logout"""

    def test_refresh_token(self, client_test):
        _, login_data = _login(client_test, 'test@example.com', 'testpass123')
        refresh_token = login_data['refresh_token']

        response = client_test.post('/api/auth/refresh',
                                    headers={'Authorization': f'Bearer {refresh_token}'})
        assert response.status_code == 200
        assert 'access_token' in json.loads(response.data)

    def test_refresh_rejects_access_token(self, client_test, user_token):
        """Access token não serve para renovar: a rota exige refresh=True."""
        response = client_test.post('/api/auth/refresh',
                                    headers={'Authorization': f'Bearer {user_token}'})
        assert response.status_code == 422

    def test_logout(self, client_test, user_token):
        response = client_test.post('/api/auth/logout',
                                    headers={'Authorization': f'Bearer {user_token}'})
        assert response.status_code == 200


class TestChangePassword:
    """POST /api/auth/change-password"""

    def test_change_password_success(self, client_test, user_token):
        response = client_test.post('/api/auth/change-password',
                                    json={'current_password': 'testpass123',
                                          'new_password': 'novasenha456'},
                                    headers={'Authorization': f'Bearer {user_token}'})
        assert response.status_code == 200

        antiga, _ = _login(client_test, 'test@example.com', 'testpass123')
        assert antiga.status_code == 401

        nova, _ = _login(client_test, 'test@example.com', 'novasenha456')
        assert nova.status_code == 200

    def test_change_password_wrong_current(self, client_test, user_token):
        response = client_test.post('/api/auth/change-password',
                                    json={'current_password': 'errada',
                                          'new_password': 'novasenha456'},
                                    headers={'Authorization': f'Bearer {user_token}'})
        assert response.status_code == 401
