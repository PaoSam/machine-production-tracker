import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import datetime, timedelta, time

st.set_page_config(page_title="Pianificatore Officina", layout="wide")

st.title("⚙️ Cronoprogramma Produzione (Asse Orario Y)")

# --- CONFIGURAZIONE ---
st.sidebar.header("Impostazioni Turni")
tipo_lavoro = st.sidebar.radio("Copertura Macchina:", ["Due Turni (Continuo)", "Solo Mio Turno (Spezzato)"])
turno_scelto = st.sidebar.selectbox("Turno:", ["Mattina (6:00-13:50)", "Pomeriggio (13:50-21:40)"]) if "Spezzato" in tipo_lavoro else None

# --- INPUT ---
col1, col2, col3 = st.columns(3)
data_inizio = col1.date_input("Data Inizio", datetime.now())
ora_inizio = col2.time_input("Ora Inizio", time(6, 0))
piazzamento_ore = col3.number_input("Tempo Piazzamento (ore)", value=1.0, step=0.5)

col4, col5 = st.columns(2)
n_pezzi = col4.number_input("Numero di Pezzi", value=60)
tempo_pezzo = col5.number_input("Tempo per Pezzo (minuti)", value=15.0, step=0.1)

def calcola_log_preciso(inizio_dt, ore_piaz, ore_pez):
    corrente = inizio_dt
    min_piaz, min_pez = ore_piaz * 60, ore_pez * 60
    log = []

    while (min_piaz + min_pez) > 0:
        wd = corrente.weekday()
        if wd > 5: # Domenica
            corrente += timedelta(days=1); corrente = corrente.replace(hour=6, minute=0); continue
        
        # Orari limite
        if wd == 5: # Sabato
            f_ini, f_fin = time(6, 0), time(12, 0)
        else: # Lun-Ven
            if tipo_lavoro == "Due Turni (Continuo)":
                f_ini, f_fin = time(6, 0), time(21, 40)
            else:
                f_ini, f_fin = (time(6, 0), time(13, 50)) if "Mattina" in turno_scelto else (time(13, 50), time(21, 40))

        lim_ini = corrente.replace(hour=f_ini.hour, minute=f_ini.minute, second=0)
        lim_fin = corrente.replace(hour=f_fin.hour, minute=f_fin.minute, second=0)
        
        # Pausa
        p_ini, p_fin = None, None
        if f_ini == time(6, 0): p_ini, p_fin = lim_ini.replace(hour=12, minute=0), lim_ini.replace(hour=12, minute=20)
        elif f_ini == time(13, 50): p_ini, p_fin = lim_ini.replace(hour=19, minute=30), lim_ini.replace(hour=19, minute=50)

        if corrente < lim_ini: corrente = lim_ini
        if corrente >= lim_fin:
            corrente += timedelta(days=1); corrente = corrente.replace(hour=6, minute=0); continue

        while corrente < lim_fin and (min_piaz + min_pez) > 0:
            if p_ini and p_ini <= corrente < p_fin:
                durata = (p_fin - corrente).total_seconds() / 60
                log.append({"Giorno": corrente.strftime('%a %d/%m'), "Inizio": corrente.strftime('%H:%M'), "Ore": durata/60, "Tipo": "PAUSA"})
                corrente = p_fin; continue
            
            stop = p_ini if (p_ini and corrente < p_ini) else lim_fin
            disp = (stop - corrente).total_seconds() / 60
            
            if min_piaz > 0:
                lavoro = min(min_piaz, disp); min_piaz -= lavoro; tipo = "PIAZZAMENTO"
            else:
                lavoro = min(min_pez, disp); min_pez -= lavoro; tipo = "PRODUZIONE"
            
            log.append({"Giorno": corrente.strftime('%a %d/%m'), "Inizio": corrente.strftime('%H:%M'), "Ore": lavoro/60, "Tipo": tipo})
            corrente += timedelta(minutes=lavoro)
    
    return corrente, pd.DataFrame(log)

if st.button("Calcola e Mostra Grafico Verticale"):
    dt_i = datetime.combine(data_inizio, ora_inizio)
    fine, df = calcola_log_preciso(dt_i, piazzamento_ore, (n_pezzi*tempo_pezzo)/60)
    
    st.success(f"### 🏁 Consegna: {fine.strftime('%d/%m/%Y alle %H:%M')}")

    if not df.empty:
        # Creiamo il grafico con i giorni sulle X e le ORE sulle Y
        fig = px.bar(df, x="Giorno", y="Ore", color="Tipo",
                     title="Occupazione Macchina per Fascia Oraria",
                     color_discrete_map={'PIAZZAMENTO': '#FFA500', 'PRODUZIONE': '#00CC96', 'PAUSA': '#FF0000'},
                     hover_data=["Inizio"], text="Inizio")

        # Impostiamo l'asse Y per riflettere la durata del turno
        fig.update_layout(
            barmode='stack',
            yaxis=dict(title="Ore di Lavoro (Cumulate nel turno)", range=[0, 16]),
            xaxis_title="Giorni Lavorativi",
            height=600
        )
        # Nascondiamo le ore notturne semplicemente non includendole nel calcolo del dataframe
        st.plotly_chart(fig, use_container_width=True)

    st.info("Nota: Il grafico mostra le ore lavorate divise per tipologia. Le ore di chiusura aziendale sono rimosse automaticamente.")
