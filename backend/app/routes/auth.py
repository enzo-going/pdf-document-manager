"""
Rotas de autenticação e gestão de usuários
"""

from flask import Blueprint, request, jsonify
from flask_jwt_extended import (
    create_access_token,
    create_refresh_token,
    jwt_required,
    get_jwt_identity,
    get_jwt
)
from datetime import datetime
from app.extensions import db
from app.models import User, UserRole, AuditLog

auth_bp = Blueprint('auth', __name__)


# ==================== AUTENTICAÇÃO ====================

@auth_bp.route('/login', methods=['POST'])
def login():
    """
    Login de usuário
    ---
    POST /api/auth/login
    Body: { "email": "admin@example.com", "password": "your-password" }
    """
    data = request.get_json()
    
    # Validação básica
    if not data or not data.get('email') or not data.get('password'):
        return jsonify({'error': 'Email e senha são obrigatórios'}), 400
    
    # Buscar usuário
    user = User.query.filter_by(email=data['email']).first()
    
    if not user:
        return jsonify({'error': 'Credenciais inválidas'}), 401
    
    # Verificar senha
    if not user.check_password(data['password']):
        return jsonify({'error': 'Credenciais inválidas'}), 401
    
    # Verificar se usuário está ativo
    if not user.is_active:
        return jsonify({'error': 'Usuário desativado'}), 403
    
    # Atualizar último login
    user.last_login = datetime.utcnow()
    db.session.commit()
    
    # Gerar tokens
    tokens = user.generate_tokens()
    
    return jsonify({
        'message': 'Login realizado com sucesso',
        'user': user.to_dict(),
        'access_token': tokens['access_token'],
        'refresh_token': tokens['refresh_token']
    }), 200


@auth_bp.route('/refresh', methods=['POST'])
@jwt_required(refresh=True)
def refresh():
    """Renovar access token usando refresh token"""
    user_id = get_jwt_identity()
    
    # ✅ CORREÇÃO 1: Converter string para int
    user = User.query.get(int(user_id))
    
    if not user or not user.is_active:
        return jsonify({'error': 'Usuário inválido ou inativo'}), 403
    
    # Gerar novo access token
    access_token = create_access_token(
        identity=str(user.id),
        additional_claims={"role": user.role.value, "name": user.name}
    )
    
    return jsonify({
        'access_token': access_token
    }), 200


@auth_bp.route('/me', methods=['GET'])
@jwt_required()
def get_current_user():
    """Retorna dados do usuário autenticado"""
    try:
        user_id = get_jwt_identity()
        
        # ✅ CORREÇÃO 2: Converter string para int
        user = User.query.get(int(user_id))
        
        if not user:
            return jsonify({'error': 'Usuário não encontrado'}), 404
        
        return jsonify(user.to_dict()), 200
        
    except Exception as e:
        return jsonify({
            'error': str(e),
            'type': type(e).__name__
        }), 500


@auth_bp.route('/logout', methods=['POST'])
@jwt_required()
def logout():
    """
    Logout (no backend não há muito o que fazer com JWT stateless)
    No frontend, remover o token do localStorage
    """
    return jsonify({'message': 'Logout realizado com sucesso'}), 200


# ==================== GESTÃO DE USUÁRIOS (ADMIN) ====================

@auth_bp.route('/users', methods=['GET'])
@jwt_required()
def list_users():
    """
    Lista todos os usuários (apenas admin)
    ---
    GET /api/auth/users
    Header: Authorization: Bearer {access_token}
    """
    user_id = get_jwt_identity()
    
    # ✅ CORREÇÃO 3: Converter string para int
    current_user = User.query.get(int(user_id))
    
    # Verificar se é admin
    if not current_user or not current_user.has_permission('manage_users'):
        return jsonify({'error': 'Acesso negado'}), 403
    
    # Listar todos os usuários
    users = User.query.all()
    
    return jsonify({
        'users': [user.to_dict() for user in users],
        'total': len(users)
    }), 200


