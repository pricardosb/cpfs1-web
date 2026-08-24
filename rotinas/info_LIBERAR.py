import streamlit as st
import json
import os
from cryptography.fernet import Fernet
from rotinas import drive_storage  # Sincronização obrigatória com o Drive

ARQUIVO_BANCO = "dados_acesso.enc"
EMAIL_MASTER = "pricardosbrito@gmail.com"

def obter_cipher():
    try:
        chave = st.secrets["CHAVE_SISTEMA"].encode()
        return Fernet(chave)
    except KeyError:
        return None

def render_liberar_acesso():
    # Validação totalmente blindada contra espaços, maiúsculas/minúsculas e perda de tipo
    usuario_logado = st.session_state.get("usuario_logado")
    
    tipo_usuario = ""
    email_usuario = ""
    
    if usuario_logado:
        tipo_usuario = str(usuario_logado.get("tipo", "")).strip().capitalize()
        email_usuario = str(usuario_logado.get("email", "")).strip().lower()
        
    # A TRAVA MÁXIMA DO MASTER: Se for tipo Master ou o seu e-mail, acesso livre absoluto
    eh_master = (tipo_usuario == "Master" or email_usuario == EMAIL_MASTER)
    
    # Se não for Master, checa se tem a permissão específica nos módulos
    if not eh_master:
        modulos = usuario_logado.get("modulos_permitidos", []) if usuario_logado else []
        if not usuario_logado or "info_liberar" not in modulos:
            st.error(f"🚨 ACESSO NEGADO! Tipo detectado: '{tipo_usuario}'. Acesso restrito.")
            return

    st.markdown("<h2 style='text-align: center; color: #002B7F;'>🔓 Gerenciamento e Liberação de Acessos</h2>", unsafe_allow_html=True)
    st.markdown("Gerencie as permissões dos funcionários e avalie novos cadastros.")
    st.markdown("---")
    
    # --- AUTOMATIZAÇÃO: Baixa os dados mais recentes do Google Drive antes de ler ---
    drive_storage.baixar_banco_drive()
    
    cipher = obter_cipher()
    if not cipher or not os.path.exists(ARQUIVO_BANCO):
        st.error("❌ Base de dados de acessos não encontrada.")
        return
        
    try:
        with open(ARQUIVO_BANCO, "rb") as f:
            dados_cifrados = f.read()
        lista_cadastros = json.loads(cipher.decrypt(dados_cifrados).decode())
    except Exception:
        st.error("❌ Falha ao descriptografar a base de dados.")
        return
        
    # Lista abrangente com todas as rotinas do programa para seleção da TI
    todos_modulos = [
        "cosis_inclusao", 
        "cosis_atualizacoes", 
        "cosis_pesquisa", 
        "ti_liberar", 
        "ti_manutencao",
        "seguranca_relatorios",
        "atendimento_geral",
        "direcao_relatorios"
    ]
    
    # Remove estritamente qualquer rotina que comece com 'super_'
    modulos_disponiveis = [m for m in todos_modulos if not m.startswith("super_")]
    
    mudancas_realizadas = False

    for i, cadastrado in enumerate(lista_cadastros):
        status_atual = cadastrado.get("status", "Bloqueado")
        
        if status_atual == "Pendente Avaliação Manual TI":
            icone = "🟠"
        elif status_atual == "Pendente Confirmação E-mail":
            icone = "🟡"
        elif status_atual == "Senha Ativa":
            icone = "🟢"
        else:
            icone = "🔴"
            
        nome = cadastrado.get("nome", "Sem Nome")
        tipo = cadastrado.get("tipo", "N/D")
        setor = cadastrado.get("setor", "").strip().lower()
        email = cadastrado.get("email", "Sem E-mail")
        cpf = cadastrado.get("cpf", "Não informado")
        
        titulo_expander = f"{icone} {nome}  |  {tipo}  |  {setor.upper() if setor else 'N/D'}  |  {email}"
        
        with st.expander(titulo_expander):
            st.markdown("### 📋 Informações Detalhadas do Cidadão / Funcionário")
            info_col1, info_col2, info_col3 = st.columns(3)
            with info_col1:
                st.markdown(f"**Nome:** {nome}")
                st.markdown(f"**CPF:** {cpf}")
            with info_col2:
                st.markdown(f"**Vínculo/Tipo:** {tipo}")
                st.markdown(f"**Setor:** {setor.upper() if setor else 'N/D'}")
            with info_col3:
                st.markdown(f"**E-mail:** {email}")
                st.markdown(f"**Status Atual:** {status_atual}")
            
            st.markdown("---")
            
            col1, col2 = st.columns(2)
            
            with col1:
                st.markdown("**Definir Novo Status:**")
                novo_status = st.selectbox(
                    "Alterar Status",
                    ["Senha Ativa", "Pendente Confirmação E-mail", "Pendente Avaliação Manual TI", "Bloqueada"],
                    index=["Senha Ativa", "Pendente Confirmação E-mail", "Pendente Avaliação Manual TI", "Bloqueada"].index(status_atual) if status_atual in ["Senha Ativa", "Pendente Confirmação E-mail", "Pendente Avaliação Manual TI", "Bloqueada"] else 3,
                    key=f"status_{i}"
                )
            
            with col2:
                st.markdown("**Rotinas Autorizadas:**")
                modulos_atuais = cadastrado.get("modulos_permitidos", [])
                
                # Pré-seleciona apenas os módulos que começam com o setor exato do usuário (se ainda não tiver salvos)
                if not modulos_atuais and setor:
                    modulos_padrao_setor = [m for m in modulos_disponiveis if m.startswith(f"{setor}_")]
                else:
                    modulos_padrao_setor = modulos_atuais

                novos_modulos = st.multiselect(
                    "Selecione os módulos",
                    modulos_disponiveis,
                    default=[m for m in modulos_padrao_setor if m in modulos_disponiveis],
                    key=f"modulos_{i}"
                )
                
            if st.button("Salvar Alterações do Usuário", key=f"btn_salvar_{i}", type="primary"):
                cadastrado["status"] = novo_status
                cadastrado["modulos_permitidos"] = novos_modulos
                mudancas_realizadas = True
                break

    if mudancas_realizadas:
        dados_json = json.dumps(lista_cadastros, ensure_ascii=False)
        dados_atualizados = cipher.encrypt(dados_json.encode())
        with open(ARQUIVO_BANCO, "wb") as f:
            f.write(dados_atualizados)
            
        # --- AUTOMATIZAÇÃO: Envia as alterações de volta para o Google Drive ---
        drive_storage.salvar_banco_drive()
        
        st.success("✅ Permissões do usuário atualizadas com sucesso!")
        st.rerun()
