import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import datetime, timedelta, time

# ✅ CONFIGURAZIONE PAGINA
st.set_page_config(
    page_title="CronoCNC", 
    page_icon="⚙️",
    layout="wide"
)

st.title("⚙️ CronoCNC - Pianificazione Produzione")

# ---------------- FUNZIONI UTILI ----------------
def italiano_giorno(giorno):
    trad = {
        "Mon": "Lun", "Tue": "Mar", "Wed": "Mer", "Thu": "Gio", 
        "Fri": "Ven", "Sat": "Sab", "Sun": "Dom"
    }
    return trad[giorno[:3]] + giorno[3:]

# ---------------- CONFIGURAZIONE LAVORO ----------------
st.sidebar.header("⚙️ Configurazione")
with st.sidebar:
    lavora_sabato = st.toggle("Lavora questo Sabato?", value=True)
    turno_iniziale = st.selectbox(
        "Mio turno QUESTA SETTIMANA:",
        ["Mattina (6:00-13:50)", "Pomeriggio (13:50-21:40)"]
    )
    tipo_lavoro = st.radio(
        "Copertura Macchina:",
        ["Turno unico", "Due Turni (Continuo)"]
    )

# ---------------- INPUT DATI ----------------
st.header("📊 Dati Lavorazione")
c1, c2, c3 = st.columns(3)
data_inizio = c1.date_input("Data Inizio", datetime.now())
ora_inizio = c2.time_input("Ora Inizio Effettiva", value=time(8, 0))
piazzamento_ore = c3.number_input("Tempo Piazzamento (ore)", value=1.0, min_value=0.0, step=0.1)

c4, c5 = st.columns(2)
n_pezzi = c4.number_input("Numero totale di Pezzi", value=500)
tempo_pezzo = c5.number_input("Tempo per Pezzo (minuti)", value=15.0, step=1.0)

# ---------------- LOGICA CALCOLO ----------------
def calcola_planning():
    minuti_piaz = piazzamento_ore * 60
    minuti_prod = n_pezzi * tempo_pezzo
    corrente = datetime.combine(data_inizio, ora_inizio)
    log = []
    
    # Identifico la settimana iniziale per gestire l'alternanza
    settimana_iniziale = data_inizio.isocalendar()[1]
    
    while minuti_piaz + minuti_prod > 0:
        wd = corrente.weekday()
        settimana_corrente = corrente.isocalendar()[1]
        
        # Gestione Alternanza Turno (Nota Salvata)
        # Se la settimana è diversa dalla iniziale, invertiamo il turno
        turno_settimanale = turno_iniziale
        if (settimana_corrente - settimana_iniziale) % 2 != 0:
            if "Mattina" in turno_iniziale:
                turno_settimanale = "Pomeriggio (13:50-21:40)"
            else:
                turno_settimanale = "Mattina (6:00-13:50)"

        if wd == 6:  # Domenica: Salta
            corrente += timedelta(days=1)
            corrente = corrente.replace(hour=6, minute=0)
            continue

        if wd == 5:  # SABATO: 6:00-12:00
            if not lavora_sabato:
                corrente += timedelta(days=1)
                corrente = corrente.replace(hour=6, minute=0)
                continue
            inizio_turno_giorno = time(6, 0)
            fine_turno_giorno = time(12, 0)
            pause = []
        else: # LUN-VEN
            if tipo_lavoro == "Due Turni (Continuo)":
                inizio_turno_giorno = time(6, 0)
                fine_turno_giorno = time(21, 40)
                pause = [(time(12, 0), time(12, 20)), (time(19, 30), time(19, 50))]
            else:
                if "Mattina" in turno_settimanale:
                    inizio_turno_giorno = time(6, 0)
                    fine_turno_giorno = time(13, 50)
                    pause = [(time(12, 0), time(12, 20))]
                else:
                    inizio_turno_giorno = time(13, 50)
                    fine_turno_giorno = time(21, 40)
                    pause = [(time(19, 30), time(19, 50))]

        # Se iniziamo a un'ora successiva alla fine turno, passiamo al giorno dopo
        if corrente.time() >= fine_turno_giorno:
            corrente += timedelta(days=1)
            corrente = corrente.replace(hour=6, minute=0)
            continue

        t_start = max(corrente.time(), inizio_turno_giorno)
        t = corrente.replace(hour=t_start.hour, minute=t_start.minute)

        while t.time() < fine_turno_giorno and (minuti_piaz + minuti_prod) > 0:
            for p1, p2 in pause:
                if p1 <= t.time() < p2:
                    log.append({
                        "Giorno": t.strftime("%a %d/%m"),
                        "Inizio": t.hour + t.minute / 60,
                        "Durata": 1/60,
                        "Tipo": "PAUSA",
                        "MinutiProd": 0
                    })
                    t += timedelta(minutes=1)
                    break
            else:
                tipo = "PIAZZAMENTO" if minuti_piaz > 0 else "PRODUZIONE"
                durata = min(10, minuti_piaz if tipo == "PIAZZAMENTO" else minuti_prod)
                
                log.append({
                    "Giorno": t.strftime("%a %d/%m"),
                    "Inizio": t.hour + t.minute / 60,
                    "Durata": durata / 60,
                    "Tipo": tipo,
                    "MinutiProd": durata if tipo == "PRODUZIONE" else 0
                })

                if tipo == "PIAZZAMENTO":
                    minuti_piaz -= durata
                else:
                    minuti_prod -= durata
                t += timedelta(minutes=durata)

        corrente = t + timedelta(days=1)
        corrente = corrente.replace(hour=6, minute=0)

    return pd.DataFrame(log)

