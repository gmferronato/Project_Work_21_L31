# Prototipo di analisi dati per una startup di servizi on-demand (vivAI)

Project Work – Corso di Laurea L-31 "Informatica per le Aziende Digitali"
Tema 1 – La digitalizzazione dell'impresa · Traccia 21

Il seguente programma costituisce un prototipo minimale e riproducibile che, partendo da dati sintetici,
realizza un **data warehouse a stella** (SQLite), una procedura **ETL**
in Python e una **dashboard interattiva** in Streamlit con gli
indicatori principali di business.

## Struttura del progetto

```
pw21_Ferronato/
├── generatore_dati.py      # generatore dei dati sintetici (CSV)
├── etl.py                  # procedura ETL -> data warehouse SQLite
├── dashboard.py            # dashboard interattiva Streamlit
├── data/                   # file CSV generati (clienti, fornitori, operatori, richieste)
└── database/warehouse.db   # data warehouse SQLite (generato dall'ETL)
```

## Avvertenza
Per evitare conflitti ed eseguire il programma in un ambiente sicuro si consiglia fortemente di installare le librerie ed eseguire gli script all'interno di un virtual environment.

Procedura:

**Creazione del virtual environment**
```bash
python -m venv .venv
```

**Attivazione — Windows (CMD)**
```bash
.venv\Scripts\activate.bat
```

**Attivazione — Windows (PowerShell)**
```bash
.venv\Scripts\Activate.ps1
```

**Attivazione — Linux / macOS**
```bash
source .venv/bin/activate
```

**Disattivazione (tutte le piattaforme)**
```bash
deactivate
```

## Requisiti

- Python 3.10+
- Librerie: `pandas`, `streamlit`, `plotly`, `faker`

Le librerie possono essere installate in uno dei seguenti modi:

```bash
pip install pandas streamlit plotly faker
```
oppure
```bash
pip install -r requirements.txt
```

## Esecuzione (3 comandi, ~2 minuti)

I comandi vanno eseguiti nell'ordine indicato, dalla cartella radice del progetto.

```bash
# 1) Generazione dei dati sintetici (creazione della cartella data/)
python generatore_dati.py

# 2) ETL: pulizia e caricamento nel data warehouse SQLite (creazione della directory database/)
python etl.py

# 3) Avvio della dashboard interattiva
streamlit run dashboard.py
```

La dashboard si apre nel browser all'indirizzo http://localhost:8501.
Dalla barra laterale è possibile filtrare per **periodo**, **zona** e
**categoria di servizio**.


## Parametri di generazione

Nel file `generatore_dati.py` è possibile modificare: numero di record per
tipologia (`TOTALE_CLIENTI`, `TOTALE_OPERATORI`, `TOTALE_RICHIESTE`, `TOTALE_FORNITORI`),
intervallo temporale (`DATA_INIZIO`, `DATA_FINE`) e seed di
riproducibilità (`SEED = 42`). Con il seed predefinito l'esperimento è
interamente riproducibile.

## Note

- Tutti i dati sono **sintetici** e privi di informazioni personali:
  gli identificativi sono codici (CL0001, FR0001, OP0001, RQ0001) e i
  nomi dei fornitori sono generati combinando prefissi di categoria + cognomi italiani generati da Faker + forma societaria.
- Il generatore introduce volutamente alcune **imperfezioni** (duplicati,
  virgole decimali, stati con maiuscole incoerenti) per dimostrare la
  fase di pulizia dell'ETL.
