"""
Testes de autenticação JWT
"""

import pytest
import json
from app import create_app
from app.extensions import db
from app.models import User, UserRole

@pytest.fixture
def app_test():
    """Criar aplicação de teste"""
    app = create_app('testing')
    
    with app.app_context():
        db.create_all()
        
        # Criar usuários de teste se não existirem
        if not User.query.filter_by(email='test@example.com').first():
            user = User(
                name='Teste User',
                email='test@example.com',
                role=UserRole.USER,
                is_active=True
            )
            user.set_password('testpass123')
            db.session.add(user)
        
        if not User.query.filter_by(email='admin@example.com').first():
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
        
        db.drop_all()

@pytest.fixture
def client_test(app_test):
    """Cliente de teste"""
    return app_test.test_client()

@pytest.fixture
def user_token(client_test):
    """Token de usuário normal"""
    response = client_test.post('/api/auth/login',
                               json={'email': 'test@example.com', 'password': 'testpass123'})
    data = json.loads(response.data)
    return data['data']['tokens']['access_token']

@pytest.fixture
def admin_token(client_test):
    """Token de administrador"""
    response = client_test.post('/api/auth/login',
                               json={'email': 'admin@example.com', 'password': 'adminpass123'})
    data = json.loads(response.data)
    return data['data']['tokens']['access_token']

class TestAuth:
    """Testes do sistema de autenticação"""
    
    def test_login_success(self, client_test):
        """Teste de login com sucesso"""
        response = client_test.post('/api/auth/login',
                                   json={'email': 'test@example.com', 'password': 'testpass123'})
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['success'] is True
        assert 'tokens' in data['data']
        assert 'access_token' in data['data']['tokens']
    
    def test_login_invalid_email(self, client_test):
        """Teste de login com email inválido"""
        response = client_test.post('/api/auth/login',
                                   json={'email': 'wrong@example.com', 'password': 'testpass123'})
        assert response.status_code == 401
        data = json.loads(response.data)
        assert data['success'] is False
    
    def test_login_invalid_password(self, client_test):
        """Teste de login com senha inválida"""
        response = client_test.post('/api/auth/login',
                                   json={'email': 'test@example.com', 'password': 'wrongpassword'})
        assert response.status_code == 401
        data = json.loads(response.data)
        assert data['success'] is False
    
    def test_profile_with_token(self, client_test, user_token):
        """Teste de acesso ao perfil com token válido"""
        response = client_test.get('/api/auth/profile',
                                  headers={'Authorization': f'Bearer {user_token}'})
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['success'] is True
        assert data['data']['email'] == 'test@example.com'
    
    def test_profile_without_token(self, client_test):
        """Teste de acesso ao perfil sem token"""
        response = client_test.get('/api/auth/profile')
        assert response.status_code == 422  # JWT required
    
    def test_create_user_as_admin(self, client_test, admin_token):
        """Teste de criação de usuário como admin"""
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
        assert data['success'] is True
    
    def test_create_user_as_regular_user(self, client_test, user_token):
        """Teste de criação de usuário como usuário normal (deve falhar)"""
        response = client_test.post('/api/auth/users',
                                   json={
                                       'name': 'New User',
                                       'email': 'new2@example.com',
                                       'password': 'newpass123',
                                       'role': 'user'
                                   },
                                   headers={'Authorization': f'Bearer {user_token}'})
        assert response.status_code == 403
        data = json.loads(response.data)
        assert data['success'] is False
    
    def test_list_users_as_admin(self, client_test, admin_token):
        """Teste de listagem de usuários como admin"""
        response = client_test.get('/api/auth/users',
                                  headers={'Authorization': f'Bearer {admin_token}'})
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['success'] is True
        assert isinstance(data['data'], list)
    
    def test_refresh_token(self, client_test):
        """Teste de renovação de token"""
        # Login primeiro
        login_response = client_test.post('/api/auth/login',
                                         json={'email': 'test@example.com', 'password': 'testpass123'})
        login_data = json.loads(login_response.data)
        refresh_token = login_data['data']['tokens']['refresh_token']
        
        # Renovar token
        response = client_test.post('/api/auth/refresh',
                                   headers={'Authorization': f'Bearer {refresh_token}'})
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['success'] is True
        assert 'access_token' in data['data']