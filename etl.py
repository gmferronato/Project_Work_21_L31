"""
Obiettivi del codice: Procedura di caricamento (ETL) e archivio dati (data warehouse).
•	✓ Progettazione dell'organizzazione “a stella”: una tabella principale con le richieste collegata alle tabelle di supporto Cliente, Fornitore, Operatore e Tempo.
•	✓ Procedura di caricamento: legge i file CSV, pulisce e uniforma i dati e li carica in un database SQLite.
•	✓ Interrogazioni in linguaggio SQL per calcolare gli indicatori principali (numero di richieste, incassi totali, tempo medio di erogazione, percentuale di clienti che tornano a richiedere il servizio).
"""

import os
import sqlite3
import pandas as pd

# creazione delle tabelle del database
def crea_database(conn): 

    # Disabilita temporaneamente i vincoli per poter eliminare in qualsiasi ordine
    # conn.execute("PRAGMA foreign_keys = OFF")

    # Ottieni la lista di tutte le tabelle
    tabelle = conn.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()

    # Elimina ogni tabella
    for (nome,) in tabelle:
        conn.execute(f"DROP TABLE IF EXISTS {nome}")
    
    conn.execute("PRAGMA foreign_keys = ON")
    
    # clienti
    conn.execute("CREATE TABLE IF NOT EXISTS clienti (" \
        "id_cliente TEXT PRIMARY KEY," \
        "zona TEXT NOT NULL," \
        "data_iscrizione TEXT NOT NULL);")
 
    # fornitori
    conn.execute("CREATE TABLE IF NOT EXISTS fornitori (" \
        "id_fornitore TEXT PRIMARY KEY," \
        "nome TEXT NOT NULL," \
        "categoria_servizio TEXT NOT NULL," \
        "zona TEXT NOT NULL);")
 
    # operatori
    conn.execute("CREATE TABLE IF NOT EXISTS operatori (" \
        "id_operatore TEXT PRIMARY KEY," \
        "zona TEXT NOT NULL," \
        "tipo_attivita TEXT NOT NULL);")
 
    # tempo
    conn.execute("CREATE TABLE IF NOT EXISTS tempo ("
        "sk_tempo INTEGER PRIMARY KEY,"\
        "data TEXT NOT NULL,"\
        "anno INT NOT NULL,"\
        "mese INT NOT NULL,"\
        "giorno INT NOT NULL,"\
        "giorno_settimana TEXT NOT NULL,"\
        "è_weekend INT NOT NULL);")
 
    # richieste
    conn.execute("CREATE TABLE IF NOT EXISTS richieste (" \
        "id_richiesta TEXT PRIMARY KEY," \
        "id_cliente TEXT NOT NULL," \
        "id_fornitore TEXT NOT NULL," \
        "id_operatore TEXT NOT NULL," \
        "data_e_ora TEXT NOT NULL," \
        "importo FLOAT DEFAULT 0," \
        "sk_tempo INTEGER NOT NULL," \
        "tempo_erogazione INT DEFAULT 0," \
        "stato TEXT NOT NULL," \
        "FOREIGN KEY (id_cliente)   REFERENCES clienti(id_cliente)," \
        "FOREIGN KEY (id_fornitore) REFERENCES fornitori(id_fornitore)," \
        "FOREIGN KEY (sk_tempo)     REFERENCES tempo(sk_tempo)," \
        "FOREIGN KEY (id_operatore) REFERENCES operatori(id_operatore));")
 
    print("Tutte le tabelle sono state generate correttamente.")


def pulisci_dataframe(df):
    
    # rimozione di eventuali spazi nelle colonne delle dataframe   
    for col in df.columns:
        if df[col].dtype == "object":
            df[col] = df[col].str.strip()
    
    # Conversione degli stati delle richieste in minuscolo e
    # controllo validità dello stato della richiesta.  
    if "stato" in df.columns:

        df["stato"] = df["stato"].str.lower()
        stati_validi = {"completata", "annullata", "in ritardo"}
        n_stati_invalidi = (~df["stato"].isin(stati_validi)).sum()
        if n_stati_invalidi > 0:
            print(f"Stati non validi trovati: {n_stati_invalidi}")
        df = df[df["stato"].isin(stati_validi)]

    # Conversione importo da virgola decimale a punto
    if "importo" in df.columns:
        
        df["importo"] = (df["importo"]
                                .astype(str)
                                .str.replace(",", ".", regex=False)
                                .astype(float).round(2))


    # Rimozione duplicati
    df = df.drop_duplicates()

    # Rimozione righe completamente vuote
    df = df.dropna(how="all")


    return df

