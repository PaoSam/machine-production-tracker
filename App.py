import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import datetime, timedelta, time

st.set_page_config(page_title="Planning Officina", layout="wide")
st.title("⚙️ Cronoprogramma Produzione Professionale")

# --- SIDEBAR ---
st.sidebar.header("Configurazione Lavoro")
lavora_sabato = st.sidebar.toggle("Lavora questo Sabato?", value=True)

turno_attuale = st.sidebar.selectbox(
    "Mio turno QUESTA SETTIMANA:",
    ["Mattina (6:00-13:50)", "Pomeriggio (13:50-21:40)"]
)

tipo_lavoro = st.sidebar.radio(
    "Copertura Macchina:",
    ["Solo Mio Turno (Spezzato)", "Due Turni (Continuo)"]
)

# --- INPUT ---
col1, col2, col3 = st.columns(3)
data_inizio_val = col1.date_input("Data Inizio", datetime.now())
ora_inizio_val = col2.time_input("Ora Inizio Effettiva", value=time(7, 0))
piazzamento_ore = col3.number_input("Tempo Piazzamento (ore)", value=1.0, step=0.5)

col4, col5 = st.columns(2)
n_pezzi = col4.number_input("Numero di Pezzi", value=60)
tempo_pezzo = col5.number_input("Tempo per Pezzo (minuti)", value=15.0, step=0.1)

# --- CALCOLO ---
def calcola_planning(data_start, ora_start, piaz_h, prod_h):
    corrente = datetime.combine(data_start, ora_start)
    min_piaz = piaz_h * 60
    min_prod = prod_h * 60
    log = []

    primo_giorno = True

    while min_piaz + min_prod > 0:
        wd = corrente.weekday()
        if wd == 6:
            corrente += timedelta(days=1)
            corrente = corrente.replace(hour=6, minute=0)
            primo_giorno = False
            continue

        # Fasce
        if tipo_lavoro == "Solo Mio Turno (Spezzato)":
            if "Mattina" in turno_attuale:
                inizio = corrente.time() if primo_giorno else time(6, 0)
                fine = time(13, 50)
                pause = [(time(12, 0), time(12, 20))]
            else:
                inizio = corrente.time() if primo_giorno else time(13, 50)
                fine = time(21, 40)
                pause = [(time(19, 30), time(19, 50))]
        else:
            inizio = corrente.time() if primo_giorno else time(6, 0)
            fine = time(21, 40)
            pause = [(time(12, 0), time(12, 20)), (time(19, 30), time(19, 50))]

        primo_giorno = False

        t = corrente.replace(hour=inizio.hour, minute=inizio.minute)

        while t.time() < fine and min_piaz + min_prod > 0:
            if any(p[0] <= t.time() < p[1] for p in pause):
                t += timedelta(minutes=1)
                continue

            tipo = "PIAZZAMENTO" if min_piaz > 0 else "PRODUZIONE"
            durata = min(10, min_piaz if tipo == "PIAZZAMENTO" else min_prod)

            log.append({
                "Giorno": t.strftime("%a %d/%m"),
                "Inizio": t.hour + t.minute / 60,
                "Durata": durata / 60,
                "Tipo": tipo,
                "Label": f"{t.strftime('%H:%M')}"
            })

            if tipo == "PIAZZAMENTO":
                min_piaz -= durata
            else:
                min_prod -= durata

            t += timedelta(minutes=durata)

        corrente += timedelta(days=1)
        corrente = corrente.replace(hour=6, minute=0)

    return pd.DataFrame(log)

# --- RENDER ---
if st.button("CALCOLA PLANNING"):
    df = calcola_planning(
        data_inizio_val,
        ora_inizio_val,
        piazzamento_ore,
        (n_pezzi * tempo_pezzo) / 60
    )

    fig = px.bar(
        df,
        x="Giorno",
        y="Durata",
        base="Inizio",
        color="Tipo",
        text="Label"
    )

    fig.update_layout(
        yaxis=dict(autorange="reversed", dtick=1),
        height=800,
        barmode="overlay"
    )

    st.plotly_chart(fig, use_container_width=True)
