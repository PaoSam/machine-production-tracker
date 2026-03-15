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

# MODIFICA: Input per piazzamento con formato ore.minuti
piazzamento_input = c3.text_input(
    "Piazzamento (ore.minuti)", 
    value="1.30",
    help="Inserisci nel formato ore.minuti (es. 1.30 per 1 ora e 30 minuti, 0.45 per 45 minuti)"
)

c4, c5 = st.columns(2)
n_pezzi = c4.number_input("Numero pezzi", value=100)
tempo_pezzo = c5.number_input("Tempo pezzo (minuti)", value=15)

# ---------------- FUNZIONE CONVERSIONE PIAZZAMENTO ----------------
def converti_piazzamento(valore_input):
    """
    Converte l'input nel formato ore.minuti in ore decimali
    Esempio: "1.30" -> 1.5 ore (1 ora e 30 minuti)
             "0.45" -> 0.75 ore (45 minuti)
             "2.15" -> 2.25 ore (2 ore e 15 minuti)
    """
    try:
        # Sostituisci eventuale virgola con punto
        valore_input = str(valore_input).replace(',', '.')
        
        if '.' in valore_input:
            ore, minuti = map(float, valore_input.split('.'))
            # Converti i minuti in frazione di ora (es. 30 minuti = 0.5 ore)
            ore_decimali = ore + (minuti / 60)
            return ore_decimali
        else:
            # Se non c'è il punto, è solo ore
            return float(valore_input)
    except:
        st.error("Formato piazzamento non valido. Usa ore.minuti (es. 1.30)")
        return 0.0

# ---------------- CALCOLO ESATTO (con Start e End reali) ----------------
def calcola(piazzamento_ore_decimali):
    minuti_piazzamento = piazzamento_ore_decimali * 60
    pezzi_restanti = n_pezzi
    tempo_residuo_pezzo = tempo_pezzo
    corrente = datetime.combine(data_inizio, ora_inizio)
    settimana_iniziale = data_inizio.isocalendar()[1]
    log = []

    while minuti_piazzamento > 0 or pezzi_restanti > 0:
        wd = corrente.weekday()

        if wd == 6 or corrente.date() in it_holidays:
            corrente += timedelta(days=1)
            corrente = corrente.replace(hour=6, minute=0, second=0, microsecond=0)
            continue

        settimana_corrente = corrente.isocalendar()[1]
        turno = turno_iniziale
        if (settimana_corrente - settimana_iniziale) % 2 != 0:
            turno = "Pomeriggio" if turno_iniziale == "Mattina" else "Mattina"

        if wd == 5:
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
                pause = [(time(12, 0), time(12, 20)), (time(19, 30), time(19, 50))]
            else:
                if turno == "Mattina":
                    inizio = time(6, 0)
                    fine = time(13, 50)
                    pause = [(time(12, 0), time(12, 20))]
                else:
                    inizio = time(13, 50)
                    fine = time(21, 40)
                    pause = [(time(19, 30), time(19, 50))]

        if corrente.time() >= fine:
            corrente += timedelta(days=1)
            corrente = corrente.replace(hour=6, minute=0, second=0, microsecond=0)
            continue

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

        if corrente.time() < inizio:
            corrente = datetime.combine(corrente.date(), inizio)
            continue

        next_event = datetime.combine(corrente.date(), fine)
        for p1, p2 in pause:
            if corrente.time() < p1:
                pause_start_dt = datetime.combine(corrente.date(), p1)
                if pause_start_dt < next_event:
                    next_event = pause_start_dt
                break

        delta_min = (next_event - corrente).total_seconds() / 60.0

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
    # Converti l'input del piazzamento
    piazzamento_ore = converti_piazzamento(piazzamento_input)
    
    # Mostra il valore convertito per chiarezza
    ore_int = int(piazzamento_ore)
    minuti_restanti = int((piazzamento_ore - ore_int) * 60)
    st.info(f"📝 Piazzamento convertito: {ore_int} ore e {minuti_restanti} minuti ({piazzamento_ore:.2f} ore decimali)")
    
    df, fine_prevista = calcola(piazzamento_ore)

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

    # ==================== GRAFICO ====================
    st.subheader("📊 Orari Reali Turno (Data sull'X • Orario sulla Y – 6:00 in alto)")

    chart_df = df.copy()
    chart_df["Start_Ore"] = (
        chart_df["Start"].dt.hour +
        chart_df["Start"].dt.minute / 60.0 +
        chart_df["Start"].dt.second / 3600.0
    )
    chart_df["Durata_Ore"] = chart_df["Minuti"] / 60.0
    chart_df["Durata_Ore_Visibile"] = chart_df["Durata_Ore"].clip(lower=0.05)

    fig = px.bar(
        chart_df,
        x="Data",
        y="Durata_Ore_Visibile",
        base="Start_Ore",
        color="Tipo",
        title="Orari esatti di Pausa • Piazzamento • Produzione",
        color_discrete_map={
            "PAUSA": "#FF4B4B",
            "PIAZZAMENTO": "#FFA500",
            "PRODUZIONE": "#00CC96"
        },
        hover_data={
            "Start": "|%H:%M:%S",
            "End": "|%H:%M:%S",
            "Minuti": True,
            "Pezzi": True,
            "Durata_Ore": True
        }
    )

    fig.update_layout(
        barmode="overlay",
        xaxis_title="Data",
        yaxis_title="Orario della giornata",
        height=650,
        legend_title="Tipo attività"
    )

    fig.update_yaxes(
        range=[5.5, 22.5],
        autorange="reversed",
        tickmode="array",
        tickvals=list(range(6, 23)),
        ticktext=[f"{h:02d}:00" for h in range(6, 23)],
        title="Orario (HH:MM)"
    )
    
    fig.update_traces(
        marker_line_width=1,
        marker_line_color="black",
        opacity=0.8
    )

    st.plotly_chart(fig, use_container_width=True)
    
    with st.expander("📋 Dettaglio attività"):
        st.dataframe(
            df[["Data", "Tipo", "Start", "End", "Minuti", "Pezzi"]].style.format({
                "Start": lambda x: x.strftime("%H:%M:%S"),
                "End": lambda x: x.strftime("%H:%M:%S"),
                "Minuti": "{:.1f}"
            }),
            use_container_width=True
        )
