"""
Validadores de entrada
"""

import re

def validate_email(email: str) -> bool:
    """Valida formato de email"""
    if not email or not isinstance(email, str):
        return False
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return re.match(pattern, email.strip()) is not None

def validate_password(password: str) -> dict:
    """Valida senha com regras de segurança"""
    if not password or not isinstance(password, str):
        return {'valid': False, 'message': 'Senha é obrigatória'}
    if len(password) < 8:
        return {'valid': False, 'message': 'Senha deve ter pelo menos 8 caracteres'}
    if len(password) > 128:
        return {'valid': False, 'message': 'Senha muito longa (máximo 128)'}
    has_letter = re.search(r'[a-zA-Z]', password)
    has_number = re.search(r'\d', password)
    if not has_letter:
        return {'valid': False, 'message': 'Senha deve conter pelo menos uma letra'}
    if not has_number:
        return {'valid': False, 'message': 'Senha deve conter pelo menos um número'}
    return {'valid': True, 'message': 'Senha válida'}