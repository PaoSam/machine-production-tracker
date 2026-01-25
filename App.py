import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import datetime, timedelta, time

st.set_page_config(page_title="Planning Officina Pro", layout="wide")

st.title("⚙️ Cronoprogramma Giornaliero Unificato")

# --- CONFIGURAZIONE TURNI ---
st.sidebar.header("Impostazioni Turni")
tipo_lavoro = st.sidebar.radio("Copertura Macchina:", ["Due Turni (Continuo)", "Solo Mio Turno (Spezzato)"])
turno_scelto = st.sidebar.selectbox("Turno:", ["Mattina (6:00-13:50)", "Pomeriggio (13:50-21:40)"]) if "Spezzato" in tipo_lavoro else None

# --- INPUT DATI ---
col1, col2, col3 = st.columns(3)
data_inizio = col1.date_input("Data Inizio", datetime.now())
ora_inizio = col2.time_input("Ora Inizio", time(6, 0))
piazzamento_ore = col3.number_input("Tempo Piazzamento (ore)", value=1.0, step=0.5)

col4, col5 = st.columns(2)
n_pezzi = col4.number_input("Numero di Pezzi", value=60)
tempo_pezzo = col5.number_input("Tempo per Pezzo (minuti)", value=15.0, step=0.1)

def calcola_planning_unificato(inizio_dt, ore_piaz, ore_pez):
    corrente = inizio_dt
    min_piaz, min_pez = ore_piaz * 60, ore_pez * 60
    log = []

    while (min_piaz + min_pez) > 0:
        wd = corrente.weekday()
        if wd > 5: # Salta Domenica
            corrente += timedelta(days=1); corrente = corrente.replace(hour=6, minute=0); continue
        
        # Definizione Orari Turni e Pause
        if wd == 5: # Sabato
            f_ini, f_fin = time(6, 0), time(12, 0)
            pause_giorno = [] # Sabato niente pausa (o specifica se serve)
        else: # Lun-Ven
            if tipo_lavoro == "Due Turni (Continuo)":
                f_ini, f_fin = time(6, 0), time(21, 40)
                pause_giorno = [(time(12, 0), time(12, 20)), (time(19, 30), time(19, 50))]
            else:
                if "Mattina" in turno_scelto:
                    f_ini, f_fin = time(6, 0), time(13, 50)
                    pause_giorno = [(time(12, 0), time(12, 20))]
                else:
                    f_ini, f_fin = time(13, 50), time(21, 40)
                    pause_giorno = [(time(19, 30), time(19, 50))]

        lim_ini = corrente.replace(hour=f_ini.hour, minute=f_ini.minute, second=0)
        lim_fin = corrente.replace(hour=f_fin.hour, minute=f_fin.minute, second=0)

        if corrente < lim_ini: corrente = lim_ini
        if corrente >= lim_fin:
            corrente += timedelta(days=1); corrente = corrente.replace(hour=6, minute=0); continue

        while corrente < lim_fin and (min_piaz + min_pez) > 0:
            ora_decimal_inizio = corrente.hour + corrente.minute / 60.0
            
            # Controllo se siamo in una delle pause previste
            in_pausa = False
            for p_start, p_end in pause_giorno:
                p_ini_dt = corrente.replace(hour=p_start.hour, minute=p_start.minute, second=0)
                p_fin_dt = corrente.replace(hour=p_end.hour, minute=p_end.minute, second=0)
                
                if p_ini_dt <= corrente < p_fin_dt:
                    durata = (p_fin_dt - corrente).total_seconds() / 60
                    log.append({
                        "Giorno": corrente.strftime('%a %d/%m'),
                        "Ora Inizio": ora_decimal_inizio,
                        "Durata": durata / 60,
                        "Tipo": "PAUSA",
                        "Orario": f"{corrente.strftime('%H:%M')} - {p_fin_dt.strftime('%H:%M')}"
                    })
                    corrente = p_fin_dt
                    in_pausa = True
                    break
            if in_pausa: continue
            
            # Trova il prossimo evento (pausa o fine turno)
            prossimi_stop = [lim_fin]
            for p_start, p_end in pause_giorno:
                p_ini_dt = corrente.replace(hour=p_start.hour, minute=p_start.minute, second=0)
                if corrente < p_ini_dt: prossimi_stop.append(p_ini_dt)
            
            stop_reale = min(prossimi_stop)
            min_disp = (stop_reale - corrente).total_seconds() / 60
            
            if min_piaz > 0:
                lavoro = min(min_piaz, min_disp); min_piaz -= lavoro; tipo = "PIAZZAMENTO"
            else:
                lavoro = min(min_pez, min_disp); min_pez -= lavoro; tipo = "PRODUZIONE"
            
            fine_blocco = corrente + timedelta(minutes=lavoro)
            log.append({
                "Giorno": corrente.strftime('%a %d/%m'),
                "Ora Inizio": ora_decimal_inizio,
                "Durata": lavoro / 60,
                "Tipo": tipo,
                "Orario": f"{corrente.strftime('%H:%M')} - {fine_blocco.strftime('%H:%M')}"
            })
            corrente = fine_blocco
    
    return corrente, pd.DataFrame(log)

if st.button("Genera Planning Giornaliero"):
    dt_i = datetime.combine(data_inizio, ora_inizio)
    fine, df = calcola_planning_unificato(dt_i, piazzamento_ore, (n_pezzi*tempo_pezzo)/60)
    
    st.success(f"### 🏁 Fine stimata: {fine.strftime('%d/%m/%Y ore %H:%M')}")

    if not df.empty:
        # Colonna unica: usiamo barmode='relative' o 'stack' con lo stesso asse X
        fig = px.bar(df, 
                     x="Giorno", 
                     y="Durata", 
                     base="Ora Inizio", 
                     color="Tipo",
                     color_discrete_map={'PIAZZAMENTO': '#FFA500', 'PRODUZIONE': '#00CC96', 'PAUSA': '#FF0000'},
                     hover_data=["Orario"],
                     text="Orario")

        fig.update_layout(
            yaxis=dict(
                title="Orario (6:00 - 21:40)",
                tickmode='linear',
                tick0=6,
                dtick=1,
                range=[22, 6], # Mattina in alto, sera in basso
                autorange=False
            ),
            xaxis_title="Giorno",
            height=800,
            showlegend=True
        )
        
        fig.update_traces(marker_line_color='black', marker_line_width=1, textposition='inside')
        st.plotly_chart(fig, use_container_width=True)
