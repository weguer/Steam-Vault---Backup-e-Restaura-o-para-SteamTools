import sys
import os
import shutil
import json
import subprocess
import argparse
import time
import pickle
from pathlib import Path

# --- AUTO-INSTALAÇÃO DE DEPENDÊNCIAS ---
def install_package(package):
    """Instala um pacote pip automaticamente."""
    print(f"[SETUP] A biblioteca '{package}' não foi encontrada.")
    print(f"[SETUP] Instalando {package} automaticamente, aguarde...")
    try:
        subprocess.check_call([sys.executable, "-m", "pip", "install", package])
        print(f"[SETUP] {package} instalado com sucesso!")
        return True
    except Exception as e:
        print(f"[ERRO] Falha ao instalar {package}: {e}")
        return False

# Tenta importar PyQt6 para modo Gráfico (Com Auto-Install)
try:
    from PyQt6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, 
                                 QHBoxLayout, QLabel, QPushButton, QFileDialog, 
                                 QProgressBar, QFrame, QMessageBox, QTextEdit, QTabWidget,
                                 QListWidget, QListWidgetItem, QDialog, QLineEdit)
    from PyQt6.QtCore import Qt, QThread, pyqtSignal, QPoint
    from PyQt6.QtGui import QCursor, QIcon
    GUI_AVAILABLE = True
except ImportError:
    # Se falhar, tenta instalar e importa de novo
    if install_package("PyQt6"):
        try:
            from PyQt6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, 
                                         QHBoxLayout, QLabel, QPushButton, QFileDialog, 
                                         QProgressBar, QFrame, QMessageBox, QTextEdit, QTabWidget,
                                         QListWidget, QListWidgetItem, QDialog, QLineEdit)
            from PyQt6.QtCore import Qt, QThread, pyqtSignal, QPoint
            from PyQt6.QtGui import QCursor, QIcon
            GUI_AVAILABLE = True
        except ImportError:
            print("[ERRO] Instalação falhou ou biblioteca ainda inacessível.")
            GUI_AVAILABLE = False
    else:
        GUI_AVAILABLE = False

# Importações para Google Drive
try:
    from google.auth.transport.requests import Request
    from google_auth_oauthlib.flow import InstalledAppFlow
    from googleapiclient.discovery import build
    from googleapiclient.http import MediaFileUpload, MediaIoBaseDownload
    import io
    import os
    from pathlib import Path
    
    # Carrega variáveis de ambiente
    if os.path.exists('.env'):
        with open('.env', 'r') as f:
            for line in f:
                if '=' in line and not line.strip().startswith('#'):
                    key, value = line.strip().split('=', 1)
                    os.environ[key] = value
    
    GOOGLE_DRIVE_AVAILABLE = True
except ImportError:
    # Tenta instalar dependências do Google Drive
    packages_needed = ["google-api-python-client", "google-auth-httplib2", "google-auth-oauthlib"]
    google_packages_installed = True
    for pkg in packages_needed:
        if not install_package(pkg):
            google_packages_installed = False
            break
    
    if google_packages_installed:
        try:
            from google.auth.transport.requests import Request
            from google_auth_oauthlib.flow import InstalledAppFlow
            from googleapiclient.discovery import build
            from googleapiclient.http import MediaFileUpload, MediaIoBaseDownload
            import io
            import os
            from pathlib import Path
            
            # Carrega variáveis de ambiente
            if os.path.exists('.env'):
                with open('.env', 'r') as f:
                    for line in f:
                        if '=' in line and not line.strip().startswith('#'):
                            key, value = line.strip().split('=', 1)
                            os.environ[key] = value
            
            GOOGLE_DRIVE_AVAILABLE = True
        except ImportError:
            GOOGLE_DRIVE_AVAILABLE = False
            print("[AVISO] Google Drive indisponível - dependências não instaladas corretamente")
    else:
        GOOGLE_DRIVE_AVAILABLE = False
        print("[AVISO] Google Drive indisponível - falha ao instalar dependências")

# --- CONFIGURAÇÕES DE TEMA (MIDNIGHT PRO) ---
THEME = {
    "bg_main": "#0b0f19",       # Azul Profundo
    "bg_panel": "#111827",      # Painel Escuro
    "accent": "#3b82f6",        # Azul Profissional
    "success": "#10b981",       # Verde Sucesso
    "error": "#ef4444",         # Vermelho Erro
    "warning": "#f59e0b",       # Amarelo Aviso
    "text_main": "#f3f4f6",     # Branco
    "text_dim": "#9ca3af",      # Cinza
    "btn_bg": "#1f2937",        # Botões
    "btn_border": "#374151",
    "close_hover": "#ef4444"
}

# --- IDENTIDADE ---
APP_NAME = "STEAM VAULT"
CONFIG_FILE = "vault_config.json"
DEFAULT_CONFIG = {
    "steam_path": "", 
    "backup_path": "",
    "gdrive_credentials": "",
    "gdrive_token": ""
}

# --- CONFIGURAÇÕES GOOGLE DRIVE ---
SCOPES = [
    'https://www.googleapis.com/auth/drive.file',
    'https://www.googleapis.com/auth/drive.metadata.readonly'
]
GDRIVE_TOKEN_FILE = "gdrive_token.pickle"
GDRIVE_CREDENTIALS_FILE = "credentials.json"

