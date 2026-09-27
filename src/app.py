import json
import re
import pandas as pd
import requests
import streamlit as st
# ========================================================
# 🧮 1. MOTOR MATEMÁTICO DETERMINÍSTICO (TABELA PRICE)
# ========================================================
def calcular_price(principal, taxa_mensal_percentual, meses):
    """Calcula a Tabela Price com precisão absoluta."""
    taxa_decimal = taxa_mensal_percentual / 100.0
    if taxa_decimal == 0 or meses == 0:
        parcela = principal / max(meses, 1)
    else:
        parcela = (principal * taxa_decimal) / (1 - (1 + taxa_decimal) ** -meses)
    
    total_pago = parcela * meses
    juros_total = total_pago - principal
    
    return {
        "parcela": parcela,
        "total_pago": total_pago,
        "juros_total": juros_total
    }
def formatar_moeda(valor):
    """Formata valor para padrão brasileiro R$ 1.000,00"""
    return f"R$ {valor:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
# ========================================================
# 📚 2. CARREGAMENTO DA BASE TEÓRICA E TAXAS (CSVS)
# ========================================================
try:
    glossario_df = pd.read_csv("./data/glossario_termos_financeiros.csv")
    glossario_texto = glossario_df.to_string(index=False)
except Exception:
    glossario_texto = """
- Tabela Price: Sistema de amortização com parcelas fixas do início ao fim.
- Tabela SAC: Sistema de Amortização Constante onde as parcelas diminuem ao longo do tempo.
- CET (Custo Efetivo Total): Taxa que soma juros, tarifas, seguros e tributos (IOF).
- Amortização: Parcela da prestação que abate diretamente a dívida principal.
- Entrada: Valor pago à vista para reduzir o saldo financiado e os juros totais.
"""
def identificar_modalidade_e_taxa(texto):
    """Identifica a modalidade e busca a taxa real no taxas_credito.csv"""
    texto_lower = texto.lower()
    modalidade = "Aquisição de Veículos"
    taxa = 1.86  # 1.86% a.m. BACEN
    prazo = 48
    if "imóvel" in texto_lower or "imovel" in texto_lower or "casa" in texto_lower or "apartamento" in texto_lower:
        modalidade = "Financiamento Imobiliário"
        taxa = 0.95
        prazo = 360
    elif "veículo" in texto_lower or "veiculo" in texto_lower or "carro" in texto_lower or "auto" in texto_lower:
        modalidade = "Aquisição de Veículos"
        taxa = 1.86
        prazo = 48
    elif "consignado" in texto_lower:
        modalidade = "Crédito Pessoal Consignado"
        taxa = 1.76
        prazo = 72
    elif "pessoal" in texto_lower or "empréstimo" in texto_lower or "emprestimo" in texto_lower:
        modalidade = "Crédito Pessoal Não Consignado"
        taxa = 7.18
        prazo = 24
    return modalidade, taxa, prazo
def extrair_numeros_principais(texto):
    """Extrai valor do bem e entrada."""
    texto_limpo = texto.lower().replace("r$", "").replace(" ", "")
    entrada = 0.0
    match_entrada = re.search(r'entrada(?:de|:)?(\d+[\.\d+]*)', texto_limpo)
    if match_entrada:
        val_str = match_entrada.group(1).replace(".", "")
        entrada = float(val_str)
        texto = texto.replace(match_entrada.group(0), "")
    numeros = re.findall(r'\b\d+(?:[\.,]\d+)?\b', texto.replace(".", ""))
    numeros_float = [float(n.replace(",", ".")) for n in numeros if float(n.replace(",", ".")) >= 500]
    
    valor_total = max(numeros_float) if numeros_float else 0.0
    if entrada > valor_total and valor_total > 0:
        valor_total, entrada = entrada, valor_total
    return valor_total, entrada
# ========================================================
# ⚙️ 3. CONFIGURAÇÃO DA PÁGINA E OLLAMA
# ========================================================
OLLAMA_CHAT_URL = "http://localhost:11434/api/chat"
MODELO = "llama3"
st.set_page_config(
    page_title="Cadu - Simulador de Crédito",
    page_icon="🤖",
    layout="centered"
)
st.title("🤖 Cadu: Simulador de Crédito e Financiamento")
st.caption("Assistente neutro para simulações de crédito e educação financeira.")
# ========================================================
# 💬 4. SYSTEM PROMPT (COM BASE TEÓRICA INJETADA)
# ========================================================
SYSTEM_PROMPT = f"""Você é o CADU, um assistente virtual especializado em Simulação de Crédito e Educação Financeira.
BASE DE CONHECIMENTO TEÓRICA (GLOSSÁRIO FINANCEIRO):
{glossario_texto}
SEU PAPEL:
1. Simulações Numéricas: Apresentar cálculos de crédito com transparência, neutralidade e clareza.
2. Dúvidas Teóricas e Conceituais: Quando o usuário perguntar o significado de algum termo (como Price, SAC, CET, Amortização, Entrada, IOF), explique de forma simples e didática utilizando as definições da Base Teórica acima.
DIRETRIZES DE RESPOSTA:
1. SEM SAUDAÇÕES REPETIDAS: Não comece dizendo "Olá! Eu sou o Cadu". Vá direto ao assunto.
2. DÚVIDAS CONCEITUAIS: Seja direto, claro e use analogias acessíveis para explicar os termos da Base Teórica.
3. SEM CRASES OU CÓDIGO: Escreva valores como texto comum (ex: R$ 500.000,00). NUNCA use crases para números.
4. NEUTRALIDADE PURA: Apenas dados e fatos conceituais. NUNCA use termos como "melhor", "vantajoso" ou "economiza".
5. SEGURANÇA: Não solicite senhas ou CPF.
"""
# ========================================================
# 📝 5. HISTÓRICO DE CHAT
# ========================================================
if "messages" not in st.session_state:
    st.session_state.messages = [
        {
            "role": "assistant",
            "content": "Olá! Eu sou o **Cadu**, seu assistente para simulações de crédito e dúvidas financeiras. Como posso te ajudar hoje?"
        }
    ]
