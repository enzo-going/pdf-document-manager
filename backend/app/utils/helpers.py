"""
Helpers e utilidades
"""

import os
import hashlib
from datetime import datetime
from flask import current_app


def generate_identifier(prefix: str) -> str:
    now = datetime.utcnow().strftime('%Y%m%d%H%M%S%f')
    return f"{prefix}-{now}"


def allowed_file(filename: str) -> bool:
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in {'pdf'}


def file_sha256(path: str) -> str:
    h = hashlib.sha256()
    with open(path, 'rb') as f:
        for chunk in iter(lambda: f.read(8192), b''):
            h.update(chunk)
    return h.hexdigest()