# --- SERVIÇO GOOGLE DRIVE ---
class GoogleDriveService:
    def __init__(self, logger_callback=None):
        self.creds = None
        self.service = None
        self.log = logger_callback or print
        self.authenticate()
    
    def authenticate(self):
        """Autentica com Google Drive usando OAuth 2.0"""
        try:
            # Carrega token existente
            if os.path.exists(GDRIVE_TOKEN_FILE):
                with open(GDRIVE_TOKEN_FILE, 'rb') as token:
                    self.creds = pickle.load(token)
            
            # Se não há credenciais válidas, solicita autenticação
            if not self.creds or not self.creds.valid:
                if self.creds and self.creds.expired and self.creds.refresh_token:
                    self.creds.refresh(Request())
                else:
                    if not os.path.exists(GDRIVE_CREDENTIALS_FILE):
                        self.log(f"[ERRO] Arquivo {GDRIVE_CREDENTIALS_FILE} não encontrado.")
                        self.log("[INFO] Baixe suas credenciais do Google Cloud Console.")
                        return False
                    
                    # Lê as URIs de redirecionamento do .env ou usa padrão
                    redirect_uris = os.environ.get('GOOGLE_DRIVE_REDIRECT_URIS', 
                                                  'http://localhost:3000/oauth2callback,'
                                                  'http://localhost:3001/oauth2callback,'
                                                  'http://localhost:3002/oauth2callback,'
                                                  'http://localhost:3003/oauth2callback,'
                                                  'http://localhost:3004/oauth2callback')
                    
                    redirect_uris_list = [uri.strip() for uri in redirect_uris.split(',') if uri.strip()]
                    
                    # Cria flow com URIs personalizadas
                    flow = InstalledAppFlow.from_client_secrets_file(
                        GDRIVE_CREDENTIALS_FILE, SCOPES)
                    
                    # Define as URIs de redirecionamento
                    flow.redirect_uri = redirect_uris_list[0] if redirect_uris_list else 'urn:ietf:wg:oauth:2.0:oob'
                    
                    self.creds = flow.run_local_server(port=0)
                
                # Salva credenciais para próxima execução
                with open(GDRIVE_TOKEN_FILE, 'wb') as token:
                    pickle.dump(self.creds, token)
            
            self.service = build('drive', 'v3', credentials=self.creds)
            
            # Testa a conexão tentando listar arquivos em vez de about.get()
            try:
                # Tenta listar algumas pastas na raiz para testar a conexão
                results = self.service.files().list(
                    q="'root' in parents and mimeType='application/vnd.google-apps.folder' and trashed=false",
                    fields="files(id, name)",
                    pageSize=1
                ).execute()
                
                folders = results.get('files', [])
                if folders:
                    self.log(f"[SUCESSO] Autenticado no Google Drive. Encontradas {len(folders)} pastas na raiz.")
                else:
                    self.log("[SUCESSO] Autenticado no Google Drive. Nenhuma pasta encontrada na raiz.")
            except Exception as e:
                # Mesmo que falhe o teste, se a autenticação funcionou, continua
                self.log(f"[AVISO] Autenticado no Google Drive, mas teste de listagem falhou: {e}")
                self.log("[SUCESSO] Autenticado no Google Drive")
            
            return True
            
        except Exception as e:
            self.log(f"[ERRO] Falha na autenticação do Google Drive: {e}")
            return False
    
    def test_connection(self):
        """Testa a conexão com o Google Drive"""
        try:
            # Testa listando algumas pastas na raiz
            results = self.service.files().list(
                q="'root' in parents and mimeType='application/vnd.google-apps.folder' and trashed=false",
                fields="files(id, name)",
                pageSize=5
            ).execute()
            
            folders = results.get('files', [])
            self.log(f"[INFO] Conexão testada com sucesso. Encontradas {len(folders)} pastas na raiz:")
            for folder in folders:
                self.log(f"[INFO]   - {folder['name']} (ID: {folder['id']})")
            return True
        except Exception as e:
            self.log(f"[ERRO] Falha no teste de conexão: {e}")
            # Mesmo com erro no teste, verifica se o serviço está ativo
            if hasattr(self, 'service') and self.service:
                self.log("[INFO] Serviço Google Drive ativo, mas operações podem estar limitadas")
                return True
            return False
    
    def create_folder(self, folder_name, parent_id='root'):
        """Cria uma pasta no Google Drive - abordagem W-Cloud com verificação de interrupção"""
        try:
            # Verifica se o backup foi interrompido antes de começar
            engine = None
            if hasattr(self, 'log') and hasattr(self.log.__self__, 'running'):
                engine = self.log.__self__
                if not engine.running:
                    self.log("[INFO] Criação de pasta interrompida")
                    return None
            # Re-inicializa o cliente para garantir configuração correta
            if not self.service:
                self.log("[ERRO] Serviço Google Drive não inicializado")
                return None
                
            folder_metadata = {
                'name': folder_name,
                'mimeType': 'application/vnd.google-apps.folder',
                'parents': [parent_id]
            }
            
            # Tenta criar a pasta com retry
            max_retries = 3
            for attempt in range(max_retries):
                # Verifica interrupção antes de cada tentativa
                if engine and not engine.running:
                    self.log("[INFO] Criação de pasta interrompida durante tentativa")
                    return None
                try:
                    response = self.service.files().create(
                        body=folder_metadata,
                        fields='id'
                    ).execute()
                    
                    folder_id = response.get('id')
                    if folder_id:
                        self.log(f"[SUCESSO] Pasta '{folder_name}' criada com ID: {folder_id}")
                        return folder_id
                    else:
                        self.log(f"[ERRO] Resposta vazia ao criar pasta '{folder_name}'")
                        return None
                        
                except Exception as e:
                    error_details = str(e)
                    # Tenta extrair detalhes mais específicos do erro
                    if hasattr(e, 'resp') and hasattr(e.resp, 'status'):
                        error_details += f" (HTTP {e.resp.status})"
                    if hasattr(e, 'error_details'):
                        error_details += f" - Details: {e.error_details}"
                    
                    self.log(f"[TENTATIVA {attempt + 1}/{max_retries}] Erro ao criar pasta '{folder_name}': {error_details}")
                    if attempt < max_retries - 1:
                        time.sleep(1)  # Espera antes de retry
                    else:
                        self.log(f"[ERRO] Falha permanente ao criar pasta '{folder_name}' após {max_retries} tentativas")
                        return None
            
        except Exception as e:
            self.log(f"[ERRO CRÍTICO] Exceção ao criar pasta '{folder_name}': {str(e)}")
            return None
    
    def find_folder(self, folder_name, parent_id='root'):
        """Procura uma pasta existente no Google Drive - abordagem W-Cloud"""
        try:
            if not self.service:
                self.log("[ERRO] Serviço Google Drive não inicializado")
                return None
                
            query = f"name='{folder_name}' and mimeType='application/vnd.google-apps.folder' and '{parent_id}' in parents and trashed=false"
            
            # Tenta encontrar a pasta com retry
            max_retries = 3
            for attempt in range(max_retries):
                try:
                    results = self.service.files().list(
                        q=query,
                        fields="files(id, name)",
                        pageSize=1
                    ).execute()
                    
                    items = results.get('files', [])
                    if items:
                        folder_id = items[0]['id']
                        self.log(f"[INFO] Pasta '{folder_name}' encontrada com ID: {folder_id}")
                        return folder_id
                    else:
                        self.log(f"[INFO] Pasta '{folder_name}' não encontrada")
                        return None
                        
                except Exception as e:
                    error_details = str(e)
                    # Tenta extrair detalhes mais específicos do erro
                    if hasattr(e, 'resp') and hasattr(e.resp, 'status'):
                        error_details += f" (HTTP {e.resp.status})"
                    if hasattr(e, 'error_details'):
                        error_details += f" - Details: {e.error_details}"
                    
                    self.log(f"[TENTATIVA {attempt + 1}/{max_retries}] Erro ao procurar pasta '{folder_name}': {error_details}")
                    if attempt < max_retries - 1:
                        time.sleep(1)
                    else:
                        self.log(f"[ERRO] Falha permanente ao procurar pasta '{folder_name}' após {max_retries} tentativas")
                        return None
            
        except Exception as e:
            self.log(f"[ERRO CRÍTICO] Exceção ao procurar pasta '{folder_name}': {str(e)}")
            return None
    
    def ensure_folder_exists(self, folder_name, parent_id='root'):
        """Garante que uma pasta exista, criando se necessário"""
        self.log(f"[INFO] Verificando pasta '{folder_name}' no pai '{parent_id}'")
        folder_id = self.find_folder(folder_name, parent_id)
        if not folder_id:
            self.log(f"[INFO] Pasta '{folder_name}' não encontrada, criando...")
            folder_id = self.create_folder(folder_name, parent_id)
            if folder_id:
                self.log(f"[SUCESSO] Pasta '{folder_name}' criada no Google Drive com ID: {folder_id}")
            else:
                self.log(f"[ERRO] Falha ao criar pasta '{folder_name}'")
        else:
            self.log(f"[INFO] Pasta '{folder_name}' já existe no Google Drive com ID: {folder_id}")
        return folder_id
    
    def upload_file(self, file_path, folder_id):
        """Faz upload de um arquivo para o Google Drive"""
        try:
            file_name = os.path.basename(file_path)
            file_metadata = {
                'name': file_name,
                'parents': [folder_id]
            }
            
            media = MediaFileUpload(file_path, resumable=True)
            file = self.service.files().create(
                body=file_metadata,
                media_body=media,
                fields='id'
            ).execute()
            
            self.log(f"[UPLOAD] {file_name} enviado para Google Drive")
            return file.get('id')
        except Exception as e:
            self.log(f"[ERRO] Falha no upload: {e}")
            return None
    
    def upload_folder(self, local_folder_path, gdrive_folder_id):
        """Faz upload recursivo de uma pasta para o Google Drive com verificação de interrupção"""
        try:
            # Verifica se temos acesso ao engine para checar interrupção
            engine = None
            if hasattr(self, 'log') and hasattr(self.log.__self__, 'running'):
                engine = self.log.__self__
            
            for root, dirs, files in os.walk(local_folder_path):
                # Verifica se o backup foi interrompido
                if engine and not engine.running:
                    self.log("[INFO] Upload interrompido pelo usuário")
                    return False
                    
                # Calcula o caminho relativo para manter a estrutura
                rel_path = os.path.relpath(root, local_folder_path)
                if rel_path == '.':
                    current_gdrive_folder_id = gdrive_folder_id
                else:
                    # Cria subpastas necessárias
                    folder_parts = rel_path.split(os.sep)
                    current_gdrive_folder_id = gdrive_folder_id
                    for part in folder_parts:
                        # Verifica interrupção novamente
                        if engine and not engine.running:
                            return False
                        subfolder_id = self.find_folder(part, current_gdrive_folder_id)
                        if not subfolder_id:
                            subfolder_id = self.create_folder(part, current_gdrive_folder_id)
                        current_gdrive_folder_id = subfolder_id
                        if not current_gdrive_folder_id:
                            self.log(f"[ERRO] Falha ao criar subpasta {part}")
                            return False
                
                # Faz upload dos arquivos nesta pasta
                for file_name in files:
                    # Verifica interrupção antes de cada upload
                    if engine and not engine.running:
                        return False
                    file_path = os.path.join(root, file_name)
                    self.upload_file(file_path, current_gdrive_folder_id)
                    
            return True
        except Exception as e:
            self.log(f"[ERRO] Falha no upload da pasta: {e}")
            return False
    
    def list_backups(self, folder_name="SteamVault_Backup"):
        """Lista backups disponíveis no Google Drive"""
        try:
            folder_id = self.find_folder(folder_name)
            if not folder_id:
                return []
            
            query = f"'{folder_id}' in parents and mimeType='application/vnd.google-apps.folder' and trashed=false"
            results = self.service.files().list(q=query, fields="files(id, name, createdTime)").execute()
            items = results.get('files', [])
            return sorted(items, key=lambda x: x.get('createdTime', ''), reverse=True)
        except Exception as e:
            self.log(f"[ERRO] Falha ao listar backups: {e}")
            return []
    
    def download_folder(self, gdrive_folder_id, local_destination):
        """Baixa uma pasta do Google Drive recursivamente com verificação de interrupção"""
        try:
            # Verifica se temos acesso ao engine através do worker
            engine = None
            if hasattr(self, 'log'):
                # O logger é um bound method do worker, então __self__ é o worker
                worker = getattr(self.log, '__self__', None)
                if worker and hasattr(worker, 'engine'):
                    engine = worker.engine
            
            # Verifica interrupção antes de começar
            if engine and not engine.running:
                self.log("[INFO] Download da pasta interrompido antes de iniciar")
                return False
            
            # Primeiro, baixa os arquivos na pasta raiz
            query = f"'{gdrive_folder_id}' in parents and trashed=false"
            results = self.service.files().list(q=query, fields="files(id, name, mimeType)").execute()
            items = results.get('files', [])
            
            # Cria diretório local se não existir
            os.makedirs(local_destination, exist_ok=True)
            
            for item in items:
                # Verifica interrupção em cada item
                if engine and not engine.running:
                    self.log("[INFO] Download da pasta interrompido pelo usuário")
                    return False
                    
                if item['mimeType'] == 'application/vnd.google-apps.folder':
                    # Pasta - chama recursivamente
                    subfolder_path = os.path.join(local_destination, item['name'])
                    self.download_folder(item['id'], subfolder_path)
                else:
                    # Arquivo - faz download
                    self.download_file(item['id'], os.path.join(local_destination, item['name']))
            
            return True
        except Exception as e:
            self.log(f"[ERRO] Falha no download da pasta: {e}")
            return False
    
    def download_file(self, file_id, local_path):
        """Baixa um arquivo do Google Drive com verificação de interrupção"""
        try:
            # Verifica se temos acesso ao engine através do worker
            engine = None
            if hasattr(self, 'log'):
                worker = getattr(self.log, '__self__', None)
                if worker and hasattr(worker, 'engine'):
                    engine = worker.engine
            
            # Verifica interrupção antes de começar
            if engine and not engine.running:
                self.log("[INFO] Download do arquivo interrompido antes de iniciar")
                return False
            
            request = self.service.files().get_media(fileId=file_id)
            fh = io.BytesIO()
            downloader = MediaIoBaseDownload(fh, request)
            done = False
            while done is False:
                # Verifica interrupção durante o download
                if engine and not engine.running:
                    self.log("[INFO] Download do arquivo interrompido pelo usuário")
                    return False
                status, done = downloader.next_chunk()
            
            # Escreve o arquivo localmente
            os.makedirs(os.path.dirname(local_path), exist_ok=True)
            with open(local_path, 'wb') as f:
                fh.seek(0)
                f.write(fh.read())
            
            self.log(f"[DOWNLOAD] {os.path.basename(local_path)} baixado do Google Drive")
            return True
        except Exception as e:
            self.log(f"[ERRO] Falha no download do arquivo: {e}")
            return False
    
    def delete_folder(self, folder_id):
        """Deleta uma pasta do Google Drive"""
        try:
            self.service.files().delete(fileId=folder_id).execute()
            self.log(f"[INFO] Pasta deletada do Google Drive")
            return True
        except Exception as e:
            self.log(f"[ERRO] Falha ao deletar pasta: {e}")
            return False
    
    def upload_file(self, local_path, gdrive_folder_id, filename=None):
        """Faz upload de um arquivo para o Google Drive substituindo se já existir com verificação de interrupção"""
        try:
            if not filename:
                filename = os.path.basename(local_path)
            
            # Verifica se o backup foi interrompido antes de começar o upload
            engine = None
            if hasattr(self, 'log') and hasattr(self.log.__self__, 'running'):
                engine = self.log.__self__
                if not engine.running:
                    self.log("[INFO] Upload interrompido antes de iniciar")
                    return False
            
            # Primeiro verifica se arquivo já existe na pasta
            query = f"name='{filename}' and '{gdrive_folder_id}' in parents and trashed=false"
            results = self.service.files().list(q=query, fields="files(id, name)").execute()
            existing_files = results.get('files', [])
            
            media = MediaFileUpload(local_path, resumable=True)
            file_metadata = {'name': filename, 'parents': [gdrive_folder_id]}
            
            if existing_files:
                # Substitui o arquivo existente
                file_id = existing_files[0]['id']
                self.service.files().update(
                    fileId=file_id,
                    body=file_metadata,
                    media_body=media
                ).execute()
                self.log(f"[UPLOAD] {filename} atualizado no Google Drive (substituído)")
            else:
                # Cria novo arquivo
                self.service.files().create(
                    body=file_metadata,
                    media_body=media
                ).execute()
                self.log(f"[UPLOAD] {filename} enviado para Google Drive")
            
            return True
        except Exception as e:
            self.log(f"[ERRO] Falha no upload do arquivo {filename}: {e}")
            return False

