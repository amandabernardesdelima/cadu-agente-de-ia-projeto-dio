import json
import re
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
# ⚙️ 2. CONFIGURAÇÃO DA PÁGINA E OLLAMA
# ========================================================
OLLAMA_CHAT_URL = "http://localhost:11434/api/chat"
MODELO = "llama3"

st.set_page_config(
    page_title="Cadu - Simulador de Crédito",
    page_icon="🤖",
    layout="centered"
)

st.title("🤖 Cadu: Simulador de Crédito e Financiamento")
st.caption("Assistente neutro e educativo para simulações de crédito.")

# ========================================================
# 💬 3. SYSTEM PROMPT OFICIAL DO CADU
# ========================================================
SYSTEM_PROMPT = """Você é o CADU, um assistente virtual especializado em Simulação de Crédito e Financiamentos.

SEU PAPEL E OBJETIVO:
Apresentar de forma estritamente numérica, clara e transparente os cálculos de operações de crédito (valor de parcelas, montante total pago, total de juros e impacto de entradas) e explicar termos conceituais quando solicitado.

DIRETRIZES DE NEUTRALIDADE E APRESENTAÇÃO NUMÉRICA:
1. NEUTRALIDADE E OBJETIVIDADE PURA:
   - Apresente APENAS os dados e resultados numéricos.
   - NUNCA utilize termos qualitativos, conselhos ou interpretações como: "isso alivia seu orçamento", "esta opção é mais vantajosa", "aqui você economiza", "não aperta no final do mês" ou "o plano X é melhor".
   - Toda comparação entre cenários deve se limitar a expor a diferença matemática absoluta (ex: "Diferença na parcela: R$ X | Diferença no total de juros: R$ Y").
2. CONFIRMAÇÃO OBRIGATÓRIA ANTES DE USAR DADOS DE REFERÊNCIA:
   - Se o usuário não fornecer a taxa de juros ou o prazo, NÃO faça a simulação imediatamente.
   - Pergunte e confirme com o usuário se ele possui o valor exato (ex: "Você possui a taxa de juros e o prazo informados pelo seu banco? Caso não tenha, posso utilizar a taxa média de mercado como referência.").
   - Apenas após a confirmação de que ele não possui os dados (ou quando ele disser "não tenho", "pode usar a média"), apresente a simulação com os dados de referência.
3. APRESENTAÇÃO DOS RESULTADOS:
   - Nas simulações padrão, apresente sempre:
     * Valor do Bem e Entrada (se houver)
     * Valor Efetivamente Financiado (descontada a entrada)
     * Prazo (número de meses)
     * Taxa de juros aplicada (% ao mês)
     * Valor da Parcela mensal (Tabela Price)
     * Montante Total Pago ao final
     * Total pago em Juros
4. CÁLCULO DE AMORTIZAÇÃO DETALHADA:
   - Apenas gere a evolução/tabela de amortização detalhada (mês a mês) se o usuário SOLICITAR EXPLICITAMENTE.
5. CONCEITOS E GLOSSÁRIO:
   - Explique termos técnicos de maneira objetiva e direta.
6. PRIVACIDADE E SEGURANÇA (GUARDRAILS):
   - Nunca solicite e nunca armazene dados sensíveis (senhas, código de segurança, dados de cartão ou CPF completo).
   - Não analise renda pessoal ou perfil de risco para aprovação de crédito.
   - Sempre reforce que os valores são estimativas simuladas para fins de planejamento e que as condições contratuais reais dependem da instituição credora.
   - NUNCA invente informações, se não souber admita.
7. LINGUAGEM:
   - Linguagem simples e acessível mantendo a formalidade.
   - Sempre responda de forma sucinta e direta, evite ambiguidades.
   - SEM SAUDAÇÕES REPETIDAS: Não diga "Olá, sou o Cadu" no meio da conversa.
   - SEM CRASES: Escreva valores monetários como texto normal com R$ (ex: R$ 940.000,00).
"""