# Lettura da file csv tramite pandas e popolamento tabelle con dati csv.
def popola_tabelle(conn):
    
    # Popolamento delle prime tre tabelle
    # Mappa per i nomi dei giorni in italiano (non dipende dal locale del sistema)
    giorni_it = {0: "Lunedì", 1: "Martedì", 2: "Mercoledì", 3: "Giovedì",
                 4: "Venerdì", 5: "Sabato", 6: "Domenica"}
 
    try:
        # Creazione dataframe, pulizia e popolamento delle tabelle clienti, fornitori e operatori
        for tabella in ["clienti", "fornitori", "operatori"]:
            df = pd.read_csv(f"data/{tabella}.csv")
            df = pulisci_dataframe(df)
            df.to_sql(tabella, conn, if_exists="append", index=False)
            print(f"Tabella {tabella} popolata correttamente.")
 
        # Creazione dataframe e pulizia della tabella richieste
        richieste = pd.read_csv("data/richieste.csv")
        richieste = pulisci_dataframe(richieste)
 
        # Calcolo della chiave tempo per ogni richiesta.
        # Stesso valore per più richieste dello stesso giorno: è corretto.
        dati = pd.to_datetime(richieste["data_e_ora"])
        richieste["sk_tempo"] = dati.dt.strftime("%Y%m%d").astype(int)
 
        # Creazione dataframe della tabella tempo. Creazione di una chiave primaria unica.
        date_distinte = pd.DatetimeIndex(sorted(dati.dt.normalize().unique()))
        df_tempo = pd.DataFrame({
            "sk_tempo":         date_distinte.strftime("%Y%m%d").astype(int),
            "data":             date_distinte.strftime("%Y-%m-%d"),
            "anno":             date_distinte.year,
            "mese":             date_distinte.month,
            "giorno":           date_distinte.day,
            "giorno_settimana": date_distinte.weekday.map(giorni_it),
            "è_weekend":        (date_distinte.weekday >= 5).astype(int),
        })
 
        # Popolamento delle tabelle tempo e richieste.
        df_tempo.to_sql("tempo", conn, if_exists="append", index=False)
        print(f"Tabella tempo popolata correttamente ({len(df_tempo)} date distinte).")
 
        richieste.to_sql("richieste", conn, if_exists="append", index=False)
        print(f"Tabella richieste popolata correttamente ({len(richieste)} righe).")
 
    except Exception as e:
        print(f"Errore durante il popolamento: {e}")
        return 0

# Carica i dati del database in un dataframe
def carica_dataframe(conn):
    df = pd.read_sql("""
        SELECT r.*, f.nome, f.categoria_servizio, f.zona
        FROM richieste r
        JOIN fornitori f ON r.id_fornitore = f.id_fornitore
    """, conn)
    df["data_e_ora"] = pd.to_datetime(df["data_e_ora"])
    df["mese"] = df["data_e_ora"].dt.to_period("M").astype(str)
    return df

# Calcola i KPI a partire dal dataframe precedentemente estratto
def calcola_kpi(df):
    df_valide = df[df["stato"] != "annullata"]
    clienti_returning = df.groupby("id_cliente").size()

    # Controllo divisione by 0
    if clienti_returning.count() > 0:
        perc = round(100 * (clienti_returning > 1).sum() / clienti_returning.count(), 2)
    else:
        perc = 0.0

    return {
        "num_richieste":          len(df),
        "tot_incassi":            round(df_valide["importo"].sum(), 2),
        "tempo_medio_erogazione": round(df_valide["tempo_erogazione"].mean(), 2),
        "percentuale_clienti":    perc
    }

def estrai_dati(conn):
    """Dati da estrarre:
        numero di richieste, 
        incassi totali, 
        tempo medio di erogazione, 
        percentuale di clienti che tornano a richiedere il servizio"""
    
    cursor = conn.cursor()

    query = {
        "num_richieste" :          "SELECT COUNT(*) AS numero_richieste " \
                                   "FROM richieste;",
        "tot_incassi" :            "SELECT ROUND(SUM(importo), 2) AS incassi_totali "
                                   "FROM richieste " \
                                   "WHERE stato != 'annullata';",
        "tempo_medio_erogazione" : "SELECT ROUND(AVG(tempo_erogazione), 2) AS tempo_medio_minuti " \
                                   "FROM richieste " \
                                   "WHERE stato != 'annullata';",
    
        "percentuale_clienti" : "SELECT ROUND(100.0 * COUNT(*) / (SELECT COUNT(DISTINCT id_cliente) FROM richieste), 2) AS percentuale_returning " \
        "FROM (SELECT id_cliente " \
        "FROM richieste " \
        "GROUP BY id_cliente HAVING COUNT(*) > 1);"
    }

    risultati = {}
    
    for nome, sql in query.items():
        cursor.execute(sql)
        risultati[nome] = cursor.fetchone()[0]

    return risultati

def main():
    
    # Crea la directory "database" se non esiste
    os.makedirs("database", exist_ok=True)
    
    # creazione del database e apertura connessione
    conn = sqlite3.connect("database/warehouse.db")

    crea_database(conn)
    popola_tabelle(conn)

    # chiusura connessione a database
    conn.close()
   
# Esecuzione
if __name__ == "__main__":
    main()