import pandas as pd
import streamlit as st

def titulo_estilizado(subtitulo=""):
    st.markdown(
        f"<div style='text-align: center; padding: 1.5rem; background: linear-gradient(135deg, #1e3c72 0%, #2a5298 100%); color: white; border-radius: 12px; margin-bottom: 1.5rem;'><h1>⚡ SINALE WEB</h1><p>{subtitulo}</p></div>",
        unsafe_allow_html=True
    )

def gerar_config_largura_colunas(df_subset, colunas):
    config = {}
    for col in colunas:
        if col in df_subset.columns:
            nome_coluna_upper = str(col).strip().upper()
            
            if nome_coluna_upper == "NOME":
                tamanho_conteudo = df_subset[col].astype(str).str.len().max() if not df_subset[col].empty else 10
                if pd.isna(tamanho_conteudo):
                    tamanho_conteudo = 10
                
                largura_pixels = int(tamanho_conteudo * 8) + 20
                largura_pixels = max(150, min(largura_pixels, 450))
                
            else:
                tamanho_titulo = len(str(col))
                largura_pixels = int(tamanho_titulo * 9) + 20
                largura_pixels = max(50, largura_pixels)
            
            config[col] = st.column_config.Column(width=largura_pixels)
            
    return config
