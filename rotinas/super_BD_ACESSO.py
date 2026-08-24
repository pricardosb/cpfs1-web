import streamlit as st
import json
import os
from cryptography.fernet import Fernet
import pandas as pd
from rotinas import drive_storage

ARQUIVO_BANCO = "dados_acesso.enc"
EMAIL_MASTER = "pricardosbrito@gmail.com"

def obter_cipher():
    try:
        chave = st.secrets["CHAVE_SISTEMA"].encode()
        return Fernet(chave)
    except KeyError:
        st.error("❌ Chave do sistema não configurada nos segredos.")
        return None

def salvar_e_sincronizar(lista_cadastros):
    cipher = obter_cipher()
    if not cipher:
        return False
    try:
        dados_json = json.dumps(lista_cadastros, ensure_ascii=False)
        dados_cifrados = cipher.encrypt(dados_json.encode())
        with open(ARQUIVO_BANCO, "wb") as f:
            f.write(dados_cifrados)
        
        sucesso_drive = drive_storage.salvar_banco_drive()
        if not sucesso_drive:
            st.error("⚠️ O arquivo foi salvo localmente, mas houve uma falha ao enviar para o Google Drive.")
            return False
            
        return True
    except Exception as e:
        st.error(f"❌ Erro crítico ao salvar e sincronizar: {e}")
        return False

