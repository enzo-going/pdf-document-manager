"""
Documentos: upload, listagem, detalhe, metadados, download e exclusão.

Os PDFs são gerados aqui mesmo com o pypdf; a pasta de upload é a `tmp_path`
de cada teste, então nada sai do diretório temporário.
"""

import io
import os

import pytest
from pypdf import PdfWriter

from app import create_app
from app.extensions import db
from app.models import AuditLog, Document, User, UserRole


def _pdf(paginas=1, marca='a'):
    """PDF válido; `marca` muda os bytes (e o hash) sem mudar o resto."""
    writer = PdfWriter()
    for _ in range(paginas):
        writer.add_blank_page(width=200, height=200)
    writer.add_metadata({'/Title': f'teste {marca}'})
    buf = io.BytesIO()
    writer.write(buf)
    return buf.getvalue()


@pytest.fixture
def app_docs(tmp_path):
    app = create_app('testing')
    app.config['UPLOAD_FOLDER'] = str(tmp_path)
    with app.app_context():
        db.create_all()
        user = User(name='Operador', email='op@example.com', role=UserRole.USER, is_active=True)
        user.set_password('senha-teste-123')
        db.session.add(user)
        db.session.commit()
        yield app
        db.session.remove()
        db.drop_all()


@pytest.fixture
def cliente(app_docs):
    return app_docs.test_client()


@pytest.fixture
def auth(cliente):
    resp = cliente.post('/api/auth/login', json={'email': 'op@example.com', 'password': 'senha-teste-123'})
    return {'Authorization': f"Bearer {resp.get_json()['access_token']}"}


def _enviar(cliente, auth, *arquivos):
    """arquivos: pares (nome, bytes). Vão todos no mesmo request, como faz a interface."""
    dados = {'files[]': [(io.BytesIO(conteudo), nome) for nome, conteudo in arquivos]}
    return cliente.post('/api/documents/upload', headers=auth, data=dados,
                        content_type='multipart/form-data')


def test_rotas_exigem_login(cliente):
    assert cliente.get('/api/documents/').status_code == 401
    assert cliente.post('/api/documents/upload').status_code == 401


def test_upload_cria_documento_com_titulo_paginas_e_auditoria(cliente, auth, tmp_path):
    resp = _enviar(cliente, auth, ('exame.pdf', _pdf(paginas=3)))

    assert resp.status_code == 200
    item = resp.get_json()['data'][0]
    assert item['success'] is True
    assert item['title'] == 'Prontuário de exame'
    assert item['pages'] == 3

    doc = db.session.get(Document, item['document_id'])
    assert doc.original_filename == 'exame.pdf'
    assert os.path.dirname(doc.file_path) == str(tmp_path)
    assert os.path.exists(doc.file_path)
    assert AuditLog.query.filter_by(document_id=doc.id, action='upload').count() == 1


def test_upload_recusa_extensao_e_pdf_invalido_sem_deixar_arquivo(cliente, auth, tmp_path):
    resp = _enviar(cliente, auth, ('planilha.xlsx', b'nao e pdf'), ('falso.pdf', b'%PDF-isto nao e um pdf'))

    erros = {r['filename']: r['error'] for r in resp.get_json()['data']}
    assert erros['planilha.xlsx'] == 'Apenas arquivos PDF são permitidos'
    assert erros['falso.pdf'] == 'PDF inválido ou corrompido'
    assert Document.query.count() == 0
    assert os.listdir(tmp_path) == []


def test_upload_recusa_duplicata_pelo_conteudo(cliente, auth, tmp_path):
    conteudo = _pdf(marca='igual')
    _enviar(cliente, auth, ('primeiro.pdf', conteudo))

    resp = _enviar(cliente, auth, ('copia.pdf', conteudo))

    assert resp.get_json()['data'][0]['error'] == 'Arquivo duplicado já existe no sistema'
    assert Document.query.count() == 1
    assert len(os.listdir(tmp_path)) == 1


def test_listagem_filtra_por_busca_e_tipo(cliente, auth):
    resp = _enviar(cliente, auth, ('contrato aluguel.pdf', _pdf(marca='1')), ('ata reuniao.pdf', _pdf(marca='2')))
    contrato_id = resp.get_json()['data'][0]['document_id']
    cliente.post(f'/api/documents/{contrato_id}/metadata', headers=auth, json={'doc_type': 'CONTRATO'})

    def titulos(**params):
        dados = cliente.get('/api/documents/', headers=auth, query_string=params).get_json()['data']
        return sorted(d['original_filename'] for d in dados['documents'])

    assert titulos() == ['ata_reuniao.pdf', 'contrato_aluguel.pdf']
    assert titulos(search='aluguel') == ['contrato_aluguel.pdf']
    assert titulos(doc_type='Contrato') == ['contrato_aluguel.pdf']


def test_metadados_atualizam_e_aparecem_no_detalhe_com_auditoria(cliente, auth):
    doc_id = _enviar(cliente, auth, ('laudo.pdf', _pdf())).get_json()['data'][0]['document_id']

    resp = cliente.post(f'/api/documents/{doc_id}/metadata', headers=auth,
                        json={'title': 'Laudo 2026', 'author': 'Dra. Ana', 'doc_type': 'LAUDO'})
    assert resp.status_code == 200

    detalhe = cliente.get(f'/api/documents/{doc_id}', headers=auth).get_json()['data']
    assert (detalhe['title'], detalhe['author'], detalhe['doc_type']) == ('Laudo 2026', 'Dra. Ana', 'laudo')
    assert {log['action'] for log in detalhe['audit_logs']} == {'upload', 'metadata_added'}


def test_download_devolve_o_arquivo_e_registra(cliente, auth):
    conteudo = _pdf(paginas=2)
    doc_id = _enviar(cliente, auth, ('receita.pdf', conteudo)).get_json()['data'][0]['document_id']

    resp = cliente.get(f'/api/documents/{doc_id}/download', headers=auth)

    assert resp.status_code == 200
    assert resp.data == conteudo
    assert 'receita.pdf' in resp.headers['Content-Disposition']
    assert AuditLog.query.filter_by(document_id=doc_id, action='download').count() == 1
