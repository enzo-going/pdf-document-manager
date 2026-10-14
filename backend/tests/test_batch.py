"""
Processamento em lote de metadados: o que a auditoria registra.
"""

from app import create_app
from app.extensions import db
from app.models import AuditLog, Document, User, UserRole
from app.services.batch_processor import BatchProcessor


def _documento(user_id, **campos):
    doc = Document(
        filename='a.pdf', original_filename='a.pdf', file_path='a.pdf', file_size=10,
        file_hash='h' * 64, uploaded_by=user_id, **campos,
    )
    db.session.add(doc)
    db.session.commit()
    return doc


def test_auditoria_do_lote_registra_valor_anterior_e_novo():
    app = create_app('testing')
    with app.app_context():
        db.create_all()
        user = User(name='Operador', email='op@example.com', role=UserRole.USER, is_active=True)
        user.set_password('senha-teste-123')
        db.session.add(user)
        db.session.commit()
        doc = _documento(user.id, title='Contrato antigo', author='Maria Souza', doc_type='ata')

        resultado = BatchProcessor()._process_task({
            'document_ids': [doc.id],
            'metadata': {'title': 'Contrato novo', 'author': 'Maria Souza', 'doc_type': 'contrato'},
            'user_id': user.id,
            'ip_address': '127.0.0.1',
        })

        assert resultado['results'][0]['success'] is True
        log = AuditLog.query.filter_by(action='metadata_batch_update').one()
        assert "title: 'Contrato antigo' → 'Contrato novo'" in log.description
        assert "doc_type: 'ata' → 'contrato'" in log.description
        # Autor reenviado igual não é mudança.
        assert 'author' not in log.description
