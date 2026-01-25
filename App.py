import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import datetime, timedelta, time

st.set_page_config(page_title="Planning Officina Pro", layout="wide")

st.title("⚙️ Cronoprogramma Produzione Professionale")

# --- SIDEBAR: CONFIGURAZIONE TURNI E MEMORIA ---
st.sidebar.header("Configurazione Lavoro")

# 1. Bottone per il Sabato
lavora_sabato = st.sidebar.toggle("Lavora questo Sabato?", value=True)

# 2. Logica Alternanza Turni
turno_attuale = st.sidebar.selectbox(
    "Mio turno questa settimana:", 
    ["Mattina (6:00-13:50)", "Pomeriggio (13:50-21:40)"],
    help="L'app invertirà automaticamente il turno se la lavorazione finisce la settimana prossima."
)

tipo_lavoro = st.sidebar.radio(
    "Copertura Macchina:", 
    ["Solo Mio Turno (Spezzato)", "Due Turni (Continuo)"],
    help="Seleziona 'Due Turni' se un collega copre l'altro turno."
)

# --- INPUT DATI COMMESSA ---
st.write("### Inserimento Dati Lavorazione")
col1, col2, col3 = st.columns(3)

data_inizio = col1.date_input("Data Inizio", datetime.now())
# L'ora di inizio ora è libera: puoi iniziare in qualsiasi momento
ora_inizio = col2.time_input("Ora Inizio Effettiva", value=time(6, 0))
piazzamento_ore = col3.number_input("Tempo Piazzamento (ore)", value=1.0, step=0.5, min_value=0.0)

col4, col5 = st.columns(2)
n_pezzi = col4.number_input("Numero di Pezzi da produrre", value=60, min_value=1)
tempo_pezzo = col5.number_input("Tempo per singolo pezzo (minuti)", value=15.0, step=0.1, min_value=0.1)

# --- FUNZIONI DI CALCOLO ---

def get_turno_settimanale(data_rif, data_partenza, turno_partenza):
    """Calcola l'alternanza del turno basandosi sulle settimane ISO"""
    sett_inizio = data_partenza.isocalendar()[1]
    sett_corrente = data_rif.isocalendar()[1]
    # Se la differenza è dispari, il turno è invertito
    if (sett_corrente - sett_inizio) % 2 == 0:
        return turno_partenza
    else:
        return "Pomeriggio (13:50-21:40)" if turno_partenza.startswith("Mattina") else "Mattina (6:00-13:50)"

