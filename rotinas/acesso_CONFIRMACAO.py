import streamlit as st
import json
import os
import time
from cryptography.fernet import Fernet
from rotinas import drive_storage

ARQUIVO_BANCO = "dados_acesso.enc"
EMAIL_MASTER = "pricardosbrito@gmail.com"

def obter_cipher():
    try:
        chave = st.secrets["CHAVE_SISTEMA"].encode()
        return Fernet(chave)
    except KeyError:
        st.error("❌ Chave do sistema não configurada no st.secrets.")
        return None

def render_confirmar_acesso():
    st.markdown("<h2 style='text-align: center; color: #002B7F;'>✅ Confirmação de Token / Ativação</h2>", unsafe_allow_html=True)
    st.markdown("<p style='text-align: center;'>Insira o e-mail cadastrado e o token de 8 dígitos recebido para ativar sua senha.</p>", unsafe_allow_html=True)

    if "ativacao_concluida" not in st.session_state:
        st.session_state.ativacao_concluida = False

    with st.form("form_confirmacao"):
        email_digitado = st.text_input("E-mail Cadastrado", autocomplete="email")
        token_digitado = st.text_input("Token de Ativação recebido por e-mail", autocomplete="off")
        btn_confirmar = st.form_submit_button("Ativar Minha Senha", use_container_width=True)

        if btn_confirmar:
            if not email_digitado or not token_digitado:
                st.error("❌ Preencha todos os campos.")
                return

            # Baixa a versão mais atual do Google Drive para garantir consistência
            drive_storage.baixar_banco_drive()

            cipher = obter_cipher()
            if not cipher or not os.path.exists(ARQUIVO_BANCO):
                st.error("❌ Base de dados indisponível.")
                return
            
            try:
                with open(ARQUIVO_BANCO, "rb") as f:
                    dados_cifrados = f.read()
                lista_cadastros = json.loads(cipher.decrypt(dados_cifrados).decode())
            except Exception:
                st.error("❌ Erro ao ler a base de dados.")
                return

            email_alvo = email_digitado.strip().lower()
            token_alvo = token_digitado.strip()
            
            usuario_encontrado = False
            token_correto = False
            sucesso_ativacao = False

            for u in lista_cadastros:
                if u.get("email", "").strip().lower() == email_alvo:
                    usuario_encontrado = True
                    
                    if u.get("status") == "Senha Ativa":
                        st.info("ℹ️ Sua senha já foi ativada anteriormente. Aguarde a liberação dos aplicativos pela TI.")
                        return
                    
                    if u.get("token", "").strip() == token_alvo:
                        token_correto = True
                        u["status"] = "Senha Ativa"
                        u["token"] = "" # Limpa o token por segurança
                        sucesso_ativacao = True
                        break

            if not usuario_encontrado:
                st.error("❌ E-mail não encontrado na base de dados.")
            elif not token_correto:
                st.error("❌ Token inválido ou incorreto.")
            elif sucesso_ativacao:
                # Salva a base criptografada localmente
                dados_json = json.dumps(lista_cadastros, ensure_ascii=False)
                dados_atualizados = cipher.encrypt(dados_json.encode())
                with open(ARQUIVO_BANCO, "wb") as f:
                    f.write(dados_atualizados)
                
                # --- GARANTIA CRÍTICA: Envia a nova situação "Senha Ativa" para o Google Drive ---
                drive_storage.salvar_banco_drive()
            
                st.session_state.ativacao_concluida = True

    if st.session_state.get("ativacao_concluida", False):
        st.success("🎉 **Sucesso!** Seu token foi validado e sua conta foi atualizada para **Senha Ativa**.")
        st.warning("⚠️ **Atenção:** Sua senha está ativa para login, mas o acesso aos aplicativos depende da liberação manual pelo setor de Informática.")
        
        with st.spinner("🔄 Concluindo e retornando ao menu em instantes..."):
            time.sleep(5)
        
        st.session_state.ativacao_concluida = False
        st.session_state["pagina"] = "menu"
        st.rerun()
