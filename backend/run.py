#!/usr/bin/env python3
"""
PDF Manager - Sistema de Gerenciamento de PDFs com Certificação Digital
"""

import os
from dotenv import load_dotenv

# Carregar variáveis de ambiente
load_dotenv()

from app import create_app

# Criar aplicação
app = create_app()

if __name__ == '__main__':
    # Configuração para desenvolvimento
    debug_mode = os.getenv('FLASK_ENV') == 'development'
    port = int(os.getenv('PORT', 5000))
    
    print(f"""
🚀 PDF Manager iniciado!
📋 Ambiente: {os.getenv('FLASK_ENV', 'development')}
🌐 URL: http://localhost:{port}
📊 Dashboard: http://localhost:{port}/api/analytics/dashboard/summary
🔐 Auth: http://localhost:{port}/api/auth/login
    """)
    
    app.run(
        host='0.0.0.0',
        port=port,
        debug=debug_mode
    )