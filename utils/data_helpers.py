import re
import pandas as pd

def tentar_converter_numero(val):
    """Converte texto numérico em int/float nativo para o Excel reconhecer como número."""
    if pd.isna(val) or val == "" or val is None:
        return ""
    if isinstance(val, (int, float)):
        return val
    val_str = str(val).strip().replace(',', '.')
    try:
        num = float(val_str)
        return int(num) if num.is_integer() else num
    except (ValueError, TypeError):
        return str(val)

def limpar_texto_xml(texto):
    """Remove caracteres inválidos de controle ASCII que corrompem documentos Word (.docx)."""
    if pd.isna(texto) or texto is None:
        return ""
    texto_str = str(texto)
    return re.sub(r'[\x00-\x08\x0B\x0C\x0E-\x1F]', '', texto_str)

def extrair_mes_ano_do_nome(nome_arquivo):
    meses = {
        "JANEIRO": "01", "FEVEREIRO": "02", "MARÇO": "03", "MARCO": "03",
        "ABRIL": "04", "MAIO": "05", "JUNHO": "06", "JULHO": "07",
        "AGOSTO": "08", "SETEMBRO": "09", "OUTUBRO": "10",
        "NOVEMBRO": "11", "DEZEMBRO": "12"
    }
    nome_upper = str(nome_arquivo).upper()
    ano_match = re.search(r'\b(20\d{2})\b', nome_upper)
    ano = ano_match.group(1) if ano_match else None
    
    mes = None
    for nome_mes, num_mes in meses.items():
        if nome_mes in nome_upper:
            mes = num_mes
            break
            
    if mes and ano:
        return f"{mes}/{ano}"
    return "SEM MÊS/ANO"

def extrair_valor_limpo(df, idx, col_name):
    try:
        val = df.iloc[idx][col_name]
        if isinstance(val, pd.Series):
            val = val.iloc[0]
        if pd.isna(val):
            return None
        return val.item() if hasattr(val, 'item') else val
    except:
        return None

def converter_valor_inteligente(val_str, dtype_original):
    if val_str is None or str(val_str).strip() == "":
        return None
    val_str = str(val_str).strip()
    if pd.api.types.is_integer_dtype(dtype_original):
        try:
            return int(val_str)
        except ValueError:
            pass
    elif pd.api.types.is_float_dtype(dtype_original):
        try:
            return float(val_str.replace(',', '.'))
        except ValueError:
            pass
    try:
        return float(val_str.replace(',', '.'))
    except ValueError:
        return val_str
