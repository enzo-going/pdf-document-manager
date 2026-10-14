#!/usr/bin/env python3
"""
PDF Manager - Sistema de Gerenciamento de PDFs com Certificação Digital
"""

import os
import sys
from dotenv import load_dotenv

# No Windows, com a saída indo para arquivo ou pipe (tarefa agendada, serviço),
# o Python usa cp1252 e os emojis das mensagens derrubavam o servidor na subida.
for _stream in (sys.stdout, sys.stderr):
    if hasattr(_stream, 'reconfigure'):
        _stream.reconfigure(encoding='utf-8', errors='replace')

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