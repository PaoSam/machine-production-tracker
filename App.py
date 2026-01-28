import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import datetime, timedelta, time

# Prova a importare la libreria per i festivi italiani
try:
    import holidays
    it_holidays = holidays.Italy()
except ImportError:
    it_holidays = []

# ✅ CONFIGURAZIONE PAGINA
st.set_page_config(
    page_title="CronoCNC", 
    page_icon="⚙️",
    layout="wide"
)

st.title("⚙️ CronoCNC - Pianificazione Produzione")

# ---------------- FUNZIONI UTILI ----------------
def italiano_giorno(giorno_str):
    trad = {
        "Mon": "Lun", "Tue": "Mar", "Wed": "Mer", "Thu": "Gio", 
        "Fri": "Ven", "Sat": "Sab", "Sun": "Dom"
    }
    giorno_sett = giorno_str[:3]
    resto = giorno_str[3:]
    return trad.get(giorno_sett, giorno_sett) + resto

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
    
    # Identifico la settimana iniziale per l'alternanza dei turni (tua nota salvata)
    settimana_iniziale = data_inizio.isocalendar()[1]
    
    while minuti_piaz + minuti_prod > 0:
        wd = corrente.weekday()
        
        # 1. Salta Domeniche e Festivi Italiani
        if wd == 6 or corrente.date() in it_holidays:
            corrente += timedelta(days=1)
            corrente = corrente.replace(hour=6, minute=0)
            continue

        # 2. Alternanza Turno Settimanale
        settimana_corrente = corrente.isocalendar()[1]
        turno_settimanale = turno_iniziale
        if (settimana_corrente - settimana_iniziale) % 2 != 0:
            if "Mattina" in turno_iniziale:
                turno_settimanale = "Pomeriggio (13:50-21:40)"
            else:
                turno_settimanale = "Mattina (6:00-13:50)"

        # 3. Definizione orari del giorno
        if wd == 5:  # SABATO (6:00-12:00)
            if not lavora_sabato:
                corrente += timedelta(days=1)
                corrente = corrente.replace(hour=6, minute=0)
                continue
            inizio_t, fine_t, pause = time(6, 0), time(12, 0), []
        else: # LUN-VEN
            if tipo_lavoro == "Due Turni (Continuo)":
                inizio_t, fine_t = time(6, 0), time(21, 40)
                pause = [(time(12, 0), time(12, 20)), (time(19, 30), time(19, 50))]
            else:
                if "Mattina" in turno_settimanale:
                    inizio_t, fine_t, pause = time(6, 0), time(13, 50), [(time(12, 0), time(12, 20))]
                else:
                    inizio_t, fine_t, pause = time(13, 50), time(21, 40), [(time(19, 30), time(19, 50))]

        # Se siamo già oltre la fine del turno, passa al giorno dopo
        if corrente.time() >= fine_t:
            corrente += timedelta(days=1)
            corrente = corrente.replace(hour=6, minute=0)
            continue

        # Orario di partenza per i calcoli odierni
        t_effettivo = max(corrente.time(), inizio_t)
        t = corrente.replace(hour=t_effettivo.hour, minute=t_effettivo.minute)

        # Ciclo lavorativo della giornata
        while t.time() < fine_t and (minuti_piaz + minuti_prod) > 0:
            # Controllo Pause
            for p1, p2 in pause:
                if p1 <= t.time() < p2:
                    log.append({"Data": t.date(), "Giorno": t.strftime("%a %d/%m"), "Inizio": t.hour + t.minute/60, "Durata": 1/60, "Tipo": "PAUSA", "MinutiProd": 0})
                    t += timedelta(minutes=1)
                    break
            else:
                tipo = "PIAZZAMENTO" if minuti_piaz > 0 else "PRODUZIONE"
                durata = min(10, minuti_piaz if tipo == "PIAZZAMENTO" else minuti_prod)
                
                log.append({
                    "Data": t.date(),
                    "Giorno": t.strftime("%a %d/%m"),
                    "Inizio": t.hour + t.minute / 60,
                    "Durata": durata / 60,
                    "Tipo": tipo,
                    "MinutiProd": durata if tipo == "PRODUZIONE" else 0
                })

                if tipo == "PIAZZAMENTO": minuti_piaz -= durata
                else: minuti_prod -= durata
                t += timedelta(minutes=durata)

        # Fine giornata: sposta al giorno successivo
        corrente = t + timedelta(days=1)
        corrente = corrente.replace(hour=6, minute=0)

    return pd.DataFrame(log)

# ---------------- RENDER RISULTATI ----------------
if st.button("🔄 CALCOLA PLANNING", type="primary", use_container_width=True):
    df_risultato = calcola_planning()
    
    # 1. Calcolo Pezzi Giornalieri Ordinati
    pezzi_per_giorno = df_risultato.groupby('Data')['MinutiProd'].sum().reset_index()
    pezzi_per_giorno['Pezzi'] = (pezzi_per_giorno['MinutiProd'] / tempo_pezzo).round(0).astype(int)
    pezzi_per_giorno['Giorno_IT'] = pezzi_per_giorno['Data'].apply(lambda x: italiano_giorno(x.strftime("%a %d/%m")))
    
    # Filtriamo solo i giorni con produzione reale
    pezzi_solo_prod = pezzi_per_giorno[pezzi_per_giorno['Pezzi'] > 0]

    st.subheader("📦 Target Pezzi Giornalieri")
    m_cols = st.columns(len(pezzi_solo_prod))
    for i, row in enumerate(pezzi_solo_prod.itertuples()):
        m_cols[i].metric(label=row.Giorno_IT, value=f"{row.Pezzi} pz")

    # 2. Calcolo Orario di Fine
    ultimo_blocco = df_risultato.iloc[-1]
    orario_fine_dec = ultimo_blocco['Inizio'] + ultimo_blocco['Durata']
    giorno_fine = italiano_giorno(ultimo_blocco['Giorno'])
    ora_fine_str = f"{int(orario_fine_dec):02d}:{int((orario_fine_dec%1)*60):02d}"

    # 3. Creazione Grafico
    df_risultato['Giorno_IT'] = df_risultato['Giorno'].apply(italiano_giorno)
    
    fig = px.bar(
        df_risultato, x="Giorno_IT", y="Durata", base="Inizio", color="Tipo",
        color_discrete_map={"PIAZZAMENTO": "#FFA500", "PRODUZIONE": "#00CC96", "PAUSA": "#FF0000"}
    )

    # Aggiunta linea di FINE
    fig.add_hline(
        y=orario_fine_dec, 
        line_dash="dash", 
        line_color="blue",
        annotation_text=f"🏁 FINE ORE {ora_fine_str}", 
        annotation_position="top right",
        annotation_font_color="blue"
    )

    fig.update_layout(
        yaxis=dict(title="Orario reale", autorange="reversed", dtick=1, range=[22, 6]),
        xaxis={'categoryorder':'array', 'categoryarray':pezzi_per_giorno['Giorno_IT'].tolist()},
        height=700,
        barmode="overlay",
        title="Cronoprogramma Produzione Macchine CNC"
    )

    st.plotly_chart(fig, use_container_width=True)
    
    st.success(f"**🏁 Fine Lavorazione Prevista:** {giorno_fine} alle ore **{ora_fine_str}**")
