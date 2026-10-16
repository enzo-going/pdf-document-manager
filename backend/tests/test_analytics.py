"""
Analytics: resumo do dashboard, gráficos e exportação.

Usuário comum vê só os próprios documentos no resumo e na exportação; admin vê
tudo e ainda a contagem de usuários.
"""

import pytest
from flask_jwt_extended import create_access_token

from app import create_app
from app.extensions import db
from app.models import AuditLog, Document, User, UserRole


def _usuario(email, papel):
    user = User(name=email, email=email, role=papel, is_active=True)
    user.set_password('senha-teste-123')
    db.session.add(user)
    db.session.flush()
    return user


def _documento(dono, nome, **campos):
    doc = Document(filename=nome, original_filename=nome, file_path=nome, file_size=1,
                   file_hash=nome.ljust(64, '0'), uploaded_by=dono.id, **campos)
    db.session.add(doc)
    db.session.flush()
    return doc


@pytest.fixture
def cenario():
    """Admin sem documentos; Ana com 2 (um assinado, tipos diferentes); Bia com 1."""
    app = create_app('testing')
    with app.app_context():
        db.create_all()
        admin = _usuario('admin@example.com', UserRole.ADMIN)
        ana = _usuario('ana@example.com', UserRole.USER)
        bia = _usuario('bia@example.com', UserRole.USER)
        d1 = _documento(ana, 'ana-contrato.pdf', doc_type='contrato', is_signed=True)
        _documento(ana, 'ana-ata.pdf', doc_type='ata')
        d3 = _documento(bia, 'bia-contrato.pdf', doc_type='contrato')
        db.session.add_all([AuditLog(document_id=d1.id, user_id=ana.id, action='upload'),
                            AuditLog(document_id=d3.id, user_id=bia.id, action='upload')])
        db.session.commit()
        tokens = {u.email.split('@')[0]: {'Authorization': f'Bearer {create_access_token(identity=str(u.id))}'}
                  for u in (admin, ana, bia)}
        yield app.test_client(), tokens
        db.session.remove()
        db.drop_all()


def test_resumo_do_admin_traz_todos_e_a_contagem_de_usuarios(cenario):
    cliente, tokens = cenario

    dados = cliente.get('/api/analytics/dashboard/summary', headers=tokens['admin']).get_json()['data']

    assert len(dados['recent_documents']) == 3
    assert (dados['totals']['active_users'], dados['totals']['total_users']) == (3, 3)
    assert dados['totals']['documents_today'] == 3
    assert dados['signing_rate'] == 33.3


def test_graficos_por_tipo_assinatura_e_linha_do_tempo(cenario):
    cliente, tokens = cenario

    def grafico(nome):
        resp = cliente.get(f'/api/analytics/charts/{nome}', headers=tokens['ana'])
        assert resp.status_code == 200
        return resp.get_json()['data']

    assert grafico('documents-by-type')['basic'] == [{'type': 'contrato', 'count': 2}, {'type': 'ata', 'count': 1}]
    assert grafico('signature-status')['basic'] == [{'status': 'Assinados', 'count': 1},
                                                    {'status': 'Não Assinados', 'count': 2}]
    linha = grafico('documents-timeline')
    assert [p['count'] for p in linha['basic']] == [3]
    assert linha['period_days'] == 30


def test_exportacao_respeita_o_dono_dos_documentos(cenario):
    cliente, tokens = cenario

    def exportar(quem, tipo):
        resp = cliente.get('/api/analytics/reports/export', headers=tokens[quem], query_string={'type': tipo})
        assert resp.status_code == 200
        return resp.get_json()['data']['data']

    assert sorted(d['original_filename'] for d in exportar('bia', 'documents')) == ['bia-contrato.pdf']
    assert len(exportar('admin', 'documents')) == 3
    assert [log['user_id'] for log in exportar('bia', 'audit_log')] == [3]
    assert len(exportar('admin', 'audit_log')) == 2


def test_exportacao_recusa_tipo_desconhecido(cenario):
    cliente, tokens = cenario

    resp = cliente.get('/api/analytics/reports/export', headers=tokens['ana'], query_string={'type': 'senhas'})

    assert resp.status_code == 400
