"""
Decorators de autorização
"""

from functools import wraps
from flask import jsonify, current_app
from flask_jwt_extended import get_jwt_identity
from app.models import User, UserRole

def admin_required(f):
    """Decorator para restringir acesso apenas a administradores"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        try:
            current_user_id = get_jwt_identity()
            user = User.query.get(current_user_id)
            
            if not user or user.role != UserRole.ADMIN:
                return jsonify({
                    'success': False,
                    'message': 'Acesso negado. Apenas administradores podem executar esta ação.'
                }), 403
            
            return f(*args, **kwargs)
        except Exception as e:
            current_app.logger.error(f"admin_required decorator error: {str(e)}")
            return jsonify({
                'success': False,
                'message': 'Erro interno de autorização'
            }), 500
    
    return decorated_function

def user_required(f):
    """Decorator para restringir acesso a usuários com permissão de escrita"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        try:
            current_user_id = get_jwt_identity()
            user = User.query.get(current_user_id)
            
            if not user or user.role == UserRole.VIEWER:
                return jsonify({
                    'success': False,
                    'message': 'Acesso negado. Permissão de usuário necessária.'
                }), 403
            
            return f(*args, **kwargs)
        except Exception as e:
            current_app.logger.error(f"user_required decorator error: {str(e)}")
            return jsonify({
                'success': False,
                'message': 'Erro interno de autorização'
            }), 500
    
    return decorated_function

def permission_required(permission):
    """Decorator para verificar permissão específica"""
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            try:
                current_user_id = get_jwt_identity()
                user = User.query.get(current_user_id)
                
                if not user or not user.has_permission(permission):
                    return jsonify({
                        'success': False,
                        'message': f'Acesso negado. Permissão "{permission}" necessária.'
                    }), 403
                
                return f(*args, **kwargs)
            except Exception as e:
                current_app.logger.error(f"permission_required decorator error: {str(e)}")
                return jsonify({
                    'success': False,
                    'message': 'Erro interno de autorização'
                }), 500
        
        return decorated_function
    return decorator