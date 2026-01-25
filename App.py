import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import datetime, timedelta, time

st.set_page_config(page_title="Pianificatore Produzione Real-Time", layout="wide")

st.title("⚙️ Timeline Produzione con Orari Esatti")

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

# --- LOGICA DI CALCOLO TIMELINE ---
def calcola_timeline_precisa(inizio_dt, ore_piazzamento, ore_pezzi, modalita, turno_sp):
    corrente = inizio_dt
    min_piazzamento = ore_piazzamento * 60
    min_pezzi = ore_pezzi * 60
    dati_timeline = []

    def aggiungi_evento(tipo, inizio, fine):
        dati_timeline.append(dict(Task=tipo, Start=inizio, Finish=fine, Resource=tipo))

    while (min_piazzamento + min_pezzi) > 0:
        wd = corrente.weekday()
        if wd < 5: # Lun-Ven
            finestre = [(time(6, 0), time(13, 50)), (time(13, 50), time(21, 40))] if modalita == "Due Turni (Continuo)" else \
                       ([(time(6, 0), time(13, 50))] if "Mattina" in turno_sp else [(time(13, 50), time(21, 40))])
        elif wd == 5: # Sabato
            finestre = [(time(6, 0), time(12, 0))]
        else: # Domenica
            corrente += timedelta(days=1); corrente = corrente.replace(hour=6, minute=0); continue

        lavorato_oggi = False
        for f_ini, f_fin in finestre:
            lim_ini = corrente.replace(hour=f_ini.hour, minute=f_ini.minute, second=0)
            lim_fin = corrente.replace(hour=f_fin.hour, minute=f_fin.minute, second=0)
            
            p_ini, p_fin = (lim_ini.replace(hour=12, minute=0), lim_ini.replace(hour=12, minute=20)) if f_ini == time(6, 0) else \
                           (lim_ini.replace(hour=19, minute=30), lim_ini.replace(hour=19, minute=50)) if f_ini == time(13, 50) else (None, None)

            if corrente >= lim_fin: continue
            if corrente < lim_ini: corrente = lim_ini

            while corrente < lim_fin and (min_piazzamento + min_pezzi) > 0:
                # GESTIONE PAUSA
                if p_ini and p_ini <= corrente < p_fin:
                    aggiungi_evento("PAUSA", corrente, p_fin)
                    corrente = p_fin
                    continue
                
                prossimo_stop = p_ini if (p_ini and corrente < p_ini) else lim_fin
                min_disp = (prossimo_stop - corrente).total_seconds() / 60
                
                start_task = corrente
                if min_piazzamento > 0:
                    lavoro = min(min_piazzamento, min_disp)
                    min_piazzamento -= lavoro
                    tipo_task = "PIAZZAMENTO"
                else:
                    lavoro = min(min_pezzi, min_disp)
                    min_pezzi -= lavoro
                    tipo_task = "PRODUZIONE"
                
                corrente += timedelta(minutes=lavoro)
                aggiungi_evento(tipo_task, start_task, corrente)
                lavorato_oggi = True
                if (min_piazzamento + min_pezzi) <= 0: break
        
        if not lavorato_oggi or (min_piazzamento + min_pezzi) > 0:
            if corrente >= lim_fin:
                corrente += timedelta(days=1)
                corrente = corrente.replace(hour=6, minute=0)

    return corrente, pd.DataFrame(dati_timeline)

# --- ESECUZIONE E GRAFICO ---
if st.button("Genera Timeline Dettagliata"):
    dt_ini = datetime.combine(data_inizio, ora_inizio)
    ore_pezzi_tot = (n_pezzi * tempo_pezzo) / 60
    
    data_fine, df_ev = calcola_timeline_precisa(dt_ini, piazzamento_ore, ore_pezzi_tot, tipo_lavoro, turno_scelto)
    
    st.write("---")
    st.subheader(f"🏁 Fine Lavorazione stimata: {data_fine.strftime('%d/%m/%Y alle ore %H:%M')}")

    if not df_ev.empty:
        # Colori specifici
        colori = {'PIAZZAMENTO': '#FFA500', 'PRODUZIONE': '#00CC96', 'PAUSA': '#FF0000'}
        
        # Creazione grafico Timeline (Gantt)
        fig = px.timeline(df_ev, x_start="Start", x_end="Finish", y="Resource", color="Resource",
                          title="Cronoprogramma Lavoro (Timeline Oraria)",
                          color_discrete_map=colori,
                          category_orders={"Resource": ["PIAZZAMENTO", "PRODUZIONE", "PAUSA"]})
        
        fig.update_yaxes(autorange="reversed") # Per avere piazzamento in alto
        fig.update_layout(xaxis_title="Orario e Giorno", yaxis_title="", showlegend=True)
        
        st.plotly_chart(fig, use_container_width=True)

    st.info(f"Riepilogo: {piazzamento_ore}h setup + {ore_pezzi_tot:.1f}h produzione.")