for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])
# ========================================================
# 🚀 6. PROCESSAMENTO (SIMULAÇÃO + TEORIA)
# ========================================================
if user_input := st.chat_input("Digite sua dúvida (ex: 'O que é CET?' ou 'Veículo de R$ 500.000')..."):
    st.session_state.messages.append({"role": "user", "content": user_input})
    with st.chat_message("user"):
        st.markdown(user_input)
    todo_texto_user = " ".join([m["content"] for m in st.session_state.messages if m["role"] == "user"]).lower()
    
    modalidade, taxa_base, prazo_base = identificar_modalidade_e_taxa(todo_texto_user)
    valor_total, entrada = extrair_numeros_principais(todo_texto_user)
    financiado = valor_total - entrada if valor_total > 0 else 0.0
    usuario_confirmou_sem_dados = any(termo in user_input.lower() for termo in [
        "não possuo", "nao possuo", "não tenho", "nao tenho", "pode usar", "use a média", "use a media", "sim", "pode ser", "ok"
    ])
    instrucao_apoio = ""
    # Caso seja uma simulação numérica
    if valor_total > 0 and not ("o que é" in user_input.lower() or "diferença" in user_input.lower() or "explique" in user_input.lower()):
        if not usuario_confirmou_sem_dados:
            instrucao_apoio = f"""
[ESTADO: ETAPA DE CONFIRMAÇÃO DE DADOS]
- Bem a financiar: {modalidade} no valor de {formatar_moeda(valor_total)} (Entrada: {formatar_moeda(entrada)} | Valor a Financiar: {formatar_moeda(financiado)}).
- Taxa de referência no CSV do BACEN para {modalidade}: {taxa_base:.2f}% a.m.
- Prazo de referência para {modalidade}: {prazo_base} meses.
INSTRUÇÃO: Pergunte se o usuário tem a taxa/prazo do banco dele ou se deseja usar a taxa média do BACEN para {modalidade} ({taxa_base:.2f}% a.m.) e o prazo de {prazo_base} meses.
"""
        else:
            calc = calcular_price(financiado, taxa_base, prazo_base)
            instrucao_apoio = f"""
[ESTADO: ETAPA DE RESULTADO NUMÉRICO]
Apresente EXATAMENTE estes valores calculados pelo sistema:
- Modalidade: {modalidade}
- Valor do Bem: {formatar_moeda(valor_total)}
- Valor da Entrada: {formatar_moeda(entrada)}
- Valor Efetivamente Financiado: {formatar_moeda(financiado)}
- Taxa Aplicada (Média BACEN): {taxa_base:.2f}% a.m.
- Prazo: {prazo_base} meses
- Parcela Mensal (Tabela Price): {formatar_moeda(calc['parcela'])}
- Montante Total Pago ao Final: {formatar_moeda(calc['total_pago'])}
- Total Pago em Juros: {formatar_moeda(calc['juros_total'])}
INSTRUÇÃO: Apresente rigorosamente estes números de forma neutra.
"""
    prompt_final = SYSTEM_PROMPT
    if instrucao_apoio:
        prompt_final += f"\n\n{instrucao_apoio}"
    mensagens_para_ollama = [{"role": "system", "content": prompt_final}]
    for m in st.session_state.messages:
        mensagens_para_ollama.append({"role": m["role"], "content": m["content"]})
    with st.chat_message("assistant"):
        with st.spinner("Cadu está processando..."):
            try:
                payload = {
                    "model": MODELO,
                    "messages": mensagens_para_ollama,
                    "stream": False,
                    "options": {"temperature": 0.1}
                }
                response = requests.post(OLLAMA_CHAT_URL, json=payload)
                if response.status_code == 200:
                    resposta_texto = response.json().get("message", {}).get("content", "")
                    st.markdown(resposta_texto)
                    st.session_state.messages.append({"role": "assistant", "content": resposta_texto})
                else:
                    st.error(f"Erro no Ollama: {response.text}")
            except Exception as e:
                st.error(f"Erro ao processar resposta: {e}")
