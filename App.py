import streamlit as st
import pandas as pd
import plotly.express as px

st.set_page_config(page_title="Monitoraggio Produzione", layout="wide")
st.title("⚙️ Machine Utensili: Analisi Tempi")

st.sidebar.info("Carica i dati della macchina per analizzare l'efficienza.")

# Esempio di input manuale per testare subito
with st.expander("Inserimento Rapido Dati"):
    col1, col2, col3 = st.columns(3)
    lavoro = col1.number_input("Minuti in Lavoro", value=400)
    fermo = col2.number_input("Minuti Fermo", value=50)
    setup = col3.number_input("Minuti Setup", value=30)

# Calcolo OEE semplificato
totale = lavoro + fermo + setup
if totale > 0:
    efficienza = (lavoro / totale) * 100
    st.metric("Efficienza (Disponibilità)", f"{efficienza:.1f}%")

    # Grafico a torta dei tempi
    df_pie = pd.DataFrame({
        "Stato": ["Lavoro", "Fermo", "Setup"],
        "Minuti": [lavoro, fermo, setup]
    })
    fig = px.pie(df_pie, values='Minuti', names='Stato', color='Stato',
                 color_discrete_map={'Lavoro':'green', 'Fermo':'red', 'Setup':'orange'})
    st.plotly_chart(fig)
