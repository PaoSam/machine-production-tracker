import streamlit as st
from datetime import datetime, timedelta, time

st.set_page_config(page_title="Pianificatore Produzione", layout="wide")

st.title("⚙️ Machine Utensili: Calcolo Fine Lavorazione")

# --- SIDEBAR CONFIGURAZIONE ---
st.sidebar.header("Impostazioni Turni")
tipo_lavoro = st.sidebar.radio("Copertura Macchina:", 
                              ["Due Turni (Continuo)", "Solo Mio Turno (Spezzato)"])

turno_scelto = None
if tipo_lavoro == "Solo Mio Turno (Spezzato)":
    turno_scelto = st.sidebar.selectbox("Quale turno copri?", ["Mattina (6:00-13:50)", "Pomeriggio (13:50-21:40)"])

pausa_minuti = 20

# --- INPUT COMMESSA ---
col1, col2, col3 = st.columns(3)
data_inizio = col1.date_input("Data Inizio", datetime.now())
ora_inizio = col2.time_input("Ora Inizio", time(6, 0))
piazzamento = col3.number_input("Tempo Piazzamento (ore)", value=1.0, step=0.5)

col4, col5 = st.columns(2)
n_pezzi = col4.number_input("Numero di Pezzi", value=60)
tempo_pezzo = col5.number_input("Tempo per Pezzo (minuti)", value=15.0, step=0.1)

# --- LOGICA DI CALCOLO ---
def calcola_fine_v2(inizio_dt, ore_totali, modalita, turno):
    corrente = inizio_dt
    minuti_rimanenti = ore_totali * 60
    
    while minuti_rimanenti > 0:
        wd = corrente.weekday() # 0=Lun, 5=Sab, 6=Dom
        
        # 1. Definizione finestre temporali in base alla modalità
        if wd < 5: # Lun-Ven
            if modalita == "Due Turni (Continuo)":
                inizio_l = time(6, 0)
                fine_l = time(21, 40)
            else: # Solo un turno
                if turno == "Mattina (6:00-13:50)":
                    inizio_l, fine_l = time(6, 0), time(13, 50)
                else:
                    inizio_l, fine_l = time(13, 50), time(21, 40)
        elif wd == 5: # Sabato (Assumiamo solo mattina 6-12)
            inizio_l, fine_l = time(6, 0), time(12, 0)
        else: # Domenica
            corrente += timedelta(days=1)
            corrente = corrente.replace(hour=6, minute=0)
            continue

        limite_inizio = corrente.replace(hour=inizio_l.hour, minute=inizio_l.minute, second=0)
        limite_fine = corrente.replace(hour=fine_l.hour, minute=fine_l.minute, second=0)

        # Se siamo già oltre la fine della finestra lavorativa di oggi
        if corrente >= limite_fine:
            corrente += timedelta(days=1)
            corrente = corrente.replace(hour=inizio_l.hour, minute=inizio_l.minute)
            continue
        
        # Se siamo prima dell'inizio della finestra
        if corrente < limite_inizio:
            corrente = limite_inizio

        # Calcolo minuti disponibili in questa finestra
        spazio_disponibile = (limite_fine - corrente).total_seconds() / 60
        
        # Sottraiamo la pausa se il lavoro "attraversa" la finestra
        # (Semplificato: togliamo i minuti se il tempo rimanente è superiore a metà turno)
        effettivi_oggi = spazio_disponibile - pausa_minuti if spazio_disponibile > 180 else spazio_disponibile

        lavoro_possibile = min(minuti_rimanenti, effettivi_oggi)
        minuti_rimanenti -= lavoro_possibile
        corrente += timedelta(minutes=lavoro_possibile)
        
        # Se abbiamo finito i minuti ma siamo "andati sopra" la pausa, la aggiungiamo al tempo finale
        if lavoro_possibile < effettivi_oggi:
            pass 

    return corrente

# --- OUTPUT ---
if st.button("Calcola Consegna"):
    ore_lavoro = piazzamento + (n_pezzi * tempo_pezzo / 60)
    dt_inizio_pieno = datetime.combine(data_inizio, ora_inizio)
    
    data_fine = calcola_fine_v2(dt_inizio_pieno, ore_lavoro, tipo_lavoro, turno_scelto)
    
    st.write("---")
    st.header(f"🏁 Fine Lavorazione: {data_fine.strftime('%A %d %B - ore %H:%M')}")
    
    # Visualizzazione dati per controllo
    c1, c2, c3 = st.columns(3)
    c1.metric("Tempo Totale", f"{ore_lavoro:.1f} h")
    c2.metric("Pezzi Totali", n_pezzi)
    c3.metric("Fine Turno", data_fine.strftime('%H:%M'))

    if data_fine.weekday() == 5:
        st.warning("⚠️ La produzione finisce durante il turno del sabato.")
