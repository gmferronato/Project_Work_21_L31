"""
Generatore dati - startup "vivAI" (consulenza botanica e giardinaggio a domicilio)

Obiettivi del codice:
•	Creazione di record coerenti per le varie tipologie:
        ✓ clienti     (identificativo, zona, data di iscrizione),
        ✓ fornitori   (identificativo, nome, categoria di fornitura, zona),
        ✓ operatori   (identificativo, zona, tipo di attività svolta),
        ✓ richieste   (identificativo, cliente, fornitore, operatore, data e ora,
                       importo, tempo di erogazione, stato della richiesta).

•	Distribuzione realistica dei volumi nel tempo (più richieste in determinate
    fasce orarie e giorni feriali) con alcuni ritardi e richieste annullate.

•	Coerenza geografica ("orchestrazione per zona"): ogni richiesta lega un
    cliente, un operatore e un fornitore della STESSA zona (approvvigionamento
    locale, a km zero). vivAI serve il cliente nella sua zona.

•	Esportazione dei dati in file CSV, uno per ogni tipologia.

Modello di business:
    vivAI è l'azienda che eroga i servizi. Gli OPERATORI sono personale di vivAI
    (dipendenti o P.IVA affiliati) e svolgono fisicamente il servizio al cliente.
    I FORNITORI vendono a vivAI i materiali (piante, terriccio, attrezzature,
    sistemi di irrigazione, ecc.). Operatori e fornitori NON hanno legami diretti
    tra loro: entrambi si relazionano solo con vivAI e si incontrano unicamente
    sulla riga della richiesta. Nello schema a stella sono quindi due dimensioni
    indipendenti della tabella fatti "richieste".
"""

import random
import csv
import os
from collections import defaultdict
from datetime import date, timedelta, datetime
from faker import Faker

# Configurazione del totale dei record
TOTALE_CLIENTI   = 500
TOTALE_OPERATORI = 500
TOTALE_RICHIESTE = 600
TOTALE_FORNITORI = 350

# Inizializzazione dei Seed per random e Faker
SEED = 42
fake = Faker('it_IT')

# Intervallo temporale delle richieste
DATA_INIZIO = date(2026, 1, 1)
DATA_FINE   = date(2026, 9, 30)
GIORNI_TOTALI = (DATA_FINE - DATA_INIZIO).days

# Zone operative (regioni italiane): vivAI opera sul mercato nazionale
ZONE = [
    "Abruzzo", "Basilicata", "Calabria", "Campania", "Emilia Romagna",
    "Friuli Venezia Giulia", "Lazio", "Liguria", "Lombardia", "Marche",
    "Molise", "Piemonte", "Puglia", "Sardegna", "Sicilia",
    "Toscana", "Trentino Alto Adige", "Umbria", "Valle d'Aosta", "Veneto"
]

# Categorie di SERVIZIO = tipo di attività svolta dagli OPERATORI
# (chi eroga fisicamente il servizio al cliente)
CATEGORIE_SERVIZIO = [
    "Consulenza arredi interni vegetali",
    "Giardinieri a domicilio",
    "Progettazione e consulenza giardini esterni",
    "Plant coaching",
    "Diagnosi e cura fitosanitaria",
]

# Categorie di FORNITURA = cosa forniscono i FORNITORI
# (approvvigionamento materiale, non servizio al cliente finale)
CATEGORIE_FORNITURA = [
    "Piante da interno",
    "Piante da esterno / da giardino",
    "Attrezzature e materiali da giardinaggio",
    "Terriccio, fertilizzanti e prodotti fitosanitari",
    "Sistemi di irrigazione",
]

# Prefissi coerenti con la categoria, per generare nomi fornitore realistici
# (invece di un nome generico) mantenendo la generazione programmatica.
PREFISSI_PER_CATEGORIA = {
    "Piante da interno":                                  ["Vivaio", "Florovivaismo", "Serra"],
    "Piante da esterno / da giardino":                    ["Vivaio", "Floricoltura", "Garden Center"],
    "Attrezzature e materiali da giardinaggio":           ["Ferramenta Verde", "Attrezzature Garden", "Utensileria"],
    "Terriccio, fertilizzanti e prodotti fitosanitari":   ["Azienda Fitosanitaria", "Agrochimica", "Agriforniture"],
    "Sistemi di irrigazione":                             ["Sistemi Irrigui", "Idroverde", "Irrigazione"],
}

# Forme societarie per dare varietà al nome
FORME_SOCIETARIE = ["S.r.l.", "S.p.A.", "& Figli", "S.n.c.", "S.a.s."]

