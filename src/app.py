import streamlit as st
import pandas as pd
import os
from google import genai
from google.genai import types

# Importa as fórmulas matemáticas que você já tem no repositório
from data.formulas_matematicas import carregar_taxa_media, carregar_prazo_padrao, calcular_price

# Configuração da página Streamlit
st.set_page_config(
    page_title="Cadu - Simulador de Crédito",
    page_icon="🤖",
    layout="centered"
)

# Título e Descrição
st.title("🤖 Cadu: Simulador de Crédito e Financiamento")
st.caption("Assistente neutro e educativo para simulações financeiras com base em dados do BACEN.")

# Configuração da Chave da API do Gemini
# Pode ser configurada nas variáveis de ambiente ou via input na barra lateral
api_key = os.environ.get("GEMINI_API_KEY")

with st.sidebar:
    st.header("⚙️ Configurações")
    if not api_key:
        api_key = st.text_input("Insira sua Gemini API Key:", type="password")
        st.info("Obtenha sua chave gratuita em [Google AI Studio](https://aistudio.google.com/).")
    
    st.markdown("---")
    st.subheader("📚 Bases Carregadas")
    st.markdown("- `taxas_credito.csv` (BACEN)")
    st.markdown("- `prazos_medios_por_modalidade.csv`")
    st.markdown("- `glossario_termos_financeiros.csv`")

# System Prompt do Cadu
SYSTEM_PROMPT = """
Você é o CADU, um assistente virtual especializado em Simulação de Crédito e Financiamentos.

SEU PAPEL E OBJETIVO:
Apresentar de forma estritamente numérica, clara e transparente os cálculos de operações de crédito (valor de parcelas, montante total pago, total de juros e impacto de entradas) e explicar termos conceituais quando solicitado.

DIRETRIZES DE NEUTRALIDADE E APRESENTAÇÃO NUMÉRICA:
1. NEUTRALIDADE E OBJETIVIDADE PURA:
   - Apresente APENAS os dados e resultados numéricos.
   - NUNCA utilize termos qualitativos ou conselhos como: "isso alivia seu orçamento", "esta opção é mais vantajosa", "aqui você economiza", "não aperta no final do mês" ou "o plano X é melhor".
   - Toda comparação entre cenários deve se limitar a expor a diferença matemática absoluta (ex: "Diferença na parcela: R$ X | Diferença no total de juros: R$ Y").
2. CONFIRMAÇÃO OBRIGATÓRIA ANTES DE USAR DADOS DE REFERÊNCIA:
   - Se o usuário não fornecer a taxa de juros ou o prazo, NÃO utilize os dados de fallback imediatamente.
   - Primeiro, confirme com o usuário se ele possui o valor exato (ex: "Você possui a taxa de juros informada pelo seu banco/concessionária? Caso não tenha, posso utilizar a taxa média de mercado do Banco Central como referência.").
   - Apenas após a confirmação de que ele não possui o dado, use as taxas e prazos médios de mercado.
3. APRESENTAÇÃO DOS RESULTADOS:
   - Nas simulações padrão, apresente sempre:
     * Valor Financiado (descontada a entrada, se houver);
     * Prazo (número de meses);
     * Taxa de juros aplicada (% ao mês);
     * Valor da Parcela mensal (Tabela Price);
     * Montante Total Pago ao final;
     * Total pago em Juros.
4. CÁLCULO DE AMORTIZAÇÃO DETALHADA:
   - Apenas gere a evolução/tabela de amortização mês a mês se o usuário SOLICITAR EXPLICITAMENTE.
5. SEGURANÇA E PRIVACIDADE:
   - Não solicite e não registre senhas, CPF ou dados bancários.
"""

# Inicializa o histórico de mensagens na sessão
if "messages" not in st.session_state:
    st.session_state.messages = [
        {
            "role": "assistant",
            "content": "Olá! Eu sou o **Cadu**, seu assistente para simulações de crédito e financiamentos. Como posso te ajudar com cálculos ou dúvidas conceituais hoje?"
        }
    ]

# Exibe as mensagens existentes na interface
for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])

# Captura nova entrada do usuário
if user_input := st.chat_input("Digite sua dúvida ou simulação (ex: Financiar R$ 20.000 em 24x)..."):
    # Adiciona a mensagem do usuário ao histórico
    st.session_state.messages.append({"role": "user", "content": user_input})
    with st.chat_message("user"):
        st.markdown(user_input)

    # Processamento com o Gemini
    if not api_key:
        with st.chat_message("assistant"):
            st.warning("Por favor, informe sua Chave de API do Gemini na barra lateral para conversar com o Cadu.")
    else:
        try:
            client = genai.Client(api_key=api_key)
            
            # Monta o histórico no formato esperado pela API
            chat_history = []
            for msg in st.session_state.messages[:-1]:
                chat_history.append(
                    types.Content(
                        role="model" if msg["role"] == "assistant" else "user",
                        parts=[types.Part.from_text(text=msg["content"])]
                    )
                )

            # Gera a resposta com o System Instruction
            with st.chat_message("assistant"):
                with st.spinner("Calculando e estruturando dados..."):
                    response = client.models.generate_content(
                        model="gemini-2.5-flash",
                        contents=user_input,
                        config=types.GenerateContentConfig(
                            system_instruction=SYSTEM_PROMPT,
                            temperature=0.2,  # Baixa temperatura para manter rigor e evitar alucinação
                        )
                    )
                    bot_reply = response.text
                    st.markdown(bot_reply)
            
            # Salva no histórico da sessão
            st.session_state.messages.append({"role": "assistant", "content": bot_reply})

        except Exception as e:
            with st.chat_message("assistant"):
                st.error(f"Ocorreu um erro ao processar a resposta: {e}")
