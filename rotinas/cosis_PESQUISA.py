import io
import pandas as pd
import streamlit as st
import streamlit.components.v1 as components

from utils.data_helpers import extrair_mes_ano_do_nome
from utils.excel_styles import deduplicar_colunas, formatar_datas_dataframe, obter_nome_coluna_por_letra
from utils.excel_word import gerar_docx_bytes, gerar_excel_bytes
from utils.ui_components import gerar_config_largura_colunas, titulo_estilizado
from utils.drive_helpers import (
    listar_arquivos_da_pasta,
    baixar_arquivo_bytes,
    salvar_arquivo_no_drive
)

try:
    from utils import titulo_estilizado
except ImportError:
    def titulo_estilizado(texto):
        st.markdown(f"## {texto}")


def eh_arquivo_valido(item):
    """Filtra pastas válidas e ignora arquivos temporários (.~, ~$), ocultos, sem extensão e arquivos de sistema (Thumbs.db, credentials.json)."""
    nome = item.get("name", "")
    if not nome:
        return False
    # Ignora explicitamente o credentials.json caso venha na listagem
    if nome.lower() == 'credentials.json':
        return False
    if item.get('mimeType') == 'application/vnd.google-apps.folder':
        return True
    if nome.lower() in ('thumbs.db', 'desktop.ini'):
        return False
    if nome.startswith(('.~', '~$', '.')):
        return False
    if '.' not in nome:
        return False
    return True

def limpar_resultados_downstream():
    """Limpa a visualização, dados consolidados e caches de arquivos para manter a tela limpa."""
    st.session_state["executar_config"] = False
    st.session_state["pesquisa_df"] = None
    st.session_state["arquivos_drive_alvo"] = []
    st.session_state["bytes_cache"] = {}


def alternar_marcar_desmarcar_pasta(folder_id, folder_name="Pasta"):
    """Alterna a seleção de todos os itens da pasta e atualiza o estado visual dos checkboxes imediatamente."""
    try:
        raw_itens = listar_arquivos_da_pasta(folder_id)
        itens = [f for f in raw_itens if eh_arquivo_valido(f)]
    except Exception:
        itens = []

    # Verifica se a pasta e todos os itens filhos já estão selecionados
    itens_ids = [item["id"] for item in itens] + [folder_id]
    todos_selecionados = all(i_id in st.session_state["itens_selecionados_map"] for i_id in itens_ids)

    novo_estado = not todos_selecionados

    if not novo_estado:
        # Desmarcar tudo da pasta
        st.session_state["itens_selecionados_map"].pop(folder_id, None)
        st.session_state[f"chk_folder_{folder_id}__in__{folder_id}"] = False # Ajuste preventivo
        
        for item in itens:
            i_id = item["id"]
            st.session_state["itens_selecionados_map"].pop(i_id, None)
            is_folder = item.get('mimeType') == 'application/vnd.google-apps.folder'
            if is_folder:
                st.session_state[f"chk_folder_{i_id}__in__{folder_id}"] = False
            else:
                st.session_state[f"chk_file_{i_id}__in__{folder_id}"] = False
    else:
        # Marcar tudo da pasta e atualizar o estado visual dos widgets
        st.session_state["pastas_abertas"].add(folder_id)
        st.session_state["itens_selecionados_map"][folder_id] = {
            "name": folder_name,
            "type": "folder",
            "id": folder_id
        }
        
        for item in itens:
            i_id = item["id"]
            i_name = item["name"]
            is_folder = item.get('mimeType') == 'application/vnd.google-apps.folder'
            
            if is_folder:
                st.session_state["pastas_abertas"].add(i_id)
                st.session_state["itens_selecionados_map"][i_id] = {
                    "name": i_name,
                    "type": "folder",
                    "id": i_id
                }
                st.session_state[f"chk_folder_{i_id}__in__{folder_id}"] = True
            else:
                st.session_state["itens_selecionados_map"][i_id] = {
                    "name": i_name,
                    "type": "file",
                    "id": i_id
                }
                st.session_state[f"chk_file_{i_id}__in__{folder_id}"] = True

    limpar_resultados_downstream()


