"""
Obiettivi del codice:
•	Creazione di record coerenti per le varie tipologie: 
        ✓ clienti (identificativo, zona, data di iscrizione), 
        ✓ fornitori (identificativo, nome, categoria di servizio, zona), 
        ✓ operatori (identificativo, zona, tipo di attività svolta), 
        ✓ richieste (identificativo, cliente, fornitore, operatore, data e ora, importo, tempo di erogazione, stato della richiesta).

•	Distribuzione realistica dei volumi nel tempo (per esempio più richieste in determinate fasce orarie o giorni della settimana)
    con alcuni ritardi e richieste annullate.

•	Esportazione dei dati in file di testo in formato CSV (tabelle con righe e colonne separate da virgole), uno per ogni tipologia.
"""

import random
import csv
import os
from datetime import date, timedelta, datetime
from faker import Faker

# Configurazione del totale dei record
TOTALE_CLIENTI   = 500
TOTALE_OPERATORI = 500
TOTALE_RICHIESTE = 600
TOTALE_FORNITORI = 350

# Inizializzazione dei Seed per random e Faker
SEED = 0
fake = Faker('it_IT')

# Inizializzazione delle date delle richieste
DATA_INIZIO = date(2026, 1, 1)
DATA_FINE   = date(2026, 9, 30)
GIORNI_TOTALI = (DATA_FINE - DATA_INIZIO).days

# Creazione della lista delle regioni
ZONE = [
    "Abruzzo", "Basilicata", "Calabria", "Campania", "Emilia Romagna",
    "Friuli Venezia Giulia", "Lazio", "Liguria", "Lombardia", "Marche",
    "Molise", "Piemonte", "Puglia", "Sardegna", "Sicilia",
    "Toscana", "Trentino Alto Adige", "Umbria", "Valle d'Aosta", "Veneto"
]

# Creazione della lista delle categorie di servizio
CATEGORIE_SERVIZIO = [
    "Pulizie domestiche",
    "Riparazioni idrauliche",
    "Riparazioni elettriche",
    "Traslochi",
    "Consegne a domicilio",
    "Assistenza informatica",
]

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

# Generazione dei fornitori

def genera_fornitori():
    fornitori = []
    for i in range(1, TOTALE_FORNITORI + 1):       
        nome = fake.company().replace('"', '')
        fornitori.append({
            "id_fornitore": f"FR{i:04d}",
            "nome": nome,
            "categoria_servizio": random.choice(CATEGORIE_SERVIZIO),
            "zona": random.choice(ZONE),
        })
    return fornitori

# Generazione degli operatori 
# Ogni operatore è legato a un fornitore, ne eredita zona e categoria
def genera_operatori(fornitori):
    operatori = []
    for i in range(TOTALE_OPERATORI):
        fornitore = random.choice(fornitori)
        operatori.append({
            "id_operatore": f"OP{i+1:04d}",
            "id_fornitore": fornitore["id_fornitore"],
            "zona": fornitore["zona"],
            "tipo_attivita": fornitore["categoria_servizio"]
        })
    return operatori

# Generazione di un un datetime con distribuzione realistica: più richieste nei feriali e in fasce di punta.
def genera_datetime_realistica():

    # Lun-Ven peso 3, Sab-Dom peso 1
    giorno_settimana = random.choices(range(7), weights=[3, 3, 3, 3, 3, 1, 1])[0]

    # Fasce orarie: picco mattina (8-10) e sera (17-19)
    ora = random.choices(
        range(24),
        weights=[1, 1, 1, 1, 1, 1, 2, 4, 5, 4, 3, 3, 3, 3, 3, 4, 5, 5, 4, 3, 2, 2, 1, 1]
    )[0]

    minuto = random.randint(0, 59)
    data_base = DATA_INIZIO + timedelta(days=random.randrange(GIORNI_TOTALI))
    offset = (giorno_settimana - data_base.weekday()) % 7
    data_finale = data_base + timedelta(days=offset)

    return datetime(data_finale.year, data_finale.month, data_finale.day, ora, minuto)

# Generazione dello stato della richiesta e tempo di erogazione coerente
def genera_stato_e_tempo():
    stato = random.choices(
        ["completata", "annullata", "in ritardo"],
        weights=[75, 15, 10]
    )[0]

    if stato == "completata":
        tempo = random.randint(30, 120)
    elif stato == "in ritardo":
        tempo = random.randint(121, 300)
    else:
        tempo = None

    return stato, tempo

# Generazione delle richieste
# Ogni richiesta collega cliente, fornitore e un operatore di quel fornitore.
# Ogni richiesta contiene:
#      identificativo, 
#      cliente, 
#      fornitore, 
#      operatore, 
#      data e ora, 
#      importo, 
#      tempo di erogazione, 
#      stato della richiesta

def genera_richieste(clienti, fornitori, operatori):

    richieste = []
    for i in range(TOTALE_RICHIESTE):
        fornitore = random.choice(fornitori)
        operatori_del_fornitore = [op for op in operatori if op["id_fornitore"] == fornitore["id_fornitore"]]
        
        # Fallback: se nessun operatore è legato a quel fornitore, prendi uno qualsiasi
        operatore = random.choice(operatori_del_fornitore) if operatori_del_fornitore else random.choice(operatori)
        
        cliente = random.choice(clienti)
        stato, tempo = genera_stato_e_tempo()

        richieste.append({
            "id_richiesta":     f"RQ{i+1:04d}",
            "id_cliente":       cliente["id_cliente"],
            "id_fornitore":     fornitore["id_fornitore"],
            "id_operatore":     operatore["id_operatore"],
            "data_e_ora":         genera_datetime_realistica().strftime("%Y-%m-%d %H:%M"),
            "importo":          round(random.uniform(20, 500), 2) if stato != "annullata" else 0,
            "tempo_erogazione": tempo,
            "stato":            stato
        })

    # Sporcatura delle richieste
    # Incoerenza di maiuscole
    for r in random.sample(richieste, 12):
        r["stato"] = r["stato"].upper() 

    # Introduzione virgola decimale al posto del punto
    for r in random.sample(richieste, 8):
        r["importo"] = str(r["importo"]).replace(".", ",")   # virgola 

    #Generazione di record duplicati
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
    operatori = genera_operatori(fornitori)
    richieste = genera_richieste(clienti, fornitori, operatori)

    salva_csv(clienti,   "clienti.csv",   ["id_cliente", "zona", "data_iscrizione"])
    salva_csv(fornitori, "fornitori.csv", ["id_fornitore", "nome", "categoria_servizio", "zona"])
    salva_csv(operatori, "operatori.csv", ["id_operatore", "zona", "tipo_attivita"])
    salva_csv(richieste, "richieste.csv", ["id_richiesta", "id_cliente", "id_fornitore", "id_operatore", "data_e_ora", "importo", "tempo_erogazione", "stato"])

# Esecuzione
if __name__ == "__main__":
    main()