"""
Rotas de autenticação - SEM IMPORT CIRCULAR
"""

from flask import request, jsonify, current_app
from flask_jwt_extended import (
    create_access_token, create_refresh_token, jwt_required, 
    get_jwt_identity
)
from datetime import datetime
from app.models import User, UserRole, db
from app.utils.validators import validate_email, validate_password
from app.utils.decorators import admin_required

# Importar o blueprint do módulo pai
from . import auth_bp

@auth_bp.route('/login', methods=['POST'])
def login():
    """Endpoint de login com JWT"""
    data = request.get_json() or {}
    email = (data.get('email') or '').strip().lower()
    password = data.get('password') or ''

    if not email or not password:
        return jsonify({'success': False, 'message': 'Email e senha são obrigatórios'}), 400

    if not validate_email(email):
        return jsonify({'success': False, 'message': 'Formato de email inválido'}), 400

    user = User.query.filter_by(email=email).first()
    if not user or not user.check_password(password):
        return jsonify({'success': False, 'message': 'Email ou senha incorretos'}), 401
    if not user.is_active:
        return jsonify({'success': False, 'message': 'Conta desativada'}), 403

    # Gerar tokens usando o método do modelo
    access_token = create_access_token(
        identity=user.id,
        additional_claims={'role': user.role.value, 'name': user.name}
    )
    refresh_token = create_refresh_token(identity=user.id)
    
    # Atualizar last_login
    user.last_login = datetime.utcnow()
    db.session.commit()

    return jsonify({
        'success': True, 
        'data': {
            'user': user.to_dict(), 
            'tokens': {
                'access_token': access_token,
                'refresh_token': refresh_token
            }
        }
    }), 200

@auth_bp.route('/refresh', methods=['POST'])
@jwt_required(refresh=True)
def refresh():
    """Renovar token de acesso"""
    user_id = get_jwt_identity()
    user = User.query.get(user_id)
    if not user or not user.is_active:
        return jsonify({'success': False, 'message': 'Usuário inválido'}), 401

    claims = {"role": user.role.value, "name": user.name}
    new_access = create_access_token(identity=user_id, additional_claims=claims)
    return jsonify({'success': True, 'data': {'access_token': new_access}}), 200

@auth_bp.route('/profile', methods=['GET'])
@jwt_required()
def profile():
    """Dados do perfil do usuário atual"""
    user_id = get_jwt_identity()
    user = User.query.get(user_id)
    if not user:
        return jsonify({'success': False, 'message': 'Usuário não encontrado'}), 404
    return jsonify({'success': True, 'data': user.to_dict()}), 200

@auth_bp.route('/users', methods=['POST'])
@jwt_required()
@admin_required
def create_user():
    """Criar novo usuário (apenas admins)"""
    data = request.get_json() or {}

    required = ['name', 'email', 'password', 'role']
    missing = [f for f in required if not data.get(f)]
    if missing:
        return jsonify({'success': False, 'message': f'Campos obrigatórios: {", ".join(missing)}'}), 400

    email = data['email'].strip().lower()
    if not validate_email(email):
        return jsonify({'success': False, 'message': 'Formato de email inválido'}), 400

    vp = validate_password(data['password'])
    if not vp['valid']:
        return jsonify({'success': False, 'message': vp['message']}), 400

    if User.query.filter_by(email=email).first():
        return jsonify({'success': False, 'message': 'Email já em uso'}), 400

    if data['role'] not in ['admin', 'user', 'viewer']:
        return jsonify({'success': False, 'message': 'Role inválida'}), 400

    user = User(name=data['name'].strip(), email=email, role=UserRole(data['role']))
    user.set_password(data['password'])
    db.session.add(user)
    db.session.commit()

    return jsonify({'success': True, 'message': 'Usuário criado', 'data': user.to_dict()}), 201

@auth_bp.route('/users', methods=['GET'])
@jwt_required()
@admin_required
def list_users():
    """Listar todos os usuários (apenas admins)"""
    users = User.query.order_by(User.created_at.desc()).all()
    return jsonify({'success': True, 'data': [u.to_dict() for u in users]}), 200