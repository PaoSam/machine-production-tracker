import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import datetime, timedelta, time

# Festivi italiani
try:
    import holidays
    it_holidays = holidays.Italy()
except:
    it_holidays = []

st.set_page_config(page_title="CronoCNC", layout="wide")

st.title("⚙️ CronoCNC - Pianificazione Produzione")

# ---------------- SIDEBAR ----------------

st.sidebar.header("Configurazione")

lavora_sabato = st.sidebar.toggle("Lavora Sabato", True)

turno_iniziale = st.sidebar.selectbox(
    "Turno iniziale settimana",
    ["Mattina", "Pomeriggio"]
)

tipo_lavoro = st.sidebar.radio(
    "Copertura macchina",
    ["Turno unico", "Due Turni (Continuo)"]
)

# ---------------- INPUT ----------------

st.header("Dati lavorazione")

c1, c2, c3 = st.columns(3)

data_inizio = c1.date_input("Data inizio", datetime.now())
ora_inizio = c2.time_input("Ora inizio", value=time(8,0))
piazzamento_ore = c3.number_input("Piazzamento ore", value=1.0)

c4, c5 = st.columns(2)

n_pezzi = c4.number_input("Numero pezzi", value=100)
tempo_pezzo = c5.number_input("Tempo pezzo (minuti)", value=15)

# ---------------- CALCOLO ----------------

def calcola():

    minuti_piazzamento = piazzamento_ore * 60
    minuti_produzione = n_pezzi * tempo_pezzo

    corrente = datetime.combine(data_inizio, ora_inizio)

    settimana_iniziale = data_inizio.isocalendar()[1]

    step = 5

    log = []

    while minuti_piazzamento > 0 or minuti_produzione > 0:

        wd = corrente.weekday()

        if wd == 6 or corrente.date() in it_holidays:
            corrente += timedelta(days=1)
            corrente = corrente.replace(hour=6, minute=0)
            continue

        settimana_corrente = corrente.isocalendar()[1]

        turno = turno_iniziale

        if (settimana_corrente - settimana_iniziale) % 2 != 0:
            turno = "Pomeriggio" if turno_iniziale == "Mattina" else "Mattina"

        # Sabato
        if wd == 5:

            if not lavora_sabato:
                corrente += timedelta(days=1)
                corrente = corrente.replace(hour=6, minute=0)
                continue

            inizio = time(6,0)
            fine = time(12,0)
            pause = []

        else:

            if tipo_lavoro == "Due Turni (Continuo)":

                inizio = time(6,0)
                fine = time(21,40)

                pause = [
                    (time(12,0),time(12,20)),
                    (time(19,30),time(19,50))
                ]

            else:

                if turno == "Mattina":

                    inizio = time(6,0)
                    fine = time(13,50)
                    pause = [(time(12,0),time(12,20))]

                else:

                    inizio = time(13,50)
                    fine = time(21,40)
                    pause = [(time(19,30),time(19,50))]

        # fuori turno
        if corrente.time() < inizio:
            corrente = corrente.replace(hour=inizio.hour, minute=inizio.minute)

        if corrente.time() >= fine:
            corrente += timedelta(days=1)
            corrente = corrente.replace(hour=6, minute=0)
            continue

        # controllo pause
        in_pausa = False

        for p1,p2 in pause:
            if p1 <= corrente.time() < p2:
                in_pausa = True
                break

        if in_pausa:
            corrente += timedelta(minutes=step)
            continue

        # piazzamento
        if minuti_piazzamento > 0:

            lavoro = min(step, minuti_piazzamento)

            log.append({
                "Data":corrente.date(),
                "Ora":corrente.strftime("%H:%M"),
                "Tipo":"PIAZZAMENTO",
                "Minuti":lavoro,
                "Pezzi":0
            })

            minuti_piazzamento -= lavoro

            corrente += timedelta(minutes=lavoro)

        else:

            lavoro = min(step, minuti_produzione)

            pezzi = lavoro / tempo_pezzo

            log.append({
                "Data":corrente.date(),
                "Ora":corrente.strftime("%H:%M"),
                "Tipo":"PRODUZIONE",
                "Minuti":lavoro,
                "Pezzi":pezzi
            })

            minuti_produzione -= lavoro

            corrente += timedelta(minutes=lavoro)

    return pd.DataFrame(log)

# ---------------- CALCOLO BUTTON ----------------

if st.button("CALCOLA PLANNING"):

    df = calcola()

    produzione = df.groupby("Data").agg(
        Minuti_lavorati=("Minuti","sum"),
        Pezzi=("Pezzi","sum")
    ).reset_index()

    produzione["Pezzi"] = produzione["Pezzi"].round(0).astype(int)

    produzione["Totale pezzi"] = produzione["Pezzi"].cumsum()

    produzione["Ore lavorate"] = (produzione["Minuti_lavorati"]/60).round(2)

    st.subheader("📋 Tabella Produzione")

    st.dataframe(
        produzione.rename(columns={
            "Minuti_lavorati":"Minuti lavorati",
            "Pezzi":"Pezzi giorno"
        }),
        use_container_width=True
    )

    ultimo = df.iloc[-1]

    st.success(
        f"🏁 Fine lavorazione prevista: {ultimo['Data']} ore {ultimo['Ora']}"
    )

    fig = px.bar(
        produzione,
        x="Data",
        y="Pezzi",
        title="Produzione giornaliera"
    )

    st.plotly_chart(fig, use_container_width=True)
