import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import datetime, timedelta, time

st.set_page_config(page_title="Pianificatore Produzione Pro", layout="wide")

st.title("⚙️ Machine Utensili: Calcolo Fine e Dettaglio Pause")

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
def calcola_produzione_completa(inizio_dt, ore_piazzamento, ore_pezzi, modalita, turno_sp):
    corrente = inizio_dt
    min_piazzamento = ore_piazzamento * 60
    min_pezzi = ore_pezzi * 60
    log_lavoro = []

    def aggiungi_log(tipo, durata_min):
        if durata_min > 0:
            giorno_str = corrente.strftime('%A %d/%m')
            log_lavoro.append({"Giorno": giorno_str, "Ore": round(durata_min / 60, 2), "Tipo": tipo})

    while (min_piazzamento + min_pezzi) > 0:
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
            
            p_inizio, p_fine = None, None
            if f_inizio == time(6, 0): # Mattina
                p_inizio, p_fine = limite_inizio.replace(hour=12, minute=0), limite_inizio.replace(hour=12, minute=20)
            elif f_inizio == time(13, 50): # Pomeriggio
                p_inizio, p_fine = limite_inizio.replace(hour=19, minute=30), limite_inizio.replace(hour=19, minute=50)

            if corrente >= limite_fine: continue
            if corrente < limite_inizio: corrente = limite_inizio

            while corrente < limite_fine and (min_piazzamento + min_pezzi) > 0:
                # GESTIONE PAUSA (Se il tempo corrente entra in pausa)
                if p_inizio and p_inizio <= corrente < p_fine:
                    durata_pausa = (p_fine - corrente).total_seconds() / 60
                    aggiungi_log("PAUSA", durata_pausa)
                    corrente = p_fine
                    continue
                
                prossimo_stop = p_inizio if (p_inizio and corrente < p_inizio) else limite_fine
                min_disponibili = (prossimo_stop - corrente).total_seconds() / 60
                
                if min_piazzamento > 0:
                    lavoro = min(min_piazzamento, min_disponibili)
                    aggiungi_log("PIAZZAMENTO", lavoro)
                    min_piazzamento -= lavoro
                else:
                    lavoro = min(min_pezzi, min_disponibili)
                    aggiungi_log("PRODUZIONE", lavoro)
                    min_pezzi -= lavoro
                
                corrente += timedelta(minutes=lavoro)
                lavorato_oggi = True
                if (min_piazzamento + min_pezzi) <= 0: break
            
            if (min_piazzamento + min_pezzi) <= 0: break
        
        if not lavorato_oggi or corrente >= limite_fine:
            corrente += timedelta(days=1)
            corrente = corrente.replace(hour=6, minute=0, second=0)

    return corrente, pd.DataFrame(log_lavoro)

# --- ESECUZIONE ---
if st.button("Calcola e Mostra Grafico"):
    dt_inizio = datetime.combine(data_inizio, ora_inizio)
    ore_pezzi_tot = (n_pezzi * tempo_pezzo) / 60
    
    data_fine, df_log = calcola_produzione_completa(dt_inizio, piazzamento_ore, ore_pezzi_tot, tipo_lavoro, turno_scelto)
    
    st.write("---")
    st.header(f"🏁 Consegna: {data_fine.strftime('%A %d %B - ore %H:%M')}")

    if not df_log.empty:
        # Mappa colori molto accesi per distinguere
        colori = {
            'PIAZZAMENTO': '#FFA500',   # Arancio
            'PRODUZIONE': '#00CC96',    # Verde
            'PAUSA': '#FF0000'          # ROSSO ACCESO
        }
        
        fig = px.bar(df_log, x='Giorno', y='Ore', color='Tipo',
                     title="Analisi Giornaliera: Lavoro vs Pause",
                     color_discrete_map=colori,
                     hover_data={'Ore': True, 'Tipo': True})
        
        # Miglioramento bordi per vedere le sezioni piccole
        fig.update_traces(marker_line_color='black', marker_line_width=1)
        fig.update_layout(barmode='stack', yaxis_title="Ore Totali")
        
        st.plotly_chart(fig, use_container_width=True)

    st.info(f"Riepilogo: {piazzamento_ore}h setup + {ore_pezzi_tot:.1f}h lavoro effettivo.")
