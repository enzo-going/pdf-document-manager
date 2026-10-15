"""
Helpers e utilidades
"""

import hashlib
from datetime import datetime

from flask import current_app, jsonify


def generate_identifier(prefix: str) -> str:
    now = datetime.utcnow().strftime('%Y%m%d%H%M%S%f')
    return f"{prefix}-{now}"


def allowed_file(filename: str) -> bool:
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in {'pdf'}


def erro_interno(mensagem: str, chave: str = 'message', status: int = 500):
    """Registra a exceção em andamento no log (com traceback) e responde só `mensagem`.

    O texto da exceção pode trazer SQL, caminhos de arquivo ou dados internos:
    fica no log do servidor, não vai para quem chamou a API.
    """
    current_app.logger.exception(mensagem)
    return jsonify({'success': False, chave: mensagem}), status


def file_sha256(path: str) -> str:
    h = hashlib.sha256()
    with open(path, 'rb') as f:
        for chunk in iter(lambda: f.read(8192), b''):
            h.update(chunk)
    return h.hexdigest()
