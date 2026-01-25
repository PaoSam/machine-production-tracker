import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import datetime, timedelta, time

st.set_page_config(page_title="Planning Officina - FIX", layout="wide")

st.title("⚙️ Cronoprogramma Produzione Professionale")

# --- SIDEBAR ---
st.sidebar.header("Configurazione Lavoro")
lavora_sabato = st.sidebar.toggle("Lavora questo Sabato?", value=True)

turno_attuale = st.sidebar.selectbox(
    "Mio turno QUESTA SETTIMANA:",
    ["Mattina (6:00-13:50)", "Pomeriggio (13:50-21:40)"]
)

tipo_lavoro = st.sidebar.radio(
    "Copertura Macchina:",
    ["Solo Mio Turno (Spezzato)", "Due Turni (Continuo)"]
)

# --- INPUT ---
col1, col2, col3 = st.columns(3)
data_inizio_val = col1.date_input("Data Inizio", datetime.now())
ora_inizio_val = col2.time_input("Ora Inizio Effettiva", value=time(7, 0))
piazzamento_ore = col3.number_input("Tempo Piazzamento (ore)", value=1.0, step=0.5)

col4, col5 = st.columns(2)
n_pezzi = col4.number_input("Numero di Pezzi", value=60)
tempo_pezzo = col5.number_input("Tempo per Pezzo (minuti)", value=15.0, step=0.1)

# --- LOGICA DI CALCOLO ---
def calcola_planning_fix(data_start, ora_start, piaz_h, prod_h):
    corrente = datetime.combine(data_start, ora_start)
    min_restanti_piaz = piaz_h * 60
    min_restanti_prod = prod_h * 60
    log = []

    inizio_sett_zero = data_start - timedelta(days=data_start.weekday())

    while (min_restanti_piaz + min_restanti_prod) > 0:
        wd = corrente.weekday()

        if wd == 6:  # Domenica
            corrente += timedelta(days=1)
            corrente = corrente.replace(hour=6, minute=0)
            continue

        settimane_trascorse = (corrente.date() - inizio_sett_zero).days // 7
        if settimane_trascorse % 2 == 0:
            turno_sett = turno_attuale
        else:
            turno_sett = (
                "Pomeriggio (13:50-21:40)"
                if turno_attuale.startswith("Mattina")
                else "Mattina (6:00-13:50)"
            )

        if wd == 5:  # Sabato
            if lavora_sabato:
                fasce, pause = [(time(6, 0), time(12, 0))], []
            else:
                corrente += timedelta(days=1)
                corrente = corrente.replace(hour=6, minute=0)
                continue
        else:
            if tipo_lavoro == "Due Turni (Continuo)":
                fasce = [(time(6, 0), time(21, 40))]
                pause = [(time(12, 0), time(12, 20)), (time(19, 30), time(19, 50))]
            else:
                if "Mattina" in turno_sett:
                    fasce = [(time(6, 0), time(13, 50))]
                    pause = [(time(12, 0), time(12, 20))]
                else:
                    fasce = [(time(13, 50), time(21, 40))]
                    pause = [(time(19, 30), time(19, 50))]

        lavorato_oggi = False

        for f_ini, f_fin in fasce:
            lim_ini = corrente.replace(hour=f_ini.hour, minute=f_ini.minute, second=0)
            lim_fin = corrente.replace(hour=f_fin.hour, minute=f_fin.minute, second=0)

            if corrente >= lim_fin:
                continue
            if corrente < lim_ini:
                corrente = lim_ini

            while corrente < lim_fin and (min_restanti_piaz + min_restanti_prod) > 0:
                pausa_attiva = None
                for p_s, p_e in pause:
                    p_s_dt = corrente.replace(hour=p_s.hour, minute=p_s.minute)
                    p_e_dt = corrente.replace(hour=p_e.hour, minute=p_e.minute)
                    if p_s_dt <= corrente < p_e_dt:
                        pausa_attiva = (p_s_dt, p_e_dt)
                        break

                ora_inizio_dec = corrente.hour + corrente.minute / 60

                if pausa_attiva:
                    durata_p = (pausa_attiva[1] - corrente).total_seconds() / 3600
                    log.append({
                        "Giorno": corrente.strftime('%a %d/%m'),
                        "Inizio": ora_inizio_dec,
                        "Durata": durata_p,
                        "Tipo": "PAUSA",
                        "Label": f"{corrente.strftime('%H:%M')}-{pausa_attiva[1].strftime('%H:%M')}"
                    })
                    corrente = pausa_attiva[1]
                    lavorato_oggi = True
                    continue

                ostacoli = [lim_fin] + [
                    corrente.replace(hour=p[0].hour, minute=p[0].minute)
                    for p in pause
                    if corrente < corrente.replace(hour=p[0].hour, minute=p[0].minute)
                ]

                fine_massima = min(ostacoli)
                min_disp = (fine_massima - corrente).total_seconds() / 60

                tipo = "PIAZZAMENTO" if min_restanti_piaz > 0 else "PRODUZIONE"
                min_da_fare = min(
                    min_restanti_piaz if min_restanti_piaz > 0 else min_restanti_prod,
                    min_disp
                )

                if tipo == "PIAZZAMENTO":
                    min_restanti_piaz -= min_da_fare
                else:
                    min_restanti_prod -= min_da_fare

                fine_eff = corrente + timedelta(minutes=min_da_fare)
                log.append({
                    "Giorno": corrente.strftime('%a %d/%m'),
                    "Inizio": ora_inizio_dec,
                    "Durata": min_da_fare / 60,
                    "Tipo": tipo,
                    "Label": f"{corrente.strftime('%H:%M')}-{fine_eff.strftime('%H:%M')}"
                })

                corrente = fine_eff
                lavorato_oggi = True

        if not lavorato_oggi:
            corrente += timedelta(days=1)
            corrente = corrente.replace(hour=6, minute=0)

    return corrente, pd.DataFrame(log)

# --- RENDERING ---
if st.button("CALCOLA PLANNING"):
    fine_lavoro, df = calcola_planning_fix(
        data_inizio_val,
        ora_inizio_val,
        piazzamento_ore,
        (n_pezzi * tempo_pezzo) / 60
    )

    st.success(
        f"### 🏁 Fine Lavorazione stimata: "
        f"{fine_lavoro.strftime('%A %d %B - ore %H:%M')}"
    )

    if not df.empty:
        giorni_unici = df["Giorno"].unique()

        fig = px.bar(
            df,
            x="Giorno",
            y="Durata",
            base="Inizio",
            color="Tipo",
            text="Label",
            hover_data=["Label"],
            category_orders={"Giorno": giorni_unici},
            color_discrete_map={
                "PIAZZAMENTO": "#FFA500",
                "PRODUZIONE": "#00CC96",
                "PAUSA": "#FF0000"
            }
        )

        fig.update_layout(
            xaxis=dict(title="Giorno di Lavoro"),
            yaxis=dict(
                title="ORARIO REALE",
                autorange="reversed",  # 🔧 FIX DEFINITIVO
                dtick=1
            ),
            height=800,
            barmode="overlay"
        )

        fig.update_traces(
            marker_line_color="black",
            marker_line_width=1,
            textposition="inside"
        )

        st.plotly_chart(fig, use_container_width=True)
