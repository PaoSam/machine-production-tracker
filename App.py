import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import datetime, timedelta, time
import numpy as np

st.set_page_config(page_title="CronoCNC", page_icon="⚙️", layout="wide")

st.title("⚙️ CronoCNC - Pianificazione Produzione")

# ---------------- CONFIGURAZIONE ----------------
st.sidebar.header("Configurazione Turno")

turno = st.sidebar.selectbox(
    "Turno",
    ["Mattina", "Pomeriggio"]
)

# orari turno
if turno == "Mattina":
    turno_start = time(6,0)
    turno_end = time(13,50)
    pause = [(time(12,0), time(12,20))]
else:
    turno_start = time(13,50)
    turno_end = time(21,40)
    pause = [(time(19,30), time(19,50))]

# ---------------- INPUT ----------------
st.header("Dati Lavorazione")

c1,c2,c3 = st.columns(3)

data_inizio = c1.date_input("Data Inizio", datetime.now())
ora_inizio = c2.time_input("Ora Inizio Effettiva", value=time(16,30))
piazzamento_ore = c3.number_input("Tempo Piazzamento (ore)", value=1.5)

c4,c5 = st.columns(2)

n_pezzi = c4.number_input("Numero Pezzi", value=100)
tempo_pezzo = c5.number_input("Tempo per pezzo (min)", value=51)

# ---------------- FUNZIONE MINUTI LAVORABILI ----------------
def minuti_lavorabili(start_dt,end_dt,pause):

    minuti = 0
    t = start_dt

    while t < end_dt:

        in_pausa = False

        for p1,p2 in pause:
            p_start = t.replace(hour=p1.hour,minute=p1.minute)
            p_end = t.replace(hour=p2.hour,minute=p2.minute)

            if p_start <= t < p_end:
                in_pausa = True
                break

        if not in_pausa:
            minuti += 1

        t += timedelta(minutes=1)

    return minuti

# ---------------- CALCOLO ----------------
def calcola():

    minuti_piaz = piazzamento_ore*60
    minuti_prod = n_pezzi*tempo_pezzo

    corrente = datetime.combine(data_inizio,ora_inizio)

    dati = []

    pezzi_tot = 0

    while minuti_piaz+minuti_prod > 0:

        giorno = corrente.date()

        start_turno = datetime.combine(giorno,turno_start)
        end_turno = datetime.combine(giorno,turno_end)

        start_eff = max(corrente,start_turno)

        minuti_disp = minuti_lavorabili(start_eff,end_turno,pause)

        minuti_usati = 0
        pezzi_giorno = 0

        # piazzamento
        if minuti_piaz>0:

            uso = min(minuti_disp,minuti_piaz)

            minuti_piaz -= uso
            minuti_disp -= uso
            minuti_usati += uso

        # produzione
        while minuti_disp >= tempo_pezzo and pezzi_tot < n_pezzi:

            minuti_disp -= tempo_pezzo
            minuti_usati += tempo_pezzo

            pezzi_giorno += 1
            pezzi_tot += 1
            minuti_prod -= tempo_pezzo

        # calcolo orario fine giornata
        fine = start_eff + timedelta(minutes=minuti_usati)

        dati.append({
            "Data":giorno,
            "Inizio":start_eff.strftime("%H:%M"),
            "Fine":fine.strftime("%H:%M"),
            "Minuti lavorati":minuti_usati,
            "Pezzi giorno":pezzi_giorno,
            "Totale pezzi":pezzi_tot
        })

        corrente = datetime.combine(giorno+timedelta(days=1),turno_start)

    return pd.DataFrame(dati)

# ---------------- ESECUZIONE ----------------
if st.button("CALCOLA PLANNING"):

    df = calcola()

    st.subheader("Tabella Verifica Produzione")

    st.dataframe(df,use_container_width=True)

    ultimo = df.iloc[-1]

    st.success(
        f"Fine lavorazione prevista: {ultimo['Data']} ore {ultimo['Fine']}"
    )

    # grafico produzione
    fig = px.bar(
        df,
        x="Data",
        y="Pezzi giorno",
        title="Produzione giornaliera"
    )

    st.plotly_chart(fig,use_container_width=True)
