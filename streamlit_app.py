import streamlit as st
import pandas as pd
import requests
from sqlalchemy import create_engine, text
from datetime import date

# --- 1. CONFIGURAZIONE PAGINA E STILE ---
st.set_page_config(page_title="SSH Financial", page_icon="💰", layout="wide")

st.markdown("""
    <style>
    /* Definizione Colori Brand */
    :root { --ssh-red: #A9093B; --ssh-aqua: #058097; --ssh-gray: #525252; }
    
    /* Titoli e Header */
    h1, h2, h3 { color: var(--ssh-aqua) !important; }
    
    /* Pulsante Principale */
    .stButton>button { 
        background-color: var(--ssh-red); 
        color: white; 
        font-weight: bold; 
        border: none; 
        width: 100%; 
        padding: 12px;
        transition: 0.3s;
    }
    .stButton>button:hover { 
        background-color: #80052b; 
        color: white; 
    }
    
    /* Intestazione Tabelle */
    [data-testid="stDataFrame"] th { 
        background-color: var(--ssh-gray); 
        color: white; 
    }
    </style>
""", unsafe_allow_html=True)

# --- 2. CONNESSIONE AL DATABASE (SUPABASE) ---
def get_db_connection():
    # Recupera la stringa segreta dalle impostazioni di Streamlit
    db_url = st.secrets["SUPABASE_URL"]
    # Crea il motore di connessione
    engine = create_engine(db_url)
    return engine

# --- 3. CARICAMENTO CONFIGURAZIONI (DA TABELLE SQL) ---
@st.cache_data(ttl=600) # Mantiene i dati in memoria per 10 minuti per velocità
def load_config_data():
    conn = get_db_connection()
    try:
        # Legge la tabella PAESI
        # Assumiamo le colonne: paese, currency_code, currency_desc
        df_c = pd.read_sql("SELECT * FROM countries_config ORDER BY paese", conn)
        
        # Legge la tabella PIANO DEI CONTI
        # Assumiamo le colonne: code, description
        df_a = pd.read_sql("SELECT * FROM accounts_config ORDER BY code", conn)
        
        return df_c, df_a
    except Exception as e:
        st.error(f"Errore caricamento configurazioni: {e}")
        return pd.DataFrame(), pd.DataFrame()

# --- 4. FUNZIONE PRINCIPALE (UI) ---
def main():
    # Header con Logo
    col_logo, col_title = st.columns([1, 4])
    with col_logo:
        # Sostituisci con il link vero del tuo logo
        st.image("https://via.placeholder.com/150x80/A9093B/ffffff?text=SSH+LOGO", width=150)
    with col_title:
        st.title("SSH Financial System")
        st.caption("Secure Cloud Database • Supabase SQL")

    # Carica i dati di configurazione dal DB
    df_countries, df_accounts = load_config_data()

    if df_countries.empty:
        st.warning("Nessuna configurazione trovata nel database.")
        st.stop()

    st.divider()

    # --- INPUT UTENTE ---
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        # Menu a tendina Paesi
        lista_paesi = df_countries['paese'].unique().tolist()
        selected_country = st.selectbox("Seleziona Paese", [""] + lista_paesi)
    
    with col2:
        data_chiusura = st.date_input("Data di Chiusura", date.today())

    # --- LOGICA VALUTA E CAMBIO ---
    valuta_code = "EUR"
    valuta_desc = "Euro"
    tasso_cambio = 1.0
    note_tasso = ""

    if selected_country:
        # Trova la riga corrispondente al paese scelto
        row = df_countries[df_countries['paese'] == selected_country].iloc[0]
        
        # Adatta questi nomi se nel DB le colonne si chiamano diversamente
        valuta_code = row.get('currency_code', 'EUR')
        valuta_desc = row.get('currency_desc', 'Euro')
        
        # Chiamata API Cambio
        if valuta_code != 'EUR':
            api_key = st.secrets["EXCHANGERATE_API_KEY"]
            try:
                # Tentativo Storico
                url = f"https://v6.exchangerate-api.com/v6/{api_key}/history/{valuta_code}/{data_chiusura.year}/{data_chiusura.month}/{data_chiusura.day}"
                res = requests.get(url)
                if res.status_code == 403: raise Exception("Plan Limit")
                
                data = res.json()
                if data['result'] == 'success':
                    tasso_cambio = data['conversion_rates']['EUR']
                else: raise Exception("API Error")
            except:
                # Fallback Cambio Odierno
                try:
                    url = f"https://v6.exchangerate-api.com/v6/{api_key}/latest/{valuta_code}"
                    res = requests.get(url).json()
                    tasso_cambio = res['conversion_rates']['EUR']
                    note_tasso = "⚠️ Cambio Odierno"
                except:
                    note_tasso = "Errore Connessione"

    with col3:
        st.text_input("Valuta", value=f"{valuta_code} - {valuta_desc}", disabled=True)
    with col4:
        st.text_input("Tasso vs EUR", value=f"{tasso_cambio:.6f}", disabled=True, help=note_tasso)
        if note_tasso: st.caption(note_tasso, unsafe_allow_html=True)

    # --- TABELLA INSERIMENTO SALDI ---
    st.subheader("Inserimento Saldi")
    
    # Prepara la tabella per l'editor
    input_df = df_accounts.copy()
    # Seleziona solo le colonne necessarie e aggiungi colonna Importo
    input_df = input_df[['code', 'description']] 
    input_df['Importo'] = 0.00
    
    edited_df = st.data_editor(
        input_df,
        column_config={
            "code": st.column_config.TextColumn("Codice", disabled=True),
            "description": st.column_config.TextColumn("Descrizione", disabled=True),
            "Importo": st.column_config.NumberColumn("Importo", step=0.01, format="%.2f")
        },
        use_container_width=True,
        hide_index=True,
        height=500
    )

    # --- SALVATAGGIO SU SUPABASE ---
    if st.button("REGISTRA NEL DATABASE", type="primary"):
        if not selected_country:
            st.error("Seleziona prima un Paese.")
            return
        
        # Filtra solo le righe con importo diverso da zero
        to_save = edited_df[edited_df['Importo'] != 0].copy()
        
        if to_save.empty:
            st.warning("Inserisci almeno un importo.")
            return

        with st.spinner("Salvataggio sicuro su Supabase..."):
            try:
                engine = get_db_connection()
                records = []
                
                # Prepara i dati riga per riga
                for _, row in to_save.iterrows():
                    records.append({
                        "paese": selected_country,
                        "anno": data_chiusura.year,
                        "valuta": valuta_code,
                        "tasso": tasso_cambio,
                        "data_chiusura": data_chiusura,
                        "codice": row['code'],
                        "descrizione": row['description'],
                        "importo": row['Importo'],
                        "tipo": "Input"
                    })
                
                # Scrive nel database
                df_to_sql = pd.DataFrame(records)
                df_to_sql.to_sql('financial_entries', engine, if_exists='append', index=False)
                
                st.success("✅ Dati salvati correttamente nel Database!")
                st.balloons()
                
            except Exception as e:
                st.error(f"Errore durante il salvataggio: {e}")

if __name__ == "__main__":
    main()
