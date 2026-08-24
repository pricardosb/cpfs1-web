import io
import streamlit as st
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseDownload, MediaIoBaseUpload

SCOPES = ['https://www.googleapis.com/auth/drive']

def get_drive_service():
    """
    Inicializa o serviço da API do Google Drive usando os segredos do Streamlit,
    suportando tanto formato em seção quanto na raiz.
    """
    if "gcp_service_account" in st.secrets:
        creds_dict = dict(st.secrets["gcp_service_account"])
    else:
        creds_dict = {
            "type": st.secrets.get("type"),
            "project_id": st.secrets.get("project_id"),
            "private_key_id": st.secrets.get("private_key_id"),
            "private_key": st.secrets.get("private_key"),
            "client_email": st.secrets.get("client_email"),
            "client_id": st.secrets.get("client_id"),
            "auth_uri": st.secrets.get("auth_uri"),
            "token_uri": st.secrets.get("token_uri"),
            "auth_provider_x509_cert_url": st.secrets.get("auth_provider_x509_cert_url"),
            "client_x509_cert_url": st.secrets.get("client_x509_cert_url"),
            "universe_domain": st.secrets.get("universe_domain", "googleapis.com")
        }
    
    if not creds_dict.get("private_key") or not creds_dict.get("client_email"):
        raise ValueError("As credenciais do Google Cloud (private_key ou client_email) estão vazias ou não foram encontradas no st.secrets.")

    creds = service_account.Credentials.from_service_account_info(
        creds_dict, scopes=SCOPES
    )
    return build('drive', 'v3', credentials=creds)

def listar_arquivos_da_pasta(folder_id):
    """
    Lista pastas e arquivos de um nível específico do Google Drive.
    """
    service = get_drive_service()
    query = f"'{folder_id}' in parents and trashed = false"
    
    try:
        results = service.files().list(
            q=query,
            fields="files(id, name, mimeType)",
            pageSize=1000
        ).execute()
        
        return results.get('files', [])
    except Exception as e:
        st.error(f"Erro detalhado da API do Google: {e}") 
        return []

def baixar_arquivo_bytes(file_id: str) -> bytes:
    """
    Baixa um arquivo do Google Drive diretamente para a memória.
    """
    service = get_drive_service()
    request = service.files().get_media(fileId=file_id)
    fh = io.BytesIO()
    downloader = MediaIoBaseDownload(fh, request)
    done = False
    while not done:
        _, done = downloader.next_chunk()
    return fh.getvalue()

def salvar_arquivo_no_drive(nome_arquivo: str, bytes_conteudo: bytes, mime_type: str, folder_id: str = None) -> str:
    """
    Cria um novo arquivo no Google Drive dentro de uma pasta específica.
    """
    service = get_drive_service()
    file_metadata = {'name': nome_arquivo}
    if folder_id:
        file_metadata['parents'] = [folder_id]

    media = MediaIoBaseUpload(
        io.BytesIO(bytes_conteudo),
        mimetype=mime_type,
        resumable=True
    )

    file = service.files().create(
        body=file_metadata,
        media_body=media,
        fields='id, webViewLink'
    ).execute()

    return file.get('webViewLink')