# --- GERENCIADOR DE CONFIG ---
class ConfigManager:
    @staticmethod
    def load():
        if os.path.exists(CONFIG_FILE):
            with open(CONFIG_FILE, 'r') as f:
                return {**DEFAULT_CONFIG, **json.load(f)}
        return DEFAULT_CONFIG

    @staticmethod
    def save(data):
        with open(CONFIG_FILE, 'w') as f:
            json.dump(data, f, indent=4)

# --- MOTOR DO COFRE (Lógica Central) ---
class VaultEngine:
    def __init__(self, logger_callback):
        self.log = logger_callback
        self.running = True
        self.gdrive_service = None
        
    def stop(self):
        self.running = False
    
    def init_gdrive(self):
        """Inicializa o serviço do Google Drive"""
        if GOOGLE_DRIVE_AVAILABLE:
            self.gdrive_service = GoogleDriveService(self.log)
            return self.gdrive_service is not None
        else:
            self.log("[ERRO] Google Drive não disponível - dependências ausentes")
            return False
    
    def test_gdrive_connection(self):
        """Testa a conexão com Google Drive sem fazer backup"""
        if not self.init_gdrive():
            self.log("[ERRO] Falha ao inicializar Google Drive")
            return False
            
        # Verifica se o serviço foi inicializado corretamente
        if self.gdrive_service and self.gdrive_service.service:
            # Testa listando algumas pastas na raiz
            try:
                folders = self.gdrive_service.list_folders('root')
                folder_count = len(folders) if folders else 0
                self.log(f"[SUCESSO] Autenticado no Google Drive. Encontradas {folder_count} pastas na raiz.")
                return True
            except Exception as e:
                self.log(f"[AVISO] Autenticado no Google Drive, mas teste de listagem falhou: {str(e)}")
                return True  # Ainda considera autenticado mesmo com falha parcial
        else:
            self.log("[ERRO] Não foi possível autenticar no Google Drive")
            return False

    def safe_create_dir(self, path):
        if not os.path.exists(path):
            try: os.makedirs(path)
            except: pass

    def safe_copy(self, src, dst):
        try:
            shutil.copy2(src, dst)
            return True
        except Exception as e:
            self.log(f"[ERRO] Falha: {os.path.basename(src)} - {e}")
        return False

    def copy_module(self, src, dst, title):
        if not os.path.exists(src):
            self.log(f"[INFO] {title}: Não localizado (Ignorado).")
            return

        total = sum([len(files) for r, d, files in os.walk(src)])
        if total == 0: return

        self.log(f">>> PROCESSANDO: {title}...")
        self.safe_create_dir(dst)

        for root, dirs, files in os.walk(src):
            if not self.running: break
            rel = os.path.relpath(root, src)
            target_dir = os.path.join(dst, rel)
            self.safe_create_dir(target_dir)

            for file in files:
                if not self.running: break
                self.safe_copy(os.path.join(root, file), os.path.join(target_dir, file))
        
        self.log(f"[SUCESSO] {title} arquivado no cofre.")

    def run_backup(self, steam, backup_root):
        vault_folder = os.path.join(backup_root, "SteamVault_Backup")
        self.log(f"--- INICIANDO PROTOCOLO {APP_NAME} ---")
        self.safe_create_dir(vault_folder)
        
        self.copy_module(os.path.join(steam, "userdata"), os.path.join(vault_folder, "userdata"), "USERDATA")
        self.copy_module(os.path.join(steam, "config", "stplug-in"), os.path.join(vault_folder, "config", "stplug-in"), "STPLUG-IN")
        self.copy_module(os.path.join(steam, "config", "depotcache"), os.path.join(vault_folder, "config", "depotcache"), "DEPOTCACHE")
        self.copy_module(os.path.join(steam, "appcache", "stats"), os.path.join(vault_folder, "appcache", "stats"), "STATS")

        for dll in ["version.dll", "winmm.dll"]:
            src = os.path.join(steam, dll)
            if os.path.exists(src):
                if self.safe_copy(src, os.path.join(vault_folder, dll)):
                    self.log(f"[DLL] {dll} Protegida.")

    def run_backup_gdrive(self, steam):
        """Executa backup diretamente para Google Drive com verificação de interrupção"""
        if not self.gdrive_service:
            if not self.init_gdrive():
                return False
        
        # Verifica interrupção antes de começar
        if not self.running:
            self.log("[INFO] Backup do Google Drive interrompido antes de iniciar")
            return False
        
        self.log("--- INICIANDO BACKUP PARA GOOGLE DRIVE ---")
        
        # Verifica interrupção após log inicial
        if not self.running:
            self.log("[INFO] Backup do Google Drive interrompido após início")
            return False
        
        # Cria pasta principal no Google Drive
        main_folder_id = self.gdrive_service.ensure_folder_exists("SteamVault_Backup")
        if not main_folder_id:
            self.log("[ERRO] Falha ao criar pasta principal no Google Drive")
            return False
        
        # Verifica interrupção após criar pasta principal
        if not self.running:
            self.log("[INFO] Backup do Google Drive interrompido após criar pasta principal")
            return False
        
        # Cria pasta com timestamp para este backup
        timestamp = time.strftime("%Y%m%d_%H%M%S")
        backup_folder_id = self.gdrive_service.create_folder(f"backup_{timestamp}", main_folder_id)
        if not backup_folder_id:
            self.log("[ERRO] Falha ao criar pasta do backup no Google Drive")
            return False
        
        # Verifica interrupção após criar pasta de backup
        if not self.running:
            self.log("[INFO] Backup do Google Drive interrompido após criar pasta de backup")
            return False
        
        # Cria estrutura de pastas no Google Drive
        userdata_folder_id = self.gdrive_service.create_folder("userdata", backup_folder_id)
        config_folder_id = self.gdrive_service.create_folder("config", backup_folder_id)
        stplugin_folder_id = self.gdrive_service.create_folder("stplug-in", config_folder_id)
        depotcache_folder_id = self.gdrive_service.create_folder("depotcache", config_folder_id)
        appcache_folder_id = self.gdrive_service.create_folder("appcache", backup_folder_id)
        stats_folder_id = self.gdrive_service.create_folder("stats", appcache_folder_id)
        
        # Verifica interrupção após criar estrutura
        if not self.running:
            self.log("[INFO] Backup do Google Drive interrompido após criar estrutura")
            return False
        
        # Faz upload dos módulos
        self.log(">>> ENVIANDO DADOS PARA GOOGLE DRIVE...")
        
        # Verifica interrupção antes de upload
        if not self.running:
            self.log("[INFO] Backup do Google Drive interrompido antes do upload")
            return False
        
        # Upload USERDATA
        userdata_src = os.path.join(steam, "userdata")
        if os.path.exists(userdata_src):
            if not self.running:
                self.log("[INFO] Backup do Google Drive interrompido antes do upload do USERDATA")
                return False
            self.gdrive_service.upload_folder(userdata_src, userdata_folder_id)
            self.log("[SUCESSO] USERDATA enviado para Google Drive")
        
        # Verifica interrupção após USERDATA
        if not self.running:
            self.log("[INFO] Backup do Google Drive interrompido após USERDATA")
            return False
        
        # Upload STPLUG-IN
        stplugin_src = os.path.join(steam, "config", "stplug-in")
        if os.path.exists(stplugin_src):
            if not self.running:
                self.log("[INFO] Backup do Google Drive interrompido antes do upload do STPLUG-IN")
                return False
            self.gdrive_service.upload_folder(stplugin_src, stplugin_folder_id)
            self.log("[SUCESSO] STPLUG-IN enviado para Google Drive")
        
        # Verifica interrupção após STPLUG-IN
        if not self.running:
            self.log("[INFO] Backup do Google Drive interrompido após STPLUG-IN")
            return False
        
        # Upload DEPOTCACHE
        depotcache_src = os.path.join(steam, "config", "depotcache")
        if os.path.exists(depotcache_src):
            if not self.running:
                self.log("[INFO] Backup do Google Drive interrompido antes do upload do DEPOTCACHE")
                return False
            self.gdrive_service.upload_folder(depotcache_src, depotcache_folder_id)
            self.log("[SUCESSO] DEPOTCACHE enviado para Google Drive")
        
        # Verifica interrupção após DEPOTCACHE
        if not self.running:
            self.log("[INFO] Backup do Google Drive interrompido após DEPOTCACHE")
            return False
        
        # Upload STATS
        stats_src = os.path.join(steam, "appcache", "stats")
        if os.path.exists(stats_src):
            if not self.running:
                self.log("[INFO] Backup do Google Drive interrompido antes do upload do STATS")
                return False
            self.gdrive_service.upload_folder(stats_src, stats_folder_id)
            self.log("[SUCESSO] STATS enviado para Google Drive")
        
        # Verifica interrupção após STATS
        if not self.running:
            self.log("[INFO] Backup do Google Drive interrompido após STATS")
            return False
        
        # Upload DLLs
        for dll in ["version.dll", "winmm.dll"]:
            if not self.running:
                self.log("[INFO] Backup do Google Drive interrompido antes do upload das DLLs")
                return False
            dll_src = os.path.join(steam, dll)
            if os.path.exists(dll_src):
                self.gdrive_service.upload_file(dll_src, backup_folder_id)
                self.log(f"[DLL] {dll} enviado para Google Drive")
        
        # Verificação final
        if not self.running:
            self.log("[INFO] Backup do Google Drive interrompido antes de finalizar")
            return False
        
        self.log(f"[SUCESSO] Backup concluído no Google Drive (ID: {backup_folder_id})")
        return True

    def run_restore_gdrive(self, steam, backup_id):
        """Restaura backup do Google Drive"""
        if not self.gdrive_service:
            if not self.init_gdrive():
                return False
        
        self.log("--- INICIANDO RESTAURAÇÃO DO GOOGLE DRIVE ---")
        
        # Cria pasta temporária para download (usando diretório com permissão)
        temp_dir = os.path.join(os.path.expanduser('~'), 'temp_gdrive_restore')
        self.safe_create_dir(temp_dir)
        
        try:
            # Faz download do backup do Google Drive
            self.log(f">>> BAIXANDO BACKUP {backup_id} DO GOOGLE DRIVE...")
            if not self.gdrive_service.download_folder(backup_id, temp_dir):
                self.log("[ERRO] Falha ao baixar backup do Google Drive")
                return False
            
            # Restaura os dados baixados
            self.log(">>> RESTAURANDO DADOS BAIXADOS...")
            
            # Copia USERDATA
            userdata_src = os.path.join(temp_dir, "userdata")
            if os.path.exists(userdata_src):
                self.copy_module(userdata_src, os.path.join(steam, "userdata"), "RESTORE USERDATA")
            
            # Copia STPLUG-IN
            stplugin_src = os.path.join(temp_dir, "config", "stplug-in")
            if os.path.exists(stplugin_src):
                self.copy_module(stplugin_src, os.path.join(steam, "config", "stplug-in"), "RESTORE STPLUG-IN")
            
            # Copia DEPOTCACHE
            depotcache_src = os.path.join(temp_dir, "config", "depotcache")
            if os.path.exists(depotcache_src):
                self.copy_module(depotcache_src, os.path.join(steam, "config", "depotcache"), "RESTORE DEPOTCACHE")
            
            # Copia STATS
            stats_src = os.path.join(temp_dir, "appcache", "stats")
            if os.path.exists(stats_src):
                self.copy_module(stats_src, os.path.join(steam, "appcache", "stats"), "RESTORE STATS")
            
            # Copia DLLs
            for dll in ["version.dll", "winmm.dll"]:
                dll_src = os.path.join(temp_dir, dll)
                if os.path.exists(dll_src):
                    if self.safe_copy(dll_src, os.path.join(steam, dll)):
                        self.log(f"[DLL] {dll} Restaurada.")
            
            self.log("[SUCESSO] Restauração do Google Drive concluída")
            return True
            
        finally:
            # Limpa pasta temporária
            try:
                shutil.rmtree(temp_dir, ignore_errors=True)
            except:
                pass

    def run_restore(self, steam, backup_root):
        vault_folder = os.path.join(backup_root, "SteamVault_Backup")
        origin = vault_folder
        
        # Retrocompatibilidade
        if not os.path.exists(origin):
            if os.path.exists(os.path.join(backup_root, "SteamBackup")):
                origin = os.path.join(backup_root, "SteamBackup")
                self.log("[AVISO] Detectado formato de backup antigo (SteamBackup).")

        if os.path.basename(backup_root) in ["SteamVault_Backup", "SteamBackup"]: 
            origin = backup_root

        self.log("--- INICIANDO RESTAURAÇÃO DO COFRE ---")
        
        if not os.path.exists(os.path.join(origin, "userdata")):
            self.log("[ERRO CRÍTICO] O Cofre está vazio ou inválido (userdata missing).")
            return

        self.copy_module(os.path.join(origin, "userdata"), os.path.join(steam, "userdata"), "RESTORE USERDATA")
        self.copy_module(os.path.join(origin, "config", "stplug-in"), os.path.join(steam, "config", "stplug-in"), "RESTORE STPLUG-IN")
        self.copy_module(os.path.join(origin, "config", "depotcache"), os.path.join(steam, "config", "depotcache"), "RESTORE DEPOTCACHE")
        self.copy_module(os.path.join(origin, "appcache", "stats"), os.path.join(steam, "appcache", "stats"), "RESTORE STATS")

        for dll in ["version.dll", "winmm.dll"]:
            src = os.path.join(origin, dll)
            if os.path.exists(src):
                if self.safe_copy(src, os.path.join(steam, dll)):
                    self.log(f"[DLL] {dll} Restaurada.")

