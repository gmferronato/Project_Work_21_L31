import streamlit as st
import pandas as pd
import sqlite3
import plotly.express as px
import etl

"""Indicatori principali in evidenza: numero totale di richieste, incassi,
tempo medio di erogazione, clienti attivi/returning."""

# Setting della pagina
st.set_page_config(
    page_title="vivAI - Dashboard",
    page_icon="📊",
    layout="wide"
)

# Setting del titolo
st.title("📊 Dashboard vivAI")


# Connessione al database.
# @st.cache_resource crea la connessione UNA sola volta e la riusa a ogni rerun
# di Streamlit.
@st.cache_resource
def get_connection():
    conn = sqlite3.connect("database/warehouse.db", check_same_thread=False)
    return conn


# Caricamento dati dalla tabella richieste (join con fornitori e operatori).
# @st.cache_data evita di rieseguire la query a ogni interazione coi filtri.
@st.cache_data
def carica_dati():
    return etl.carica_dataframe(get_connection())


# Gestione reset filtri
if "reset_filtri" not in st.session_state:
    st.session_state.reset_filtri = False

if st.session_state.reset_filtri:
    st.session_state.reset_filtri = False
    st.session_state["add_zona"] = "Tutte"
    st.session_state["add_periodo"] = "Tutti"
    st.session_state["add_categoria"] = "Tutte"

# Dataframe dei dati
df = carica_dati()

# Creazione della sidebar con le opzioni di filtro
with st.sidebar:

    st.header("Metriche globali")
    dati = etl.estrai_dati(get_connection())
    
    st.caption(
        "Valori calcolati con interrogazioni SQL dirette sull'intero database, "
        "indipendenti dai filtri: servono da verifica di quadratura dell'ETL."
    )

    st.markdown(
    """
    <style>
    .st-key-kpi_globali [data-testid="stMetricValue"] {
        font-size: 20px;
    }
    </style>
    """,
    unsafe_allow_html=True,
)

    with st.container(key="kpi_globali"):
        st.metric(label="Numero richieste",
                value=f"{dati['num_richieste']:,}")
        st.metric(label="Incassi totali",
                value=f"€ {dati['tot_incassi']:,.2f}")
        st.metric(label="Tempo medio erogazione",
                value=f"{dati['tempo_medio_erogazione']} min")
        st.metric(label="Clienti returning",
                value=f"{dati['percentuale_clienti']}%")

    st.header("Filtri")

    # Zona (zona di erogazione = zona dell'operatore)
    lista_zone = ["Tutte"] + sorted(df["zona"].dropna().unique())
    add_zona = st.selectbox("Zona", lista_zone, key="add_zona")

    # Periodo
    lista_mesi = ["Tutti"] + sorted(df["mese"].unique())
    add_periodo = st.selectbox("Periodo", lista_mesi, key="add_periodo")

    # Categoria di servizio = tipo di attività erogata dall'operatore
    lista_cat_serv = ["Tutte"] + sorted(df["tipo_attivita"].dropna().unique())
    add_categoria = st.selectbox("Categoria di servizio", lista_cat_serv, key="add_categoria")

    st.divider()

    # Tasto reset filtri
    if st.button("🔄 Reset filtri"):
        st.session_state.reset_filtri = True
        st.rerun()


# Applicazione filtri
df_filtrato = df.copy()

if add_zona != "Tutte":
    df_filtrato = df_filtrato[df_filtrato["zona"] == add_zona]

if add_periodo != "Tutti":
    df_filtrato = df_filtrato[df_filtrato["mese"] == add_periodo]

if add_categoria != "Tutte":
    df_filtrato = df_filtrato[df_filtrato["tipo_attivita"] == add_categoria]

# KPI su df_filtrato
kpi = etl.calcola_kpi(df_filtrato)

col1, col2, col3, col4 = st.columns(4)
with col1:
    st.metric("Numero richieste", kpi["num_richieste"])
with col2:
    st.metric("Incassi totali", f"€ {kpi['tot_incassi']:,.2f}")
with col3:
    st.metric("Tempo medio erogazione", f"{kpi['tempo_medio_erogazione']} min")
with col4:
    st.metric("Clienti returning", f"{kpi['percentuale_clienti']}%")


# Grafici
col_sx1, col_dx1 = st.columns(2)

with col_sx1:
    if add_periodo == "Tutti":
        # Vista d'insieme: andamento per MESE
        andamento = df_filtrato.groupby("mese").size().reset_index(name="richieste")
        fig1 = px.line(andamento, x="mese", y="richieste", markers=True,
                       title="Andamento richieste nel tempo",
                       labels={"mese": "Mese", "richieste": "Numero richieste"})
    else:
        # Drill-down: un solo mese selezionato -> andamento per GIORNO
        andamento = (df_filtrato
                     .assign(giorno=df_filtrato["data_e_ora"].dt.date)
                     .groupby("giorno").size().reset_index(name="richieste"))
        fig1 = px.line(andamento, x="giorno", y="richieste", markers=True,
                       title=f"Andamento richieste – {add_periodo}",
                       labels={"giorno": "Giorno", "richieste": "Numero richieste"})
    st.plotly_chart(fig1, width="stretch")

with col_dx1:
    top_fornitori = df_filtrato[df_filtrato["stato"] != "annullata"] \
        .groupby("nome")["importo"].sum() \
        .nlargest(5).reset_index()
    top_fornitori.columns = ["fornitore", "incassi"]
    fig2 = px.bar(top_fornitori, x="incassi", y="fornitore",
                  orientation="h",
                  title="Top 5 fornitori per incassi",
                  labels={"incassi": "Incassi (€)", "fornitore": "Fornitore"})
    fig2.update_layout(yaxis={"categoryorder": "total ascending"})
    st.plotly_chart(fig2, width="stretch")

col_sx2, col_dx2 = st.columns(2)

with col_sx2:
    zona_filtrata = df_filtrato.groupby("zona").size().reset_index(name="richieste")
    fig3 = px.bar(zona_filtrata, x="zona", y="richieste",
                  title="Richieste per zona",
                  labels={"zona": "Zona", "richieste": "Numero richieste"})
    fig3.update_xaxes(tickangle=45)
    st.plotly_chart(fig3, width="stretch")

with col_dx2:
    categoria_filtrata = df_filtrato.groupby("tipo_attivita").size().reset_index(name="richieste")
    fig4 = px.pie(categoria_filtrata, values="richieste", names="tipo_attivita",
                  title="Richieste per categoria di servizio")
    st.plotly_chart(fig4, width="stretch")

col_sx3, col_dx3 = st.columns(2)

# Calcolo delle richieste per fascia oraria.
with col_sx3:
    ore = df_filtrato["data_e_ora"].dt.hour.value_counts().sort_index().reset_index()
    ore.columns = ["ora", "richieste"]
    fig5 = px.bar(ore, x="ora", y="richieste",
                title="Richieste per fascia oraria",
                labels={"ora": "Ora del giorno", "richieste": "Numero richieste"})
    st.plotly_chart(fig5, width="stretch")

with col_dx3:
    conteggi = df_filtrato.groupby("stato").size()
    n_completate = int(conteggi.get("completata", 0))
    n_annullate = int(conteggi.get("annullata", 0))
    n_ritardi = int (conteggi.get("in ritardo", 0))
    st.metric("Richieste completate", n_completate)
    st.metric("Richieste annullate", n_annullate)
    st.metric("Richieste in ritardo", n_ritardi)