@auth_bp.route('/users', methods=['POST'])
@jwt_required()
def create_user():
    """
    Cria novo usuário (apenas admin)
    ---
    POST /api/auth/users
    Header: Authorization: Bearer {access_token}
    Body: {
        "email": "user@example.com",
        "name": "Nome do Usuário",
        "password": "senha123",
        "role": "user"  # admin, user, viewer
    }
    """
    user_id = get_jwt_identity()
    
    # ✅ CORREÇÃO 4: Converter string para int
    current_user = User.query.get(int(user_id))
    
    # Verificar se é admin
    if not current_user or not current_user.has_permission('manage_users'):
        return jsonify({'error': 'Acesso negado'}), 403
    
    data = request.get_json()
    
    # Validações
    if not data or not all(k in data for k in ['email', 'name', 'password']):
        return jsonify({'error': 'Email, nome e senha são obrigatórios'}), 400
    
    # Verificar se email já existe
    if User.query.filter_by(email=data['email']).first():
        return jsonify({'error': 'Email já cadastrado'}), 409
    
    # Validar role
    role_str = data.get('role', 'user').upper()
    try:
        role = UserRole[role_str]
    except KeyError:
        return jsonify({'error': f'Role inválida. Use: admin, user ou viewer'}), 400
    
    # Criar usuário
    new_user = User(
        email=data['email'],
        name=data['name'],
        role=role,
        is_active=data.get('is_active', True)
    )
    new_user.set_password(data['password'])
    
    db.session.add(new_user)
    db.session.commit()
    
    # Log de auditoria
    log = AuditLog(
        action='create_user',
        description=f'Usuário {new_user.email} criado por {current_user.email}',
        user_id=current_user.id,
        document_id=None,
        ip_address=request.remote_addr,
        user_agent=request.headers.get('User-Agent')
    )
    db.session.add(log)
    db.session.commit()
    
    return jsonify({
        'message': 'Usuário criado com sucesso',
        'user': new_user.to_dict()
    }), 201


@auth_bp.route('/users/<int:user_id>', methods=['PUT'])
@jwt_required()
def update_user(user_id):
    """
    Atualiza dados de um usuário (apenas admin)
    ---
    PUT /api/auth/users/<user_id>
    Header: Authorization: Bearer {access_token}
    Body: { "name": "Novo Nome", "role": "admin", "is_active": true }
    """
    current_user_id = get_jwt_identity()
    
    # ✅ CORREÇÃO 5: Converter string para int
    current_user = User.query.get(int(current_user_id))
    
    # Verificar se é admin
    if not current_user or not current_user.has_permission('manage_users'):
        return jsonify({'error': 'Acesso negado'}), 403
    
    # Buscar usuário a ser atualizado
    user = User.query.get(user_id)
    if not user:
        return jsonify({'error': 'Usuário não encontrado'}), 404
    
    data = request.get_json()
    
    # Atualizar campos permitidos
    if 'name' in data:
        user.name = data['name']
    
    if 'email' in data and data['email'] != user.email:
        # Verificar se novo email já existe
        if User.query.filter_by(email=data['email']).first():
            return jsonify({'error': 'Email já cadastrado'}), 409
        user.email = data['email']
    
    if 'role' in data:
        try:
            user.role = UserRole[data['role'].upper()]
        except KeyError:
            return jsonify({'error': 'Role inválida'}), 400
    
    if 'is_active' in data:
        user.is_active = data['is_active']
    
    if 'password' in data:
        user.set_password(data['password'])
    
    db.session.commit()
    
    return jsonify({
        'message': 'Usuário atualizado com sucesso',
        'user': user.to_dict()
    }), 200


@auth_bp.route('/users/<int:user_id>', methods=['DELETE'])
@jwt_required()
def delete_user(user_id):
    """
    Deleta um usuário (apenas admin)
    ---
    DELETE /api/auth/users/<user_id>
    Header: Authorization: Bearer {access_token}
    """
    current_user_id = get_jwt_identity()
    
    # ✅ CORREÇÃO 6: Converter string para int
    current_user = User.query.get(int(current_user_id))
    
    # Verificar se é admin
    if not current_user or not current_user.has_permission('manage_users'):
        return jsonify({'error': 'Acesso negado'}), 403
    
    # Não pode deletar a si mesmo
    if user_id == int(current_user_id):
        return jsonify({'error': 'Não é possível deletar seu próprio usuário'}), 400
    
    # Buscar usuário
    user = User.query.get(user_id)
    if not user:
        return jsonify({'error': 'Usuário não encontrado'}), 404
    
    # Deletar
    db.session.delete(user)
    db.session.commit()
    
    return jsonify({'message': 'Usuário deletado com sucesso'}), 200


# ==================== TROCAR SENHA ====================

@auth_bp.route('/change-password', methods=['POST'])
@jwt_required()
def change_password():
    """
    Usuário troca sua própria senha
    ---
    POST /api/auth/change-password
    Header: Authorization: Bearer {access_token}
    Body: { "current_password": "antiga", "new_password": "nova" }
    """
    user_id = get_jwt_identity()
    
    # ✅ CORREÇÃO 7: Converter string para int
    user = User.query.get(int(user_id))
    
    if not user:
        return jsonify({'error': 'Usuário não encontrado'}), 404
    
    data = request.get_json()
    
    if not data or not all(k in data for k in ['current_password', 'new_password']):
        return jsonify({'error': 'Senha atual e nova senha são obrigatórias'}), 400
    
    # Verificar senha atual
    if not user.check_password(data['current_password']):
        return jsonify({'error': 'Senha atual incorreta'}), 401
    
    # Atualizar senha
    user.set_password(data['new_password'])
    db.session.commit()
    
    return jsonify({'message': 'Senha alterada com sucesso'}), 200
