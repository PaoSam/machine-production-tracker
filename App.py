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

# ---------------- FUNZIONE PER OTTENERE IL NOME DEL GIORNO IN ITALIANO ----------------
def nome_giorno_italiano(data):
    giorni = ["Lunedì", "Martedì", "Mercoledì", "Giovedì", "Venerdì", "Sabato", "Domenica"]
    return giorni[data.weekday()]

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

    # Assicuriamoci che la colonna Data sia datetime
    df['Data'] = pd.to_datetime(df['Data'])

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

    # ==================== GRAFICO CON BARRE PIENE ====================
    st.subheader("📊 Orari Reali Turno - Aree piene per attività")

    chart_df = df.copy()
    
    # Convertiamo gli orari in ore decimali
    chart_df["Start_Ore"] = (
        chart_df["Start"].dt.hour +
        chart_df["Start"].dt.minute / 60.0 +
        chart_df["Start"].dt.second / 3600.0
    )
    chart_df["Durata_Ore"] = chart_df["Minuti"] / 60.0
    
    # Per il piazzamento, assicuriamoci che sia visibile anche se breve
    chart_df["Durata_Ore_Visibile"] = chart_df.apply(
        lambda row: max(row["Durata_Ore"], 0.1) if row["Tipo"] == "PIAZZAMENTO" and row["Durata_Ore"] < 0.1 else row["Durata_Ore"],
        axis=1
    )
    
    # Aggiungiamo il giorno della settimana
    chart_df["Giorno_Settimana"] = chart_df["Data"].apply(nome_giorno_italiano)
    
    # Creiamo una colonna per le etichette
    chart_df["Etichetta"] = chart_df.apply(lambda row: f"{int(row['Pezzi'])} pz" if row['Pezzi'] > 0 else "", axis=1)
    
    # Creiamo il grafico con barre
    fig = px.bar(
        chart_df,
        x="Data",
        y="Durata_Ore_Visibile",
        base="Start_Ore",
        color="Tipo",
        title="Orari di Pausa • Piazzamento • Produzione",
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
            "Giorno_Settimana": True,
            "Durata_Ore": True
        }
    )

    # Configurazione del layout
    fig.update_layout(
        barmode="overlay",
        xaxis_title="Data",
        yaxis_title="Orario della giornata",
        height=700,
        legend_title="Tipo attività",
        plot_bgcolor='white',
        paper_bgcolor='white',
        font=dict(size=11),
        legend=dict(
            yanchor="top",
            y=0.99,
            xanchor="left",
            x=0.01,
            bgcolor='rgba(255, 255, 255, 0.9)',
            bordercolor='black',
            borderwidth=1
        ),
        margin=dict(l=60, r=30, t=80, b=100),
        hovermode="x unified",
        bargap=0.1,  # Spazio tra le barre di giorni diversi
        bargroupgap=0  # Nessuno spazio tra barre dello stesso giorno
    )

    # Configurazione asse X con giorni della settimana
    giorni_unici = sorted(chart_df["Data"].unique())
    fig.update_xaxes(
        tickmode="array",
        tickvals=giorni_unici,
        ticktext=[f"{d.strftime('%d/%m')}<br>({nome_giorno_italiano(d)})" for d in giorni_unici],
        tickangle=0,
        tickfont=dict(size=11, family='Arial'),
        showgrid=True,
        gridcolor='lightgray',
        gridwidth=1,
        griddash='solid',
        showline=True,
        linewidth=1,
        linecolor='black',
        mirror=True
    )

    # Configurazione asse Y con scala invertita (6:00 in alto)
    fig.update_yaxes(
        range=[22.5, 5.5],  # Invertito per avere 6:00 in alto
        tickmode="linear",
        tick0=6,
        dtick=1,
        ticktext=[f"{h:02d}:00" for h in range(6, 23)],
        tickvals=list(range(6, 23)),
        tickfont=dict(size=10),
        showgrid=True,
        gridcolor='lightgray',
        gridwidth=1,
        griddash='solid',
        showline=True,
        linewidth=1,
        linecolor='black',
        mirror=True,
        title_font=dict(size=12)
    )

    # Personalizzazione delle barre (senza text parameter che causa l'errore)
    fig.update_traces(
        marker_line_width=1,
        marker_line_color="black",
        opacity=0.9
    )

    # Aggiungiamo le etichette con i numeri dei pezzi separatamente
    for idx, row in chart_df[chart_df["Pezzi"] > 0].iterrows():
        fig.add_annotation(
            x=row["Data"],
            y=row["Start_Ore"] + row["Durata_Ore_Visibile"]/2,
            text=f"{int(row['Pezzi'])} pz",
            showarrow=False,
            font=dict(size=10, color="black", family='Arial'),
            align="center",
            xanchor="center",
            yanchor="middle"
        )

    # Aggiungiamo linee verticali tratteggiate tra i giorni
    if len(giorni_unici) > 1:
        for giorno in giorni_unici[1:]:
            fig.add_vline(
                x=giorno - timedelta(hours=12),  # Mezzanotte
                line_width=1,
                line_dash="dash",
                line_color="gray",
                opacity=0.7,
                layer="below"
            )

    st.plotly_chart(fig, use_container_width=True)
    
    # Tabella dettagliata
    with st.expander("📋 Dettaglio attività"):
        df_dettaglio = df.copy()
        df_dettaglio["Giorno"] = df_dettaglio["Data"].apply(nome_giorno_italiano)
        df_dettaglio["Data_Completa"] = df_dettaglio["Data"].dt.strftime("%d/%m/%Y")
        df_dettaglio["Ora_Inizio"] = df_dettaglio["Start"].dt.strftime("%H:%M")
        df_dettaglio["Ora_Fine"] = df_dettaglio["End"].dt.strftime("%H:%M")
        
        st.dataframe(
            df_dettaglio[["Data_Completa", "Giorno", "Tipo", "Ora_Inizio", "Ora_Fine", "Minuti", "Pezzi"]],
            use_container_width=True,
            column_config={
                "Data_Completa": "Data",
                "Giorno": "Giorno",
                "Tipo": "Tipo",
                "Ora_Inizio": "Inizio",
                "Ora_Fine": "Fine",
                "Minuti": st.column_config.NumberColumn("Durata (min)", format="%.1f"),
                "Pezzi": "Pezzi"
            },
            hide_index=True
        )
    
    # Riepilogo giorni lavorati
    with st.expander("📅 Riepilogo giorni"):
        giorni_unici = sorted(df["Data"].unique())
        riepilogo_giorni = []
        totale_ore = 0
        totale_pezzi = 0
        
        for giorno in giorni_unici:
            df_giorno = df[df["Data"] == giorno]
            ore_lavorate = df_giorno[df_giorno["Tipo"] != "PAUSA"]["Minuti"].sum() / 60
            pezzi_giorno = df_giorno[df_giorno["Tipo"] == "PRODUZIONE"]["Pezzi"].sum()
            nome_giorno = nome_giorno_italiano(giorno)
            data_str = giorno.strftime("%d/%m/%Y")
            
            riepilogo_giorni.append({
                "Data": data_str,
                "Giorno": nome_giorno,
                "Ore lavorate": ore_lavorate,
                "Pezzi prodotti": pezzi_giorno
            })
            
            totale_ore += ore_lavorate
            totale_pezzi += pezzi_giorno
        
        df_riepilogo = pd.DataFrame(riepilogo_giorni)
        
        # Aggiungiamo riga totale
        totale_row = pd.DataFrame({
            "Data": ["TOTALE"],
            "Giorno": [""],
            "Ore lavorate": [totale_ore],
            "Pezzi prodotti": [totale_pezzi]
        })
        df_riepilogo = pd.concat([df_riepilogo, totale_row], ignore_index=True)
        
        st.dataframe(
            df_riepilogo,
            use_container_width=True,
            column_config={
                "Data": "Data",
                "Giorno": "Giorno",
                "Ore lavorate": st.column_config.NumberColumn("Ore lavorate", format="%.2f"),
                "Pezzi prodotti": "Pezzi prodotti"
            },
            hide_index=True
        )