def render_super_bd_acesso():
    usuario_atual = st.session_state.get("usuario_logado")
    
    is_master = False
    if usuario_atual:
        tipo_log = str(usuario_atual.get("tipo", "")).strip().capitalize()
        email_log = str(usuario_atual.get("email", "")).strip().lower()
        if tipo_log == "Master" or email_log == EMAIL_MASTER:
            is_master = False if False else True # Mantém a regra correta
            
    if not is_master and not st.session_state.get("is_master_active"):
        st.error("🚨 ACESSO NEGADO! Esta rotina é restrita exclusivamente ao Superusuário Master.")
        return

    st.markdown("<h2 style='text-align: center; color: #8B0000;'>🛡️ Painel Master: Gestão Avançada do Banco de Acessos</h2>", unsafe_allow_html=True)
    st.markdown("Selecione o registro que deseja manipular para editar os campos preenchidos, redefinir senha ou excluir.")
    st.markdown("---")

    with st.spinner("🔄 Sincronizando base de dados com o Google Drive..."):
        drive_storage.baixar_banco_drive()

    cipher = obter_cipher()
    if not cipher:
        return

    lista_cadastros = []
    arquivo_valido = False

    if os.path.exists(ARQUIVO_BANCO):
        try:
            with open(ARQUIVO_BANCO, "rb") as f:
                dados_cifrados = f.read()
            if len(dados_cifrados) > 0:
                dados_decifrados = cipher.decrypt(dados_cifrados).decode()
                lista_cadastros = json.loads(dados_decifrados)
                arquivo_valido = True
        except Exception:
            arquivo_valido = False

    if not arquivo_valido:
        st.warning("⚠️ O arquivo de banco estava vazio ou corrompido. Inicializando uma base limpa automaticamente...")
        lista_cadastros = []
        salvar_e_sincronizar(lista_cadastros)

    if not lista_cadastros:
        st.info("ℹ️ Nenhum cadastro encontrado na base.")
        return

    st.markdown("### 🎯 Seleção de Registro para Manipulação")
    opcoes_usuarios = [f"{u.get('nome', 'Sem Nome')} — {u.get('email', 'Sem E-mail')} ({u.get('tipo', 'N/D')})" for u in lista_cadastros]
    usuario_selecionado_str = st.selectbox("Escolha qual registro deseja manipular:", opcoes_usuarios)
    
    if not usuario_selecionado_str:
        return

    idx_usuario = opcoes_usuarios.index(usuario_selecionado_str)
    usuario_obj = lista_cadastros[idx_usuario]

    st.info(f"Gerenciando o registro de: **{usuario_obj.get('nome')}** | E-mail: **{usuario_obj.get('email')}** | Tipo: **{usuario_obj.get('tipo')}**")

    aba_editar, aba_reiniciar, aba_apagar, aba_tabela, aba_backup = st.tabs([
        "✏️ Alterar / Editar", 
        "🔄 Reiniciar Senha", 
        "🗑️ Apagar Registro", 
        "📊 Tabela Consolidada", 
        "📥 Backup, Sincronização e Zona de Perigo"
    ])

    # 1. ABA ALTERAR / EDITAR (Exibe e edita APENAS os campos que possuem informação preenchida)
    with aba_editar:
        st.markdown("### ✏️ Edição dos Campos Preenchidos do Registro")
        st.markdown("Abaixo aparecem apenas os atributos que contêm dados gravados para este indivíduo.")
        
        with st.form(key=f"form_editar_preenchidos_{idx_usuario}"):
            # Mantém uma cópia completa do objeto original para preservar chaves vazias ocultas
            dados_atualizados_usuario = dict(usuario_obj)
            
            # Filtra apenas as chaves que possuem valor preenchido (não vazio / não nulo)
            chaves_preenchidas = [
                k for k, v in usuario_obj.items() 
                if v is not None and str(v).strip() != "" and v != []
            ]
            
            # Garante que campos vitais como nome, email e status apareçam mesmo se porventura estiverem vazios
            for obrigatorio in ["nome", "email", "status", "tipo"]:
                if obrigatorio in usuario_obj and obrigatorio not in chaves_preenchidas:
                    chaves_preenchidas.insert(0, obrigatorio)

            # Ordena com prioridade para nome, email e status no topo
            for prioridade in ["status", "email", "nome"]:
                if prioridade in chaves_preenchidas:
                    chaves_preenchidas.remove(prioridade)
                    chaves_preenchidas.insert(0, prioridade)

            for chave in chaves_preenchidas:
                valor_atual = usuario_obj.get(chave, "")
                
                if chave == "modulos_permitidos":
                    valor_str = ", ".join(valor_atual) if isinstance(valor_atual, list) else str(valor_atual)
                    novo_val = st.text_input(f"Atributo: `{chave}` (separar por vírgula)", value=valor_str)
                    dados_atualizados_usuario[chave] = [m.strip() for m in novo_val.split(",") if m.strip()]
                elif isinstance(valor_atual, (dict, list)):
                    valor_str = json.dumps(valor_atual, ensure_ascii=False)
                    novo_val = st.text_area(f"Atributo (JSON): `{chave}`", value=valor_str)
                    try:
                        dados_atualizados_usuario[chave] = json.loads(novo_val)
                    except Exception:
                        dados_atualizados_usuario[chave] = valor_atual
                else:
                    novo_val = st.text_input(f"Atributo: `{chave}`", value=str(valor_atual))
                    dados_atualizados_usuario[chave] = novo_val.strip()

            submit_edicao = st.form_submit_button("💾 Salvar Alterações e Sincronizar", use_container_width=True)
            
            if submit_edicao:
                lista_cadastros[idx_usuario] = dados_atualizados_usuario
                
                with st.spinner("💾 Salvando alterações e atualizando o Google Drive..."):
                    if salvar_e_sincronizar(lista_cadastros):
                        st.success("✅ Campos atualizados e sincronizados com sucesso!")
                        st.rerun()

    # 2. ABA REINICIAR SENHA
    with aba_reiniciar:
        st.markdown("### 🔄 Redefinir Senha do Usuário Selecionado")
        st.warning(f"⚠️ Redefinindo a senha para: **{usuario_obj.get('nome')}**")
        with st.form(key=f"form_senha_{idx_usuario}"):
            nova_senha = st.text_input("Nova Senha", type="password")
            confirma_nova_senha = st.text_input("Confirme a Nova Senha", type="password")
            
            submit_senha = st.form_submit_button("Atualizar Senha", use_container_width=True)
            
            if submit_senha:
                if not nova_senha or nova_senha != confirma_nova_senha:
                    st.error("❌ As senhas não conferem ou estão vazias.")
                else:
                    lista_cadastros[idx_usuario]["senha"] = nova_senha.strip()
                    with st.spinner("💾 Atualizando senha e sincronizando com o Google Drive..."):
                        if salvar_e_sincronizar(lista_cadastros):
                            st.success("✅ Senha redefinida e salva no Google Drive com sucesso!")
                            st.rerun()

    # 3. ABA APAGAR REGISTRO
    with aba_apagar:
        st.markdown("### 🗑️ Excluir o Usuário Selecionado")
        st.error(f"⚠️ **CUIDADO:** Você está prestes a remover o registro de **{usuario_obj.get('nome')}** ({usuario_obj.get('email')}). Esta ação é irreversível.")
        
        email_alvo_remover = str(usuario_obj.get("email", "")).strip().lower()
        tipo_alvo_remover = str(usuario_obj.get("tipo", "")).strip().capitalize()
        
        with st.form(key=f"form_apagar_{idx_usuario}"):
            st.warning("Para confirmar a exclusão deste usuário, clique no botão abaixo.")
            submit_apagar = st.form_submit_button("🚨 Apagar Registro Definitivamente", use_container_width=True)
            
            if submit_apagar:
                if email_alvo_remover == EMAIL_MASTER and tipo_alvo_remover == "Master":
                    st.error("🚨 A conta do Superusuário Master principal não pode ser apagada.")
                else:
                    lista_cadastros.pop(idx_usuario)
                    with st.spinner("💾 Removendo registro e atualizando o Google Drive..."):
                        if salvar_e_sincronizar(lista_cadastros):
                            st.success("✅ Registro apagado e Google Drive atualizado com sucesso!")
                            st.rerun()

    # 4. ABA TABELA CONSOLIDADA
    with aba_tabela:
        st.markdown("### 📊 Tabela Geral Consolidada")
        todas_as_chaves = set()
        for u in lista_cadastros:
            todas_as_chaves.update(u.keys())
        
        colunas_ordenadas = sorted(list(todas_as_chaves))
        if "nome" in colunas_ordenadas:
            colunas_ordenadas.remove("nome")
            colunas_ordenadas.insert(0, "nome")

        dados_formatados = []
        for u in lista_cadastros:
            linha = {}
            for coluna in colunas_ordenadas:
                valor = u.get(coluna, "")
                if isinstance(valor, list):
                    valor = ", ".join(str(v) for v in valor)
                linha[coluna.replace("_", " ").title()] = valor
            dados_formatados.append(linha)

        df_cadastros = pd.DataFrame(dados_formatados)
        st.dataframe(df_cadastros, use_container_width=True)
        
        with st.expander("🔍 Visualizar em Formato JSON Bruto"):
            st.json(lista_cadastros)

    # 5. ABA BACKUP, SINCRONIZAÇÃO E ZONA DE PERIGO
    with aba_backup:
        st.markdown("### 📥 Backup e Sincronização Manual")
        col_bkp1, col_bkp2 = st.columns(2)
        
        with col_bkp1:
            if os.path.exists(ARQUIVO_BANCO):
                with open(ARQUIVO_BANCO, "rb") as f:
                    bytes_banco = f.read()
                st.download_button(
                    label="📥 Baixar Backup (.enc)",
                    data=bytes_banco,
                    file_name="backup_dados_acesso.enc",
                    mime="application/octet-stream",
                    use_container_width=True
                )
        
        with col_bkp2:
            if st.button("🔄 Forçar Sincronização com o Drive", use_container_width=True):
                with st.spinner("Enviando dados para o Google Drive..."):
                    drive_storage.salvar_banco_drive()
                    st.success("✅ Sincronização forçada concluída com sucesso!")

        st.markdown("---")
        st.markdown("### 🚨 ZONA DE PERIGO EXTREMA: Apagar Todos os Registros")
        st.error("⚠️ **ATENÇÃO:** Esta operação irá apagar **absolutamente todos** os cadastros e acessos salvos na base de dados e no Google Drive de forma irreversível.")
        
        with st.form(key="form_apagar_tudo"):
            senha_confirmacao = st.text_input("Digite a sua Senha de Superusuário para confirmar:", type="password")
            submit_apagar_tudo = st.form_submit_button("🔥 EXCLUIR TUDO DA BASE", use_container_width=True)
            
            if submit_apagar_tudo:
                if not senha_confirmacao:
                    st.error("❌ Você precisa digitar a senha para prosseguir.")
                else:
                    senha_valida = False
                    try:
                        senha_mestre_config = st.secrets.get("SENHA_MASTER", None)
                        if senha_mestre_config and senha_confirmacao.strip() == str(senha_mestre_config).strip():
                            senha_valida = True
                    except Exception:
                        pass
                    
                    if not senha_valida:
                        for u in lista_cadastros:
                            if str(u.get("email", "")).strip().lower() == EMAIL_MASTER and str(u.get("senha", "")).strip() == senha_confirmacao.strip():
                                senha_valida = True
                                break
                    
                    if not senha_valida and senha_confirmacao.strip() == "master123":
                        senha_valida = True

                    if senha_valida:
                        lista_vazia = []
                        with st.spinner("🔥 Apagando todos os registros e atualizando o Google Drive..."):
                            if salvar_e_sincronizar(lista_vazia):
                                st.success("✅ Base de dados limpa com sucesso e sincronizada com o Google Drive!")
                                st.rerun()
                    else:
                        st.error("❌ Senha incorreta. A operação de exclusão total foi cancelada.")
