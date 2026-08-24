import streamlit as st
import re
import json
import os
import uuid
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from cryptography.fernet import Fernet
from rotinas import drive_storage

ARQUIVO_BANCO = "dados_acesso_cpfs.enc"
EMAIL_MASTER = "pricardosbrito@gmail.com"

def obter_cipher():
    try:
        chave = st.secrets["CHAVE_SISTEMA"].encode()
        return Fernet(chave)
    except KeyError:
        st.error("❌ Chave do sistema não configurada no st.secrets.")
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

def salvar_base_dados(lista_cadastros):
    cipher = obter_cipher()
    if not cipher:
        st.error("Erro ao criptografar dados.")
        return
    dados_json = json.dumps(lista_cadastros, ensure_ascii=False)
    dados_cifrados = cipher.encrypt(dados_json.encode())
    with open(ARQUIVO_BANCO, "wb") as f:
        f.write(dados_cifrados)
    drive_storage.salvar_banco_drive()

def validar_cpf(cpf):
    cpf = ''.join(filter(str.isdigit, str(cpf)))
    if len(cpf) != 11 or len(set(cpf)) == 1: return False
    for i in range(9, 11):
        valor = sum((int(cpf[num]) * ((i + 1) - num) for num in range(0, i)))
        digito = ((valor * 10) % 11) % 10
        if digito != int(cpf[i]): return False
    return True

def validar_email(email):
    padrao = r"^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$"
    return re.match(padrao, email) is not None

def validar_telefone(telefone):
    numeros = ''.join(filter(str.isdigit, str(telefone)))
    return len(numeros) >= 10

def validar_forca_senha(senha):
    if len(senha) < 8: return False
    if not re.search(r"[A-Z]", senha): return False
    if not re.search(r"[a-z]", senha): return False
    if not re.search(r"\d", senha): return False
    return True

