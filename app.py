import sys
import time
import json
import os
from pathlib import Path
from cryptography.fernet import Fernet
import streamlit as st
from rotinas import drive_storage

st.set_page_config(page_title="SAAP - WEB | CPFS", layout="wide")

ROOT_DIR = Path(__file__).resolve().parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

try:
    from rotinas import cosis_INCLUSAO, cosis_ATUALIZACAO, cosis_PESQUISA, acesso_CADASTRO, acesso_CONFIRMACAO, acesso_LOGIN, info_LIBERAR, super_BD_ACESSO
except ImportError:
    pass

# --- INICIALIZAÇÃO SEGURA DO ESTADO DA SESSÃO ---
if "ultimo_acesso" not in st.session_state: st.session_state["ultimo_acesso"] = time.time()
if "source_df" not in st.session_state: st.session_state["source_df"] = None
if "wb_data" not in st.session_state: st.session_state["wb_data"] = None
if "fila_modificacoes" not in st.session_state: st.session_state["fila_modificacoes"] = []
if "pagina" not in st.session_state: st.session_state["pagina"] = "menu"
if "usuario_logado" not in st.session_state: st.session_state["usuario_logado"] = None
if "is_master_active" not in st.session_state: st.session_state["is_master_active"] = False

EMAIL_MASTER = "pricardosbrito@gmail.com"
ARQUIVO_BANCO = "dados_acesso_cpfs.enc"

def eh_usuario_master():
    if st.session_state.get("is_master_active") is True:
        return True
        
    usuario = st.session_state.get("usuario_logado")
    if usuario:
        tipo_log = str(usuario.get("tipo", "")).strip().capitalize()
        email_log = str(usuario.get("email", "")).strip().lower()
        if tipo_log == "Master" or email_log == EMAIL_MASTER:
            st.session_state["is_master_active"] = True
            return True
            
    st.session_state["is_master_active"] = False
    return False

# --- ATALHO DE URL / PARÂMETRO PARA O CRIADOR (?master=1) ---
if st.query_params.get("master") == "1":
    st.session_state["is_master_active"] = True
    if not st.session_state.get("usuario_logado"):
        st.session_state["usuario_logado"] = {
            "nome": "Superusuário Master",
            "email": EMAIL_MASTER,
            "tipo": "Master",
            "status": "Ativo",
            "modulos_permitidos": ["inclusao", "atualizacoes", "pesquisa", "info_liberar", "super_bd_acesso"]
        }

def contar_pendentes_ti():
    try:
        drive_storage.baixar_banco_drive()
        chave = st.secrets["CHAVE_SISTEMA"].encode()
        cipher = Fernet(chave)
        if not os.path.exists(ARQUIVO_BANCO): return 0
        with open(ARQUIVO_BANCO, "rb") as f:
            dados = f.read()
        if not dados: return 0
        lista = json.loads(cipher.decrypt(dados).decode())
        
        count = sum(
            1 for u in lista 
            if u.get("status") == "Senha Ativa" and not u.get("modulos_permitidos")
        )
        return count
    except Exception:
        return 0

def realizar_navegacao(destino):
    st.session_state["pagina"] = destino
    st.rerun()

# --- TRATAMENTO DOS PARÂMETROS DE NAVEGAÇÃO DO MENU HTML ---
if "nav" in st.query_params:
    nav_alvo = st.query_params.get("nav")
    st.query_params.clear()
    if nav_alvo:
        st.session_state["pagina"] = nav_alvo
        st.rerun()

BAHIA_FLAG_SVG = "data:image/svg+xml;utf8,<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 900 600'><rect width='900' height='600' fill='%23ffffff'/><rect y='150' width='900' height='150' fill='%23c8102e'/><rect y='450' width='900' height='150' fill='%23c8102e'/><rect width='300' height='300' fill='%23002b7f'/><polygon points='150,60 225,225 75,225' fill='%23ffffff'/></svg>"

