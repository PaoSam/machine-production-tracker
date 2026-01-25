import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import datetime, timedelta, time

st.set_page_config(page_title="Cronoprogramma Produzione", layout="wide")
st.title("⚙️ Cronoprogramma Produzione Professionale")

# ---------------- SIDEBAR ----------------
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

# ---------------- INPUT ----------------
c1, c2, c3 = st.columns(3)
data_inizio = c1.date_input("Data Inizio", datetime.now())
ora_inizio = c2.time_input("Ora Inizio Effettiva", value=time(8, 0))
piazzamento_ore = c3.number_input("Tempo Piazzamento (ore)", value=1.0, step=0.5)

c4, c5 = st.columns(2)
n_pezzi = c4.number_input("Numero di Pezzi", value=500)
tempo_pezzo = c5.number_input("Tempo per Pezzo (minuti)", value=15.0)

# ---------------- LOGICA CORRETTA ----------------
def calcola_planning():
    minuti_piaz = piazzamento_ore * 60
    minuti_prod = n_pezzi * tempo_pezzo
    corrente = datetime.combine(data_inizio, ora_inizio)
    log = []

    while minuti_piaz + minuti_prod > 0:
        wd = corrente.weekday()

        # Skip domenica
        if wd == 6:
            corrente += timedelta(days=1)
            continue

        # Skip sabato se non lavora
        if wd == 5 and not lavora_sabato:
            corrente += timedelta(days=1)
            continue

        # Orari turno basati su tipo_lavoro
        if tipo_lavoro == "Due Turni (Continuo)":
            inizio_turno_giorno = time(6, 0)
            fine_turno_giorno = time(21, 40)
            pause = [(time(12, 0), time(12, 20)), (time(19, 30), time(19, 50))]
        else:  # Solo Mio Turno
            if "Mattina" in turno_attuale:
                inizio_turno_giorno = time(6, 0)
                fine_turno_giorno = time(13, 50)
                pause = [(time(12, 0), time(12, 20))]
            else:
                inizio_turno_giorno = time(13, 50)
                fine_turno_giorno = time(21, 40)
                pause = [(time(19, 30), time(19, 50))]

        # Parte da max(corrente.time(), inizio_turno_giorno)
        t_start = max(corrente.time(), inizio_turno_giorno)
        t = corrente.replace(hour=t_start.hour, minute=t_start.minute)

        # Continua fino a fine_turno_giorno o fine giornata
        while t.time() < fine_turno_giorno and (minuti_piaz + minuti_prod) > 0:
            # Skip pause
            in_pausa = False
            for p1, p2 in pause:
                if p1 <= t.time() < p2:
                    t += timedelta(minutes=1)
                    in_pausa = True
                    break
            if in_pausa:
                continue

            tipo = "PIAZZAMENTO" if minuti_piaz > 0 else "PRODUZIONE"
            durata = min(10, minuti_piaz if tipo == "PIAZZAMENTO" else minuti_prod)

            log.append({
                "Giorno": t.strftime("%a %d/%m"),
                "Inizio": t.hour + t.minute / 60,
                "Durata": durata / 60,
                "Tipo": tipo,
                "Label": f"{t.strftime('%H:%M')}"
            })

            if tipo == "PIAZZAMENTO":
                minuti_piaz -= durata
            else:
                minuti_prod -= durata

            t += timedelta(minutes=durata)

        # Passa al giorno dopo, reset a inizio_turno_giorno
        corrente = corrente + timedelta(days=1)
        corrente = corrente.replace(hour=inizio_turno_giorno.hour, minute=inizio_turno_giorno.minute)

    return pd.DataFrame(log)

# ---------------- RENDER ----------------
if st.button("🔄 CALCOLA PLANNING"):
    df = calcola_planning()

    fig = px.bar(
        df,
        x="Giorno",
        y="Durata",
        base="Inizio",
        color="Tipo",
        text="Label",
        color_discrete_map={
            "PIAZZAMENTO": "#FFA500",
            "PRODUZIONE": "#00CC96"
        }
    )

    fig.update_layout(
        yaxis=dict(
            title="Orario reale",
            autorange="reversed",
            dtick=1
        ),
        height=800,
        barmode="overlay",
        title="Cronoprogramma Produzione Macchine CNC"
    )

    st.plotly_chart(fig, use_container_width=True)
    
    # Info totali
    st.info(f"**Totale:** {len(df[df['Tipo']=='PIAZZAMENTO'])} blocchi piazzamento, {len(df[df['Tipo']=='PRODUZIONE'])} blocchi produzione")
