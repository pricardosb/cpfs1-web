import os
import io
import json
import streamlit as st
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseDownload, MediaFileUpload

NOME_ARQUIVO_DRIVE = "dados_acesso_cpfs.enc"

def obter_servico_drive():
    try:
        credenciais_dict = dict(st.secrets["gcp_service_account"])
        SCOPES = ['https://www.googleapis.com/auth/drive']
        creds = service_account.Credentials.from_service_account_info(credenciais_dict, scopes=SCOPES)
        service = build('drive', 'v3', credentials=creds)
        return service
    except Exception as e:
        st.error(f"❌ Erro na autenticação do Google Drive: {e}")
        return None

def obter_id_pasta(service):
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
        
        folder_id = obter_id_pasta(service)
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
    except Exception as e:
        return False

def salvar_banco_drive():
    try:
        service = obter_servico_drive()
        if not service: return False
        
        folder_id = obter_id_pasta(service)
        if not folder_id: return False

        if not os.path.exists(NOME_ARQUIVO_DRIVE):
            st.error(f"❌ O arquivo local '{NOME_ARQUIVO_DRIVE}' não existe para ser enviado.")
            return False

        file_id = buscar_arquivo_drive(service, folder_id)
        media = MediaFileUpload(NOME_ARQUIVO_DRIVE, mimetype='application/octet-stream', resumable=True)

        if file_id:
            # Atualiza o arquivo existente (consumindo a cota da sua conta pessoal onde a pasta está)
            service.files().update(fileId=file_id, media_body=media).execute()
            return True
        else:
            st.error("❌ O arquivo 'dados_acesso.enc' não foi encontrado na pasta do Google Drive. Crie um arquivo vazio com esse nome na pasta compartilhada para que o sistema possa atualizá-lo.")
            return False
    except Exception as e:
        st.error(f"❌ Falha ao atualizar o banco no Google Drive: {e}")
        return False