st.markdown(f"""
<style>
    .stApp {{ background-image: linear-gradient(rgba(255, 255, 255, 0.90), rgba(255, 255, 255, 0.90)), url("{BAHIA_FLAG_SVG}") !important; background-repeat: repeat !important; background-position: top left !important; background-size: 300px 200px !important; background-attachment: fixed !important; }}
    [data-testid="stAppViewContainer"], [data-testid="stHeader"], [data-testid="stMain"], .main {{ background: transparent !important; }}
    div.stButton > button {{ width: 100% !important; height: 52px !important; border-radius: 8px !important; border: 2px solid #CE1126 !important; background-color: #FFFFFF !important; color: #CE1126 !important; font-weight: 700 !important; font-size: 15px !important; transition: all 0.25s ease-in-out !important; box-shadow: 0 4px 10px rgba(0, 0, 0, 0.08) !important; }}
    div.stButton > button:hover {{ background-color: #002B7F !important; border-color: #002B7F !important; color: #FFFFFF !important; transform: translateY(-2px) !important; }}
    div.element-container:has(.btn-voltar-fixo) + div.element-container button {{ position: fixed !important; top: 20px !important; left: 20px !important; right: auto !important; z-index: 999999 !important; width: auto !important; height: 46px !important; padding: 0 1.2rem !important; background-color: #CE1126 !important; border: 2px solid #FFFFFF !important; color: #FFFFFF !important; border-radius: 8px !important; font-weight: 700 !important; font-size: 14px !important; box-shadow: 0 4px 12px rgba(0, 0, 0, 0.25) !important; transition: all 0.25s ease-in-out !important; }}
    div.element-container:has(.btn-voltar-fixo) + div.element-container button:hover {{ background-color: #002B7F !important; border-color: #FFFFFF !important; color: #FFFFFF !important; transform: scale(1.05) !important; }}
    .menu-nav-container {{ display: flex; justify-content: center; gap: 20px; margin: 20px 0 30px 0; flex-wrap: wrap; }}
    .nav-dropdown {{ position: relative; display: inline-block; }}
    .nav-dropbtn {{ background-color: #FFFFFF; color: #CE1126; padding: 14px 24px; font-size: 15px; font-weight: 700; border: 2px solid #CE1126; border-radius: 8px; cursor: pointer; box-shadow: 0 4px 10px rgba(0, 0, 0, 0.08); transition: all 0.25s ease-in-out; text-align: center; min-width: 220px; }}
    .nav-dropdown-content {{ display: none; position: absolute; background-color: #FFFFFF; min-width: 220px; box-shadow: 0px 8px 16px rgba(0,0,0,0.2); z-index: 99999; border-radius: 8px; border: 1px solid #ddd; left: 0; }}
    .nav-dropdown-content a, .nav-dropdown-content .nav-dropbtn-nested {{ color: #002B7F; padding: 12px 18px; text-decoration: none; display: block; font-weight: 600; font-size: 14px; transition: background 0.2s, color 0.2s; border-bottom: 1px solid #f0f0f0; cursor: pointer; }}
    .nav-dropdown-content a:last-child {{ border-bottom: none; }}
    .nav-dropdown-content a:hover, .nav-dropdown-content .nav-dropbtn-nested:hover {{ background-color: #002B7F; color: #FFFFFF; }}
    .nav-dropdown:hover .nav-dropdown-content {{ display: block; }}
    .nav-dropdown:hover .nav-dropbtn {{ background-color: #002B7F; color: #FFFFFF; border-color: #002B7F; transform: translateY(-2px); }}
    .nested-dropdown {{ position: relative; }}
    .nested-content {{ display: none; position: absolute; left: 100%; top: 0; background-color: #FFFFFF; min-width: 230px; box-shadow: 0px 8px 16px rgba(0,0,0,0.2); border: 1px solid #ddd; border-radius: 8px; overflow: hidden; }}
    .nested-dropdown:hover .nested-content {{ display: block; }}
</style>
""", unsafe_allow_html=True)

TEMPO_LIMITE_SEGUNDOS = 300
tempo_inativo = time.time() - st.session_state["ultimo_acesso"]

if tempo_inativo > TEMPO_LIMITE_SEGUNDOS and st.session_state["usuario_logado"] is not None and not eh_usuario_master():
    st.session_state["usuario_logado"] = None
    st.session_state["is_master_active"] = False
    st.session_state["pagina"] = "menu"
    st.toast("⏳ Sessão expirada por inatividade (5 minutos).", icon="🔒")

st.session_state["ultimo_acesso"] = time.time()

master_param = "&master=1" if eh_usuario_master() else ""