def render_pesquisa_remicao():
    titulo_estilizado("Pesquisa para Remição")

    if "uploader_key" not in st.session_state:
        st.session_state["uploader_key"] = 0

    ROOT_FOLDER_ID = "1ZeCu40Bzt1hb1BsgNArG_zKR54GPcuOY"

    if "itens_selecionados_map" not in st.session_state:
        st.session_state["itens_selecionados_map"] = {}

    if "pastas_abertas" not in st.session_state:
        st.session_state["pastas_abertas"] = set()

    st.subheader("1. Seleção de Pastas e Arquivos (Google Drive)")

    if not ROOT_FOLDER_ID.strip():
        st.error("ID da pasta do Google Drive não configurado.")
        return

    ITEMS_PER_ROW = 3

    pastas_para_processar = [{"id": ROOT_FOLDER_ID, "name": "Pasta Raiz"}]
    pastas_processadas = set()

    while pastas_para_processar:
        atual = pastas_para_processar.pop(0)
        p_id = atual["id"]
        p_name = atual["name"]

        if p_id in pastas_processadas:
            continue
        pastas_processadas.add(p_id)

        with st.container():
            st.markdown(f"📂 **Pasta Atual: `{p_name}`**")

            try:
                raw_itens = listar_arquivos_da_pasta(p_id)
                itens = [f for f in raw_itens if eh_arquivo_valido(f)]
            except Exception as e:
                st.error(f"Erro ao listar arquivos de '{p_name}': {e}")
                itens = []

            if not itens:
                st.caption("*(Pasta vazia ou sem arquivos válidos)*")
                st.markdown("---")
                continue

            pastas = sorted(
                [f for f in itens if f.get('mimeType') == 'application/vnd.google-apps.folder'],
                key=lambda x: x['name'].lower()
            )
            arquivos = sorted(
                [f for f in itens if f.get('mimeType') != 'application/vnd.google-apps.folder'],
                key=lambda x: x['name'].lower()
            )

            # Botão de Marcar / Desmarcar Tudo da pasta atual
            col_b1, _ = st.columns([2, 4])
            with col_b1:
                if st.button("Marcar / Desmarcar Tudo", key=f"btn_toggle_all_{p_id}"):
                    alternar_marcar_desmarcar_pasta(p_id, p_name)
                    st.rerun()

            # --- SUBPASTAS COM CHECKBOX ---
            if pastas:
                st.markdown("**📁 Subpastas:**")
                for i in range(0, len(pastas), ITEMS_PER_ROW):
                    chunk = pastas[i:i + ITEMS_PER_ROW]
                    cols = st.columns(ITEMS_PER_ROW)
                    for idx, p in enumerate(chunk):
                        with cols[idx]:
                            sub_id = p['id']
                            sub_name = p['name']
                            chk_key = f"chk_folder_{sub_id}__in__{p_id}"
                            
                            # Sincroniza o estado inicial do widget com o mapa de selecionados
                            if chk_key not in st.session_state:
                                st.session_state[chk_key] = (sub_id in st.session_state["itens_selecionados_map"])

                            checked = st.checkbox(
                                f"📁 {sub_name}",
                                key=chk_key
                            )

                            is_selected = (sub_id in st.session_state["itens_selecionados_map"])
                            if checked != is_selected:
                                if checked:
                                    st.session_state["itens_selecionados_map"][sub_id] = {"name": sub_name, "type": "folder", "id": sub_id}
                                    st.session_state["pastas_abertas"].add(sub_id)
                                else:
                                    st.session_state["itens_selecionados_map"].pop(sub_id, None)
                                limpar_resultados_downstream()
                                st.rerun()

                            if checked or sub_id in st.session_state["pastas_abertas"]:
                                pastas_para_processar.append({"id": sub_id, "name": sub_name})

            # --- ARQUIVOS COM CHECKBOX ---
            if arquivos:
                st.markdown("**📄 Arquivos:**")
                for i in range(0, len(arquivos), ITEMS_PER_ROW):
                    chunk = arquivos[i:i + ITEMS_PER_ROW]
                    cols = st.columns(ITEMS_PER_ROW)
                    for idx, f in enumerate(chunk):
                        with cols[idx]:
                            f_id = f['id']
                            f_name = f['name']
                            chk_key = f"chk_file_{f_id}__in__{p_id}"
                            
                            # Sincroniza o estado inicial do widget com o mapa de selecionados
                            if chk_key not in st.session_state:
                                st.session_state[chk_key] = (f_id in st.session_state["itens_selecionados_map"])

                            checked = st.checkbox(
                                f"📄 {f_name}",
                                key=chk_key
                            )

                            is_selected = (f_id in st.session_state["itens_selecionados_map"])
                            if checked != is_selected:
                                if checked:
                                    st.session_state["itens_selecionados_map"][f_id] = {"name": f_name, "type": "file", "id": f_id}
                                else:
                                    st.session_state["itens_selecionados_map"].pop(f_id, None)
                                limpar_resultados_downstream()
                                st.rerun()

            st.markdown("---")

    # --- ÁREA DE ITENS SELECIONADOS ---
    st.markdown("### 📋 Área de Itens Selecionados (Unificação Geral)")

    arquivos_finais_map = {}
    for item_id, item_info in list(st.session_state["itens_selecionados_map"].items()):
        if item_info["type"] == "file":
            arquivos_finais_map[item_id] = item_info["name"]

    # Ordena alfabeticamente pelo nome do arquivo
    arquivos_selecionados_lista = sorted(
        [{"id": fid, "name": fname} for fid, fname in arquivos_finais_map.items()],
        key=lambda x: x["name"].lower()
    )

    with st.expander(f"📦 Resumo Consolidado de Arquivos Selecionados ({len(arquivos_selecionados_lista)} arquivo(s) mapeado(s))", expanded=True):
        if arquivos_selecionados_lista:
            df_selecionados = pd.DataFrame(arquivos_selecionados_lista)
            st.dataframe(df_selecionados[["name"]].rename(columns={"name": "Nome do Arquivo"}), use_container_width=True, hide_index=True)

            if st.button("❌ Limpar Toda a Seleção"):
                st.session_state["itens_selecionados_map"] = {}
                st.session_state["pastas_abertas"] = set()
                # Limpa todas as chaves de checkboxes do state
                for k in list(st.session_state.keys()):
                    if k.startswith("chk_folder_") or k.startswith("chk_file_"):
                        st.session_state[k] = False
                limpar_resultados_downstream()
                st.rerun()
        else:
            st.info("Nenhum arquivo selecionado até o momento.")

    fazer_upload_btn = st.button("2. Carregar do Drive e Configurar Abas", key="btn_fazer_upload_op3", type="primary")

    if fazer_upload_btn:
        if arquivos_selecionados_lista:
            st.session_state["executar_config"] = True
            st.session_state["rolar_apos_upload"] = True
            st.session_state["arquivos_drive_alvo"] = arquivos_selecionados_lista
            st.success("Arquivos prontos para processamento!")
        else:
            st.error("Selecione pelo menos um arquivo para continuar.")
            limpar_resultados_downstream()

    # --- CONFIGURAÇÃO E CONSOLIDAÇÃO ---
    arquivos_alvo = st.session_state.get("arquivos_drive_alvo", [])
    if arquivos_alvo and st.session_state.get("executar_config"):
        settings = {}
        if "bytes_cache" not in st.session_state:
            st.session_state["bytes_cache"] = {}

        for f_idx, f_info in enumerate(arquivos_alvo):
            f_name = f_info["name"]
            f_id = f_info["id"]
            file_key = f"{f_idx}_{f_name}"

            if f_id not in st.session_state["bytes_cache"]:
                with st.spinner(f"Baixando {f_name} do Drive..."):
                    st.session_state["bytes_cache"][f_id] = baixar_arquivo_bytes(f_id)

            f_bytes = st.session_state["bytes_cache"][f_id]
            file_ext = f_name.split('.')[-1].lower()

            try:
                engine_val = 'odf' if file_ext == 'ods' else None
                xl = pd.ExcelFile(io.BytesIO(f_bytes), engine=engine_val)
                sheets_available = xl.sheet_names
            except Exception as e:
                st.error(f"Erro ao ler o arquivo {f_name}: {e}.")
                continue

            pref_sheets = [s for s in sheets_available if any(p in s.strip().upper() for p in ["COM REMUNER", "SEM REMUNER", "DEM_COM", "DEM_SEM"])]

            if pref_sheets:
                default_sheets = pref_sheets
                is_fallback = False
            else:
                default_sheets = [sheets_available[0]] if sheets_available else []
                is_fallback = True

            with st.expander(f"📁 Configurações para: Arquivo {f_idx+1} - **{f_name}**", expanded=True):
                selected_sheets = st.multiselect(
                    f"Selecione aba(s) para {f_name}",
                    sheets_available,
                    default=default_sheets,
                    key=f"sheets_{file_key}_{st.session_state['uploader_key']}"
                )

                sheet_config = {}
                for i, sheet in enumerate(selected_sheets):
                    st.markdown(f"**Aba: `{sheet}`**")

                    sheet_upper = sheet.strip().upper()
                    if "DEM_COM" in sheet_upper:
                        default_header = 17
                    elif "DEM_SEM" in sheet_upper:
                        default_header = 19
                    elif any(p in sheet_upper for p in ["COM REMUNER", "SEM REMUNER"]):
                        default_header = 11
                    else:
                        default_header = 10 if is_fallback else 11

                    header_row = st.number_input(
                        f"Linha do cabeçalho para aba '{sheet}'",
                        value=default_header,
                        min_value=1,
                        key=f"head_{file_key}_{sheet}_{st.session_state['uploader_key']}"
                    )

                    try:
                        df_preview = pd.read_excel(io.BytesIO(f_bytes), sheet_name=sheet, header=header_row - 1, nrows=0, engine=engine_val)
                        cols_aba = [str(c).strip() for c in df_preview.columns]
                    except:
                        cols_aba = []

                    default_col = None
                    for c in cols_aba:
                        c_up = str(c).strip().upper()
                        if c_up in ["NOME DO INTERNO", "NOME DO INTERNO "]:
                            default_col = c
                            break
                    if not default_col:
                        for c in cols_aba:
                            if str(c).strip().upper() == "NOME":
                                default_col = c
                                break
                    if not default_col:
                        for c in cols_aba:
                            if str(c).strip().upper().startswith("NOME"):
                                default_col = c
                                break
                    if not default_col:
                        for c in cols_aba:
                            if "NOME" in str(c).strip().upper():
                                default_col = c
                                break
                    if not default_col and len(cols_aba) > 8:
                        default_col = cols_aba[8]
                    elif not default_col and cols_aba:
                        default_col = cols_aba[0]

                    opcoes_colunas = ["--- Não pesquisar nesta aba ---"] + cols_aba
                    default_idx = opcoes_colunas.index(default_col) if default_col in opcoes_colunas else 0

                    col_escolhida = st.selectbox(
                        f"Selecione o campo (coluna) para a pesquisa na aba '{sheet}':",
                        opcoes_colunas,
                        index=default_idx,
                        key=f"col_search_{file_key}_{sheet}_{st.session_state['uploader_key']}"
                    )

                    sheet_config[sheet] = {
                        "header_idx": header_row - 1,
                        "col_busca": col_escolhida if col_escolhida != "--- Não pesquisar nesta aba ---" else None
                    }
                    st.markdown("---")

                settings[file_key] = sheet_config

        btn_consolidar = st.button("🔍 Carregar e Consolidar Dados para Pesquisa", key="btn_consolidar_op3", type="primary")

        if st.session_state.get("rolar_apos_upload"):
            components.html(
                """
                <script>
                    function rolarAteOFinal() {
                        const doc = window.parent.document;
                        const container = doc.querySelector('section.main') || doc.querySelector('[data-testid="stMain"]') || doc.querySelector('[data-testid="stAppViewContainer"]') || doc.documentElement;
                        if (container) {
                            container.scrollTo({ top: container.scrollHeight, behavior: 'smooth' });
                        }
                    }
                    setTimeout(rolarAteOFinal, 400);
                    setTimeout(rolarAteOFinal, 800);
                </script>
                """,
                height=0
            )
            st.session_state["rolar_apos_upload"] = False

        if btn_consolidar:
            all_results = []
            
            # Mapeamento para converter o mês numérico em sigla
            meses_sigla_map = {
                "1": "JAN", "01": "JAN",
                "2": "FEV", "02": "FEV",
                "3": "MAR", "03": "MAR",
                "4": "ABR", "04": "ABR",
                "5": "MAI", "05": "MAI",
                "6": "JUN", "06": "JUN",
                "7": "JUL", "07": "JUL",
                "8": "AGO", "08": "AGO",
                "9": "SET", "09": "SET",
                "10": "OUT",
                "11": "NOV",
                "12": "DEZ"
            }

            for f_idx, f_info in enumerate(arquivos_alvo):
                f_name = f_info["name"]
                f_id = f_info["id"]
                file_key = f"{f_idx}_{f_name}"
                f_bytes = st.session_state["bytes_cache"].get(f_id, b"")
                file_ext = f_name.split('.')[-1].lower()
                engine_val = 'odf' if file_ext == 'ods' else None

                try:
                    xl = pd.ExcelFile(io.BytesIO(f_bytes), engine=engine_val)
                    mes_ano_arquivo = extrair_mes_ano_do_nome(f_name)
                except:
                    mes_ano_arquivo = "SEM MÊS/ANO"

                # Formata o mês/ano para usar a sigla (ex: JAN/2025)
                mes_ano_formatado = mes_ano_arquivo
                if "/" in mes_ano_arquivo and mes_ano_arquivo != "SEM MÊS/ANO":
                    partes_data = mes_ano_arquivo.split("/")
                    num_mes = partes_data[0].strip()
                    ano_val_str = partes_data[1].strip()
                    sigla_mes = meses_sigla_map.get(num_mes, num_mes)
                    mes_ano_formatado = f"{sigla_mes}/{ano_val_str}"

                file_cfg = settings.get(file_key, {})
                for sheet, cfg in file_cfg.items():
                    try:
                        df_tmp = pd.read_excel(io.BytesIO(f_bytes), sheet_name=sheet, header=cfg["header_idx"], engine=engine_val)
                        df_tmp.columns = [str(c).strip() for c in df_tmp.columns]
                        df_tmp.columns = deduplicar_colunas(df_tmp.columns)

                        col_pedida = cfg.get("col_busca")
                        target_col = None
                        if col_pedida:
                            for c in df_tmp.columns:
                                if str(c).strip().upper() == str(col_pedida).strip().upper():
                                    target_col = c
                                    break
                        if not target_col:
                            for c in df_tmp.columns:
                                if "NOME DO INTERNO" in str(c).strip().upper():
                                    target_col = c
                                    break
                        if not target_col:
                            for c in df_tmp.columns:
                                if "NOME" in str(c).strip().upper():
                                    target_col = c
                                    break
                        if not target_col and len(df_tmp.columns) > 8:
                            target_col = df_tmp.columns[8]
                        elif not target_col and len(df_tmp.columns) > 0:
                            target_col = df_tmp.columns[0]

                        if target_col and target_col in df_tmp.columns:
                            colunas_originais = list(df_tmp.columns)

                            df_tmp["Aba Original"] = sheet
                            df_tmp["Campo Pesquisado"] = target_col

                            val_nome = df_tmp[target_col].astype(str).str.strip()
                            df_tmp["Nome (Visualização)"] = val_nome
                            df_tmp["NOME_LIMPO"] = val_nome.str.upper()

                            df_tmp = df_tmp[~df_tmp["NOME_LIMPO"].isin(['', 'NAN', 'NONE', '0', 'NAT', 'NC', 'N/C'])].copy()

                            aba_upper = sheet.strip().upper()
                            is_dem_com = "DEM_COM" in aba_upper
                            is_dem_sem = "DEM_SEM" in aba_upper
                            is_com_remuner = "COM REMUNER" in aba_upper
                            is_sem_remuner = "SEM REMUNER" in aba_upper
                            col_f = obter_nome_coluna_por_letra(df_tmp, colunas_originais, 'F')

                            usar_padrao_antigo = False
                            usar_dem_sem_antigo = False

                            is_03_a_05_2023 = False
                            is_06_a_07_2023 = False
                            is_08_2023 = False

                            if mes_ano_arquivo != "SEM MÊS/ANO":
                                try:
                                    mes_str, ano_str = mes_ano_arquivo.split('/')
                                    mes_val, ano_val = int(mes_str), int(ano_str)

                                    if ano_val == 2023 and mes_val in [3, 4, 5]:
                                        is_03_a_05_2023 = True
                                    elif ano_val == 2023 and mes_val in [6, 7]:
                                        is_06_a_07_2023 = True
                                    elif ano_val == 2023 and mes_val == 8:
                                        is_08_2023 = True

                                    if ano_val < 2025 or (ano_val == 2025 and mes_val < 9):
                                        usar_padrao_antigo = True

                                    if ano_val < 2019 or (ano_val == 2019 and mes_val < 11):
                                        usar_dem_sem_antigo = True
                                except Exception:
                                    pass

                            def extrair_dados_e_categoria(row):
                                if is_03_a_05_2023:
                                    if is_dem_com or is_com_remuner:
                                        cat = "COM REMUNERAÇÃO"
                                        letras = ["I", "B", "T", "V", "W", "X", "Y"]
                                    elif is_dem_sem or is_sem_remuner:
                                        cat = "SEM REMUNERAÇÃO"
                                        letras = ["J", "B", "S", "U", "V", "W", "X"]
                                    else:
                                        val_f = row[col_f] if (col_f and col_f in row) else None
                                        is_sim = str(val_f).strip().upper() == "SIM" if pd.notna(val_f) else False
                                        cat = "COM REMUNERAÇÃO" if is_sim else "SEM REMUNERAÇÃO"
                                        letras = ["I", "B", "T", "V", "W", "X", "Y"] if is_sim else ["J", "B", "S", "U", "V", "W", "X"]

                                elif is_06_a_07_2023:
                                    if is_dem_com or is_com_remuner:
                                        cat = "COM REMUNERAÇÃO"
                                        letras = ["I", "B", "U", "W", "X", "Y", "Z"]
                                    elif is_dem_sem or is_sem_remuner:
                                        cat = "SEM REMUNERAÇÃO"
                                        letras = ["J", "B", "S", "V", "W", "X", "Y"]
                                    else:
                                        val_f = row[col_f] if (col_f and col_f in row) else None
                                        is_sim = str(val_f).strip().upper() == "SIM" if pd.notna(val_f) else False
                                        cat = "COM REMUNERAÇÃO" if is_sim else "SEM REMUNERAÇÃO"
                                        letras = ["I", "B", "U", "W", "X", "Y", "Z"] if is_sim else ["J", "B", "S", "V", "W", "X", "Y"]

                                elif is_08_2023:
                                    if is_dem_com or is_com_remuner:
                                        cat = "COM REMUNERAÇÃO"
                                        letras = ["I", "B", "R", "T", "U", "V", "W"]
                                    elif is_dem_sem or is_sem_remuner:
                                        cat = "SEM REMUNERAÇÃO"
                                        letras = ["I", "B", "Q", "S", "T", "U", "V"]
                                    else:
                                        val_f = row[col_f] if (col_f and col_f in row) else None
                                        is_sim = str(val_f).strip().upper() == "SIM" if pd.notna(val_f) else False
                                        cat = "COM REMUNERAÇÃO" if is_sim else "SEM REMUNERAÇÃO"
                                        letras = ["I", "B", "R", "T", "U", "V", "W"] if is_sim else ["I", "B", "Q", "S", "T", "U", "V"]

                                else:
                                    if is_dem_com:
                                        cat = "COM REMUNERAÇÃO"
                                        letras = ["I", "B", None, "S", "T", "U", "V"]

                                    elif is_dem_sem:
                                        cat = "SEM REMUNERAÇÃO"
                                        if usar_dem_sem_antigo:
                                            letras = ["I", "B", "Y", "R", "S", "T", "U"]
                                        else:
                                            letras = ["I", "B", "Y", "S", "T", "U", "V"]

                                    elif is_com_remuner:
                                        cat = "COM REMUNERAÇÃO"
                                        if usar_padrao_antigo:
                                            letras = ["I", "B", "Q", "S", "T", "U", "V"]
                                        else:
                                            letras = ["B", "I", "J", "T", "U", "V", "W"]

                                    elif is_sem_remuner:
                                        cat = "SEM REMUNERAÇÃO"
                                        letras = ["I", "B", "W", "R", "S", "T", "U"]

                                    else:
                                        val_f = row[col_f] if (col_f and col_f in row) else None
                                        is_sim = str(val_f).strip().upper() == "SIM" if pd.notna(val_f) else False

                                        cat = "COM REMUNERAÇÃO" if is_sim else "SEM REMUNERAÇÃO"
                                        letras = ["J", "C", "X", "S", "T", "U", "V"]

                                row_vals = {
                                    "Categoria_Aba": cat,
                                    "LABEL_EXIBICAO": f"{mes_ano_formatado} - {cat}"
                                }
                                for idx_p, let in enumerate(letras):
                                    if let is None:
                                        val = ""
                                        header_title = ""
                                    else:
                                        col_n = obter_nome_coluna_por_letra(df_tmp, colunas_originais, let)
                                        val = row[col_n] if col_n and col_n in row else None
                                        header_title = str(col_n) if col_n else f"Campo {idx_p+1}"
                                    row_vals[f"POS_{idx_p}"] = val
                                    row_vals[f"HEADER_{idx_p}"] = header_title

                                return pd.Series(row_vals)

                            res_df = df_tmp.apply(extrair_dados_e_categoria, axis=1)
                            df_tmp["MÊS/ANO - ABA"] = res_df["LABEL_EXIBICAO"]

                            df_processed = pd.concat([
                                df_tmp[[
                                    "MÊS/ANO - ABA",
                                    "Aba Original",
                                    "Campo Pesquisado",
                                    "Nome (Visualização)",
                                    "NOME_LIMPO"
                                ]],
                                res_df
                            ], axis=1)
                            all_results.append(df_processed)
                    except Exception as e:
                        st.error(f"Erro ao ler {f_name} - Aba {sheet}: {e}")

            if all_results:
                st.session_state["pesquisa_df"] = pd.concat(all_results, ignore_index=True)
                st.success(f"Dados consolidados com sucesso! **{len(st.session_state['pesquisa_df'])}** registros carregados.")
            else:
                st.warning("Nenhum dado encontrado com as configurações informadas.")
                st.session_state["pesquisa_df"] = None

    if st.session_state.get("pesquisa_df") is not None:
        df_pesq = st.session_state["pesquisa_df"]
        st.markdown("---")
        st.subheader("🔍 Filtros de Visualização e Busca")

        col_ord1, col_ord2 = st.columns([2, 2])
        with col_ord1:
            ordem_escolhida = st.radio(
                "📅 Ordenação por Mês/Ano:",
                ["Crescente (Antigo ➔ Recente)", "Decrescente (Recente ➔ Antigo)"],
                horizontal=True,
                key=f"ordem_radio_{st.session_state['uploader_key']}"
            )

        is_ascending = True if "Crescente" in ordem_escolhida else False

        nomes_disponiveis = sorted(df_pesq["Nome (Visualização)"].dropna().unique())
        nomes_selecionados = st.multiselect(
            "🔍 Digite para pesquisar e selecione o(s) nome(s):",
            options=nomes_disponiveis,
            key=f"busca_nomes_{st.session_state['uploader_key']}"
        )

        df_view = df_pesq.copy()
        if nomes_selecionados:
            df_view = df_view[df_view["Nome (Visualização)"].isin(nomes_selecionados)]

        st.metric("Total de Registros Encontrados", len(df_view))

        if not df_view.empty:

            def extrair_chave_data(val):
                try:
                    data_str = str(val).split(' - ')[0].strip()
                    if data_str == "SEM MÊS/ANO":
                        return 999999 if is_ascending else -1
                    
                    # Converte de volta caso esteja em formato de sigla para manter a ordenação correta
                    mes_map_inverso = {
                        "JAN": "01", "FEV": "02", "MAR": "03", "ABR": "04",
                        "MAI": "05", "JUN": "06", "JUL": "07", "AGO": "08",
                        "SET": "09", "OUT": "10", "NOV": "11", "DEZ": "12"
                    }
                    m_part, y_part = data_str.split('/')
                    m_num = mes_map_inverso.get(m_part.upper(), m_part)
                    return int(y_part) * 100 + int(m_num)
                except:
                    return 999999 if is_ascending else -1

            df_view['chave_ordenacao'] = df_view['MÊS/ANO - ABA'].apply(extrair_chave_data)
            df_view = df_view.sort_values(by=['chave_ordenacao'], ascending=is_ascending).drop(columns=['chave_ordenacao'])

            df_display_all = formatar_datas_dataframe(df_view)

            def formatar_sem_decimal(val):
                if pd.isna(val) or str(val).strip() in ["", "nan", "None"]:
                    return ""
                try:
                    num = float(val)
                    return str(int(round(num)))
                except (ValueError, TypeError):
                    return str(val).strip()

            def conv_num(val):
                try:
                    v_str = str(val).replace(',', '.').strip()
                    return float(v_str) if v_str not in ["", "nan", "None"] else 0.0
                except:
                    return 0.0

            grupos_categorias = [
                ("🟢 COM REMUNERAÇÃO", "COM REMUNERAÇÃO", "com_rem"),
                ("🟡 SEM REMUNERAÇÃO", "SEM REMUNERAÇÃO", "sem_rem")
            ]

            mapa_meses = {
                "JAN": "JAN", "FEV": "FEV", "MAR": "MAR", "ABR": "ABR",
                "MAI": "MAI", "JUN": "JUN", "JUL": "JUL", "AGO": "AGO",
                "SET": "SET", "OUT": "OUT", "NOV": "NOV", "DEZ": "DEZ",
                "01": "JAN", "1": "JAN", "02": "FEV", "2": "FEV",
                "03": "MAR", "3": "MAR", "04": "ABR", "4": "ABR",
                "05": "MAI", "5": "MAI", "06": "JUN", "6": "JUN",
                "07": "JUL", "7": "JUL", "08": "AGO", "8": "AGO",
                "09": "SET", "9": "SET", "10": "OUT", "11": "NOV", "12": "DEZ"
            }
            ordem_meses_siglas = ["JAN", "FEV", "MAR", "ABR", "MAI", "JUN", "JUL", "AGO", "SET", "OUT", "NOV", "DEZ"]

            todos_dados_exportacao = []

            for titulo_grupo, cat_key, prefixo_key in grupos_categorias:
                df_grupo = df_display_all[df_display_all["Categoria_Aba"] == cat_key]

                if not df_grupo.empty:
                    pos_cols = [c for c in df_grupo.columns if str(c).startswith("POS_")]
                    pos_cols.sort(key=lambda x: int(x.split("_")[1]))

                    cabecalhos_padrao = ["NOME", "ORGANIZ", "FUNÇÃO", "ENTRADA", "SAIDA", "PREV", "REAL"]
                    rename_map = {}

                    for idx_p, pos_col in enumerate(pos_cols):
                        if idx_p < len(cabecalhos_padrao):
                            rename_map[pos_col] = cabecalhos_padrao[idx_p]
                        else:
                            rename_map[pos_col] = f"Campo {idx_p+1}"

                    cols_exibir = ["MÊS/ANO - ABA"] + pos_cols
                    df_render = df_grupo[cols_exibir].rename(columns=rename_map)
                    df_render = df_render.rename(columns={"MÊS/ANO - ABA": "MES/ANO - ABA"})

                    if "REAL" in df_render.columns:
                        df_render["REAL"] = df_render["REAL"].apply(formatar_sem_decimal)

                    st.markdown(f"### {titulo_grupo} ({len(df_render)} registro(s))")

                    key_select = f"select_all_{prefixo_key}"
                    if key_select not in st.session_state:
                        st.session_state[key_select] = False

                    col_b1, _ = st.columns([2, 4])
                    with col_b1:
                        if st.button("Marcar / Desmarcar Todos", key=f"btn_toggle_{prefixo_key}_{st.session_state['uploader_key']}"):
                            st.session_state[key_select] = not st.session_state[key_select]
                            st.rerun()

                    df_render.insert(0, "SELECIONAR?", st.session_state[key_select])

                    col_config_conteudo = gerar_config_largura_colunas(df_render, df_render.columns.tolist())
                    col_config_conteudo["SELECIONAR?"] = st.column_config.CheckboxColumn("SELECIONAR?", default=False)

                    df_editado_res = st.data_editor(
                        df_render,
                        column_config=col_config_conteudo,
                        use_container_width=True,
                        hide_index=True,
                        key=f"editor_res_{prefixo_key}_{st.session_state['uploader_key']}"
                    )

                    selecionados_grupo = df_editado_res[df_editado_res["SELECIONAR?"] == True]

                    if not selecionados_grupo.empty:
                        st.markdown("---")
                        st.markdown(f"### 📋 Espaço de Visualização dos Registros Selecionados — {titulo_grupo}")

                        nomes_unicos = selecionados_grupo["NOME"].dropna().unique()

                        for nome_interno in nomes_unicos:
                            df_nome_sel = selecionados_grupo[selecionados_grupo["NOME"] == nome_interno]

                            organiz_val = ", ".join([str(v) for v in df_nome_sel["ORGANIZ"].dropna().unique() if str(v).strip() != ""])
                            funcao_val = ", ".join([str(v) for v in df_nome_sel["FUNÇÃO"].dropna().unique() if str(v).strip() != ""])
                            saida_val = ", ".join([str(v) for v in df_nome_sel["SAIDA"].dropna().unique() if str(v).strip() != ""])

                            soma_real = sum(conv_num(v) for v in df_nome_sel["REAL"])
                            total_dias_nome = int(round(soma_real))

                            st.markdown(
                                f"**NOME:** {nome_interno} &nbsp;|&nbsp; "
                                f"**ORGANIZAÇÃO:** {organiz_val if organiz_val else 'N/A'} &nbsp;|&nbsp; "
                                f"**FUNÇÃO:** {funcao_val if funcao_val else 'N/A'} &nbsp;|&nbsp; "
                                f"**REMUNERAÇÃO:** {cat_key} &nbsp;|&nbsp; "
                                f"**SAÍDA:** {saida_val if saida_val else 'N/A'}"
                            )

                            matrix_data = []
                            for _, r_row in df_nome_sel.iterrows():
                                raw_mes_ano_aba = str(r_row.get("MES/ANO - ABA", ""))
                                data_mes_ano = raw_mes_ano_aba.split(" - ")[0] if " - " in raw_mes_ano_aba else raw_mes_ano_aba

                                mes_sigla, ano_str = "N/A", "N/A"
                                if "/" in data_mes_ano:
                                    parts = data_mes_ano.split("/")
                                    if len(parts) == 2:
                                        mes_token, ano_str = parts[0].strip(), parts[1].strip()
                                        mes_sigla = mapa_meses.get(mes_token.upper(), mes_token)

                                val_real = formatar_sem_decimal(r_row.get("REAL", ""))

                                matrix_data.append({
                                    "ANO": ano_str,
                                    "MÊS": mes_sigla,
                                    "REAL": val_real
                                })

                            df_pivot = pd.DataFrame()
                            if matrix_data:
                                df_mat = pd.DataFrame(matrix_data)

                                df_pivot = df_mat.pivot_table(
                                    index="ANO",
                                    columns="MÊS",
                                    values="REAL",
                                    aggfunc=lambda x: " / ".join([str(v) for v in x if pd.notna(v) and str(v).strip() != ""])
                                ).fillna("")

                                cols_meses = sorted(df_pivot.columns, key=lambda m: ordem_meses_siglas.index(m) if m in ordem_meses_siglas else 99)
                                df_pivot = df_pivot[cols_meses]

                                st.dataframe(df_pivot, use_container_width=True)

                            st.markdown(f"**Total de Dias:** {total_dias_nome}")
                            st.markdown("<br>", unsafe_allow_html=True)

                            todos_dados_exportacao.append({
                                "nome": nome_interno,
                                "organiz": organiz_val if organiz_val else "N/A",
                                "funcao": funcao_val if funcao_val else "N/A",
                                "remuneracao": cat_key,
                                "saida": saida_val if saida_val else "N/A",
                                "pivot_df": df_pivot,
                                "total_dias": total_dias_nome
                            })

                        total_marcados = len(selecionados_grupo)
                        st.caption(f"📌 **{total_marcados}** item(ns) selecionado(s) nesta tabela.")
                        st.markdown("---")

            if todos_dados_exportacao:
                st.markdown("### 📥 Baixar ou Salvar Relatório Unificado")
                st.info(f"O relatório gerado conterá **{len(todos_dados_exportacao)}** registro(s) selecionado(s) nas tabelas acima.")

                excel_bytes = gerar_excel_bytes(todos_dados_exportacao)
                docx_bytes = gerar_docx_bytes(todos_dados_exportacao)

                col_dl1, col_dl2 = st.columns(2)
                with col_dl1:
                    st.download_button(
                        label="📊 Baixar Excel Consolidador (.xlsx)",
                        data=excel_bytes,
                        file_name="salvamento_remicao_consolidado.xlsx",
                        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                        key=f"btn_dl_xlsx_unico_{st.session_state['uploader_key']}",
                        type="primary"
                    )
                with col_dl2:
                    st.download_button(
                        label="📄 Baixar Word Consolidador (.docx)",
                        data=docx_bytes,
                        file_name="salvamento_remicao_consolidado.docx",
                        mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                        key=f"btn_dl_docx_unico_{st.session_state['uploader_key']}",
                        type="primary"
                    )

                st.markdown("<br>", unsafe_allow_html=True)
                st.markdown("#### ☁️ Salvar Diretamente no Google Drive")

                col_drive_1, col_drive_2 = st.columns(2)
                with col_drive_1:
                    if st.button("💾 Salvar Excel no Google Drive", key="btn_save_excel_drive"):
                        with st.spinner("Enviando Excel para o Drive..."):
                            link = salvar_arquivo_no_drive(
                                nome_arquivo="salvamento_remicao_consolidado.xlsx",
                                bytes_conteudo=excel_bytes,
                                mime_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                                folder_id=ROOT_FOLDER_ID.strip()
                            )
                            st.success(f"Excel salvo no Drive com sucesso! [Abrir arquivo no Drive]({link})")

                with col_drive_2:
                    if st.button("💾 Salvar Word no Google Drive", key="btn_save_word_drive"):
                        with st.spinner("Enviando Word para o Drive..."):
                            link = salvar_arquivo_no_drive(
                                nome_arquivo="salvamento_remicao_consolidado.docx",
                                bytes_conteudo=docx_bytes,
                                mime_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                                folder_id=ROOT_FOLDER_ID.strip()
                            )
                            st.success(f"Word salvo no Drive com sucesso! [Abrir arquivo no Drive]({link})")

                st.markdown("---")
        else:
            st.info("ℹ️ Nenhum registro selecionado ou encontrado na pesquisa.")

    if st.button("🗑️ Limpar Tudo", key="btn_limpar_tudo_op3"):
        chave_atual = st.session_state.get("uploader_key", 0) + 1
        st.session_state.clear()
        st.session_state["uploader_key"] = chave_atual
        st.rerun()