# Coerenza tematica tra attività dell'operatore e categoria del fornitore.
# Ogni attività ha un insieme di categorie "preferite": in fase di assegnazione
# operatore→fornitore queste ricevono un peso maggiore, ma NON sono obbligatorie.
CATEGORIE_PREFERITE = {
    "Consulenza arredi interni vegetali": {
        "Piante da interno",
        "Attrezzature e materiali da giardinaggio",
    },
    "Giardinieri a domicilio": {
        "Piante da esterno / da giardino",
        "Attrezzature e materiali da giardinaggio",
        "Terriccio, fertilizzanti e prodotti fitosanitari",
    },
    "Progettazione e consulenza giardini esterni": {
        "Piante da esterno / da giardino",
        "Sistemi di irrigazione",
        "Attrezzature e materiali da giardinaggio",
    },
    "Plant coaching": {
        "Piante da interno",
        "Terriccio, fertilizzanti e prodotti fitosanitari",
    },
    "Diagnosi e cura fitosanitaria": {
        "Terriccio, fertilizzanti e prodotti fitosanitari",
        "Piante da interno",
        "Piante da esterno / da giardino",
    },
}

# Range di tempo_erogazione (in minuti) per lo stato "completata", differenziati
# per tipo di attività: un plant coaching è breve, una progettazione è lunga.
# Lo stato "in ritardo" supera il massimo di categoria; "annullata" non ha tempo.
TEMPI_PER_CATEGORIA = {
    "Consulenza arredi interni vegetali":          (45, 120),
    "Giardinieri a domicilio":                     (60, 180),
    "Progettazione e consulenza giardini esterni": (90, 240),
    "Plant coaching":                              (30, 75),
    "Diagnosi e cura fitosanitaria":               (40, 120),
}

# PESO categoria preferita vs non preferita nella scelta soft del fornitore
PESO_PREFERITA     = 5
PESO_NON_PREFERITA = 1


# FUNZIONI DI GENERAZIONE

# Generazione dei clienti
def genera_clienti():
    clienti = []
    for i in range(TOTALE_CLIENTI):
        clienti.append({
            "id_cliente": f"CL{i+1:04d}",
            "zona": random.choice(ZONE),
            "data_iscrizione": (DATA_INIZIO + timedelta(days=random.randrange(GIORNI_TOTALI))).strftime("%Y-%m-%d")
        })
    return clienti


# Generazione dei fornitori.
# Il nome è composto da un prefisso coerente con la categoria + un cognome
# (Faker) + una forma societaria, così il nome suggerisce l'attività.
# Garantiamo inoltre che ogni zona abbia almeno un fornitore: senza questa
# copertura, a valle non si potrebbero assegnare operatori coerenti alla zona.
def genera_fornitori():
    fornitori = []
    for i in range(1, TOTALE_FORNITORI + 1):
        categoria = random.choice(CATEGORIE_FORNITURA)
        prefisso  = random.choice(PREFISSI_PER_CATEGORIA[categoria])
        suffisso  = random.choice(FORME_SOCIETARIE)
        nome = f"{prefisso} {fake.last_name()} {suffisso}".replace('"', '')
        fornitori.append({
            "id_fornitore": f"FR{i:04d}",
            "nome": nome,
            "categoria_fornitura": categoria,
            "zona": random.choice(ZONE),
        })

    # Copertura: ogni zona deve avere almeno un fornitore
    zone_coperte = {f["zona"] for f in fornitori}
    for zona in set(ZONE) - zone_coperte:
        random.choice(fornitori)["zona"] = zona

    return fornitori


# Generazione degli operatori.
# Gli operatori sono personale di vivAI (dipendenti o P.IVA affiliati): NON sono
# legati ad alcun fornitore. Ogni operatore ha una zona e un tipo di attività.
# Ogni zona ha almeno un operatore, altrimenti i clienti di
# quella zona non potrebbero essere serviti.
def genera_operatori():
    operatori = []
    for i in range(TOTALE_OPERATORI):
        operatori.append({
            "id_operatore": f"OP{i+1:04d}",
            "zona": random.choice(ZONE),
            "tipo_attivita": random.choice(CATEGORIE_SERVIZIO),
        })

    # Copertura: ogni zona deve avere almeno un operatore
    zone_coperte = {o["zona"] for o in operatori}
    for zona in set(ZONE) - zone_coperte:
        random.choice(operatori)["zona"] = zona

    return operatori


# Generazione di un datetime con distribuzione realistica:
# più richieste nei giorni feriali e nelle fasce di punta (mattina/sera).
def genera_datetime_realistica():
    # Lun-Ven peso 3, Sab-Dom peso 1
    giorno_settimana = random.choices(range(7), weights=[3, 3, 3, 3, 3, 1, 0])[0]

    # Fasce orarie: picco mattina (8-10) e sera (17-19)
    ora = random.choices(
        range(24),
        weights=[0, 0, 0, 0, 0, 0, 0, 4, 5, 4, 3, 3, 3, 3, 3, 4, 5, 5, 4, 3, 2, 2, 0, 0]
    )[0]

    minuto = random.randint(0, 59)
    data_base = DATA_INIZIO + timedelta(days=random.randrange(GIORNI_TOTALI))
    offset = (giorno_settimana - data_base.weekday()) % 7
    data_finale = data_base + timedelta(days=offset)
    data_finale = min(data_finale, DATA_FINE)
    

    return datetime(data_finale.year, data_finale.month, data_finale.day, ora, minuto)


