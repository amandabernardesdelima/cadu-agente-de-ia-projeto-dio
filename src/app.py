import streamlit as st
import pandas as pd
import os
import google.genai as genai
from google.genai import types

from data.formulas_matematicas import carregar_taxa_media, carregar_prazo_padrao, calcular_price

st.set_page_config(
    page_title="Cadu - Simulador de Crédito",
    page_icon="🤖",
    layout="centered"
)

st.title("🤖 Cadu: Simulador de Crédito e Financiamento")
st.caption("Assistente neutro e educativo para simulações financeiras com base em dados do BACEN.")

if "api_key" not in st.session_state:
    st.session_state.api_key = os.environ.get("GEMINI_API_KEY")

with st.sidebar:
    st.header("⚙️ Configurações")
    if not st.session_state.api_key:
        st.session_state.api_key = st.text_input("Insira sua Gemini API Key:", type="password")
        st.info("Obtenha sua chave gratuita em [Google AI Studio](https://aistudio.google.com/).")

    st.markdown("---")
    st.subheader("📚 Bases Carregadas")
    st.markdown("- `taxas_credito.csv` (BACEN)")
    st.markdown("- `prazos_medios_por_modalidade.csv`")
    st.markdown("- `glossario_termos_financeiros.csv`")

SYSTEM_PROMPT = """ ... """

if "messages" not in st.session_state:
    st.session_state.messages = [
        {"role": "assistant", "content": "Olá! Eu sou o **Cadu**..."}
    ]

for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])

if user_input := st.chat_input("Digite sua dúvida ou simulação..."):
    st.session_state.messages.append({"role": "user", "content": user_input})
    with st.chat_message("user"):
        st.markdown(user_input)

    if not st.session_state.api_key:
        with st.chat_message("assistant"):
            st.warning("Por favor, informe sua Chave de API do Gemini.")
    else:
        try:
            client = genai.Client(api_key=st.session_state.api_key)

            chat_history = [
                types.Content(
                    role="model" if msg["role"] == "assistant" else "user",
                    parts=[types.Part.from_text(text=msg["content"])]
                )
                for msg in st.session_state.messages[:-1]
            ]

            with st.chat_message("assistant"):
                with st.spinner("Calculando e estruturando dados..."):
                    response = client.models.generate_content(
                        model="gemini-2.5-flash",
                        contents=chat_history + [
                            types.Content(
                                role="user",
                                parts=[types.Part.from_text(text=user_input)]
                            )
                        ],
                        config=types.GenerateContentConfig(
                            system_instruction=SYSTEM_PROMPT,
                            temperature=0.2,
                        )
                    )
                    bot_reply = response.text
                    st.markdown(bot_reply)

            st.session_state.messages.append({"role": "assistant", "content": bot_reply})

        except Exception as e:
            with st.chat_message("assistant"):
                st.error(f"Ocorreu um erro: {e}")
