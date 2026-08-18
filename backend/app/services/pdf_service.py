"""
Serviço de processamento de PDFs
"""

import os
import hashlib
from datetime import datetime
from pathlib import Path
from typing import Tuple, Optional
from pypdf import PdfReader, PdfWriter
import pypdf
from flask import current_app

class PDFService:
    """Serviço para manipulação de arquivos PDF"""
    
    def __init__(self):
        self.supported_extensions = ['.pdf']
    
    def validate_pdf(self, file_path: str) -> Tuple[bool, str]:
        """Valida se o arquivo é um PDF válido"""
        try:
            if not os.path.exists(file_path):
                return False, "Arquivo não encontrado"
            
            # Verificar extensão
            if not file_path.lower().endswith('.pdf'):
                return False, "Arquivo não é um PDF"
            
            # Tentar ler o PDF
            with open(file_path, 'rb') as file:
                reader = PdfReader(file)
                
                # Verificar se tem pelo menos 1 página
                if len(reader.pages) == 0:
                    return False, "PDF vazio ou corrompido"
                
                # Tentar acessar primeira página
                first_page = reader.pages[0]
                _ = first_page.extract_text()  # Força leitura
            
            return True, "PDF válido"
            
        except Exception as e:
            return False, f"Erro ao validar PDF: {str(e)}"
    
    def calculate_hash(self, file_path: str) -> str:
        """Calcula hash SHA256 do arquivo"""
        hash_sha256 = hashlib.sha256()
        
        try:
            with open(file_path, 'rb') as f:
                for chunk in iter(lambda: f.read(8192), b''):
                    hash_sha256.update(chunk)
            return hash_sha256.hexdigest()
        except Exception as e:
            raise Exception(f"Erro ao calcular hash: {str(e)}")
    
    def get_file_size(self, file_path: str) -> int:
        """Obtém tamanho do arquivo em bytes"""
        try:
            return os.path.getsize(file_path)
        except Exception as e:
            raise Exception(f"Erro ao obter tamanho: {str(e)}")
    
    def get_page_count(self, file_path: str) -> int:
        """Obtém número de páginas do PDF"""
        try:
            with open(file_path, 'rb') as file:
                reader = PdfReader(file)
                return len(reader.pages)
        except Exception as e:
            return 0
    
    def extract_metadata(self, file_path: str) -> dict:
        """Extrai metadados existentes do PDF"""
        try:
            with open(file_path, 'rb') as file:
                reader = PdfReader(file)
                metadata = reader.metadata or {}
                
                return {
                    'title': metadata.get('/Title', ''),
                    'author': metadata.get('/Author', ''),
                    'subject': metadata.get('/Subject', ''),
                    'creator': metadata.get('/Creator', ''),
                    'producer': metadata.get('/Producer', ''),
                    'creation_date': metadata.get('/CreationDate', ''),
                    'modification_date': metadata.get('/ModDate', ''),
                    'pages': len(reader.pages)
                }
        except Exception as e:
            return {'error': str(e)}
    
    def add_metadata(self, input_path: str, metadata: dict, output_path: str) -> Tuple[bool, str]:
        """Adiciona metadados ao PDF"""
        try:
            with open(input_path, 'rb') as input_file:
                reader = PdfReader(input_file)
                writer = PdfWriter()
                
                # Copiar todas as páginas
                for page in reader.pages:
                    writer.add_page(page)
                
                # Adicionar metadados
                writer.add_metadata({
                    '/Title': metadata.get('title', ''),
                    '/Author': metadata.get('author', ''),
                    '/Subject': metadata.get('subject', ''),
                    '/Creator': 'PDF Manager v2.0',
                    '/Producer': f"{current_app.config.get('COMPANY_NAME', 'Example Organization')} - {metadata.get('digitalization_location', '')}",
                    '/CreationDate': datetime.utcnow().strftime('D:%Y%m%d%H%M%S'),
                    '/ModDate': datetime.utcnow().strftime('D:%Y%m%d%H%M%S'),
                    '/Custom': f"ID:{metadata.get('identifier', '')};Hash:{metadata.get('hash_sha256', '')[:16]}"
                })
                
                # Salvar arquivo com metadados
                os.makedirs(os.path.dirname(output_path), exist_ok=True)
                with open(output_path, 'wb') as output_file:
                    writer.write(output_file)
            
            return True, "Metadados adicionados com sucesso"
            
        except Exception as e:
            return False, f"Erro ao adicionar metadados: {str(e)}"
    
    def merge_pdfs(self, pdf_paths: list, output_path: str) -> Tuple[bool, str]:
        """Mescla múltiplos PDFs em um só"""
        try:
            writer = PdfWriter()
            
            for pdf_path in pdf_paths:
                if not os.path.exists(pdf_path):
                    continue
                    
                with open(pdf_path, 'rb') as file:
                    reader = PdfReader(file)
                    for page in reader.pages:
                        writer.add_page(page)
            
            os.makedirs(os.path.dirname(output_path), exist_ok=True)
            with open(output_path, 'wb') as output_file:
                writer.write(output_file)
            
            return True, f"PDFs mesclados em {output_path}"
            
        except Exception as e:
            return False, f"Erro ao mesclar PDFs: {str(e)}"
    
    def split_pdf(self, input_path: str, output_dir: str, pages_per_file: int = 1) -> Tuple[bool, str]:
        """Divide PDF em arquivos menores"""
        try:
            with open(input_path, 'rb') as file:
                reader = PdfReader(file)
                total_pages = len(reader.pages)
                
                if total_pages == 0:
                    return False, "PDF vazio"
                
                os.makedirs(output_dir, exist_ok=True)
                
                files_created = []
                for i in range(0, total_pages, pages_per_file):
                    writer = PdfWriter()
                    
                    # Adicionar páginas ao writer
                    for page_num in range(i, min(i + pages_per_file, total_pages)):
                        writer.add_page(reader.pages[page_num])
                    
                    # Salvar arquivo
                    base_name = Path(input_path).stem
                    output_file = os.path.join(output_dir, f"{base_name}_part_{i//pages_per_file + 1}.pdf")
                    
                    with open(output_file, 'wb') as output:
                        writer.write(output)
                    
                    files_created.append(output_file)
                
                return True, f"{len(files_created)} arquivos criados"
                
        except Exception as e:
            return False, f"Erro ao dividir PDF: {str(e)}"
    
    def add_watermark(self, input_path: str, output_path: str, watermark_text: str) -> Tuple[bool, str]:
        """Adiciona marca d'água ao PDF"""
        try:
            # Por enquanto, apenas copia o arquivo
            # TODO: Implementar marca d'água real com reportlab
            import shutil
            shutil.copy2(input_path, output_path)
            
            return True, "Marca d'água adicionada (placeholder)"
            
        except Exception as e:
            return False, f"Erro ao adicionar marca d'água: {str(e)}"