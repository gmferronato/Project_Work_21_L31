import streamlit as st
import pandas as pd
import sqlite3
import plotly.express as px
import etl

"""Indicatori principali in evidenza: numero totale di richieste, incassi, tempo medio di erogazione, clienti attivi."""

# Setting della pagina
st.set_page_config(
    page_title="Dashboard - Startup On-Demand",
    page_icon="📊",
    layout="wide"
)

# Setting del titolo
st.title("📊 Dashboard Startup Servizi On-Demand")

# Connessione al database
conn = sqlite3.connect("database/warehouse.db")

if "reset_filtri" not in st.session_state:
    st.session_state.reset_filtri = False

if st.session_state.reset_filtri:
    st.session_state.reset_filtri = False
    st.session_state["add_zona"] = "Tutte"
    st.session_state["add_periodo"] = "Tutti"
    st.session_state["add_categoria"] = "Tutte"

# Importazione del dataframe contenente i dati della tabella richieste da etl.py
df = etl.carica_dataframe(conn)

# Creazione della sidebar con le opzioni di filtro
with st.sidebar:

    st.header("Filtri")

    # Zona
    lista_zone = ["Tutte"] + sorted(df["zona"].dropna().unique())
    add_zona = st.selectbox("Zona", lista_zone, key="add_zona")

    # Periodo
    lista_mesi = ["Tutti"] + sorted(df["mese"].unique())
    add_periodo = st.selectbox("Periodo", lista_mesi, key="add_periodo")

    # Distribuzione per categoria di servizio
    lista_cat_serv = ["Tutte"] + sorted(df["categoria_servizio"].dropna().unique())
    add_categoria = st.selectbox("Categoria di servizio", lista_cat_serv, key="add_categoria")

    st.divider()  # linea separatrice

    # Aggiunta tasto reset filtri
    if st.button("🔄 Reset filtri"):
        st.session_state.reset_filtri = True
        st.rerun()
    
# Sezione filtri

# Applicazione filtri
df_filtrato = df.copy()

if add_zona != "Tutte":
    df_filtrato = df_filtrato[df_filtrato["zona"] == add_zona]

if add_periodo != "Tutti":
    df_filtrato = df_filtrato[df_filtrato["mese"] == add_periodo]

if add_categoria != "Tutte":
    df_filtrato = df_filtrato[df_filtrato["categoria_servizio"] == add_categoria]


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

# Creazione grafici
col_sx1, col_dx1 = st.columns(2)

with col_sx1:
    andamento_filtrato = df_filtrato.groupby("mese").size().reset_index(name="richieste")
    fig1 = px.line(andamento_filtrato, x="mese", y="richieste",
                   title="Andamento richieste nel tempo",
                   labels={"mese": "Mese", "richieste": "Numero richieste"})
    st.plotly_chart(fig1, width='stretch')

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
    st.plotly_chart(fig2, width='stretch')

col_sx2, col_dx2 = st.columns(2)

with col_sx2:
    zona_filtrata = df_filtrato.groupby("zona").size().reset_index(name="richieste")
    fig3 = px.bar(zona_filtrata, x="zona", y="richieste",
                  title="Richieste per zona",
                  labels={"zona": "Zona", "richieste": "Numero richieste"})
    fig3.update_xaxes(tickangle=45)
    st.plotly_chart(fig3, width="stretch")

with col_dx2:
    categoria_filtrata = df_filtrato.groupby("categoria_servizio").size().reset_index(name="richieste")
    fig4 = px.pie(categoria_filtrata, values="richieste", names="categoria_servizio",
                  title="Richieste per categoria di servizio")
    st.plotly_chart(fig4, width="stretch")