# Generazione di stato e tempo di erogazione, coerenti con il tipo di attività.
# I range di "completata" dipendono dalla categoria di servizio; "in ritardo"
# supera il massimo di categoria; "annullata" non ha tempo di erogazione.
def genera_stato_e_tempo(tipo_attivita):
    stato = random.choices(
        ["completata", "annullata", "in ritardo"],
        weights=[75, 15, 10]
    )[0]

    min_c, max_c = TEMPI_PER_CATEGORIA[tipo_attivita]

    if stato == "completata":
        tempo = random.randint(min_c, max_c)
    elif stato == "in ritardo":
        tempo = random.randint(max_c + 1, max_c * 2)
    else:  # annullata
        tempo = None

    return stato, tempo


# Generazione delle richieste (orchestrazione per zona).
# Ordine: si sceglie prima il CLIENTE, poi un OPERATORE della sua stessa zona e,
# INDIPENDENTEMENTE, un FORNITORE locale (stessa zona: approvvigionamento a km
# zero) i cui materiali siano tematicamente coerenti col servizio.
# Operatore e fornitore sono due dimensioni indipendenti: non si conoscono tra
# loro, si incontrano solo qui, sulla riga della richiesta.
def genera_richieste(clienti, operatori, fornitori):
    operatori_per_zona = defaultdict(list)
    for o in operatori:
        operatori_per_zona[o["zona"]].append(o)

    fornitori_per_zona = defaultdict(list)
    for f in fornitori:
        fornitori_per_zona[f["zona"]].append(f)

    richieste = []
    for i in range(TOTALE_RICHIESTE):
        cliente       = random.choice(clienti)
        zona          = cliente["zona"]
        operatore     = random.choice(operatori_per_zona[zona])   # operatore locale
        tipo_attivita = operatore["tipo_attivita"]

        # Scelta SOFT del fornitore: locale (stessa zona) e tematicamente coerente
        # col servizio erogato. Le categorie di fornitura "preferite" per quel tipo
        # di attività pesano di più, ma tutte restano possibili: è una preferenza,
        # non un vincolo assoluto (evita il caso "nessun fornitore compatibile").
        fornitori_zona = fornitori_per_zona[zona]
        preferite = CATEGORIE_PREFERITE.get(tipo_attivita, set())
        pesi = [PESO_PREFERITA if f["categoria_fornitura"] in preferite
                else PESO_NON_PREFERITA for f in fornitori_zona]
        fornitore = random.choices(fornitori_zona, weights=pesi)[0]

        stato, tempo = genera_stato_e_tempo(tipo_attivita)

        richieste.append({
            "id_richiesta":     f"RQ{i+1:04d}",
            "id_cliente":       cliente["id_cliente"],
            "id_fornitore":     fornitore["id_fornitore"],   # scelto per la richiesta
            "id_operatore":     operatore["id_operatore"],
            "data_e_ora":       genera_datetime_realistica().strftime("%Y-%m-%d %H:%M"),
            "importo":          round(random.uniform(20, 500), 2) if stato != "annullata" else 0,
            "tempo_erogazione": tempo,
            "stato":            stato
        })

    # Sporcatura volontaria dei dati (per dare all'ETL qualcosa da correggere).
    # NB: la coerenza di zona è mantenuta piena (nessuna incoerenza geografica).

    # Incoerenza di maiuscole nello stato
    for r in random.sample(richieste, 12):
        r["stato"] = r["stato"].upper()

    # Virgola decimale al posto del punto nell'importo
    for r in random.sample(richieste, 8):
        r["importo"] = str(r["importo"]).replace(".", ",")

    # Record duplicati
    duplicati = random.sample(richieste, 4)
    richieste.extend([dict(d) for d in duplicati])

    return richieste


# Salvataggio dei CSV
def salva_csv(dati, nome_file, fieldnames):
    directory = ("data/")
    percorso_completo = os.path.join(directory, nome_file)

    with open(percorso_completo, mode="w", newline='', encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(dati)
    print(f"✓ {nome_file}: {len(dati)} record salvati")


# Definizione del Main
def main():
    random.seed(SEED)
    Faker.seed(SEED)

    # creazione della cartella "data", se non presente
    os.makedirs("data", exist_ok=True)

    clienti   = genera_clienti()
    fornitori = genera_fornitori()
    operatori = genera_operatori()
    richieste = genera_richieste(clienti, operatori, fornitori)

    salva_csv(clienti,   "clienti.csv",   ["id_cliente", "zona", "data_iscrizione"])
    salva_csv(fornitori, "fornitori.csv", ["id_fornitore", "nome", "categoria_fornitura", "zona"])
    salva_csv(operatori, "operatori.csv", ["id_operatore", "zona", "tipo_attivita"])
    salva_csv(richieste, "richieste.csv", ["id_richiesta", "id_cliente", "id_fornitore", "id_operatore", "data_e_ora", "importo", "tempo_erogazione", "stato"])


# Esecuzione
if __name__ == "__main__":
    main()