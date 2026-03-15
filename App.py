import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import datetime, timedelta, time

# Festivi italiani
try:
    import holidays
    it_holidays = holidays.Italy()
except:
    it_holidays = []

st.set_page_config(page_title="CronoCNC", layout="wide")
st.title("⚙️ CronoCNC - Pianificazione Produzione")

# ---------------- SIDEBAR ----------------
st.sidebar.header("Configurazione")
lavora_sabato = st.sidebar.toggle("Lavora Sabato", True)
turno_iniziale = st.sidebar.selectbox(
    "Turno iniziale settimana",
    ["Mattina", "Pomeriggio"]
)
tipo_lavoro = st.sidebar.radio(
    "Copertura macchina",
    ["Turno unico", "Due Turni (Continuo)"]
)

# ---------------- INPUT ----------------
st.header("Dati lavorazione")
c1, c2, c3 = st.columns(3)
data_inizio = c1.date_input("Data inizio", datetime.now())
ora_inizio = c2.time_input(
    "Ora inizio", 
    value=time(8, 0),
    step=timedelta(minutes=5)
)
piazzamento_ore = c3.number_input("Piazzamento ore", value=1.0)
c4, c5 = st.columns(2)
n_pezzi = c4.number_input("Numero pezzi", value=100)
tempo_pezzo = c5.number_input("Tempo pezzo (minuti)", value=15)

# ---------------- CALCOLO ESATTO (con Start e End reali) ----------------
def calcola():
    minuti_piazzamento = piazzamento_ore * 60
    pezzi_restanti = n_pezzi
    tempo_residuo_pezzo = tempo_pezzo
    corrente = datetime.combine(data_inizio, ora_inizio)
    settimana_iniziale = data_inizio.isocalendar()[1]
    log = []

    while minuti_piazzamento > 0 or pezzi_restanti > 0:
        wd = corrente.weekday()

        # Festivi / Domenica
        if wd == 6 or corrente.date() in it_holidays:
            corrente += timedelta(days=1)
            corrente = corrente.replace(hour=6, minute=0, second=0, microsecond=0)
            continue

        settimana_corrente = corrente.isocalendar()[1]
        turno = turno_iniziale
        if (settimana_corrente - settimana_iniziale) % 2 != 0:
            turno = "Pomeriggio" if turno_iniziale == "Mattina" else "Mattina"

        # Definizione turno e pause
        if wd == 5:  # Sabato
            if not lavora_sabato:
                corrente += timedelta(days=1)
                corrente = corrente.replace(hour=6, minute=0, second=0, microsecond=0)
                continue
            inizio = time(6, 0)
            fine = time(12, 0)
            pause = []
        else:
            if tipo_lavoro == "Due Turni (Continuo)":
                inizio = time(6, 0)
                fine = time(21, 40)
                pause = [
                    (time(12, 0), time(12, 20)),
                    (time(19, 30), time(19, 50))
                ]
            else:
                if turno == "Mattina":
                    inizio = time(6, 0)
                    fine = time(13, 50)
                    pause = [(time(12, 0), time(12, 20))]
                else:
                    inizio = time(13, 50)
                    fine = time(21, 40)
                    pause = [(time(19, 30), time(19, 50))]

        # Fuori orario di lavoro?
        if corrente.time() >= fine:
            corrente += timedelta(days=1)
            corrente = corrente.replace(hour=6, minute=0, second=0, microsecond=0)
            continue

        # Dentro una pausa? → la registriamo con orario reale
        in_pausa = False
        pausa_end = None
        for p1, p2 in pause:
            if p1 <= corrente.time() < p2:
                in_pausa = True
                pausa_end = p2
                break
        if in_pausa:
            start = corrente
            pausa_end_dt = datetime.combine(corrente.date(), pausa_end)
            pausa_min = (pausa_end_dt - corrente).total_seconds() / 60.0
            log.append({
                "Data": corrente.date(),
                "Start": start,
                "End": pausa_end_dt,
                "Tipo": "PAUSA",
                "Minuti": pausa_min,
                "Pezzi": 0
            })
            corrente = pausa_end_dt
            continue

        # Prima dell'inizio turno?
        if corrente.time() < inizio:
            corrente = datetime.combine(corrente.date(), inizio)
            continue

        # Calcolo tempo disponibile fino al prossimo evento
        next_event = datetime.combine(corrente.date(), fine)
        for p1, p2 in pause:
            if corrente.time() < p1:
                pause_start_dt = datetime.combine(corrente.date(), p1)
                if pause_start_dt < next_event:
                    next_event = pause_start_dt
                break

        delta_min = (next_event - corrente).total_seconds() / 60.0

        # Piazzamento
        if minuti_piazzamento > 0:
            start = corrente
            work = min(minuti_piazzamento, delta_min)
            end = corrente + timedelta(minutes=work)
            log.append({
                "Data": corrente.date(),
                "Start": start,
                "End": end,
                "Tipo": "PIAZZAMENTO",
                "Minuti": work,
                "Pezzi": 0
            })
            minuti_piazzamento -= work
            corrente = end
            continue

        # Produzione
        if pezzi_restanti <= 0:
            break

        remaining_prod = tempo_residuo_pezzo + max(0, pezzi_restanti - 1) * tempo_pezzo
        work = min(delta_min, remaining_prod)

        pezzi_this = 0
        time_used = 0.0
        curr_res = tempo_residuo_pezzo
        while time_used < work and pezzi_restanti > 0:
            if time_used + curr_res <= work:
                time_used += curr_res
                pezzi_this += 1
                pezzi_restanti -= 1
                curr_res = tempo_pezzo
            else:
                partial = work - time_used
                curr_res -= partial
                time_used += partial
                break

        tempo_residuo_pezzo = curr_res

        start = corrente
        end = corrente + timedelta(minutes=work)
        log.append({
            "Data": corrente.date(),
            "Start": start,
            "End": end,
            "Tipo": "PRODUZIONE",
            "Minuti": work,
            "Pezzi": pezzi_this
        })
        corrente = end

    df = pd.DataFrame(log)
    return df, corrente


