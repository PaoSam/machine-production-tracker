import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import datetime, timedelta, time

st.set_page_config(page_title="Pianificatore Produzione Pro", layout="wide")

st.title("⚙️ Machine Utensili: Calcolo Fine e Carico Lavoro")

# --- SIDEBAR CONFIGURAZIONE ---
st.sidebar.header("Impostazioni Turni")
tipo_lavoro = st.sidebar.radio("Copertura Macchina:", 
                              ["Due Turni (Continuo)", "Solo Mio Turno (Spezzato)"])

turno_scelto = None
if tipo_lavoro == "Solo Mio Turno (Spezzato)":
    turno_scelto = st.sidebar.selectbox("Quale turno copri?", ["Mattina (6:00-13:50)", "Pomeriggio (13:50-21:40)"])

# --- INPUT COMMESSA ---
col1, col2, col3 = st.columns(3)
data_inizio = col1.date_input("Data Inizio", datetime.now())
ora_inizio = col2.time_input("Ora Inizio", time(6, 0))
piazzamento_ore = col3.number_input("Tempo Piazzamento (ore)", value=1.0, step=0.5)

col4, col5 = st.columns(2)
n_pezzi = col4.number_input("Numero di Pezzi", value=60)
tempo_pezzo = col5.number_input("Tempo per Pezzo (minuti)", value=15.0, step=0.1)

# --- LOGICA DI CALCOLO ---
def calcola_produzione_dettagliata(inizio_dt, ore_piazzamento, ore_pezzi, modalita, turno_sp):
    corrente = inizio_dt
    minuti_piazzamento_restanti = ore_piazzamento * 60
    minuti_pezzi_restanti = ore_pezzi * 60
    log_lavoro = []

    def aggiungi_log(tipo, durata_min):
        giorno_str = corrente.strftime('%A %d/%m')
        log_lavoro.append({"Giorno": giorno_str, "Ore": durata_min / 60, "Tipo": tipo})

    while (minuti_piazzamento_restanti + minuti_pezzi_restanti) > 0:
        wd = corrente.weekday()
        if wd < 5: # Lun-Ven
            if modalita == "Due Turni (Continuo)":
                finestre = [(time(6, 0), time(13, 50)), (time(13, 50), time(21, 40))]
            else:
                finestre = [(time(6, 0), time(13, 50))] if "Mattina" in turno_sp else [(time(13, 50), time(21, 40))]
        elif wd == 5: # Sabato
            finestre = [(time(6, 0), time(12, 0))]
        else: # Domenica
            corrente += timedelta(days=1)
            corrente = corrente.replace(hour=6, minute=0, second=0)
            continue

        lavorato_oggi = False
        for f_inizio, f_fine in finestre:
            limite_inizio = corrente.replace(hour=f_inizio.hour, minute=f_inizio.minute, second=0)
            limite_fine = corrente.replace(hour=f_fine.hour, minute=f_fine.minute, second=0)
            
            # Definizione Pausa specifica per la finestra
            p_inizio, p_fine = None, None
            if f_inizio == time(6, 0): # Mattina
                p_inizio, p_fine = limite_inizio.replace(hour=12, minute=0), limite_inizio.replace(hour=12, minute=20)
            elif f_inizio == time(13, 50): # Pomeriggio
                p_inizio, p_fine = limite_inizio.replace(hour=19, minute=30), limite_inizio.replace(hour=19, minute=50)

            if corrente >= limite_fine: continue
            if corrente < limite_inizio: corrente = limite_inizio

            while corrente < limite_fine and (minuti_piazzamento_restanti + minuti_pezzi_restanti) > 0:
                # Se siamo in orario di pausa, saltiamo avanti
                if p_inizio and p_inizio <= corrente < p_fine:
                    corrente = p_fine
                    continue
                
                # Calcoliamo quanto tempo possiamo lavorare prima della pausa o della fine turno
                prossimo_stop = p_inizio if (p_inizio and corrente < p_inizio) else limite_fine
                minuti_disponibili = (prossimo_stop - corrente).total_seconds() / 60
                
                # Priorità al piazzamento, poi ai pezzi
                if minuti_piazzamento_restanti > 0:
                    lavoro = min(minuti_piazzamento_restanti, minuti_disponibili)
                    aggiungi_log("Piazzamento", lavoro)
                    minuti_piazzamento_restanti -= lavoro
                else:
                    lavoro = min(minuti_pezzi_restanti, minuti_disponibili)
                    aggiungi_log("Produzione Pezzi", lavoro)
                    minuti_pezzi_restanti -= lavoro
                
                corrente += timedelta(minutes=lavoro)
                lavorato_oggi = True
                if minuti_piazzamento_restanti + minuti_pezzi_restanti <= 0: break
            
            if minuti_piazzamento_restanti + minuti_pezzi_restanti <= 0: break
        
        if not lavorato_oggi or corrente >= limite_fine:
            corrente += timedelta(days=1)
            corrente = corrente.replace(hour=6, minute=0, second=0)

    return corrente, pd.DataFrame(log_lavoro)

# --- ESECUZIONE ---
if st.button("Calcola Pianificazione"):
    dt_inizio = datetime.combine(data_inizio, ora_inizio)
    ore_pezzi_tot = (n_pezzi * tempo_pezzo) / 60
    
    data_fine, df_log = calcola_produzione_dettagliata(dt_inizio, piazzamento_ore, ore_pezzi_tot, tipo_lavoro, turno_scelto)
    
    st.write("---")
    st.header(f"🏁 Fine stimata: {data_fine.strftime('%A %d %B - ore %H:%M')}")

    if not df_log.empty:
        # Raggruppiamo per giorno e tipo per il grafico
        df_plot = df_log.groupby(['Giorno', 'Tipo']).sum().reset_index()
        
        fig = px.bar(df_plot, x='Giorno', y='Ore', color='Tipo',
                     title="Carico di Lavoro Giornaliero",
                     color_discrete_map={'Piazzamento': '#FFA500', 'Produzione Pezzi': '#00CC96'},
                     text_auto='.1f')
        
        fig.update_layout(barmode='stack', xaxis_title="Giorno", yaxis_title="Ore Macchina")
        st.plotly_chart(fig, use_container_width=True)

    st.info(f"Lavoro totale: {piazzamento_ore}h piazzamento + {ore_pezzi_tot:.1f}h produzione.")
