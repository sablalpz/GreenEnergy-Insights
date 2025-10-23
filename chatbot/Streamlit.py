import streamlit as st
from Chatbotbases import responder_chat

st.set_page_config(page_title="Chatbot de Energía Inteligente", layout="wide")

st.title("Chatbot de Energía Inteligente")
st.markdown("Haz preguntas sobre **consumos**, **predicciones** o **anomalías eléctricas** y obtén explicaciones técnicas detalladas.")

# Historial de conversación
if "historial" not in st.session_state:
    st.session_state.historial = []

# Formulario para enviar pregunta
with st.form("qa"):
    pregunta = st.text_area("Tu pregunta:", height=100, placeholder="Ejemplo: ¿Qué es una anomalía en una red eléctrica?")
    enviado = st.form_submit_button("Enviar")

# Procesar la pregunta
if enviado and pregunta:
    with st.spinner("Analizando y generando respuesta..."):
        respuesta = responder_chat(pregunta)
        st.session_state.historial.append((pregunta, respuesta))

# Mostrar historial (de último a primero)
for q, r in reversed(st.session_state.historial):
    st.markdown(f" Tú:\n{q}")
    st.markdown(f"**Chatbot:**")
    # Renderiza texto largo con saltos de línea y formato Markdown completo
    st.markdown(r, unsafe_allow_html=True)
    st.markdown("---")