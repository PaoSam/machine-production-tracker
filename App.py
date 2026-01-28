import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import datetime, timedelta, time

# Prova a importare holidays per i festivi automatici
try:
    import holidays
    it_holidays = holidays.Italy()
except ImportError:
    it_holidays = []

# ✅ CONFIGURAZIONE PAGINA
st.set_page_config(page_title="CronoCNC", page_icon="⚙️", layout="wide")
st.title("⚙️ CronoCNC - Pianificazione Produzione")

# ---------------- FUNZIONI UTILI ----------------
def italiano_giorno(giorno_str):
    trad = {"Mon": "Lun", "Tue": "Mar", "Wed": "Mer", "Thu": "Gio", "Fri": "Ven", "Sat": "Sab", "Sun": "Dom"}
    return trad.get(giorno_str[:3], giorno_str[:3]) + giorno_str[3:]

# ---------------- CONFIGURAZIONE LAVORO ----------------
st.sidebar.header("⚙️ Configurazione")
with st.sidebar:
    lavora_sabato = st.toggle("Lavora questo Sabato?", value=True)
    turno_iniziale = st.selectbox("Mio turno QUESTA SETTIMANA:", ["Mattina (6:00-13:50)", "Pomeriggio (13:50-21:40)"])
    tipo_lavoro = st.radio("Copertura Macchina:", ["Turno unico", "Due Turni (Continuo)"])

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
    
    settimana_iniziale = data_inizio.isocalendar()[1]
    
    while minuti_piaz + minuti_prod > 0:
        wd = corrente.weekday()
        # Festività e Domeniche
        if wd == 6 or corrente.date() in it_holidays:
            corrente += timedelta(days=1)
            corrente = corrente.replace(hour=6, minute=0)
            continue

        # Alternanza turno settimanale
        settimana_corrente = corrente.isocalendar()[1]
        turno_settimanale = turno_iniziale
        if (settimana_corrente - settimana_iniziale) % 2 != 0:
            turno_settimanale = "Pomeriggio (13:50-21:40)" if "Mattina" in turno_iniziale else "Mattina (6:00-13:50)"

        # Orari del giorno
        if wd == 5: # Sabato
            if not lavora_sabato:
                corrente += timedelta(days=1); corrente = corrente.replace(hour=6, minute=0)
                continue
            inizio_t, fine_t, pause = time(6, 0), time(12, 0), []
        else: # Lun-Ven
            if tipo_lavoro == "Due Turni (Continuo)":
                inizio_t, fine_t = time(6, 0), time(21, 40)
                pause = [(time(12, 0), time(12, 20)), (time(19, 30), time(19, 50))]
            else:
                if "Mattina" in turno_settimanale:
                    inizio_t, fine_t, pause = time(6, 0), time(13, 50), [(time(12, 0), time(12, 20))]
                else:
                    inizio_t, fine_t, pause = time(13, 50), time(21, 40), [(time(19, 30), time(19, 50))]

        if corrente.time() >= fine_t:
            corrente += timedelta(days=1); corrente = corrente.replace(hour=6, minute=0)
            continue

        t = corrente.replace(hour=max(corrente.time(), inizio_t).hour, minute=max(corrente.time(), inizio_t).minute)

        while t.time() < fine_t and (minuti_piaz + minuti_prod) > 0:
            for p1, p2 in pause:
                if p1 <= t.time() < p2:
                    log.append({"Data": t.date(), "Giorno": t.strftime("%a %d/%m"), "Inizio": t.hour + t.minute/60, "Durata": 1/60, "Tipo": "PAUSA", "MinutiProd": 0})
                    t += timedelta(minutes=1); break
            else:
                tipo = "PIAZZAMENTO" if minuti_piaz > 0 else "PRODUZIONE"
                durata = min(10, minuti_piaz if tipo == "PIAZZAMENTO" else minuti_prod)
                log.append({"Data": t.date(), "Giorno": t.strftime("%a %d/%m"), "Inizio": t.hour + t.minute/60, "Durata": durata/60, "Tipo": tipo, "MinutiProd": durata if tipo == "PRODUZIONE" else 0})
                if tipo == "PIAZZAMENTO": minuti_piaz -= durata
                else: minuti_prod -= durata
                t += timedelta(minutes=durata)

        corrente = t + timedelta(days=1); corrente = corrente.replace(hour=6, minute=0)

    return pd.DataFrame(log)

# ---------------- RENDER ----------------
if st.button("🔄 CALCOLA PLANNING", type="primary", use_container_width=True):
    df = calcola_planning()
    
    # ORDINE CORRETTO: Raggruppiamo per Data (che è ordinabile) e poi formattiamo
    pezzi_df = df.groupby('Data')['MinutiProd'].sum().reset_index()
    pezzi_df['Pezzi'] = (pezzi_df['MinutiProd'] / tempo_pezzo).round(0).astype(int)
    pezzi_df['Giorno_IT'] = pezzi_df['Data'].apply(lambda x: italiano_giorno(x.strftime("%a %d/%m")))
    
    # Mostriamo solo i giorni dove effettivamente si producono pezzi > 0
    pezzi_df = pezzi_df[pezzi_df['Pezzi'] > 0]

    st.subheader("📦 Target Pezzi Giornalieri")
    m_cols = st.columns(len(pezzi_df))
    for i, row in enumerate(pezzi_df.itertuples()):
        m_cols[i].metric(label=row.Giorno_IT, value=f"{row.Pezzi} pz")

    # Grafico (usiamo Giorno per l'asse X ma assicuriamoci che l'ordine sia quello della data)
    df['Giorno_IT'] = df['Giorno'].apply(italiano_giorno)
    df = df.sort_values('Data') # Forza ordine cronologico

    fig = px.bar(df, x="Giorno_IT", y="Durata", base="Inizio", color="Tipo",
                 color_discrete_map={"PIAZZAMENTO": "#FFA500", "PRODUZIONE": "#00CC96", "PAUSA": "#FF0000"})
    
    fig.update_layout(yaxis=dict(title="Orario", autorange="reversed", dtick=1, range=[22, 6]),
                      xaxis={'categoryorder':'array', 'categoryarray':pezzi_df['Giorno_IT'].tolist()},
                      height=600, barmode="overlay")
    
    st.plotly_chart(fig, use_container_width=True)
# --- CODICE PER AGGIUNGERE LA LINEA DI FINE AL GRAFICO ---

# 1. Calcolo l'orario di fine basandomi sull'ultimo blocco di produzione
ultimo_blocco = df.iloc[-1]
orario_fine_dec = ultimo_blocco['Inizio'] + ultimo_blocco['Durata']
ora_fine_formattata = f"{int(orario_fine_dec):02d}:{int((orario_fine_dec%1)*60):02d}"

# 2. Aggiungo la linea e l'etichetta al grafico Plotly
fig.add_hline(
    y=orario_fine_dec, 
    line_dash="dash", 
    line_color="blue",
    annotation_text=f"🏁 FINE ORE {ora_fine_formattata}", 
    annotation_position="top right"
)
