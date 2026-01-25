import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import datetime, timedelta, time

st.set_page_config(page_title="Planning Officina Pro", layout="wide")

st.title("⚙️ Cronoprogramma con Alternanza Turni")

# --- MEMORIA TURNI E IMPOSTAZIONI ---
st.sidebar.header("Configurazione Lavoro")

# 1. Bottone per il Sabato
lavora_sabato = st.sidebar.toggle("Lavora questo Sabato?", value=True)

# 2. Logica Alternanza Turni
# Selezionando il turno di questa settimana, l'app calcolerà automaticamente 
# l'inversione se la lavorazione scavalca la domenica.
turno_attuale = st.sidebar.selectbox(
    "Turno di questa settimana:", 
    ["Mattina (6:00-13:50)", "Pomeriggio (13:50-21:40)"]
)

tipo_lavoro = st.sidebar.radio("Copertura Macchina:", ["Due Turni (Continuo)", "Solo Mio Turno (Spezzato)"])

# --- INPUT DATI ---
col1, col2, col3 = st.columns(3)
data_inizio = col1.date_input("Data Inizio", datetime.now())
ora_inizio = col2.time_input("Ora Inizio", time(6, 0))
piazzamento_ore = col3.number_input("Tempo Piazzamento (ore)", value=1.0, step=0.5)

col4, col5 = st.columns(2)
n_pezzi = col4.number_input("Numero di Pezzi", value=60)
tempo_pezzo = col5.number_input("Tempo per Pezzo (minuti)", value=15.0, step=0.1)

def get_turno_settimanale(data_rif, turno_partenza):
    """Calcola il turno corretto in base alla settimana (alternanza)"""
    settimana_inizio = data_inizio.isocalendar()[1]
    settimana_corrente = data_rif.isocalendar()[1]
    
    # Se la differenza delle settimane è dispari, il turno è invertito
    if (settimana_corrente - settimana_inizio) % 2 == 0:
        return turno_partenza
    else:
        return "Pomeriggio (13:50-21:40)" if turno_partenza.startswith("Mattina") else "Mattina (6:00-13:50)"

def calcola_planning_dinamico(inizio_dt, ore_piaz, ore_pez):
    corrente = inizio_dt
    min_piaz, min_pez = ore_piaz * 60, ore_pez * 60
    log = []

    while (min_piaz + min_pez) > 0:
        wd = corrente.weekday()
        
        # Gestione Domenica (Salto e cambio turno teorico)
        if wd == 6: 
            corrente += timedelta(days=1)
            corrente = corrente.replace(hour=6, minute=0)
            continue
        
        # Determina il turno per la settimana della data 'corrente'
        turno_sett = get_turno_settimanale(corrente, turno_attuale)
        
        # Definizione Orari Turni e Pause
        if wd == 5: # Sabato
            if lavora_sabato:
                f_ini, f_fin = time(6, 0), time(12, 0)
                pause_giorno = []
            else:
                corrente += timedelta(days=1)
                continue
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

        if corrente < lim_ini: corrente = lim_ini
        if corrente >= lim_fin:
            corrente += timedelta(days=1)
            corrente = corrente.replace(hour=6, minute=0)
            continue

        while corrente < lim_fin and (min_piaz + min_pez) > 0:
            ora_decimal_inizio = corrente.hour + corrente.minute / 60.0
            
            # Controllo Pause
            in_pausa = False
            for p_start, p_end in pause_giorno:
                p_ini_dt = corrente.replace(hour=p_start.hour, minute=p_start.minute)
                p_fin_dt = corrente.replace(hour=p_end.hour, minute=p_end.minute)
                if p_ini_dt <= corrente < p_fin_dt:
                    log.append({"Giorno": corrente.strftime('%a %d/%m'), "Ora Inizio": ora_decimal_inizio, 
                                "Durata": (p_fin_dt - corrente).total_seconds()/3600, "Tipo": "PAUSA", 
                                "Orario": f"{corrente.strftime('%H:%M')}-{p_end.strftime('%H:%M')}"})
                    corrente = p_fin_dt
                    in_pausa = True; break
            if in_pausa: continue
            
            stop_reale = min([lim_fin] + [corrente.replace(hour=p[0].hour, minute=p[0].minute) for p in pause_giorno if corrente < corrente.replace(hour=p[0].hour, minute=p[0].minute)])
            min_disp = (stop_reale - corrente).total_seconds() / 60
            
            tipo = "PIAZZAMENTO" if min_piaz > 0 else "PRODUZIONE"
            lavoro = min(min_piaz if min_piaz > 0 else min_pez, min_disp)
            
            if tipo == "PIAZZAMENTO": min_piaz -= lavoro
            else: min_pez -= lavoro
            
            fine_blocco = corrente + timedelta(minutes=lavoro)
            log.append({"Giorno": corrente.strftime('%a %d/%m'), "Ora Inizio": ora_decimal_inizio, 
                        "Durata": lavoro/60, "Tipo": tipo, "Orario": f"{corrente.strftime('%H:%M')}-{fine_blocco.strftime('%H:%M')}"})
            corrente = fine_blocco
    
    return corrente, pd.DataFrame(log)

if st.button("Calcola Pianificazione"):
    dt_i = datetime.combine(data_inizio, ora_inizio)
    fine, df = calcola_planning_dinamico(dt_i, piazzamento_ore, (n_pezzi*tempo_pezzo)/60)
    
    st.success(f"### 🏁 Fine stimata: {fine.strftime('%A %d %B - ore %H:%M')}")
    if (fine.isocalendar()[1] > data_inizio.isocalendar()[1]):
        st.warning(f"Nota: La lavorazione finisce la settimana prossima, quindi il turno è stato invertito in: {get_turno_settimanale(fine, turno_attuale)}")

    if not df.empty:
        fig = px.bar(df, x="Giorno", y="Durata", base="Ora Inizio", color="Tipo",
                     color_discrete_map={'PIAZZAMENTO': '#FFA500', 'PRODUZIONE': '#00CC96', 'PAUSA': '#FF0000'},
                     hover_data=["Orario"], text="Orario")
        fig.update_layout(yaxis=dict(title="Orario", range=[22, 6], autorange=False), height=800)
        st.plotly_chart(fig, use_container_width=True)
