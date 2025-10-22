import streamlit as st
from Chatbotbases import responder_chat 

st.title("Chatbot de Energía Inteligente")
st.markdown("Pregunta sobre consumos, predicciones o anomalías eléctricas.")

if "historial" not in st.session_state:
    st.session_state.historial = []

with st.form("qa"):
    pregunta = st.text_input("Tu pregunta:")
    enviado = st.form_submit_button("Enviar")

if enviado and pregunta:
    respuesta = responder_chat(pregunta)
    st.session_state.historial.append((pregunta, respuesta))

for q, r in reversed(st.session_state.historial):
    st.markdown(f"**Tú:** {q}")
    st.markdown(f"**Chatbot:** {r}")