def calcola_planning(inizio_dt, ore_piaz, ore_pez):
    corrente = inizio_dt
    min_piaz, min_pez = ore_piaz * 60, ore_pez * 60
    log = []

    while (min_piaz + min_pez) > 0:
        wd = corrente.weekday()
        
        # Gestione Domenica (Chiuso)
        if wd == 6: 
            corrente += timedelta(days=1)
            corrente = corrente.replace(hour=6, minute=0)
            continue
        
        # Calcolo turno per la settimana corrente
        turno_sett = get_turno_settimanale(corrente.date(), data_inizio, turno_attuale)
        
        # Definizione orari e pause del giorno corrente
        if wd == 5: # Sabato
            if lavora_sabato:
                f_ini, f_fin = time(6, 0), time(12, 0)
                pause_giorno = []
            else:
                corrente += timedelta(days=1); corrente = corrente.replace(hour=6, minute=0); continue
        else: # Lun-Ven
            if tipo_lavoro == "Due Turni (Continuo)":
                f_ini, f_fin = time(6, 0), time(21, 40)
                pause_giorno = [(time(12, 0), time(12, 20)), (time(19, 30), time(19, 50))]
            else:
                if "Mattina" in turno_sett:
                    f_ini, f_fin = time(6, 0), time(13, 50)
                    pause_giorno = [(time(12, 0), time(12, 20))]
                else:
                    f_ini, f_fin = time(13, 50), time(21, 40)
                    pause_giorno = [(time(19, 30), time(19, 50))]

        lim_ini = corrente.replace(hour=f_ini.hour, minute=f_ini.minute, second=0)
        lim_fin = corrente.replace(hour=f_fin.hour, minute=f_fin.minute, second=0)

        # Se siamo fuori orario, saltiamo al prossimo slot utile
        if corrente >= lim_fin:
            corrente += timedelta(days=1)
            corrente = corrente.replace(hour=6, minute=0)
            continue
        if corrente < lim_ini:
            corrente = lim_ini

        while corrente < lim_fin and (min_piaz + min_pez) > 0:
            ora_dec_inizio = corrente.hour + corrente.minute / 60.0
            
            # 1. Verifica Pause
            in_pausa = False
            for p_start, p_end in pause_giorno:
                p_ini_dt = corrente.replace(hour=p_start.hour, minute=p_start.minute)
                p_fin_dt = corrente.replace(hour=p_end.hour, minute=p_end.minute)
                if p_ini_dt <= corrente < p_fin_dt:
                    durata_p = (p_fin_dt - corrente).total_seconds() / 60
                    log.append({"Giorno": corrente.strftime('%a %d/%m'), "Ora Inizio": ora_dec_inizio, 
                                "Durata": durata_p/60, "Tipo": "PAUSA", 
                                "Orario": f"{corrente.strftime('%H:%M')}-{p_end.strftime('%H:%M')}"})
                    corrente = p_fin_dt
                    in_pausa = True; break
            if in_pausa: continue
            
            # 2. Identifica prossimo ostacolo (pausa o fine turno)
            ostacoli = [lim_fin]
            for p_s, p_e in pause_giorno:
                p_dt = corrente.replace(hour=p_s.hour, minute=p_s.minute)
                if corrente < p_dt: ostacoli.append(p_dt)
            
            prossimo_stop = min(ostacoli)
            min_disp = (prossimo_stop - corrente).total_seconds() / 60
            
            # 3. Assegna lavoro (Piazzamento o Produzione)
            tipo = "PIAZZAMENTO" if min_piaz > 0 else "PRODUZIONE"
            lavoro = min(min_piaz if min_piaz > 0 else min_pez, min_disp)
            
            if tipo == "PIAZZAMENTO": min_piaz -= lavoro
            else: min_pez -= lavoro
            
            fine_blocco = corrente + timedelta(minutes=lavoro)
            log.append({"Giorno": corrente.strftime('%a %d/%m'), "Ora Inizio": ora_dec_inizio, 
                        "Durata": lavoro/60, "Tipo": tipo, "Orario": f"{corrente.strftime('%H:%M')}-{fine_blocco.strftime('%H:%M')}"})
            corrente = fine_blocco
    
    return corrente, pd.DataFrame(log)

# --- ESECUZIONE E GRAFICO ---

if st.button("Calcola Pianificazione Lavoro"):
    dt_partenza = datetime.combine(data_inizio, ora_inizio)
    minuti_totali_pezzi = n_pezzi * tempo_pezzo
    
    data_fine, df_risultati = calcola_planning(dt_partenza, piazzamento_ore, minuti_totali_pezzi / 60)
    
    st.write("---")
    st.success(f"### 🏁 Fine stimata: {data_fine.strftime('%A %d %B - ore %H:%M')}")

    if not df_risultati.empty:
        # Colori e Grafico
        colori = {'PIAZZAMENTO': '#FFA500', 'PRODUZIONE': '#00CC96', 'PAUSA': '#FF0000'}
        
        fig = px.bar(df_risultati, x="Giorno", y="Durata", base="Ora Inizio", color="Tipo",
                     title="Planning Giornaliero (Asse Y = Orario Reale)",
                     color_discrete_map=colori,
                     hover_data=["Orario"], text="Orario")

        fig.update_layout(
            yaxis=dict(title="Orario della Giornata", range=[22, 6], dtick=1, autorange=False),
            xaxis_title="Giorno",
            height=850,
            showlegend=True,
            barmode='stack'
        )
        
        fig.update_traces(marker_line_color='black', marker_line_width=1, textposition='inside')
        st.plotly_chart(fig, use_container_width=True)

    st.info(f"Riepilogo: {piazzamento_ore}h piazzamento + {minuti_totali_pezzi/60:.1f}h produzione effettiva.")