# ========================================================
# 📝 4. HISTÓRICO DE CHAT
# ========================================================
if "messages" not in st.session_state:
    st.session_state.messages = [
        {
            "role": "assistant",
            "content": "Olá! Eu sou o **Cadu**, seu assistente para simulações de crédito e financiamentos. Como posso te ajudar com sua simulação hoje?"
        }
    ]

for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])

# ========================================================
# 🚀 5. ENTRADA E FLUXO CONVERSACIONAL INTELIGENTE
# ========================================================
if user_input := st.chat_input("Digite sua simulação (ex: Imóvel de R$ 1.000.000 com entrada de R$ 60.000)..."):
    st.session_state.messages.append({"role": "user", "content": user_input})
    with st.chat_message("user"):
        st.markdown(user_input)

    # Identifica valores do histórico acumulado
    todo_texto = " ".join([m["content"] for m in st.session_state.messages if m["role"] == "user"]).lower()
    
    # Detecção se o usuário está confirmando que não tem os dados
    usuario_confirmou_sem_dados = any(termo in user_input.lower() for termo in [
        "não possuo", "nao possuo", "não tenho", "nao tenho", "pode usar", "use a média", "use a media", "sim", "pode ser"
    ])

    instrucao_apoio = ""
    
    # Se detectamos valor de 1 milhão com 60 mil de entrada no contexto
    if ("1000000" in todo_texto or "1.000.000" in todo_texto) and ("60000" in todo_texto or "60.000" in todo_texto):
        valor_bem = 1000000.0
        entrada = 60000.0
        financiado = 940000.0
        
        if not usuario_confirmou_sem_dados:
            # ETAPA 1: O usuário acabou de informar os valores -> Cadu deve confirmar taxa e prazo!
            instrucao_apoio = f"""
[ESTADO DA CONVERSA: ETAPA DE CONFIRMAÇÃO]
- O usuário deseja financiar um imóvel de {formatar_moeda(valor_bem)} com entrada de {formatar_moeda(entrada)}.
- O valor a ser financiado é de {formatar_moeda(financiado)}.
- INSTRUÇÃO OBRIGATÓRIA: Não faça o cálculo da parcela agora! Pergunte ao usuário se ele possui a taxa de juros e o prazo informados pelo banco dele, ou se deseja que você utilize as taxas médias do BACEN (0,90% a.m. e 360 meses) como referência.
"""
        else:
            # ETAPA 2: O usuário confirmou que não tem -> Cadu calcula com precisão pelo Python!
            taxa = 0.90
            prazo = 360
            calc = calcular_price(financiado, taxa, prazo)
            instrucao_apoio = f"""
[ESTADO DA CONVERSA: ETAPA DE RESULTADO MATEMÁTICO]
O usuário confirmou que não tem os dados. Apresente exatamente estes números calculados pelo sistema:
- Modalidade: Financiamento Imobiliário
- Valor do Imóvel: {formatar_moeda(valor_bem)}
- Valor da Entrada: {formatar_moeda(entrada)}
- Valor Efetivamente Financiado: {formatar_moeda(financiado)}
- Taxa de Juros média: {taxa:.2f}% a.m.
- Prazo médio: {prazo} meses
- Parcela Mensal (Tabela Price): {formatar_moeda(calc['parcela'])}
- Montante Total Pago ao Final: {formatar_moeda(calc['total_pago'])}
- Total Pago em Juros: {formatar_moeda(calc['juros_total'])}

INSTRUÇÃO: Apresente estritamente estes valores de forma limpa, direta e neutra.
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
                response = requests.post(OLLAMA_CHAT_URL, json=payload, timeout=180)
                if response.status_code == 200:
                    resposta_texto = response.json().get("message", {}).get("content", "")
                    st.markdown(resposta_texto)
                    st.session_state.messages.append({"role": "assistant", "content": resposta_texto})
                else:
                    st.error(f"Erro no Ollama: {response.text}")
            except Exception as e:
                st.error(f"Erro de conexão: {e}")
