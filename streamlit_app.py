import streamlit as st
import pandas as pd
import requests
from supabase import create_client, Client
from datetime import date, datetime
import time

# --- 1. CONFIGURAZIONE PAGINA E STILE ---
st.set_page_config(page_title="SSH Financial", page_icon="🔒", layout="centered")

# CSS PERSONALIZZATO PER REPLICARE IL DESIGN HTML
st.markdown("""
    <style>
    /* 1. Sfondo e Font */
    .stApp {
        background-color: #ffffff;
        font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
    }
    
    /* 2. Colori Brand */
    :root { 
        --ssh-red: #A9093B; 
        --ssh-hover: #80052b;
        --input-highlight: #f8f9fa; /* Grigio chiarissimo per i campi */
        --border-color: #ced4da;
    }
    
    /* 3. Titoli */
    h1, h2, h3 { color: #058097 !important; }
    
    /* 4. Pulsanti (Rosso SSH) */
    .stButton>button { 
        background-color: var(--ssh-red); 
        color: white; 
        font-weight: 600; 
        border: none; 
        border-radius: 6px;
        padding: 0.5rem 1rem;
        width: 100%;
        transition: 0.3s;
    }
    .stButton>button:hover { 
        background-color: var(--ssh-hover); 
        color: white;
        box-shadow: 0 4px 6px rgba(0,0,0,0.1);
    }

    /* 5. EVIDENZIAZIONE CAMPI INPUT (Richiesta Specifica) */
    /* Input di testo, numeri e date */
    input[type="text"], input[type="number"], input[type="password"], input[type="date"] {
        background-color: var(--input-highlight) !important;
        border: 1px solid var(--border-color) !important;
        border-radius: 4px;
        color: #333;
    }
    
    /* Effetto Focus (Quando clicchi dentro) */
    input:focus {
        border-color: var(--ssh-red) !important;
        box-shadow: 0 0 0 0.2rem rgba(169, 9, 59, 0.25) !important;
        background-color: #fff !important;
    }

    /* Selectbox (Menu a tendina) */
    div[data-baseweb="select"] > div {
        background-color: var(--input-highlight) !important;
        border: 1px solid var(--border-color) !important;
        border-radius: 4px;
    }
    
    /* Tabella Editor */
    [data-testid="stDataFrame"] {
        border: 1px solid #eee;
        border-radius: 8px;
    }
    [data-testid="stDataFrame"] th { 
        background-color: #525252; 
        color: white; 
    }
    </style>
""", unsafe_allow_html=True)

# --- 2. CONNESSIONE SUPABASE ---
@st.cache_resource
def init_connection():
    try:
        url = st.secrets["SUPABASE_URL"]
        key = st.secrets["SUPABASE_KEY"]
        return create_client(url, key)
    except Exception as e:
        st.error("Errore Secrets. Controlla configurazione.")
        return None

supabase = init_connection()

# --- 3. GESTIONE LOGIN (Session State) ---
if 'logged_in' not in st.session_state:
    st.session_state['logged_in'] = False
if 'username' not in st.session_state:
    st.session_state['username'] = ""

def check_login():
    user = st.session_state['input_user']
    pwd = st.session_state['input_pwd']
    
    try:
        # Query alla tabella UTENTI (Case Sensitive sui nomi colonne)
        response = supabase.table('UTENTI').select("*").eq('UTENTE', user).eq('PWD', pwd).execute()
        
        if len(response.data) > 0:
            st.session_state['logged_in'] = True
            st.session_state['username'] = user
            st.success("Login effettuato!")
            time.sleep(0.5) # Piccolo delay per mostrare il successo
        else:
            st.error("Utente o Password non corretti.")
    except Exception as e:
        st.error(f"Errore connessione Login: {e}")

def logout():
    st.session_state['logged_in'] = False
    st.session_state['username'] = ""

# --- 4. FUNZIONI DI CARICAMENTO DATI ---
@st.cache_data(ttl=600)
def load_config_data():
    if not supabase: return pd.DataFrame(), pd.DataFrame()
    try:
        res_c = supabase.table('COUNTRIES').select("*").execute()
        df_c = pd.DataFrame(res_c.data)
        
        res_a = supabase.table('CHARTS OF ACCOUNTS').select("*").execute()
        df_a = pd.DataFrame(res_a.data)
        
        if not df_c.empty:
            df_c.columns = df_c.columns.str.lower()
            col_paese = next((c for c in df_c.columns if 'paese' in c or 'country' in c), df_c.columns[0])
            df_c = df_c.sort_values(by=col_paese)
            
        if not df_a.empty:
            df_a.columns = df_a.columns.str.lower()
            col_code = next((c for c in df_a.columns if 'code' in c or 'codice' in c), df_a.columns[0])
            df_a = df_a.sort_values(by=col_code)
            
        return df_c, df_a
    except Exception as e:
        return pd.DataFrame(), pd.DataFrame()

