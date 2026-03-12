import streamlit as st
import pandas as pd
import numpy as np
from datetime import datetime, timedelta, time

# Prova a importare festivi italiani
try:
    import holidays
    it_holidays = holidays.Italy()
except ImportError:
    it_holidays = []

# ---------------- CONFIGURAZIONE PAGINA ----------------
st.set_page_config(page_title="CronoCNC", layout="wide")
st.title("⚙️ CronoCNC - Pianificazione Produzione")

# ---------------- SIDEBAR ----------------
st.sidebar.header("Configurazione Turno")
lavora_sabato = st.sidebar.toggle("Lavora questo Sabato?", value=True)
turno_iniziale = st.sidebar.selectbox(
    "Mio turno QUESTA SETTIMANA:",
    ["Mattina (6:00-13:50)", "Pomeriggio (13:50-21:40)"]
)
tipo_lavoro = st.sidebar.radio(
    "Copertura Macchina:",
    ["Turno unico", "Due Turni (Continuo)"]
)

# ---------------- INPUT DATI ----------------
st.header("📊 Dati Lavorazione")
c1, c2, c3 = st.columns(3)
data_inizio = c1.date_input("Data Inizio", datetime.now())
ora_inizio = c2.time_input("Ora Inizio Effettiva", value=time(8, 0))
piazzamento_ore = c3.number_input("Tempo Piazzamento (ore)", value=1.0, min_value=0.0, step=0.1)

c4, c5 = st.columns(2)
n_pezzi = c4.number_input("Numero totale di Pezzi", value=100)
tempo_pezzo = c5.number_input("Tempo per Pezzo (minuti)", value=51.0, step=1.0)

# ---------------- FUNZIONE PER CALCOLO MINUTI LAVORABILI ----------------
def minuti_lavorabili(start_dt, end_dt, pause_list):
    minuti = 0
    t = start_dt
    while t < end_dt:
        in_pausa = False
        for p1, p2 in pause_list:
            p_start = t.replace(hour=p1.hour, minute=p1.minute)
            p_end = t.replace(hour=p2.hour, minute=p2.minute)
            if p_start <= t < p_end:
                in_pausa = True
                break
        if not in_pausa:
            minuti += 1
        t += timedelta(minutes=1)
    return minuti

# ---------------- FUNZIONE CALCOLO PLANNING ----------------
def calcola_planning():
    minuti_piaz = piazzamento_ore * 60
    minuti_prod = n_pezzi * tempo_pezzo
    corrente = datetime.combine(data_inizio, ora_inizio)
    dati = []
    
    settimana_iniziale = data_inizio.isocalendar()[1]
    pezzi_tot = 0
    
    while minuti_piaz + minuti_prod > 0:
        wd = corrente.weekday()
        
        # Salta domeniche e festivi
        if wd == 6 or corrente.date() in it_holidays:
            corrente += timedelta(days=1)
            corrente = corrente.replace(hour=6, minute=0)
            continue
        
        # Alternanza turno settimanale
        settimana_corrente = corrente.isocalendar()[1]
        turno_sett = turno_iniziale
        if (settimana_corrente - settimana_iniziale) % 2 != 0:
            if "Mattina" in turno_iniziale:
                turno_sett = "Pomeriggio (13:50-21:40)"
            else:
                turno_sett = "Mattina (6:00-13:50)"
        
        # Definizione orari e pause
        if wd == 5:  # sabato
            if not lavora_sabato:
                corrente += timedelta(days=1)
                corrente = corrente.replace(hour=6, minute=0)
                continue
            inizio_t, fine_t, pause_list = time(6,0), time(12,0), []
        else:
            if tipo_lavoro == "Due Turni (Continuo)":
                inizio_t, fine_t = time(6,0), time(21,40)
                pause_list = [(time(12,0), time(12,20)), (time(19,30), time(19,50))]
            else:
                if "Mattina" in turno_sett:
                    inizio_t, fine_t, pause_list = time(6,0), time(13,50), [(time(12,0), time(12,20))]
                else:
                    inizio_t, fine_t, pause_list = time(13,50), time(21,40), [(time(19,30), time(19,50))]
        
        # Se siamo oltre la fine turno, passa al giorno dopo
        if corrente.time() >= fine_t:
            corrente += timedelta(days=1)
            corrente = corrente.replace(hour=6, minute=0)
            continue
        
        t_effettivo = max(corrente.time(), inizio_t)
        t = corrente.replace(hour=t_effettivo.hour, minute=t_effettivo.minute)
        minuti_disp = minuti_lavorabili(t, t.replace(hour=fine_t.hour, minute=fine_t.minute), pause_list)
        
        minuti_usati = 0
        pezzi_giorno = 0
        
        # Piazzamento
        if minuti_piaz > 0:
            uso = min(minuti_disp, minuti_piaz)
            minuti_piaz -= uso
            minuti_disp -= uso
            minuti_usati += uso
        
        # Produzione
        while minuti_disp >= tempo_pezzo and pezzi_tot < n_pezzi:
            minuti_disp -= tempo_pezzo
            minuti_usati += tempo_pezzo
            pezzi_giorno += 1
            pezzi_tot += 1
            minuti_prod -= tempo_pezzo
        
        # Orario di fine giornata
        fine = t + timedelta(minutes=minuti_usati)
        
        dati.append({
            "Data": corrente.date(),
            "Inizio": t.strftime("%H:%M"),
            "Fine": fine.strftime("%H:%M"),
            "Minuti lavorati": minuti_usati,
            "Pezzi giorno": pezzi_giorno,
            "Totale pezzi": pezzi_tot
        })
        
        corrente = datetime.combine(corrente.date() + timedelta(days=1), inizio_t)
    
    return pd.DataFrame(dati)

# ---------------- ESECUZIONE ----------------
if st.button("🔄 CALCOLA PLANNING"):
    df_risultato = calcola_planning()
    
    # Tabella verifica completa
    st.subheader("📋 Tabella Verifica Produzione")
    st.dataframe(df_risultato, use_container_width=True)
    
    # Orario di fine totale
    ultimo = df_risultato.iloc[-1]
    st.success(f"🏁 Fine lavorazione prevista: {ultimo['Data']} ore {ultimo['Fine']}")
    
    # Grafico produzione
    import plotly.express as px
    fig = px.bar(
        df_risultato,
        x="Data",
        y="Pezzi giorno",
        title="Produzione giornaliera"
    )
    st.plotly_chart(fig, use_container_width=True)
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
