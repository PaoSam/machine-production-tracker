import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
from datetime import datetime, timedelta, time

st.set_page_config(page_title="Pianificatore Produzione", layout="wide")

st.title("⚙️ Machine Utensili: Calcolo e Carico Settimanale")

# --- SIDEBAR CONFIGURAZIONE ---
st.sidebar.header("Impostazioni Turni")
tipo_lavoro = st.sidebar.radio("Copertura Macchina:", 
                              ["Due Turni (Continuo)", "Solo Mio Turno (Spezzato)"])

turno_scelto = None
if tipo_lavoro == "Solo Mio Turno (Spezzato)":
    turno_scelto = st.sidebar.selectbox("Quale turno copri?", ["Mattina (6:00-13:50)", "Pomeriggio (13:50-21:40)"])

pausa_minuti = 20

# --- INPUT COMMESSA ---
col1, col2, col3 = st.columns(3)
data_inizio = col1.date_input("Data Inizio", datetime.now())
ora_inizio = col2.time_input("Ora Inizio", time(6, 0))
piazzamento = col3.number_input("Tempo Piazzamento (ore)", value=1.0, step=0.5)

col4, col5 = st.columns(2)
n_pezzi = col4.number_input("Numero di Pezzi", value=60)
tempo_pezzo = col5.number_input("Tempo per Pezzo (minuti)", value=15.0, step=0.1)

# --- LOGICA DI CALCOLO E TRACCIAMENTO GIORNALIERO ---
def calcola_produzione(inizio_dt, ore_totali, modalita, turno):
    corrente = inizio_dt
    minuti_rimanenti = ore_totali * 60
    log_lavoro = [] # Per il grafico
    
    while minuti_rimanenti > 0:
        wd = corrente.weekday() 
        if wd < 5: # Lun-Ven
            if modalita == "Due Turni (Continuo)":
                inizio_l, fine_l = time(6, 0), time(21, 40)
            else:
                inizio_l, fine_l = (time(6, 0), time(13, 50)) if turno.startswith("Mattina") else (time(13, 50), time(21, 40))
        elif wd == 5: # Sabato
            inizio_l, fine_l = time(6, 0), time(12, 0)
        else: # Domenica
            corrente += timedelta(days=1)
            corrente = corrente.replace(hour=6, minute=0)
            continue

        limite_inizio = corrente.replace(hour=inizio_l.hour, minute=inizio_l.minute, second=0)
        limite_fine = corrente.replace(hour=fine_l.hour, minute=fine_l.minute, second=0)

        if corrente >= limite_fine:
            corrente += timedelta(days=1)
            corrente = corrente.replace(hour=inizio_l.hour, minute=inizio_l.minute)
            continue
        
        if corrente < limite_inizio:
            corrente = limite_inizio

        spazio_disponibile = (limite_fine - corrente).total_seconds() / 60
        effettivi_oggi = spazio_disponibile - pausa_minuti if spazio_disponibile > 180 else spazio_disponibile
        
        lavoro_oggi = min(minuti_rimanenti, effettivi_oggi)
        
        # Salviamo i dati per il grafico
        log_lavoro.append({
            "Giorno": corrente.strftime('%A %d/%m'),
            "Ore Lavoro": lavoro_oggi / 60
        })
        
        minuti_rimanenti -= lavoro_oggi
        corrente += timedelta(minutes=lavoro_oggi + (pausa_minuti if lavoro_oggi == effettivi_oggi else 0))

    return corrente, pd.DataFrame(log_lavoro)

# --- OUTPUT ---
if st.button("Calcola e Genera Grafico"):
    ore_lavoro_tot = piazzamento + (n_pezzi * tempo_pezzo / 60)
    dt_inizio_pieno = datetime.combine(data_inizio, ora_inizio)
    
    data_fine, df_carico = calcola_produzione(dt_inizio_pieno, ore_lavoro_tot, tipo_lavoro, turno_scelto)
    
    st.write("---")
    st.header(f"🏁 Consegna prevista: {data_fine.strftime('%d/%m/%Y ore %H:%M')}")
    
    # Grafico a barre dei giorni
    if not df_carico.empty:
        st.subheader("📅 Carico di lavoro giornaliero (Ore)")
        fig = px.bar(df_carico, x='Giorno', y='Ore Lavoro', 
                     text_auto='.1f', color='Ore Lavoro',
                     color_continuous_scale='Blues')
        fig.update_layout(xaxis_title="Giorno della Settimana", yaxis_title="Ore di Lavoro sulla Macchina")
        st.plotly_chart(fig, use_container_width=True)

    st.info(f"Il lavoro richiede un totale di **{ore_lavoro_tot:.1f} ore** di macchina presidiata.")
