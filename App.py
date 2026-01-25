import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import datetime, timedelta, time

st.set_page_config(page_title="Planning Officina", layout="wide")

st.title("⚙️ Cronoprogramma Orario Verticale")

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

def calcola_planning_verticale(inizio_dt, ore_piaz, ore_pez):
    corrente = inizio_dt
    min_piaz, min_pez = ore_piaz * 60, ore_pez * 60
    log = []

    while (min_piaz + min_pez) > 0:
        wd = corrente.weekday()
        if wd > 5: # Salta Domenica
            corrente += timedelta(days=1); corrente = corrente.replace(hour=6, minute=0); continue
        
        # Orari limite del giorno
        if wd == 5: # Sabato
            f_ini, f_fin = time(6, 0), time(12, 0)
        else: # Lun-Ven
            if tipo_lavoro == "Due Turni (Continuo)":
                f_ini, f_fin = time(6, 0), time(21, 40)
            else:
                f_ini, f_fin = (time(6, 0), time(13, 50)) if "Mattina" in turno_scelto else (time(13, 50), time(21, 40))

        lim_ini = corrente.replace(hour=f_ini.hour, minute=f_ini.minute, second=0)
        lim_fin = corrente.replace(hour=f_fin.hour, minute=f_fin.minute, second=0)
        
        # Definizione Pause
        p_ini, p_fin = None, None
        if f_ini == time(6, 0): p_ini, p_fin = lim_ini.replace(hour=12, minute=0), lim_ini.replace(hour=12, minute=20)
        elif f_ini == time(13, 50) or (tipo_lavoro == "Due Turni (Continuo)" and corrente >= lim_ini.replace(hour=13, minute=50)):
            p_ini, p_fin = lim_ini.replace(hour=19, minute=30), lim_ini.replace(hour=19, minute=50)

        if corrente < lim_ini: corrente = lim_ini
        if corrente >= lim_fin:
            corrente += timedelta(days=1); corrente = corrente.replace(hour=6, minute=0); continue

        while corrente < lim_fin and (min_piaz + min_pez) > 0:
            # Orario in formato decimale per il grafico (es. 12:30 -> 12.5)
            ora_decimal_inizio = corrente.hour + corrente.minute / 60.0
            
            # Gestione Pausa
            if p_ini and p_ini <= corrente < p_fin:
                durata = (p_fin - corrente).total_seconds() / 60
                log.append({
                    "Giorno": corrente.strftime('%a %d/%m'),
                    "Ora Inizio": ora_decimal_inizio,
                    "Durata": durata / 60,
                    "Tipo": "PAUSA",
                    "Orario": f"{corrente.strftime('%H:%M')} - {p_fin.strftime('%H:%M')}"
                })
                corrente = p_fin; continue
            
            # Calcolo prossimo blocco
            stop = p_ini if (p_ini and corrente < p_ini) else lim_fin
            min_disp = (stop - corrente).total_seconds() / 60
            
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

if st.button("Genera Planning Orario"):
    dt_i = datetime.combine(data_inizio, ora_inizio)
    fine, df = calcola_planning_verticale(dt_i, piazzamento_ore, (n_pezzi*tempo_pezzo)/60)
    
    st.success(f"### 🏁 Fine stimata: {fine.strftime('%d/%m/%Y ore %H:%M')}")

    if not df.empty:
        # Usiamo un grafico a barre dove 'base' indica l'orario di partenza
        fig = px.bar(df, 
                     x="Giorno", 
                     y="Durata", 
                     base="Ora Inizio", 
                     color="Tipo",
                     color_discrete_map={'PIAZZAMENTO': '#FFA500', 'PRODUZIONE': '#00CC96', 'PAUSA': '#FF0000'},
                     hover_data=["Orario"],
                     text="Orario")

        fig.update_layout(
            title="Svolgimento Giornaliero (Asse Y = Orario Reale)",
            yaxis=dict(
                title="Orario della Giornata",
                tickmode='linear',
                tick0=6,
                dtick=1, # Un segno ogni ora
                range=[22, 6], # Invertito per avere la mattina in alto (o viceversa)
                autorange=False
            ),
            xaxis_title="Giorno",
            barmode='group', # Mantiene i blocchi allineati correttamente sul 'base'
            height=800
        )
        
        # Miglioramento visivo barre
        fig.update_traces(marker_line_color='black', marker_line_width=1, textposition='inside')
        
        st.plotly_chart(fig, use_container_width=True)

    st.info("L'asse Y rappresenta l'orario solare. Le ore notturne (21:40 - 06:00) sono escluse dal grafico.")