# ---------------- RENDER RISULTATI ----------------
if st.button("🔄 CALCOLA PLANNING", type="primary", use_container_width=True):
    df = calcola_planning()
    df['Giorno_IT'] = df['Giorno'].apply(italiano_giorno)
    
    # Calcolo pezzi giornalieri
    pezzi_per_giorno = df.groupby('Giorno_IT')['MinutiProd'].sum() / tempo_pezzo
    pezzi_per_giorno = pezzi_per_giorno.round(0).astype(int)

    # Info fine lavoro
    ultimo_blocco = df.iloc[-1]
    orario_fine_dec = ultimo_blocco['Inizio'] + ultimo_blocco['Durata']
    giorno_fine = ultimo_blocco['Giorno_IT']
    ora_fine = f"{int(orario_fine_dec):02d}:{int((orario_fine_dec%1)*60):02d}"

    # Visualizzazione metriche pezzi
    st.subheader("📦 Target Pezzi da produrre")
    m_cols = st.columns(len(pezzi_per_giorno))
    for i, (giorno, qta) in enumerate(pezzi_per_giorno.items()):
        m_cols[i].metric(label=giorno, value=f"{qta} pz")

    # Grafico
    fig = px.bar(
        df, x="Giorno_IT", y="Durata", base="Inizio", color="Tipo",
        color_discrete_map={"PIAZZAMENTO": "#FFA500", "PRODUZIONE": "#00CC96", "PAUSA": "#FF0000"}
    )

    fig.add_hline(y=orario_fine_dec, line_dash="dash", line_color="blue",
                  annotation_text=f"🏁 FINE {ora_fine}", annotation_position="top right")

    fig.update_layout(
        yaxis=dict(title="Orario", autorange="reversed", dtick=1, range=[22, 6]),
        height=700, barmode="overlay",
        title="Cronoprogramma Produzione Macchine CNC"
    )

    st.plotly_chart(fig, use_container_width=True)
    
    st.info(f"**⏱️ Totale ore produzione:** {round((n_pezzi * tempo_pezzo)/60, 1)}h | "
            f"**🏁 Consegna stimata:** {giorno_fine} alle {ora_fine}")
