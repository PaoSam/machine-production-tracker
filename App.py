File "/mount/src/machine-production-tracker/App.py", line 210
      st.plotly_chart(fig,use_container_width=True)ora_inizio = c2.time_input("Ora inizio", value=time(8,0))
                                                   ^
SyntaxError: invalid syntaxdata_inizio = c1.date_input("Data inizio", datetime.now())
ora_inizio = c2.time_input("Ora inizio", value=time(8,0))
piazzamento_ore = c3.number_input("Piazzamento ore", value=1.0)

c4,c5 = st.columns(2)

n_pezzi = c4.number_input("Numero pezzi", value=100)
tempo_pezzo = c5.number_input("Tempo pezzo (min)", value=51)

# ---------------- CALCOLO ----------------

def calcola():

    minuti_piaz = piazzamento_ore * 60
    pezzi_fatti = 0

    corrente = datetime.combine(data_inizio, ora_inizio)

    settimana_iniziale = data_inizio.isocalendar()[1]

    log = []

    step = 5

    while pezzi_fatti < n_pezzi or minuti_piaz > 0:

        wd = corrente.weekday()

        # salta domenica o festivi
        if wd == 6 or corrente.date() in it_holidays:
            corrente += timedelta(days=1)
            corrente = corrente.replace(hour=6, minute=0)
            continue

        settimana_corrente = corrente.isocalendar()[1]

        turno = turno_iniziale

        if (settimana_corrente - settimana_iniziale) % 2 != 0:
            turno = "Pomeriggio" if turno_iniziale == "Mattina" else "Mattina"

        # definizione turni
        if wd == 5:
            if not lavora_sabato:
                corrente += timedelta(days=1)
                corrente = corrente.replace(hour=6,minute=0)
                continue

            inizio = time(6,0)
            fine = time(12,0)
            pause = []

        else:

            if tipo_lavoro == "Due Turni (Continuo)":

                inizio = time(6,0)
                fine = time(21,40)

                pause = [
                    (time(12,0),time(12,20)),
                    (time(19,30),time(19,50))
                ]

            else:

                if turno == "Mattina":

                    inizio = time(6,0)
                    fine = time(13,50)
                    pause = [(time(12,0),time(12,20))]

                else:

                    inizio = time(13,50)
                    fine = time(21,40)
                    pause = [(time(19,30),time(19,50))]

        # fuori turno
        if corrente.time() < inizio:
            corrente = corrente.replace(hour=inizio.hour,minute=inizio.minute)

        if corrente.time() >= fine:
            corrente += timedelta(days=1)
            corrente = corrente.replace(hour=6,minute=0)
            continue

        pausa = False

        for p1,p2 in pause:
            if p1 <= corrente.time() < p2:
                pausa = True
                break

        if pausa:
            corrente += timedelta(minutes=step)
            continue

        # piazzamento
        if minuti_piaz > 0:

            lavoro = min(step, minuti_piaz)

            log.append({
                "Data":corrente.date(),
                "Ora":corrente.strftime("%H:%M"),
                "Tipo":"PIAZZAMENTO",
                "Minuti":lavoro,
                "Pezzi":0
            })

            minuti_piaz -= lavoro

            corrente += timedelta(minutes=lavoro)

        else:

            lavoro = min(step, tempo_pezzo)

            corrente += timedelta(minutes=lavoro)

            pezzi_fatti += 1

            log.append({
                "Data":corrente.date(),
                "Ora":corrente.strftime("%H:%M"),
                "Tipo":"PRODUZIONE",
                "Minuti":lavoro,
                "Pezzi":1
            })

    return pd.DataFrame(log)

# ---------------- ESECUZIONE ----------------

if st.button("CALCOLA PLANNING"):

    df = calcola()

    produzione = df.groupby("Data").agg(
        Minuti_lavorati=("Minuti","sum"),
        Pezzi=("Pezzi","sum")
    ).reset_index()

    produzione["Totale pezzi"] = produzione["Pezzi"].cumsum()

    produzione["Ore lavorate"] = (produzione["Minuti_lavorati"]/60).round(2)

    st.subheader("📋 Tabella Produzione")

    st.dataframe(
        produzione.rename(columns={
            "Minuti_lavorati":"Minuti lavorati",
            "Pezzi":"Pezzi giorno"
        }),
        use_container_width=True
    )

    ultimo = df.iloc[-1]

    st.success(
        f"🏁 Fine lavorazione prevista: {ultimo['Data']} ore {ultimo['Ora']}"
    )

    import plotly.express as px

    fig = px.bar(
        produzione,
        x="Data",
        y="Pezzi",
        title="Produzione giornaliera"
    )

    st.plotly_chart(fig,use_container_width=True)ora_inizio = c2.time_input("Ora inizio", value=time(8,0))
