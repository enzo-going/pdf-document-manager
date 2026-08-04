#!/usr/bin/env python3
"""
Diagnostico de imports: confere dependencias, modelos, blueprints e rotas.

Uso: a partir de backend/, `python scripts/diagnostico_imports.py`
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv

# Carregar .env
load_dotenv()

print("1. Testando imports básicos...")
try:
    from flask import Flask
    print("✅ Flask: OK")
except Exception as e:
    print(f"❌ Flask: {e}")
    exit(1)

try:
    from flask_cors import CORS
    print("✅ CORS: OK")
except Exception as e:
    print(f"❌ CORS: {e}")

try:
    from flask_jwt_extended import JWTManager
    print("✅ JWT: OK")
except Exception as e:
    print(f"❌ JWT: {e}")

try:
    from flask_bcrypt import Bcrypt
    print("✅ Bcrypt: OK")
except Exception as e:
    print(f"❌ Bcrypt: {e}")

try:
    from flask_sqlalchemy import SQLAlchemy
    print("✅ SQLAlchemy: OK")
except Exception as e:
    print(f"❌ SQLAlchemy: {e}")

print("\n2. Testando modelos...")
try:
    from app.models import User, UserRole, Document
    print("✅ Modelos: OK")
except Exception as e:
    print(f"❌ Modelos: {e}")

print("\n3. Testando blueprints...")
try:
    from app.auth import auth_bp
    print(f"✅ Auth Blueprint: {auth_bp.name}")
    print(f"✅ Auth Rules: {len(auth_bp.url_map._rules_by_endpoint)} endpoints")
except Exception as e:
    print(f"❌ Auth Blueprint: {e}")

try:
    from app.routes.documents import documents_bp
    print(f"✅ Documents Blueprint: {documents_bp.name}")
except Exception as e:
    print(f"❌ Documents Blueprint: {e}")

try:
    from app.routes.analytics import analytics_bp
    print(f"✅ Analytics Blueprint: {analytics_bp.name}")
except Exception as e:
    print(f"❌ Analytics Blueprint: {e}")

print("\n4. Testando aplicação completa...")
try:
    from app import create_app
    app = create_app()
    print(f"✅ App criada: {app.name}")
    print(f"✅ Blueprints registrados: {len(app.blueprints)}")
    
    # Listar todas as rotas
    print("\n📋 ROTAS REGISTRADAS:")
    for rule in app.url_map.iter_rules():
        print(f"  {rule.methods} {rule.rule} -> {rule.endpoint}")
        
except Exception as e:
    print(f"❌ App: {e}")
    import traceback
    traceback.print_exc()

print("\n✅ Teste concluído!")