# --- MODO GUI (INTERFACE) ---
if GUI_AVAILABLE:
    class VaultWorkerGUI(QThread):
        log = pyqtSignal(str)
        finished = pyqtSignal()

        def __init__(self, mode, steam, backup, gdrive_mode=False, backup_id=None):
            super().__init__()
            self.mode = mode
            self.steam = steam
            self.backup = backup
            self.gdrive_mode = gdrive_mode
            self.backup_id = backup_id
            self.engine = VaultEngine(self.emit_log)

        def emit_log(self, text):
            self.log.emit(text)

        def run(self):
            if self.gdrive_mode:
                if self.mode == "backup":
                    # Verifica se o backup foi interrompido antes de iniciar
                    if not self.engine.running:
                        self.log.emit("[INFO] Backup interrompido antes de iniciar")
                        self.finished.emit()
                        return
                    self.engine.run_backup_gdrive(self.steam)
                elif self.mode == "auth_only":
                    # Apenas autenticação, não faz backup
                    self.engine.test_gdrive_connection()
                else:  # restore
                    self.engine.run_restore_gdrive(self.steam, self.backup_id)
            else:
                if self.mode == "backup":
                    self.engine.run_backup(self.steam, self.backup)
                else:
                    self.engine.run_restore(self.steam, self.backup)
            self.finished.emit()

    class SteamVaultGUI(QMainWindow):
        def __init__(self):
            super().__init__()
            self.config = ConfigManager.load()
            self.setFixedSize(900, 500)
            self.setWindowFlags(Qt.WindowType.FramelessWindowHint)
            self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
            self.old_pos = None
            self.init_ui()
            self.apply_styles()

        def init_ui(self):
            self.main_frame = QFrame()
            self.main_frame.setObjectName("MainFrame")
            self.setCentralWidget(self.main_frame)
            main_layout = QVBoxLayout(self.main_frame)
            main_layout.setContentsMargins(25, 15, 25, 25)
            main_layout.setSpacing(20)
        
            # --- TOPO ---
            top_bar = QHBoxLayout()
            title_box = QVBoxLayout(); title_box.setSpacing(0)
                    
            lbl_title = QLabel(APP_NAME); lbl_title.setObjectName("Title")
            lbl_sub = QLabel("BACKUP E RESTAURAÇÃO"); lbl_sub.setObjectName("Subtitle")
                    
            title_box.addWidget(lbl_title); title_box.addWidget(lbl_sub)
            top_bar.addLayout(title_box)
            top_bar.addStretch()
                    
            self.btn_close = QPushButton("✕"); self.btn_close.setObjectName("BtnClose"); self.btn_close.setFixedSize(30, 30)
            self.btn_close.clicked.connect(self.close)
            top_bar.addWidget(self.btn_close)
            main_layout.addLayout(top_bar)
        
            # --- ABAS PRINCIPAIS ---
            self.tabs = QTabWidget()
            self.tabs.setObjectName("Tabs")
                    
            # Aba Local
            self.local_tab = QWidget()
            self.setup_local_tab()
            self.tabs.addTab(self.local_tab, "💻 Local")
                    
            # Aba Google Drive
            if GOOGLE_DRIVE_AVAILABLE:
                self.gdrive_tab = QWidget()
                self.setup_gdrive_tab()
                self.tabs.addTab(self.gdrive_tab, "☁️ Google Drive")
                    
            main_layout.addWidget(self.tabs)

        def setup_local_tab(self):
            """Configura a aba de backup local"""
            layout = QHBoxLayout(self.local_tab)
            layout.setSpacing(25)
            
            # Coluna Esquerda
            left = QVBoxLayout(); left.setSpacing(15)
            self.create_path(left, "DIRETÓRIO STEAM:", self.config['steam_path'], self.sel_steam, "lbl_steam")
            self.create_path(left, "LOCAL DO COFRE (BACKUP):", self.config['backup_path'], self.sel_backup, "lbl_backup")
            left.addStretch()
            
            actions = QHBoxLayout(); actions.setSpacing(10)
            btn_bkp = QPushButton("CRIAR BACKUP"); btn_bkp.setObjectName("BtnPrimary"); btn_bkp.clicked.connect(lambda: self.run_p("backup"))
            btn_res = QPushButton("RESTAURAR"); btn_res.setObjectName("BtnSecondary"); btn_res.clicked.connect(lambda: self.run_p("restore"))
            actions.addWidget(btn_bkp); actions.addWidget(btn_res)
            left.addLayout(actions)
            layout.addLayout(left, stretch=4)

            # Coluna Direita (Log)
            right = QVBoxLayout(); right.setSpacing(5)
            right.addWidget(QLabel("REGISTRO DE OPERAÇÕES", styleSheet=f"color:{THEME['text_dim']}; font-weight:bold; font-size:10px;"))
            self.console = QTextEdit(); self.console.setReadOnly(True); self.console.setObjectName("Terminal")
            self.console.append(f"<span style='color:{THEME['text_dim']}'>Steam Vault Inicializado.</span>")
            right.addWidget(self.console)
            layout.addLayout(right, stretch=6)
        
        def setup_gdrive_tab(self):
            """Configura a aba do Google Drive"""
            layout = QHBoxLayout(self.gdrive_tab)
            layout.setSpacing(25)
            
            # Coluna Esquerda
            left = QVBoxLayout(); left.setSpacing(15)
            self.create_path(left, "DIRETÓRIO STEAM:", self.config['steam_path'], self.sel_steam_gdrive, "lbl_steam_gdrive")
            
            # Status do Google Drive
            status_layout = QHBoxLayout()
            self.gdrive_status = QLabel("Status: Não autenticado")
            self.gdrive_status.setStyleSheet(f"color:{THEME['warning']}; font-size:10px;")
            btn_auth = QPushButton("Autenticar Google Drive")
            btn_auth.setObjectName("BtnSmall")
            btn_auth.clicked.connect(self.authenticate_gdrive)
            
            # Botão de teste de conexão
            btn_test = QPushButton("Testar Conexão")
            btn_test.setObjectName("BtnSmall")
            btn_test.clicked.connect(self.test_gdrive_connection)
            
            status_layout.addWidget(self.gdrive_status)
            status_layout.addWidget(btn_auth)
            status_layout.addWidget(btn_test)
            left.addLayout(status_layout)
            
            left.addStretch()
            
            # Ações do Google Drive
            gdrive_actions = QVBoxLayout(); gdrive_actions.setSpacing(10)
            
            # Backup para Google Drive
            backup_row = QHBoxLayout()
            btn_bkp_gdrive = QPushButton("📤 Backup para Google Drive")
            btn_bkp_gdrive.setObjectName("BtnPrimary")
            btn_bkp_gdrive.clicked.connect(lambda: self.run_p("backup", gdrive_mode=True))
            self.btn_backup_gdrive = btn_bkp_gdrive
            
            # Botão de parar backup
            btn_stop_gdrive = QPushButton("⏹ Parar Backup")
            btn_stop_gdrive.setObjectName("BtnDanger")
            btn_stop_gdrive.clicked.connect(self.stop_gdrive_backup)
            btn_stop_gdrive.setEnabled(False)
            self.btn_stop_gdrive = btn_stop_gdrive
            
            backup_row.addWidget(btn_bkp_gdrive)
            backup_row.addWidget(btn_stop_gdrive)
            gdrive_actions.addLayout(backup_row)
            
            # Lista de backups
            gdrive_actions.addWidget(QLabel("Backups disponíveis:", styleSheet=f"color:{THEME['text_dim']}; font-size:10px;"))
            self.backups_list = QListWidget()
            self.backups_list.setObjectName("BackupList")
            self.backups_list.itemDoubleClicked.connect(self.restore_selected_backup)
            self.backups_list.itemSelectionChanged.connect(self.on_backup_selection_changed)
            gdrive_actions.addWidget(self.backups_list)
            
            # Botões de ação para backups
            backup_buttons_row = QHBoxLayout()
            
            # Botão de atualizar lista
            btn_refresh = QPushButton("Atualizar lista")
            btn_refresh.setObjectName("BtnSmall")
            btn_refresh.clicked.connect(self.refresh_backups_list)
            backup_buttons_row.addWidget(btn_refresh)
            
            # Botão de restaurar backup
            btn_restore_gdrive = QPushButton("📥 Restaurar Backup")
            btn_restore_gdrive.setObjectName("BtnPrimary")
            btn_restore_gdrive.clicked.connect(self.restore_selected_backup_action)
            btn_restore_gdrive.setEnabled(False)
            self.btn_restore_gdrive = btn_restore_gdrive
            
            # Botão de parar restauração
            btn_stop_restore_gdrive = QPushButton("⏹ Parar Restauração")
            btn_stop_restore_gdrive.setObjectName("BtnDanger")
            btn_stop_restore_gdrive.clicked.connect(self.stop_gdrive_restore)
            btn_stop_restore_gdrive.setEnabled(False)
            self.btn_stop_restore_gdrive = btn_stop_restore_gdrive
            
            backup_buttons_row.addWidget(btn_restore_gdrive)
            backup_buttons_row.addWidget(btn_stop_restore_gdrive)
            
            backup_buttons_row.addStretch()
            gdrive_actions.addLayout(backup_buttons_row)
            
            left.addLayout(gdrive_actions)
            layout.addLayout(left, stretch=4)

            # Coluna Direita (Log)
            right = QVBoxLayout(); right.setSpacing(5)
            right.addWidget(QLabel("REGISTRO DE OPERAÇÕES", styleSheet=f"color:{THEME['text_dim']}; font-weight:bold; font-size:10px;"))
            self.console_gdrive = QTextEdit(); self.console_gdrive.setReadOnly(True); self.console_gdrive.setObjectName("Terminal")
            self.console_gdrive.append(f"<span style='color:{THEME['text_dim']}'>Google Drive não autenticado.</span>")
            right.addWidget(self.console_gdrive)
            layout.addLayout(right, stretch=6)
            
            # Verifica status inicial
            self.check_gdrive_status()
        
        def check_gdrive_status(self):
            """Verifica o status da autenticação do Google Drive"""
            if os.path.exists(GDRIVE_TOKEN_FILE):
                self.gdrive_status.setText("Status: Autenticado")
                self.gdrive_status.setStyleSheet(f"color:{THEME['success']}; font-size:10px;")
                self.btn_backup_gdrive.setEnabled(True)
                self.refresh_backups_list()
            else:
                self.gdrive_status.setText("Status: Não autenticado")
                self.gdrive_status.setStyleSheet(f"color:{THEME['warning']}; font-size:10px;")
                self.btn_backup_gdrive.setEnabled(False)
        
        def authenticate_gdrive(self):
            """Inicia processo de autenticação do Google Drive"""
            # Primeiro, verifica se já existe credentials.json na pasta
            if os.path.exists(GDRIVE_CREDENTIALS_FILE):
                reply = QMessageBox.question(
                    self, 
                    'Credenciais Encontradas',
                    f'Arquivo {GDRIVE_CREDENTIALS_FILE} já existe.\n\nDeseja usar o arquivo existente ou selecionar outro?',
                    QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                    QMessageBox.StandardButton.Yes
                )
                
                if reply == QMessageBox.StandardButton.Yes:
                    # Usa o arquivo existente
                    self.log_gdrive_info(f"[INFO] Usando arquivo de credenciais existente: {GDRIVE_CREDENTIALS_FILE}")
                else:
                    # Permite selecionar novo arquivo
                    self.select_new_credentials_file()
            else:
                # Nenhum arquivo encontrado, pede para selecionar
                self.select_new_credentials_file()
            
            # Força reautenticação
            if os.path.exists(GDRIVE_TOKEN_FILE):
                try:
                    os.remove(GDRIVE_TOKEN_FILE)
                except:
                    pass
            
            # Inicia worker apenas para autenticação, não backup
            self.worker = VaultWorkerGUI("auth_only", self.config['steam_path'], "", gdrive_mode=True)
            self.worker.log.connect(self.update_term_gdrive)
            self.worker.finished.connect(self.check_gdrive_status)
            self.worker.start()
        
        def select_new_credentials_file(self):
            """Permite selecionar um novo arquivo de credenciais"""
            credentials_file, _ = QFileDialog.getOpenFileName(
                self, 
                "Selecione o arquivo de credenciais do Google Drive",
                "", 
                "JSON Files (*.json)"
            )
            
            if not credentials_file:
                return False
            
            # Copia o arquivo de credenciais para o local esperado (se for diferente)
            if os.path.abspath(credentials_file) != os.path.abspath(GDRIVE_CREDENTIALS_FILE):
                try:
                    shutil.copy2(credentials_file, GDRIVE_CREDENTIALS_FILE)
                    self.log_gdrive_info(f"[INFO] Arquivo de credenciais copiado para: {GDRIVE_CREDENTIALS_FILE}")
                except Exception as e:
                    self.log_gdrive_error(f"[ERRO] Falha ao copiar arquivo de credenciais: {e}")
                    return False
            else:
                self.log_gdrive_info(f"[INFO] Usando arquivo de credenciais já presente: {GDRIVE_CREDENTIALS_FILE}")
            
            return True
        
        def test_gdrive_connection(self):
            """Testa a conexão com o Google Drive"""
            try:
                # Tenta criar um serviço temporário para testar
                gdrive_service = GoogleDriveService(lambda msg: self.console_gdrive.append(f"<span style='color:{THEME['text_dim']}'>{msg}</span>"))
                if gdrive_service.service:
                    if gdrive_service.test_connection():
                        self.log_gdrive_info("[SUCESSO] Conexão com Google Drive testada com sucesso!")
                    else:
                        self.log_gdrive_error("[ERRO] Falha no teste de conexão com Google Drive")
                else:
                    self.log_gdrive_error("[ERRO] Não foi possível conectar ao Google Drive")
            except Exception as e:
                self.log_gdrive_error(f"[ERRO] Exceção durante teste: {str(e)}")
        
        def log_gdrive_info(self, message):
            """Adiciona mensagem informativa ao log do Google Drive"""
            self.console_gdrive.append(f"<span style='color:{THEME['text_dim']}'>{message}</span>")
        
        def log_gdrive_error(self, message):
            """Adiciona mensagem de erro ao log do Google Drive"""
            self.console_gdrive.append(f"<span style='color:{THEME['error']}'>{message}</span>")
        
        def stop_gdrive_backup(self):
            """Para o backup em andamento do Google Drive"""
            if hasattr(self, 'worker') and self.worker:
                self.worker.engine.stop()
                self.log_gdrive_info("[INFO] Backup do Google Drive interrompido pelo usuário")
                self.btn_stop_gdrive.setEnabled(False)
                self.btn_backup_gdrive.setEnabled(True)
        
        def stop_gdrive_restore(self):
            """Para a restauração em andamento do Google Drive"""
            if hasattr(self, 'worker') and self.worker:
                self.worker.engine.stop()
                self.log_gdrive_info("[INFO] Restauração do Google Drive interrompida pelo usuário")
                self.btn_stop_restore_gdrive.setEnabled(False)
                self.btn_restore_gdrive.setEnabled(True)
        
        def on_gdrive_backup_finished(self):
            """Chamado quando o backup do Google Drive termina"""
            self.btn_stop_gdrive.setEnabled(False)
            self.btn_backup_gdrive.setEnabled(True)
            self.refresh_backups_list()  # Atualiza a lista de backups
            
        def on_gdrive_restore_finished(self):
            """Chamado quando a restauração do Google Drive termina"""
            self.btn_stop_restore_gdrive.setEnabled(False)
            self.btn_restore_gdrive.setEnabled(True)
            self.refresh_backups_list()  # Atualiza a lista de backups
            
            # Mostra mensagem de sucesso
            self.log_gdrive_info("[SUCESSO] Backup para Google Drive concluído!")
        
        def refresh_backups_list(self):
            """Atualiza a lista de backups do Google Drive"""
            self.backups_list.clear()
            
            if not os.path.exists(GDRIVE_TOKEN_FILE):
                item = QListWidgetItem("Google Drive não autenticado")
                item.setFlags(item.flags() & ~Qt.ItemFlag.ItemIsSelectable)
                self.backups_list.addItem(item)
                return
            
            try:
                gdrive_service = GoogleDriveService(lambda x: None)  # Logger silencioso
                backups = gdrive_service.list_backups()
                
                if not backups:
                    item = QListWidgetItem("Nenhum backup encontrado")
                    item.setFlags(item.flags() & ~Qt.ItemFlag.ItemIsSelectable)
                    self.backups_list.addItem(item)
                else:
                    for backup in backups:
                        display_text = f"{backup['name']} - {backup.get('createdTime', '')[:19].replace('T', ' ')}"
                        item = QListWidgetItem(display_text)
                        item.setData(Qt.ItemDataRole.UserRole, backup['id'])
                        self.backups_list.addItem(item)
            except Exception as e:
                item = QListWidgetItem(f"Erro ao carregar backups: {str(e)}")
                item.setFlags(item.flags() & ~Qt.ItemFlag.ItemIsSelectable)
                self.backups_list.addItem(item)
        
        def restore_selected_backup(self, item):
            """Restaura o backup selecionado (duplo clique)"""
            backup_id = item.data(Qt.ItemDataRole.UserRole)
            if not backup_id:
                return
            
            reply = QMessageBox.question(self, 'Confirmar Restauração',
                                       f'Tem certeza que deseja restaurar este backup?\n\nIsso substituirá seus saves atuais!',
                                       QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
            
            if reply == QMessageBox.StandardButton.Yes:
                self.run_p("restore", gdrive_mode=True, backup_id=backup_id)
        
        def restore_selected_backup_action(self):
            """Restaura o backup selecionado através do botão"""
            current_item = self.backups_list.currentItem()
            if not current_item:
                QMessageBox.warning(self, 'Nenhum backup selecionado', 'Por favor, selecione um backup da lista primeiro.')
                return
            
            self.restore_selected_backup(current_item)
        
        def on_backup_selection_changed(self):
            """Habilita/desabilita botão de restaurar baseado na seleção"""
            has_selection = bool(self.backups_list.currentItem())
            self.btn_restore_gdrive.setEnabled(has_selection)
        
        def update_term_gdrive(self, text):
            """Atualiza o terminal da aba Google Drive"""
            col = THEME['text_main']
            if "[SUCESSO]" in text: col = THEME['success']
            elif "[ERRO]" in text: col = THEME['error']
            elif "[AVISO]" in text: col = THEME['warning']
            elif ">>>" in text: col = THEME['accent']
            self.console_gdrive.append(f"<span style='color:{col}'>{text}</span>")
            self.console_gdrive.verticalScrollBar().setValue(self.console_gdrive.verticalScrollBar().maximum())

        def create_path(self, layout, title, val, cb, attr):
            layout.addWidget(QLabel(title, styleSheet=f"color:{THEME['accent']}; font-size:10px; font-weight:bold;"))
            row = QHBoxLayout()
            lbl = QLabel(val or "Não definido"); lbl.setStyleSheet(f"color:{THEME['text_main']}; font-family:'Consolas'; font-size:11px;")
            setattr(self, attr, lbl)
            btn = QPushButton("..."); btn.setFixedSize(30,25); btn.setObjectName("BtnSmall"); btn.clicked.connect(cb)
            row.addWidget(lbl); row.addWidget(btn)
            layout.addLayout(row)
            line = QFrame(); line.setFrameShape(QFrame.Shape.HLine); line.setStyleSheet(f"background:{THEME['btn_border']}; max-height:1px;")
            layout.addWidget(line)

        def update_term(self, text):
            col = THEME['text_main']
            if "[SUCESSO]" in text: col = THEME['success']
            elif "[ERRO]" in text: col = THEME['error']
            elif ">>>" in text: col = THEME['accent']
            self.console.append(f"<span style='color:{col}'>{text}</span>")
            self.console.verticalScrollBar().setValue(self.console.verticalScrollBar().maximum())

        def apply_styles(self):
            self.setStyleSheet(f"""
                QFrame#MainFrame {{ background: {THEME['bg_main']}; border: 1px solid {THEME['btn_border']}; border-radius: 8px; }}
                QLabel {{ color: {THEME['text_main']}; font-family: 'Segoe UI'; }}
                QLabel#Title {{ font-size: 22px; font-weight: 800; letter-spacing: 1px; }}
                QLabel#Subtitle {{ color: {THEME['text_dim']}; font-size: 10px; letter-spacing: 2px; }}
                QPushButton {{ background: {THEME['btn_bg']}; border: 1px solid {THEME['btn_border']}; color: {THEME['text_main']}; padding: 5px; border-radius: 4px; }}
                QPushButton:hover {{ border-color: {THEME['accent']}; }}
                QPushButton#BtnClose {{ background: transparent; border: none; font-weight: bold; }}
                QPushButton#BtnClose:hover {{ color: {THEME['close_hover']}; }}
                QPushButton#BtnPrimary {{ background: {THEME['accent']}; color: white; border: none; font-weight: bold; padding: 12px; }}
                QPushButton#BtnPrimary:hover {{ background: #2563eb; }}
                QPushButton#BtnSecondary {{ border: 1px solid {THEME['accent']}; color: {THEME['accent']}; font-weight: bold; padding: 12px; }}
                QTextEdit#Terminal {{ background: {THEME['bg_panel']}; border: 1px solid {THEME['btn_border']}; color: {THEME['text_main']}; font-family: 'Consolas'; font-size: 11px; padding: 10px; }}
                QTabWidget::pane {{ border: 1px solid {THEME['btn_border']}; background: {THEME['bg_main']}; }}
                QTabBar::tab {{ background: {THEME['btn_bg']}; color: {THEME['text_dim']}; padding: 8px 15px; margin: 2px; border: 1px solid {THEME['btn_border']}; border-bottom: none; }}
                QTabBar::tab:selected {{ background: {THEME['accent']}; color: white; }}
                QTabBar::tab:hover:!selected {{ background: {THEME['btn_border']}; }}
                QListWidget {{ background: {THEME['bg_panel']}; border: 1px solid {THEME['btn_border']}; color: {THEME['text_main']}; }}
                QListWidget::item {{ padding: 5px; }}
                QListWidget::item:selected {{ background: {THEME['accent']}; }}
                
                /* Estilo do Popup de Pergunta (QMessageBox) */
                QMessageBox {{ background-color: {THEME['bg_panel']}; color: {THEME['text_main']}; }}
                QMessageBox QLabel {{ color: {THEME['text_main']}; }}
            """)

        def sel_steam(self):
            p = QFileDialog.getExistingDirectory(self, "Pasta Steam"); 
            if p: self.config['steam_path'] = p; self.lbl_steam.setText(p); ConfigManager.save(self.config)
        def sel_backup(self):
            p = QFileDialog.getExistingDirectory(self, "Pasta para o Cofre"); 
            if p: self.config['backup_path'] = p; self.lbl_backup.setText(p); ConfigManager.save(self.config)
        def sel_steam_gdrive(self):
            p = QFileDialog.getExistingDirectory(self, "Pasta Steam"); 
            if p: self.config['steam_path'] = p; self.lbl_steam_gdrive.setText(p); ConfigManager.save(self.config)

        def run_p(self, mode, gdrive_mode=False, backup_id=None):
            if not self.config['steam_path']:
                if gdrive_mode:
                    self.update_term_gdrive("[ERRO] Defina o diretório Steam.")
                else:
                    self.update_term("[ERRO] Defina o diretório Steam.")
                return
            
            if not gdrive_mode and not self.config['backup_path']:
                self.update_term("[ERRO] Defina o diretório de backup.")
                return
            
            # Check Segurança (Overwrite) para backup local
            if mode == "backup" and not gdrive_mode:
                tgt = os.path.join(self.config['backup_path'], "SteamVault_Backup")
                if os.path.exists(tgt) and os.listdir(tgt):
                    msg = QMessageBox(self)
                    msg.setWindowTitle("Cofre Ocupado")
                    msg.setText("Já existe um backup anterior.\nDeseja sobrescrever o cofre?")
                    msg.setIcon(QMessageBox.Icon.Question)
                    btn_sim = msg.addButton("Sim", QMessageBox.ButtonRole.YesRole)
                    btn_nao = msg.addButton("Não", QMessageBox.ButtonRole.NoRole)
                    msg.setStyleSheet(f"background-color: {THEME['bg_panel']}; color: {THEME['text_main']};")
                    msg.exec()
                    if msg.clickedButton() != btn_sim:
                        self.update_term("Operação cancelada pelo usuário.")
                        return

            backup_path = self.config['backup_path'] if not gdrive_mode else ""
            self.worker = VaultWorkerGUI(mode, self.config['steam_path'], backup_path, gdrive_mode, backup_id)
            if gdrive_mode:
                self.worker.log.connect(self.update_term_gdrive)
                if mode == "backup":
                    # Habilita botão de parar durante backup
                    self.btn_stop_gdrive.setEnabled(True)
                    self.btn_backup_gdrive.setEnabled(False)
                    self.worker.finished.connect(lambda: self.on_gdrive_backup_finished())
                else:  # restore
                    # Habilita botão de parar durante restauração
                    self.btn_stop_restore_gdrive.setEnabled(True)
                    self.btn_restore_gdrive.setEnabled(False)
                    self.worker.finished.connect(lambda: self.on_gdrive_restore_finished())
            else:
                self.worker.log.connect(self.update_term)
            self.worker.start()
                
        def update_term(self, text):
            col = THEME['text_main']
            if "[SUCESSO]" in text: col = THEME['success']
            elif "[ERRO]" in text: col = THEME['error']
            elif ">>>" in text: col = THEME['accent']
            self.console.append(f"<span style='color:{col}'>{text}</span>")
            self.console.verticalScrollBar().setValue(self.console.verticalScrollBar().maximum())

        def apply_styles(self):
            self.setStyleSheet(f"""
                QFrame#MainFrame {{ background: {THEME['bg_main']}; border: 1px solid {THEME['btn_border']}; border-radius: 8px; }}
                QLabel {{ color: {THEME['text_main']}; font-family: 'Segoe UI'; }}
                QLabel#Title {{ font-size: 22px; font-weight: 800; letter-spacing: 1px; }}
                QLabel#Subtitle {{ color: {THEME['text_dim']}; font-size: 10px; letter-spacing: 2px; }}
                QPushButton {{ background: {THEME['btn_bg']}; border: 1px solid {THEME['btn_border']}; color: {THEME['text_main']}; padding: 5px; border-radius: 4px; }}
                QPushButton:hover {{ border-color: {THEME['accent']}; }}
                QPushButton#BtnClose {{ background: transparent; border: none; font-weight: bold; }}
                QPushButton#BtnClose:hover {{ color: {THEME['close_hover']}; }}
                QPushButton#BtnPrimary {{ background: {THEME['accent']}; color: white; border: none; font-weight: bold; padding: 12px; }}
                QPushButton#BtnPrimary:hover {{ background: #2563eb; }}
                QPushButton#BtnSecondary {{ border: 1px solid {THEME['accent']}; color: {THEME['accent']}; font-weight: bold; padding: 12px; }}
                QTextEdit#Terminal {{ background: {THEME['bg_panel']}; border: 1px solid {THEME['btn_border']}; color: {THEME['text_main']}; font-family: 'Consolas'; font-size: 11px; padding: 10px; }}
                
                /* Estilo do Popup de Pergunta (QMessageBox) */
                QMessageBox {{ background-color: {THEME['bg_panel']}; color: {THEME['text_main']}; }}
                QMessageBox QLabel {{ color: {THEME['text_main']}; }}
            """)

        def sel_steam(self):
            p = QFileDialog.getExistingDirectory(self, "Pasta Steam"); 
            if p: self.config['steam_path'] = p; self.lbl_steam.setText(p); ConfigManager.save(self.config)
        def sel_backup(self):
            p = QFileDialog.getExistingDirectory(self, "Pasta para o Cofre"); 
            if p: self.config['backup_path'] = p; self.lbl_backup.setText(p); ConfigManager.save(self.config)
        def sel_steam_gdrive(self):
            p = QFileDialog.getExistingDirectory(self, "Pasta Steam"); 
            if p: self.config['steam_path'] = p; self.lbl_steam_gdrive.setText(p); ConfigManager.save(self.config)

        def mousePressEvent(self, e): self.old_pos = e.globalPosition().toPoint() if e.button() == Qt.MouseButton.LeftButton else None
        def mouseMoveEvent(self, e): 
            if self.old_pos: 
                d = e.globalPosition().toPoint() - self.old_pos; self.move(self.x()+d.x(), self.y()+d.y()); self.old_pos = e.globalPosition().toPoint()

# --- MODO CLI ---
def run_cli(args):
    config = ConfigManager.load()
    steam = args.steam if args.steam else config.get('steam_path')
    backup = args.backup_path if args.backup_path else config.get('backup_path')

    print(f"\n{'-'*40}")
    print(f"   {APP_NAME} CLI")
    print(f"{'-'*40}")

    if not steam or not backup:
        print("[ERRO] Caminhos inválidos.")
        return

    engine = VaultEngine(print)

    if args.action == "backup":
        tgt = os.path.join(backup, "SteamVault_Backup")
        if os.path.exists(tgt) and os.listdir(tgt) and not args.force:
            if input("Sobrescrever Cofre? [S/N]: ").upper() != 'S': return
        engine.run_backup(steam, backup)
    elif args.action == "restore":
        engine.run_restore(steam, backup)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=f"{APP_NAME} Tool")
    parser.add_argument("action", nargs="?", choices=["backup", "restore"])
    parser.add_argument("--steam", help="Caminho Steam")
    parser.add_argument("--backup-path", help="Caminho Backup")
    parser.add_argument("--force", action="store_true")
    args = parser.parse_args()

    if args.action: run_cli(args)
    elif GUI_AVAILABLE:
        app = QApplication(sys.argv)
        w = SteamVaultGUI()
        w.show()
        sys.exit(app.exec())
    else: print("[ERRO] Instale PyQt6 ou use argumentos CLI.")