import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import datetime, timedelta, time

st.set_page_config(page_title="Cronoprogramma Produzione", layout="wide")
st.title("⚙️ Cronoprogramma Produzione Professionale")

# ---------------- CONFIGURAZIONE LAVORO SOPRA ----------------
st.header("⚙️ Configurazione Lavoro")

col1, col2 = st.columns(2)
with col1:
    lavora_sabato = st.toggle("Lavora questo Sabato?", value=True)
    
with col2:
    turno_attuale = st.selectbox(
        "Mio turno QUESTA SETTIMANA:",
        ["Mattina (6:00-13:50)", "Pomeriggio (13:50-21:40)"]
    )

tipo_lavoro = st.radio(
    "Copertura Macchina:",
    ["Turno unico", "Due Turni (Continuo)"]
)

# ---------------- INPUT ----------------
st.header("📊 Dati Lavorazione")

c1, c2, c3 = st.columns(3)
data_inizio = c1.date_input("Data Inizio", datetime.now())
ora_inizio = c2.time_input("Ora Inizio Effettiva", value=time(8, 0))
piazzamento_ore = c3.number_input("Tempo Piazzamento", value=1.0, min_value=0.0, step=5/60)

c4, c5 = st.columns(2)
n_pezzi = c4.number_input("Numero di Pezzi", value=500)
tempo_pezzo = c5.number_input("Tempo per Pezzo", value=15.0, step=1.0)

# ---------------- VALIDAZIONE ORARI ----------------
if "Mattina" in turno_attuale and ora_inizio > time(13, 50):
    st.error("❌ **ERRORE**: Turno Mattina - non puoi iniziare dopo le 13:50!")
    st.info("👉 Scegli ora tra 6:00-13:50")
    st.stop()

if "Pomeriggio" in turno_attuale and ora_inizio < time(13, 50):
    st.error("❌ **ERRORE**: Turno Pomeriggio - non puoi iniziare prima delle 13:50!")
    st.info("👉 Scegli ora tra 13:50-21:40")
    st.stop()

# ---------------- FUNZIONE GIORNI ITALIANI ----------------
def italiano_giorno(giorno):
    trad = {
        "Mon": "Lun", "Tue": "Mar", "Wed": "Mer", "Thu": "Gio", "Fri": "Ven",
        "Sat": "Sab", "Sun": "Dom"
    }
    return trad[giorno[:3]]

# ---------------- LOGICA CON PAUSE VISIBILI ----------------
def calcola_planning():
    minuti_piaz = piazzamento_ore * 60
    minuti_prod = n_pezzi * tempo_pezzo
    corrente = datetime.combine(data_inizio, ora_inizio)
    log = []

    while minuti_piaz + minuti_prod > 0:
        wd = corrente.weekday()

        if wd == 6:  # Skip domenica
            corrente += timedelta(days=1)
            continue

        if wd == 5:  # SABATO: 6:00-12:00 NO PAUSE
            if not lavora_sabato:
                corrente += timedelta(days=1)
                continue
            inizio_turno_giorno = time(6, 0)
            fine_turno_giorno = time(12, 0)
            pause = []
        else:
            if tipo_lavoro == "Due Turni (Continuo)":
                inizio_turno_giorno = time(6, 0)
                fine_turno_giorno = time(21, 40)
                pause = [(time(12, 0), time(12, 20)), (time(19, 30), time(19, 50))]
            else:  # Turno unico
                if "Mattina" in turno_attuale:
                    inizio_turno_giorno = time(6, 0)
                    fine_turno_giorno = time(13, 50)
                    pause = [(time(12, 0), time(12, 20))]
                else:
                    inizio_turno_giorno = time(13, 50)
                    fine_turno_giorno = time(21, 40)
                    pause = [(time(19, 30), time(19, 50))]

        t_start = max(corrente.time(), inizio_turno_giorno)
        t = corrente.replace(hour=t_start.hour, minute=t_start.minute)

        while t.time() < fine_turno_giorno and (minuti_piaz + minuti_prod) > 0:
            for p1, p2 in pause:
                if p1 <= t.time() < p2:
                    log.append({
                        "Giorno": t.strftime("%a %d/%m"),
                        "Inizio": t.hour + t.minute / 60,
                        "Durata": 1 / 60,
                        "Tipo": "PAUSA",
                        "Label": ""
                    })
                    t += timedelta(minutes=1)
                    break
            else:
                tipo = "PIAZZAMENTO" if minuti_piaz > 0 else "PRODUZIONE"
                durata = min(10, minuti_piaz if tipo == "PIAZZAMENTO" else minuti_prod)

                log.append({
                    "Giorno": t.strftime("%a %d/%m"),
                    "Inizio": t.hour + t.minute