piazzamento_ore = c3.number_input("Piazzamento ore", value=1.0)

c4,c5 = st.columns(2)

n_pezzi = c4.number_input("Numero pezzi", value=100)
tempo_pezzo = c5.number_input("Tempo pezzo (min)", value=51)

# ---------------- FUNZIONE CALCOLO ----------------

def calcola():

    minuti_piaz = piazzamento_ore * 60
    pezzi_fatti = 0

    corrente = datetime.combine(data_inizio, ora_inizio)

    settimana_iniziale = data_inizio.isocalendar()[1]

    log = []

    step = 5

    while pezzi_fatti < n_pezzi or minuti_piaz > 0:

        wd = corrente.weekday()

        # salta domenica
        if wd == 6 or corrente.date() in it_holidays:
            corrente += timedelta(days=1)
            corrente = corrente.replace(hour=6, minute=0)
            continue

        # alternanza turno
        settimana_corrente = corrente.isocalendar()[1]

        turno = turno_iniziale

        if (settimana_corrente - settimana_iniziale) % 2 != 0:
            turno = "Pomeriggio" if turno_iniziale == "Mattina" else "Mattina"

        # definizione turni

        if wd == 5:  # sabato
            if not lavora_sabato:
                corrente += timedelta(days=1)
                corrente = corrente.replace(hour=6,minute=0)
                continue

            inizio = time(6,0)
            fine = time(12,0)
            pause = []

        else:

            if tipo_lavoro == "Due Turni (Continuo)":

                inizio = time(6,0)
                fine = time(21,40)

                pause = [
                    (time(12,0),time(12,20)),
                    (time(19,30),time(19,50))
                ]

            else:

                if turno == "Mattina":

                    inizio = time(6,0)
                    fine = time(13,50)
                    pause = [(time(12,0),time(12,20))]

                else:

                    inizio = time(13,50)
                    fine = time(21,40)
                    pause = [(time(19,30),time(19,50))]

        # fuori turno
        if corrente.time() < inizio:
            corrente = corrente.replace(hour=inizio.hour,minute=inizio.minute)

        if corrente.time() >= fine:
            corrente += timedelta(days=1)
            corrente = corrente.replace(hour=6,minute=0)
            continue

        # pausa
        pausa = False

        for p1,p2 in pause:
            if p1 <= corrente.time() < p2:
                pausa = True
                break

        if pausa:
            corrente += timedelta(minutes=step)
            continue

        # piazzamento
        if minuti_piaz > 0:

            lavoro = min(step, minuti_piaz)

            log.append({
                "Data":corrente.date(),
                "Ora":corrente.strftime("%H:%M"),
                "Tipo":"PIAZZAMENTO",
                "Minuti":lavoro,
                "Pezzi":0
            })

            minuti_piaz -= lavoro

            corrente += timedelta(minutes=lavoro)

        else:

            lavoro = min(step, tempo_pezzo)

            log.append({
                "Data":corrente.date(),
                "Ora":corrente.strftime("%H:%M"),
                "Tipo":"PRODUZIONE",
                "Minuti":lavoro,
                "Pezzi":0
            })

            corrente += timedelta(minutes=lavoro)

            tempo_pezzo_res = tempo_pezzo - lavoro

            while tempo_pezzo_res > 0:

                corrente += timedelta(minutes=step)
                tempo_pezzo_res -= step

            pezzi_fatti += 1

            log[-1]["Pezzi"] = 1

    return pd.DataFrame(log)

# ---------------- ESECUZIONE ----------------

if st.button("CALCOLA PLANNING"):

    df = calcola()

    # produzione giornaliera

    produzione = df.groupby("Data")["Pezzi"].sum().reset_index()

    produzione["Totale"] = produzione["Pezzi"].cumsum()

    st.subheader("📋 Tabella Produzione")

    st.dataframe(produzione, use_container_width=True)

    # fine lavoro

    ultimo = df.iloc[-1]

    st.success(
        f"🏁 Fine lavorazione prevista: {ultimo['Data']} ore {ultimo['Ora']}"
    )

    # grafico produzione

    import plotly.express as px

    fig = px.bar(
        produzione,
        x="Data",
        y="Pezzi",
        title="Produzione giornaliera"
    )

    st.plotly_chart(fig,use_container_width=True)
