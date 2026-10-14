#!/usr/bin/env python3
"""
PDF Manager - Sistema de Gerenciamento de PDFs com Certificação Digital
"""

import os
from dotenv import load_dotenv

# Carregar variáveis de ambiente
load_dotenv()

from app import create_app
from app.config import opcoes_servidor_dev

# Criar aplicação
app = create_app()

if __name__ == '__main__':
    host, port, debug_mode = opcoes_servidor_dev()
    
    print(f"""
🚀 PDF Manager iniciado!
📋 Ambiente: {os.getenv('FLASK_ENV', 'development')}
🌐 URL: http://{host}:{port}
📊 Dashboard: http://localhost:{port}/api/analytics/dashboard/summary
🔐 Auth: http://localhost:{port}/api/auth/login
    """)
    
    app.run(
        host=host,
        port=port,
        debug=debug_mode
    )