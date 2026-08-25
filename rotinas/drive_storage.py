import os
import io
import re
import streamlit as st
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseDownload, MediaFileUpload

NOME_ARQUIVO_DRIVE = "dados_acesso_cpfs.enc"

def corrigir_chave_privada(chave_bruta):
    """
    Reconstrói a chave privada para o formato PEM estrito exigido pelo Google.
    Remove caracteres invisíveis, barras e quebras erradas, remontando a chave
    em blocos exatos de 64 caracteres.
    """
    cabecalho = "-----BEGIN PRIVATE KEY-----"
    rodape = "-----END PRIVATE KEY-----"
    
    # Isola o miolo da chave
    if cabecalho in chave_bruta and rodape in chave_bruta:
        conteudo = chave_bruta.split(cabecalho)[1].split(rodape)[0]
    else:
        conteudo = chave_bruta
        
    # Mantém ESTRITAMENTE caracteres válidos de Base64 (letras, números, +, / e =)
    # Isso impede que barras (\) causem erro 92 e garante que nenhuma letra válida seja perdida
    conteudo_limpo = re.sub(r'[^A-Za-z0-9+/=]', '', conteudo)
    
    # Divide a string em pedaços exatos de 64 caracteres
    linhas = [conteudo_limpo[i:i+64] for i in range(0, len(conteudo_limpo), 64)]
    
    # Remonta o arquivo PEM perfeito
    chave_perfeita = f"{cabecalho}\n" + "\n".join(linhas) + f"\n{rodape}\n"
    return chave_perfeita

def obter_servico_drive():
    try:
        chave_bruta = st.secrets.get("gcp_private_key", "")
        if not chave_bruta:
            st.error("❌ A chave 'gcp_private_key' não foi encontrada nos segredos.")
            return None
            
        chave_formatada = corrigir_chave_privada(str(chave_bruta))
        
        credenciais_dict = {
            "type": st.secrets.get("gcp_type", "service_account"),
            "project_id": st.secrets.get("gcp_project_id", "cpfs-web"),
            "private_key_id": st.secrets.get("gcp_private_key_id", ""),
            "private_key": chave_formatada,
            "client_email": st.secrets.get("gcp_client_email", ""),
            "client_id": st.secrets.get("gcp_client_id", ""),
            "auth_uri": st.secrets.get("gcp_auth_uri", "https://accounts.google.com/o/oauth2/auth"),
            "token_uri": st.secrets.get("gcp_token_uri", "https://oauth2.googleapis.com/token"),
            "auth_provider_x509_cert_url": st.secrets.get("gcp_auth_provider_x509_cert_url", "https://www.googleapis.com/oauth2/v1/certs"),
            "client_x509_cert_url": st.secrets.get("gcp_client_x509_cert_url", ""),
            "universe_domain": st.secrets.get("gcp_universe_domain", "googleapis.com")
        }
        
        SCOPES = ['https://www.googleapis.com/auth/drive']
        creds = service_account.Credentials.from_service_account_info(credenciais_dict, scopes=SCOPES)
        return build('drive', 'v3', credentials=creds)
    except Exception as e:
        st.error(f"❌ Erro na autenticação do Google Drive: {e}")
        return None
        
def obter_id_pasta():
    try:
        return st.secrets["pasta_id"]
    except KeyError:
        st.error("❌ 'pasta_id' não encontrado nos st.secrets.")
        return None

def buscar_arquivo_drive(service, folder_id):
    try:
        query = f"trashed = false and name = '{NOME_ARQUIVO_DRIVE}' and '{folder_id}' in parents"
        results = service.files().list(q=query, spaces='drive', fields="files(id, name)").execute()
        files = results.get('files', [])
        return files[0]['id'] if files else None
    except Exception as e:
        st.error(f"❌ Erro ao buscar arquivo no Drive: {e}")
        return None

def baixar_banco_drive():
    try:
        service = obter_servico_drive()
        if not service: return False
        
        folder_id = obter_id_pasta()
        if not folder_id: return False

        file_id = buscar_arquivo_drive(service, folder_id)
        if not file_id:
            return False

        request = service.files().get_media(fileId=file_id)
        fh = io.BytesIO()
        downloader = MediaIoBaseDownload(fh, request)
        done = False
        while not done:
            status, done = downloader.next_chunk()
        
        fh.seek(0)
        with open(NOME_ARQUIVO_DRIVE, "wb") as f:
            f.write(fh.read())
        return True
    except Exception:
        return False

def salvar_banco_drive():
    try:
        service = obter_servico_drive()
        if not service: return False
        
        folder_id = obter_id_pasta()
        if not folder_id: return False

        if not os.path.exists(NOME_ARQUIVO_DRIVE):
            st.error(f"❌ O arquivo local '{NOME_ARQUIVO_DRIVE}' não existe para ser enviado.")
            return False

        file_id = buscar_arquivo_drive(service, folder_id)
        media = MediaFileUpload(NOME_ARQUIVO_DRIVE, mimetype='application/octet-stream', resumable=True)

        if file_id:
            service.files().update(fileId=file_id, media_body=media).execute()
            return True
        else:
            st.error(f"❌ O arquivo '{NOME_ARQUIVO_DRIVE}' não foi encontrado no Drive.")
            return False
    except Exception as e:
        st.error(f"❌ Falha ao atualizar o banco no Google Drive: {e}")
        return False