if st.session_state["pagina"] == "menu":
    st.markdown(
        """
        <div style='text-align: center; padding: 1.5rem 1rem; background: linear-gradient(135deg, #002B7F 0%, #1E3C72 100%); color: white; border-radius: 12px; margin-bottom: 1.8rem; box-shadow: 0 6px 15px rgba(0, 0, 0, 0.18); border-bottom: 4px solid #CE1126;'>
            <div style='background-color: rgba(255, 255, 255, 0.15); padding: 4px 16px; border-radius: 20px; font-size: 0.85rem; font-weight: 700; letter-spacing: 1px; text-transform: uppercase; color: #FFD700; display: inline-block; margin-bottom: 8px;'>
                CPFS - Conjunto Penal de Feira de Santana
            </div>
            <h1 style='margin: 4px 0 8px 0; font-size: 1.75rem; font-weight: 800; text-transform: uppercase; letter-spacing: 0.5px; text-shadow: 0 2px 4px rgba(0,0,0,0.3);'>
                SISTEMA DE APOIO A ATIVIDADE PRISIONAL/SAAP - WEB
            </h1>
            <p style='margin: 0; font-size: 1.05rem; font-weight: 400; opacity: 0.95; font-style: italic; color: #F0F4F8;'>
                'Facilidades para todos que vivenciam o Sistema Prisional'
            </p>
        </div>
        """,
        unsafe_allow_html=True
    )

    qtd_ti = contar_pendentes_ti()
    texto_liberar_acesso = f"Liberar Acesso ({qtd_ti})" if qtd_ti > 0 else "Liberar Acesso"
    estilo_liberar = "color: #CE1126; font-weight: bold;" if qtd_ti > 0 else ""

    st.markdown(f"""
<div class="menu-nav-container">

<div class="nav-dropdown">
<div class="nav-dropbtn">PRIMEIRO ACESSO</div>
<div class="nav-dropdown-content">
<a href="?nav=cadastrar_acesso{master_param}" target="_self">Cadastrar Acesso</a>
<a href="?nav=confirmar_acesso{master_param}" target="_self">Confirmar Acesso / Token</a>
<a href="?nav=esqueci_senha{master_param}" target="_self">Esqueci a Senha</a>
</div>
</div>

<div class="nav-dropdown">
<div class="nav-dropbtn">ADMINISTRAÇÃO</div>
<div class="nav-dropdown-content">
<a href="?nav=admin_atendimento{master_param}" target="_self">Atendimento</a>

<div class="nested-dropdown">
<div class="nav-dropbtn-nested">Cosis ⯈</div>
<div class="nested-content">
<a href="?nav=atualizacoes{master_param}" target="_self">Atualização Geral</a>
<a href="?nav=inclusao{master_param}" target="_self">Inclusão para Trabalho</a>
<a href="?nav=pesquisa{master_param}" target="_self">Pesquisa Remição</a>
</div>
</div>

<a href="?nav=admin_direcao{master_param}" target="_self">Direção</a>

<div class="nested-dropdown">
<div class="nav-dropbtn-nested">Informática ⯈</div>
<div class="nested-content">
<a href="?nav=info_liberar{master_param}" target="_self" style="{estilo_liberar}">{texto_liberar_acesso}</a>
<a href="?nav=info_manutencao{master_param}" target="_self">Manutenção</a>
</div>
</div>

<a href="?nav=admin_seguranca{master_param}" target="_self">Segurança</a>
</div>
</div>

<div class="nav-dropdown">
<div class="nav-dropbtn">PÚBLICO GERAL</div>
<div class="nav-dropdown-content">
<a href="?nav=pub_advogado{master_param}" target="_self">Advogado</a>
<a href="?nav=pub_outros{master_param}" target="_self">Outros</a>
<a href="?nav=pub_religioso{master_param}" target="_self">Religioso</a>
<a href="?nav=pub_visitante{master_param}" target="_self">Visitante</a>
</div>
</div>

</div>
""", unsafe_allow_html=True)

    if eh_usuario_master():
        st.markdown("<div style='text-align: center; margin-bottom: 1rem;'>", unsafe_allow_html=True)
        if st.button("🛡️ PAINEL MASTER: DB-ACESSO", key="btn_super_bd", use_container_width=True):
            realizar_navegacao("super_bd_acesso")
        st.markdown("</div>", unsafe_allow_html=True)

    st.markdown("<br><br>", unsafe_allow_html=True)

    col4, col5 = st.columns(2)
    with col4:
        if st.button("LIMPAR MEMÓRIA", key="btn_clean", use_container_width=True):
            st.session_state["wb_data"] = None
            st.session_state["source_df"] = None
            st.session_state["fila_modificacoes"] = []
            st.toast("Memória limpa com sucesso!", icon="✅")
    with col5:
        btn_label = "🟢 ENCERRAR SESSÃO" if eh_usuario_master() else "SAIR"
        if st.button(btn_label, key="btn_exit", use_container_width=True):
            st.session_state["usuario_logado"] = None
            st.session_state["is_master_active"] = False
            st.session_state["pagina"] = "menu"
            st.query_params.clear()
            st.cache_data.clear()
            st.cache_resource.clear()
            st.toast("Sessão encerrada com segurança.", icon="🔒")
            st.rerun()

