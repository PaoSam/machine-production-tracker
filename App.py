import streamlit as st
from datetime import datetime, timedelta, time

st.set_page_config(page_title="Pianificatore Produzione", layout="wide")

st.title("⏱️ Calcolatore Fine Lavorazione")

# --- CONFIGURAZIONE TURNI ---
st.sidebar.header("Configurazione Orari")
inizio_t1 = time(6, 0)
fine_t1 = time(13, 50)
inizio_t2 = time(13, 50)
fine_t2 = time(21, 40)
pausa_minuti = 20

# --- INPUT UTENTE ---
with st.container():
    st.subheader("Dati Commessa")
    col1, col2, col3 = st.columns(3)
    
    data_inizio = col1.date_input("Data Inizio", datetime.now())
    ora_inizio = col2.time_input("Ora Inizio", time(6, 0))
    piazzamento = col3.number_input("Tempo Piazzamento (ore)", value=1.0)
    
    col4, col5 = st.columns(2)
    n_pezzi = col4.number_input("Numero di Pezzi", value=60)
    tempo_pezzo = col5.number_input("Tempo per Pezzo (minuti)", value=15)

# --- CALCOLO LOGICA ---
def calcola_fine(inizio_dt, ore_lavoro):
    corrente = inizio_dt
    minuti_rimanenti = ore_lavoro * 60
    
    # Ciclo finché non ho esaurito i minuti di lavoro
    while minuti_rimanenti > 0:
        wd = corrente.weekday() # 0=Lun, 5=Sab, 6=Dom
        
        # Definiamo i limiti di oggi
        if wd < 5: # Lun-Ven
            inizio_lavoro = corrente.replace(hour=6, minute=0, second=0)
            fine_lavoro = corrente.replace(hour=21, minute=40, second=0)
            # Semplificazione: consideriamo 2 turni continui meno 40 min totali di pausa
            minuti_disponibili_oggi = (15 * 60 + 40) - (pausa_minuti * 2) 
        elif wd == 5: # Sabato
            inizio_lavoro = corrente.replace(hour=6, minute=0, second=0)
            fine_lavoro = corrente.replace(hour=12, minute=0, second=0)
        else: # Domenica si salta
            corrente += timedelta(days=1)
            corrente = corrente.replace(hour=6, minute=0)
            continue

        # Se siamo oltre la fine del turno, passiamo a domani
        if corrente >= fine_lavoro:
            corrente += timedelta(days=1)
            corrente = corrente.replace(hour=6, minute=0)
            continue
            
        # Se siamo prima dell'inizio, partiamo dall'inizio turno
        if corrente < inizio_lavoro:
            corrente = inizio_lavoro

        # Calcoliamo quanto tempo resta oggi fino alla fine del turno
        spazio_oggi = (fine_lavoro - corrente).total_seconds() / 60
        
        # (Opzionale: qui si potrebbe sottrarre la pausa se l'orario corrente la attraversa)
        
        lavoro_effettivo = min(minuti_rimanenti, spazio_oggi)
        minuti_rimanenti -= lavoro_effettivo
        corrente += timedelta(minutes=lavoro_effettivo)
        
    return corrente

# Esecuzione calcolo
tempo_totale_ore = piazzamento + (n_pezzi * tempo_pezzo / 60)
dt_inizio_completo = datetime.combine(data_inizio, ora_inizio)

if st.button("Calcola Data e Ora di Fine"):
    dt_fine = calcola_fine(dt_inizio_completo, tempo_totale_ore)
    
    st.write("---")
    st.success(f"### 🏁 Fine stimata: {dt_fine.strftime('%d/%m/%Y alle ore %H:%M')}")
    st.info(f"Tempo totale di lavoro necessario: **{tempo_totale_ore:.1f} ore**")

    # Avviso se finisce di sabato
    if dt_fine.weekday() == 5:
        st.warning("⚠️ Attenzione: La lavorazione termina di Sabato.")
