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


def test_mesmo_nome_no_mesmo_envio_nao_sobrescreve_o_outro_arquivo(cliente, auth):
    # Dois PDFs diferentes chamados "scan.pdf" (de pastas diferentes) no mesmo
    # upload: cada documento tem de baixar o próprio conteúdo.
    um, outro = _pdf(marca='um'), _pdf(marca='outro')
    resp = _enviar(cliente, auth, ('scan.pdf', um), ('scan.pdf', outro))

    ids = [r['document_id'] for r in resp.get_json()['data']]
    assert len(ids) == 2
    baixados = [cliente.get(f'/api/documents/{i}/download', headers=auth).data for i in ids]
    assert baixados == [um, outro]


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


def test_exclusao_apaga_o_arquivo_e_mantem_a_auditoria(cliente, auth):
    doc_id = _enviar(cliente, auth, ('apagar.pdf', _pdf())).get_json()['data'][0]['document_id']
    caminho = db.session.get(Document, doc_id).file_path

    resp = cliente.delete(f'/api/documents/{doc_id}', headers=auth)

    assert resp.status_code == 200
    assert db.session.get(Document, doc_id) is None
    assert not os.path.exists(caminho)
    # O registro de quem apagou (e o histórico do documento) sobrevive à exclusão,
    # agora sem apontar para o documento que não existe mais.
    logs = AuditLog.query.filter(AuditLog.description.contains('apagar')).all()
    assert {log.action for log in logs} == {'upload', 'document_deleted'}
    assert all(log.document_id is None for log in logs)


def test_exclusao_em_lote_apaga_arquivos_e_mantem_a_auditoria(cliente, auth):
    resp = _enviar(cliente, auth, ('lote1.pdf', _pdf(marca='1')), ('lote2.pdf', _pdf(marca='2')))
    ids = [r['document_id'] for r in resp.get_json()['data']]
    caminhos = [db.session.get(Document, i).file_path for i in ids]

    resp = cliente.post('/api/documents/delete_many', headers=auth, json={'document_ids': ids + [999]})

    corpo = resp.get_json()
    assert corpo['deleted'] == 2
    assert corpo['errors'] == [{'id': 999, 'error': 'Documento não encontrado'}]
    assert Document.query.count() == 0
    assert not any(os.path.exists(c) for c in caminhos)
    assert AuditLog.query.filter_by(action='document_deleted').count() == 2
