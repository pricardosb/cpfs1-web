import streamlit as st
import json
import os
from cryptography.fernet import Fernet
from rotinas import drive_storage

ARQUIVO_BANCO = "dados_acesso.enc"

def obter_cipher():
    try:
        chave = st.secrets["CHAVE_SISTEMA"].encode()
        return Fernet(chave)
    except KeyError:
        return None

def carregar_base_dados():
    drive_storage.baixar_banco_drive()
    cipher = obter_cipher()
    if not cipher or not os.path.exists(ARQUIVO_BANCO):
        return []
    try:
        with open(ARQUIVO_BANCO, "rb") as f:
            dados_cifrados = f.read()
        if not dados_cifrados:
            return []
        return json.loads(cipher.decrypt(dados_cifrados).decode())
    except Exception:
        return []

def render_tela_login(modulo_destino):
    st.markdown("<h2 style='text-align: center; color: #002B7F;'>🔐 Acesso Restrito</h2>", unsafe_allow_html=True)
    st.markdown(f"<p style='text-align: center; color: #555;'>Para acessar a rotina <b>{modulo_destino.replace('_', ' ').title()}</b>, faça o login abaixo:</p>", unsafe_allow_html=True)
    
    col1, col2, col3 = st.columns([1, 2, 1])
    
    with col2:
        with st.form(key="form_login_usuario"):
            email_input = st.text_input("E-mail de Acesso")
            senha_input = st.text_input("Senha", type="password")
            
            submit_login = st.form_submit_button("Entrar no Sistema", use_container_width=True)
            
            if submit_login:
                email_limpo = email_input.strip().lower()
                senha_limpa = senha_input.strip()
                
                if not email_limpo or not senha_limpa:
                    st.error("❌ Preencha o e-mail e a senha.")
                else:
                    base_cadastros = carregar_base_dados()
                    usuario_encontrado = None
                    
                    # Busca o usuário na base descriptografada
                    for u in base_cadastros:
                        if str(u.get("email", "")).strip().lower() == email_limpo:
                            usuario_encontrado = u
                            break
                            
                    if not usuario_encontrado:
                        st.error("❌ E-mail não encontrado na base de dados.")
                    else:
                        senha_salva = str(usuario_encontrado.get("senha", "")).strip()
                        status_conta = str(usuario_encontrado.get("status", ""))
                        
                        if senha_salva != senha_limpa:
                            st.error("❌ Senha incorreta.")
                        elif "Pendente" in status_conta:
                            st.warning("⚠️ Esta conta ainda aguarda confirmação por e-mail ou liberação de acesso.")
                        else:
                            # Credenciais corretas! Registra o usuário na sessão
                            st.session_state["usuario_logado"] = usuario_encontrado
                            
                            # Se o tipo do usuário for Master, ativa a flag suprema da sessão
                            tipo_usuario = str(usuario_encontrado.get("tipo", "")).strip().capitalize()
                            if tipo_usuario == "Master":
                                st.session_state["is_master_active"] = True
                            else:
                                st.session_state["is_master_active"] = False
                                
                            st.success(f"✅ Bem-vindo(a), {usuario_encontrado.get('nome')}!")
                            st.rerun()

    st.markdown("---")
    col_a, col_b = st.columns(2)
    with col_a:
        if st.button("📝 Fazer Cadastro", use_container_width=True):
            st.session_state["pagina"] = "cadastrar_acesso"
            st.rerun()
    with col_b:
        if st.button("🔑 Esqueci a Senha", use_container_width=True):
            st.session_state["pagina"] = "esqueci_senha"
            st.rerun()