# ---------------- ESECUZIONE ----------------
if st.button("CALCOLA PLANNING"):
    df, fine_prevista = calcola()

    # Tabella Produzione (solo tempo lavorativo effettivo)
    produzione = df[df["Tipo"] != "PAUSA"].groupby("Data").agg(
        Minuti_lavorati=("Minuti", "sum"),
        Pezzi=("Pezzi", "sum")
    ).reset_index()
    produzione["Totale pezzi"] = produzione["Pezzi"].cumsum()
    produzione["Ore lavorate"] = produzione["Minuti_lavorati"] / 60

    st.subheader("📋 Tabella Produzione")
    st.dataframe(
        produzione.rename(columns={
            "Minuti_lavorati": "Minuti lavorati",
            "Pezzi": "Pezzi giorno"
        }),
        use_container_width=True
    )

    st.success(
        f"🏁 Fine lavorazione prevista: {fine_prevista.date()} ore {fine_prevista.strftime('%H:%M:%S')}"
    )

    # ==================== TIMELINE ORARI REALI (come fai tu) ====================
    st.subheader("📊 Orari Reali Turno - Inizio e Fine di ogni attività")

    fig = px.timeline(
        df,
        x_start="Start",
        x_end="End",
        y="Data",
        color="Tipo",
        title="Timeline giornaliera: orari esatti di Pausa • Piazzamento • Produzione",
        color_discrete_map={
            "PAUSA": "#FF4B4B",
            "PIAZZAMENTO": "#FFA500",
            "PRODUZIONE": "#00CC96"
        },
        hover_data=["Minuti", "Pezzi"]
    )
    fig.update_layout(
        xaxis_title="Orario reale (Inizio → Fine)",
        yaxis_title="Data",
        height=600
    )
    fig.update_xaxes(tickformat="%d/%m %H:%M")

    st.plotly_chart(fig, use_container_width=True)
