"""
Modelos do banco de dados (User, Document, AuditLog)
"""

from datetime import datetime
from enum import Enum
from flask_jwt_extended import create_access_token, create_refresh_token
from app.extensions import db, bcrypt


class UserRole(Enum):
    ADMIN = "admin"
    USER = "user"
    VIEWER = "viewer"


class User(db.Model):
    __tablename__ = 'users'
    
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(120), unique=True, nullable=False, index=True)
    name = db.Column(db.String(100), nullable=False)
    password_hash = db.Column(db.String(128), nullable=False)
    role = db.Column(db.Enum(UserRole), nullable=False, default=UserRole.USER)
    is_active = db.Column(db.Boolean, default=True)
    
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    last_login = db.Column(db.DateTime)
    
    documents = db.relationship('Document', back_populates='uploader', lazy='dynamic')
    audit_logs = db.relationship('AuditLog', back_populates='user', lazy='dynamic')
    
    def set_password(self, password: str):
        self.password_hash = bcrypt.generate_password_hash(password).decode('utf-8')
    
    def check_password(self, password: str) -> bool:
        return bcrypt.check_password_hash(self.password_hash, password)
    
    def generate_tokens(self):
        claims = {
            "role": self.role.value,
            "name": self.name
        }
        
        return {
            'access_token': create_access_token(
                identity=str(self.id),  # ✅ CONVERTER PARA STRING
                additional_claims=claims
            ),
            'refresh_token': create_refresh_token(
                identity=str(self.id)  # ✅ CONVERTER PARA STRING
            )
        }

    def has_permission(self, permission: str) -> bool:
        permissions = {
            UserRole.ADMIN: ['create', 'read', 'update', 'delete', 'manage_users'],
            UserRole.USER: ['create', 'read', 'update'],
            UserRole.VIEWER: ['read']
        }
        return permission in permissions.get(self.role, [])
    
    def to_dict(self):
        return {
            'id': self.id,
            'email': self.email,
            'name': self.name,
            'role': self.role.value,
            'is_active': self.is_active,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'last_login': self.last_login.isoformat() if self.last_login else None
        }


class Document(db.Model):
    __tablename__ = 'documents'
    
    id = db.Column(db.Integer, primary_key=True)
    filename = db.Column(db.String(255), nullable=False)
    original_filename = db.Column(db.String(255), nullable=False)
    file_path = db.Column(db.String(500), nullable=False)
    file_size = db.Column(db.Integer, nullable=False)
    file_hash = db.Column(db.String(64), unique=True, nullable=False, index=True)
    
    title = db.Column(db.String(255))
    author = db.Column(db.String(255))
    subject = db.Column(db.String(500))
    doc_type = db.Column(db.String(100))
    keywords = db.Column(db.String(500))
    
    is_signed = db.Column(db.Boolean, default=False)
    signed_at = db.Column(db.DateTime)
    
    uploaded_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    uploaded_by = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    uploader = db.relationship('User', back_populates='documents')
    
    # ✅ CORREÇÃO: Mudar lazy=True para lazy='dynamic'
    audit_logs = db.relationship('AuditLog', 
                                  back_populates='document', 
                                  lazy='dynamic',  # ✅ MUDOU AQUI
                                  cascade='all, delete-orphan')
    
    def to_dict(self):
        return {
            'id': self.id,
            'filename': self.filename,
            'original_filename': self.original_filename,
            'file_size': self.file_size,
            'file_hash': self.file_hash,
            'title': self.title,
            'author': self.author,
            'subject': self.subject,
            'doc_type': self.doc_type,
            'keywords': self.keywords,
            'is_signed': self.is_signed,
            'signed_at': self.signed_at.isoformat() if self.signed_at else None,
            'uploaded_at': self.uploaded_at.isoformat(),
            'updated_at': self.updated_at.isoformat(),
            'uploaded_by': self.uploaded_by
        }


class AuditLog(db.Model):
    __tablename__ = 'audit_logs'
    
    id = db.Column(db.Integer, primary_key=True)
    document_id = db.Column(db.Integer, db.ForeignKey('documents.id'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    action = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text)
    ip_address = db.Column(db.String(50))
    user_agent = db.Column(db.String(500))
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)
    
    document = db.relationship('Document', back_populates='audit_logs')
    user = db.relationship('User', back_populates='audit_logs')
    
    def to_dict(self):
        return {
            'id': self.id,
            'action': self.action,
            'description': self.description,
            'timestamp': self.timestamp.isoformat() if self.timestamp else None,
            'ip_address': self.ip_address,
            'user_agent': self.user_agent,
            'document_id': self.document_id,
            'user_id': self.user_id
        }