# --- 5. INTERFACCIA PRINCIPALE ---
def main_app():
    # Sidebar per Logout
    with st.sidebar:
        st.write(f"Utente: **{st.session_state['username']}**")
        st.button("Esci / Logout", on_click=logout)

    # Header
    col_logo, col_title = st.columns([1, 4])
    with col_logo:
        st.image("https://via.placeholder.com/150x80/A9093B/ffffff?text=SSH+LOGO", width=150)
    with col_title:
        st.title("SSH Financial System")
        st.caption("Accesso Autorizzato • Inserimento Dati")

    df_countries, df_accounts = load_config_data()

    if df_countries.empty or df_accounts.empty:
        st.warning("⚠️ Errore caricamento tabelle di configurazione.")
        st.stop()

    st.divider()

    # INPUT
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        col_paese = next((c for c in df_countries.columns if 'paese' in c or 'country' in c), df_countries.columns[0])
        lista_paesi = df_countries[col_paese].unique().tolist()
        selected_country = st.selectbox("Seleziona Paese", [""] + lista_paesi)
    
    with col2:
        data_chiusura = st.date_input("Data di Chiusura", date.today())

    # VALUTA
    valuta_code = "EUR"
    tasso = 1.0
    note = ""

    if selected_country:
        row = df_countries[df_countries[col_paese] == selected_country].iloc[0]
        col_valuta = next((c for c in df_countries.columns if 'currency' in c or 'valuta' in c or 'symbol' in c), None)
        if col_valuta: valuta_code = row[col_valuta]
        
        if valuta_code != 'EUR':
            api_key = st.secrets["EXCHANGERATE_API_KEY"]
            try:
                url = f"https://v6.exchangerate-api.com/v6/{api_key}/history/{valuta_code}/{data_chiusura.year}/{data_chiusura.month}/{data_chiusura.day}"
                res = requests.get(url)
                if res.status_code == 403: raise Exception("Free")
                data = res.json()
                if data['result'] == 'success': tasso = data['conversion_rates']['EUR']
            except:
                try: 
                    url = f"https://v6.exchangerate-api.com/v6/{api_key}/latest/{valuta_code}"
                    res = requests.get(url).json()
                    tasso = res['conversion_rates']['EUR']
                    note = "⚠️ Cambio Odierno"
                except: note = "Errore API"

    with col3: st.text_input("Valuta", value=valuta_code, disabled=True)
    with col4: st.text_input("Tasso vs EUR", value=f"{tasso:.6f}", disabled=True, help=note)

    # TABELLA
    st.subheader("Inserimento Saldi")
    cols_acc = df_accounts.columns
    c_code = next((c for c in cols_acc if 'code' in c or 'codice' in c), cols_acc[0])
    c_desc = next((c for c in cols_acc if 'desc' in c), cols_acc[1] if len(cols_acc)>1 else cols_acc[0])
    
    input_df = df_accounts[[c_code, c_desc]].copy()
    input_df.columns = ['Codice', 'Descrizione'] 
    input_df['Importo'] = 0.00
    
    edited_df = st.data_editor(
        input_df,
        column_config={
            "Codice": st.column_config.TextColumn(disabled=True),
            "Descrizione": st.column_config.TextColumn(disabled=True),
            "Importo": st.column_config.NumberColumn(step=0.01, format="%.2f")
        },
        use_container_width=True,
        hide_index=True,
        height=500
    )

    # SALVATAGGIO
    if st.button("REGISTRA NEL DATABASE", type="primary"):
        if not selected_country:
            st.error("Seleziona un Paese.")
            return
        
        to_save = edited_df[edited_df['Importo'] != 0]
        if to_save.empty:
            st.warning("Inserisci un importo.")
            return

        with st.spinner("Salvataggio..."):
            try:
                records = []
                for idx, row in to_save.iterrows():
                    unique_id = datetime.now().isoformat()
                    records.append({
                        "ID": unique_id,
                        "PAESE": selected_country,
                        "ANNO": int(data_chiusura.year),
                        "VALUTA": valuta_code,
                        "TASSO DI CAMBIO": float(tasso),
                        "DATA CHIUSURA": data_chiusura.isoformat(),
                        "CODICE CONTO": str(row['Codice']),
                        "IMPORTO": float(row['Importo'])
                    })
                
                supabase.table('DATABASE').insert(records).execute()
                st.success("✅ Dati salvati con successo!")
                st.balloons()
            except Exception as e:
                st.error(f"Errore salvataggio: {e}")

# --- 6. LOGICA DI FLUSSO ---
if not st.session_state['logged_in']:
    # SCHERMATA DI LOGIN
    st.markdown("<br><br>", unsafe_allow_html=True)
    st.image("https://via.placeholder.com/200x80/A9093B/ffffff?text=SSH+LOGO", width=200)
    st.title("Area Riservata")
    st.markdown("Inserisci le credenziali per accedere al sistema.")
    
    with st.form("login_form"):
        st.text_input("Utente", key="input_user")
        st.text_input("Password", type="password", key="input_pwd")
        submit = st.form_submit_button("ACCEDI")
        
        if submit:
            check_login()
            if st.session_state['logged_in']:
                st.rerun() # Ricarica la pagina per mostrare l'app
else:
    # MOSTRA L'APP VERA
    main_app()