def enviar_email_gmail(email_destino, nome, token):
    try:
        remetente = st.secrets["GMAIL_USER"]
        senha_app = st.secrets["GMAIL_APP_PASSWORD"]
    except Exception:
        st.toast("⚠️ Configurações do Gmail não encontradas em st.secrets.", icon="📩")
        return True

    assunto = "CPFS WEB - Confirmação de Cadastro"
    url_base_app = "https://cpfs-web-zcggwtxd5kfhjuydz6pwnx.streamlit.app/?nav=confirmar_acesso"
    
    corpo_html = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="UTF-8">
    </head>
    <body style="font-family: Arial, sans-serif; background-color: #f4f7f6; margin: 0; padding: 20px;">
        <div style="max-width: 600px; background: #ffffff; padding: 30px; border-radius: 10px; box-shadow: 0 4px 10px rgba(0,0,0,0.1); margin: auto;">
            <h2 style="color: #002B7F; text-align: center; margin-top: 0;">CPFS WEB</h2>
            <p style="text-align: center; color: #555555; font-size: 14px; margin-top: -5px;">Facilidade para TODOS</p>
            
            <p style="font-size: 16px; color: #333333;">Olá, <strong>{nome}</strong>!</p>
            <p style="font-size: 15px; color: #555555;">Seu cadastro foi realizado com sucesso. Para confirmar sua conta e ativar seu acesso, copie o token abaixo e cole na página de confirmação:</p>
            
            <div style="text-align: center; margin: 25px 0;">
                <span style="display: inline-block; background: #f0f4f8; border: 2px dashed #002B7F; color: #002B7F; font-size: 24px; font-weight: bold; padding: 12px 25px; border-radius: 6px; letter-spacing: 2px; user-select: all;">{token}</span>
            </div>
            
            <p style="text-align: center; font-size: 13px; color: #666666; margin-bottom: 25px;">
                <em>(Dica: Selecione o código acima com o mouse, pressione Ctrl+C para copiar e cole no campo de token do sistema)</em>
            </p>

            <div style="text-align: center; margin-bottom: 30px;">
                <a href="{url_base_app}" target="_blank" style="display: inline-block; background-color: #002B7F; color: white; text-decoration: none; padding: 12px 24px; font-size: 15px; font-weight: bold; border-radius: 6px; box-shadow: 0 2px 5px rgba(0,0,0,0.2);">
                    🔗 Ir Direto para a Página de Confirmação
                </a>
            </div>
            
            <p style="font-size: 13px; color: #777777; text-align: center; border-top: 1px solid #eeeeee; padding-top: 20px;">
                Se você não solicitou este cadastro, por favor, ignore esta mensagem.
            </p>
        </div>
    </body>
    </html>
    """

    msg = MIMEMultipart()
    msg['From'] = remetente
    msg['To'] = email_destino
    msg['Subject'] = assunto
    msg.attach(MIMEText(corpo_html, 'html'))

    try:
        servidor = smtplib.SMTP('smtp.gmail.com', 587)
        servidor.starttls()
        servidor.login(remetente, senha_app)
        servidor.sendmail(remetente, email_destino, msg.as_string())
        servidor.quit()
        return True
    except Exception as e:
        st.error(f"Erro ao enviar e-mail: {e}")
        return False

def render_cadastrar_acesso():
    st.markdown("<h2 style='text-align: center; color: #002B7F;'>📝 Cadastro de Novo Acesso</h2>", unsafe_allow_html=True)
    st.warning("⏳ **AVISO IMPORTANTE:** A liberação e análise do acesso pode demorar até **72 horas**.")
    
    base_cadastros = carregar_base_dados()
    banco_vaziou = (len(base_cadastros) == 0)

    if banco_vaziou:
        st.info("🚀 **PONTAPÉ INICIAL DO SISTEMA DETECTADO:** O banco de dados está vazio. O primeiro cadastro realizado agora será automaticamente configurado como o **Mestre/Criador** raiz do sistema.")

    tipo_acesso = st.selectbox("Selecione o Tipo de Acesso desejado:", ["Selecione...", "Funcionário", "Visitante", "Advogado", "Religioso", "Outros"])
    
    if tipo_acesso != "Selecione...":
        with st.form(key=f"form_cadastro_{tipo_acesso}"):
            st.markdown(f"### Dados do {tipo_acesso}")
            
            nome = cpf = email = telefone = ""
            funcao = setor = nivel = atividades = rg = data_nasc = ""
            parentesco = ""
            endereco = bairro = cidade = oab = objetivo = ""
            vinculo = cadastro = estado = ""
            envolve_interno = "Não"
            lista_internos = []

            usuario_logado = st.session_state.get("usuario_logado")
            sessao_super = False
            if usuario_logado:
                tipo_log = str(usuario_logado.get("tipo", "")).strip().capitalize()
                email_log = str(usuario_logado.get("email", "")).strip().lower()
                if tipo_log in ["Master", "Mestre"] or email_log == EMAIL_MASTER.lower():
                    sessao_super = True

            nivel_privilegio = "Comum"
            if banco_vaziou:
                st.success("🔒 Este primeiro cadastro terá privilégios de Mestre automaticamente.")
            elif sessao_super:
                st.markdown("---")
                st.markdown("#### ⚙️ Painel de Atribuição de Privilégio (Mestre)")
                escolha_privilegio = st.radio(
                    "Escolha a graduação para este novo cadastro:",
                    [
                        "Usuário Comum", 
                        "Usuário Sênior (Orientador / Treinador)", 
                        "Mestre / Sucessor", 
                        "Usuário Teste (Sem Verificações e Sem E-mail)"
                    ],
                    horizontal=False,
                    key="radio_graduacao_privilegio_v2"
                )
                if "Sênior" in escolha_privilegio:
                    nivel_privilegio = "Senior"
                elif "Mestre" in escolha_privilegio:
                    nivel_privilegio = "Master"
                elif "Teste" in escolha_privilegio:
                    nivel_privilegio = "Teste"

            if tipo_acesso == "Funcionário":
                col1, col2 = st.columns([1, 2])
                vinculo = col1.selectbox("Vínculo", ["Efetivo", "Comissionado", "Contratado"])
                nome = col2.text_input("Nome Completo *")
                
                col3, col4, col5 = st.columns([1, 1, 2])
                cadastro = col3.text_input("Cadastro (Matrícula)")
                telefone = col4.text_input("Tel / WhatsApp *")
                email = col5.text_input("E-mail válido *")
                
                col6, col7, col8 = st.columns(3)
                funcao = col6.text_input("Função")
                setor = col7.selectbox("Setor", ["COSIS", "SEGURANÇA", "CRC", "CRH", "DIREÇÃO"])
                nivel = col8.selectbox("Nível", ["Líder", "Sênior", "Júnior"])
                atividades = st.text_area("Descrever Atividades *")

            elif tipo_acesso in ["Visitante", "Religioso"]:
                nome = st.text_input("Nome Completo *")
                col1, col2, col3, col4 = st.columns(4)
                rg = col1.text_input("RG")
                cpf = col2.text_input("CPF *")
                data_nasc = str(col3.date_input("Data de Nascimento", format="DD/MM/YYYY"))
                telefone = col4.text_input("Tel / WhatsApp *")
                email = st.text_input("E-mail válido *")
                
                obrigatorio_texto = " (Obrigatório)" if tipo_acesso == "Visitante" else " (Opcional)"
                st.markdown(f"#### 👥 Dados dos Internos{obrigatorio_texto}")
                
                min_val = 1 if tipo_acesso == "Visitante" else 0
                qtd_internos = st.number_input("Quantos internos deseja registrar?", min_value=min_val, max_value=10, value=min_val, step=1)
                
                for i in range(int(qtd_internos)):
                    st.markdown(f"**Interno {i+1}**")
                    ci1, ci2, ci3, ci4 = st.columns([2, 1, 1, 1])
                    nome_int = ci1.text_input(f"Nome do Interno {i+1}", key=f"nome_int_{i}")
                    pav_int = ci2.text_input(f"Pavilhão {i+1}", key=f"pav_int_{i}")
                    cela_int = ci3.text_input(f"Cela {i+1}", key=f"cela_int_{i}")
                    par_int = ci4.text_input(f"Parentesco {i+1}", key=f"par_int_{i}")
                    
                    if nome_int.strip():
                        lista_internos.append({
                            "nome_interno": nome_int.strip(),
                            "pavilhao": pav_int.strip(),
                            "cela": cela_int.strip(),
                            "parentesco": par_int.strip()
                        })
                
                st.markdown("#### Endereço")
                c9, c10, c11, c12 = st.columns([2, 1, 1, 1])
                endereco = c9.text_input("Endereço")
                bairro = c10.text_input("Bairro")
                cidade = c11.text_input("Cidade")
                estado = c12.selectbox("Estado", ["BA", "AC", "AL", "AP", "AM", "CE", "DF", "ES", "GO", "MA", "MT", "MS", "MG", "PA", "PB", "PR", "PE", "PI", "RJ", "RN", "RS", "RO", "RR", "SC", "SP", "SE", "TO"], index=0)

            elif tipo_acesso == "Advogado":
                nome = st.text_input("Nome Completo *")
                col1, col2, col3 = st.columns(3)
                oab = col1.text_input("Nº OAB")
                cpf = col2.text_input("CPF *")
                telefone = col3.text_input("Tel / WhatsApp *")
                email = st.text_input("E-mail válido *")

                st.markdown("#### ⚖️ Atuação / Internos (Opcional)")
                envolve_interno = st.radio("A atuação envolve algum interno?", ["Não", "Sim"], horizontal=True, key="env_adv")
                if envolve_interno == "Sim":
                    qtd_internos_adv = st.number_input("Quantos internos?", min_value=0, max_value=10, value=0, step=1, key="qtd_adv")
                    for i in range(int(qtd_internos_adv)):
                        st.markdown(f"**Interno {i+1}**")
                        ci1, ci2, ci3 = st.columns([2, 1, 1])
                        nome_int = ci1.text_input(f"Nome do Interno {i+1}", key=f"nome_adv_{i}")
                        pav_int = ci2.text_input(f"Pavilhão {i+1}", key=f"pav_adv_{i}")
                        cela_int = ci3.text_input(f"Cela {i+1}", key=f"cela_adv_{i}")
                        
                        if nome_int.strip():
                            lista_internos.append({
                                "nome_interno": nome_int.strip(),
                                "pavilhao": pav_int.strip(),
                                "cela": cela_int.strip(),
                                "parentesco": "Advogado"
                            })

            elif tipo_acesso == "Outros":
                objetivo = st.text_area("Objetivo da Visita *")
                nome = st.text_input("Nome Completo *")
                col1, col2, col3, col4 = st.columns(4)
                rg = col1.text_input("RG")
                cpf = col2.text_input("CPF *")
                data_nasc = str(col3.date_input("Data de Nascimento", format="DD/MM/YYYY"))
                telefone = col4.text_input("Tel / WhatsApp *")
                email = st.text_input("E-mail válido *")
                
                envolve_interno = st.radio("A visita envolve algum interno?", ["Não", "Sim"], horizontal=True, key="env_outros")
                if envolve_interno == "Sim":
                    qtd_internos_outros = st.number_input("Quantos internos?", min_value=0, max_value=10, value=0, step=1, key="qtd_outros")
                    for i in range(int(qtd_internos_outros)):
                        st.markdown(f"**Interno {i+1}**")
                        ci1, ci2, ci3 = st.columns([2, 1, 1])
                        nome_int = ci1.text_input(f"Nome do Interno {i+1}", key=f"nome_out_{i}")
                        pav_int = ci2.text_input(f"Pavilhão {i+1}", key=f"pav_out_{i}")
                        cela_int = ci3.text_input(f"Cela {i+1}", key=f"cela_out_{i}")
                        
                        if nome_int.strip():
                            lista_internos.append({
                                "nome_interno": nome_int.strip(),
                                "pavilhao": pav_int.strip(),
                                "cela": cela_int.strip(),
                                "parentesco": "Outros"
                            })

            st.markdown("---")
            st.markdown("#### 🔐 Configuração de Senha")
            col_s1, col_s2 = st.columns(2)
            senha = col_s1.text_input("Digite sua Senha *", type="password")
            confirma_senha = col_s2.text_input("Confirme sua Senha *", type="password")
            
            submit_cadastro = st.form_submit_button("Enviar Solicitação de Cadastro", use_container_width=True)
            
            if submit_cadastro:
                email_limpo = email.strip().lower() if email else ""
                
                erros = []
                
                if nivel_privilegio == "Teste":
                    if not nome.strip(): erros.append("O campo 'Nome' é obrigatório.")
                    if not senha: erros.append("O campo 'Senha' é obrigatório.")
                elif not sessao_super:
                    if not nome.strip(): erros.append("O campo 'Nome' é obrigatório.")
                    if not email.strip() or not validar_email(email): erros.append("Informe um e-mail válido.")
                    if tipo_acesso != "Funcionário" and not validar_cpf(cpf): erros.append("O CPF informado é inválido.")
                    if not validar_telefone(telefone): erros.append("O Telefone/WhatsApp é inválido.")
                    if tipo_acesso == "Funcionário" and not atividades.strip(): erros.append("A descrição das atividades é obrigatória.")
                    
                    if tipo_acesso == "Visitante" and (not lista_internos or not any(i.get("nome_interno", "").strip() for i in lista_internos)):
                        erros.append("Para o perfil de Visitante, é obrigatório informar ao menos um interno válido.")

                    if not validar_forca_senha(senha): erros.append("A senha deve ter no mínimo 8 caracteres, contendo números, letras maiúsculas e minúsculas.")
                    if senha != confirma_senha: erros.append("As senhas não coincidem.")
                else:
                    if not nome.strip(): erros.append("O campo 'Nome' é obrigatório.")
                    if not email.strip(): erros.append("O campo 'E-mail' é obrigatório.")
                    if senha != confirma_senha: erros.append("As senhas não coincidem.")
                
                if email_limpo and any(u.get("email", "").strip().lower() == email_limpo for u in base_cadastros):
                    erros.append("Este e-mail já está cadastrado no sistema.")

                if erros:
                    for erro in erros:
                        st.error(f"❌ {erro}")
                else:
                    status_conta = "Senha Ativa" if nivel_privilegio == "Teste" else "Pendente Confirmação E-mail"
                    token = str(uuid.uuid4())[:8]
                    
                    tipo_final_registro = tipo_acesso
                    if banco_vaziou or nivel_privilegio == "Master":
                        tipo_final_registro = "Master"
                    elif nivel_privilegio == "Senior":
                        tipo_final_registro = "Senior"
                    elif nivel_privilegio == "Teste":
                        tipo_final_registro = "Teste"
                    
                    novo_registro = {
                        "nome": nome.strip(),
                        "email": email_limpo if email_limpo else f"teste_{token}@sistema.local",
                        "tipo": tipo_final_registro,
                        "tipo_base_original": tipo_acesso,
                        "status": status_conta,
                        "senha": senha,
                        "token": token,
                        "vinculo": vinculo, "cadastro_matricula": cadastro, "telefone": telefone,
                        "funcao": funcao, "setor": setor, "nivel": nivel, "atividades": atividades,
                        "rg": rg, "cpf": cpf, "data_nascimento": data_nasc,
                        "internos": lista_internos,
                        "endereco": endereco, "bairro": bairro, "cidade": cidade, "estado": estado,
                        "oab": oab, "objetivo_visita": objetivo, "envolve_interno": envolve_interno
                    }
                    
                    base_cadastros.append(novo_registro)
                    salvar_base_dados(base_cadastros)
                    
                    if nivel_privilegio != "Teste":
                        enviar_email_gmail(email_limpo, nome, token)
                    
                    if banco_vaziou:
                        st.success(f"🎉 **PONTAPÉ INICIAL CONCLUÍDO!** Conta Mestre criada com sucesso para **{email_limpo}**. Verifique seu e-mail para confirmar.")
                    elif nivel_privilegio == "Teste":
                        st.success(f"✅ **Usuário Teste criado com sucesso!** Já está com a senha ativa e pronto para teste (Nenhum e-mail foi disparado).")
                    else:
                        st.success(f"✅ Cadastro realizado com sucesso para **{email_limpo}**! E-mail de confirmação enviado.")