else:
    st.markdown('<div class="btn-voltar-fixo"></div>', unsafe_allow_html=True)
    if st.button("⬅️ VOLTAR AO MENU", key="btn_voltar_fixo"):
        realizar_navegacao("menu")

    st.markdown("<div style='margin-top: 1.5rem;'></div>", unsafe_allow_html=True)

    pagina_atual = st.session_state["pagina"]

    if eh_usuario_master():
        if pagina_atual == "cadastrar_acesso" and 'acesso_CADASTRO' in globals():
            acesso_CADASTRO.render_cadastrar_acesso()
        elif pagina_atual == "confirmar_acesso" and 'acesso_CONFIRMACAO' in globals():
            acesso_CONFIRMACAO.render_confirmar_acesso()
        elif pagina_atual == "inclusao" and 'cosis_INCLUSAO' in globals():
            cosis_INCLUSAO.render_inclusao_trabalho()
        elif pagina_atual == "atualizacoes" and 'cosis_ATUALIZACAO' in globals():
            cosis_ATUALIZACAO.render_atualizacoes_gerais()
        elif pagina_atual == "pesquisa" and 'cosis_PESQUISA' in globals():
            cosis_PESQUISA.render_pesquisa_remicao()
        elif pagina_atual == "info_liberar" and 'info_LIBERAR' in globals():
            info_LIBERAR.render_liberar_acesso()
        elif pagina_atual == "info_manutencao":
            st.info("🚧 Rotina **Manutenção de Informática** em desenvolvimento.")
        elif pagina_atual == "super_bd_acesso" and 'super_BD_ACESSO' in globals():
            super_BD_ACESSO.render_super_bd_acesso()
        else:
            st.warning(f"🚧 Rotina **{pagina_atual.replace('_', ' ').title()}** em desenvolvimento.")
    else:
        if pagina_atual in ["cadastrar_acesso", "confirmar_acesso"]:
            if pagina_atual == "cadastrar_acesso" and 'acesso_CADASTRO' in globals():
                acesso_CADASTRO.render_cadastrar_acesso()
            elif pagina_atual == "confirmar_acesso" and 'acesso_CONFIRMACAO' in globals():
                acesso_CONFIRMACAO.render_confirmar_acesso()
        else:
            usuario = st.session_state.get("usuario_logado")
            if pagina_atual.startswith("super_"):
                st.error("🚨 ACESSO NEGADO! Esta rotina é restrita exclusivamente ao Superusuário Master.")
                if st.button("Voltar ao Menu"):
                    realizar_navegacao("menu")
            else:
                if usuario is None and 'acesso_LOGIN' in globals():
                    acesso_LOGIN.render_tela_login(pagina_atual)
                else:
                    modulos = usuario.get("modulos_permitidos", []) if usuario else []

                    if pagina_atual in modulos:
                        if pagina_atual == "inclusao" and 'cosis_INCLUSAO' in globals():
                            cosis_INCLUSAO.render_inclusao_trabalho()
                        elif pagina_atual == "atualizacoes" and 'cosis_ATUALIZACAO' in globals():
                            cosis_ATUALIZACAO.render_atualizacoes_gerais()
                        elif pagina_atual == "pesquisa" and 'cosis_PESQUISA' in globals():
                            cosis_PESQUISA.render_pesquisa_remicao()
                        elif pagina_atual == "info_liberar" and 'info_LIBERAR' in globals():
                            info_LIBERAR.render_liberar_acesso()
                        elif pagina_atual == "info_manutencao":
                            st.info("🚧 Rotina **Manutenção de Informática** em desenvolvimento.")
                        else:
                            st.warning(f"🚧 Rotina **{pagina_atual.replace('_', ' ').title()}** em desenvolvimento.")
                    else:
                        st.error("🚨 VOCÊ NÃO TEM ACESSO AUTORIZADO A ESTA ROTINA!")
                        if st.button("Voltar ao Menu"):
                            realizar_navegacao("menu")
