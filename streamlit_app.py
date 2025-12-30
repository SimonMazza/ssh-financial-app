import streamlit as st
import pandas as pd
import requests
from supabase import create_client, Client
from datetime import date, datetime
import time

# --- 1. CONFIGURAZIONE PAGINA ---
st.set_page_config(page_title="SSH Annual Report", page_icon="📊", layout="centered")

# --- 2. CSS AVANZATO (DESIGN) ---
st.markdown("""
    <style>
    /* RESET SFONDO E TESTO */
    .stApp { background-color: #ffffff; color: #000000; }
    h1, h2, h3 { color: #000000 !important; }

    /* --- MENU A TENDINA (SELECTBOX) --- */
    
    /* Contenitore principale del menu: Sfondo Grigio Chiaro */
    div[data-baseweb="select"] > div {
        background-color: #f0f2f6 !important;
        border: 1px solid #d1d1d1 !important;
    }
    
    /* Testo del valore selezionato: Acquamarina */
    div[data-baseweb="select"] div {
        color: #058097 !important;
        font-weight: bold;
    }
    
    /* Icona Freccia (SVG): Acquamarina */
    div[data-baseweb="select"] svg {
        fill: #058097 !important;
    }
    
    /* Opzioni nel menu a discesa (quando aperto) */
    ul[data-baseweb="menu"] li {
        color: #058097 !important; /* Acquamarina anche nella lista */
    }

    /* --- CAMPI INPUT (TESTO E NUMERI) --- */
    input {
        background-color: #f0f2f6 !important;
        border: 1px solid #d1d1d1 !important;
        color: #A9093B !important; /* Rosso SSH */
        font-weight: bold;
    }
    
    /* --- LABELS --- */
    label p { font-size: 14px !important; font-weight: bold !important; color: #000000 !important; }

    /* --- TABELLA --- */
    [data-testid="stDataFrame"] { background-color: #f8f9fa !important; }
    [data-testid="stDataFrame"] th { background-color: #e0e0e0 !important; color: #000000 !important; }

    /* --- PULSANTI --- */
    .stButton>button {
        background-color: #A9093B !important;
        color: white !important;
        font-weight: bold;
        border: none;
    }
    .stButton>button:hover { background-color: #80052b !important; color: white !important; }
    </style>
""", unsafe_allow_html=True)

# --- 3. CONNESSIONE ---
@st.cache_resource
def init_connection():
    try:
        return create_client(st.secrets["SUPABASE_URL"], st.secrets["SUPABASE_KEY"])
    except: return None

supabase = init_connection()

# --- 4. GESTIONE LOGIN ---
if 'logged_in' not in st.session_state: st.session_state['logged_in'] = False
if 'username' not in st.session_state: st.session_state['username'] = ""

def check_login():
    user = st.session_state['input_user']
    pwd = st.session_state['input_pwd']
    try:
        # Verifica credenziali su Supabase
        response = supabase.table('UTENTI').select("*").eq('UTENTE', user).eq('PWD', pwd).execute()
        if len(response.data) > 0:
            st.session_state['logged_in'] = True
            st.session_state['username'] = user
            st.success("Accesso eseguito.")
            time.sleep(0.5)
        else:
            st.error("Credenziali non valide.")
    except: st.error("Errore connessione.")

def logout():
    st.session_state['logged_in'] = False

# --- 5. CARICAMENTO DATI ---
@st.cache_data(ttl=600)
def load_config_data():
    if not supabase: return pd.DataFrame(), pd.DataFrame()
    try:
        df_c = pd.DataFrame(supabase.table('COUNTRIES').select("*").execute().data)
        df_a = pd.DataFrame(supabase.table('CHARTS OF ACCOUNTS').select("*").execute().data)
        
        # Pulizia nomi colonne e rimozione spazi extra
        if not df_c.empty:
            df_c.columns = df_c.columns.str.lower().str.strip()
            # Cerca colonna paese
            col_p = next((c for c in df_c.columns if 'paese' in c or 'country' in c), df_c.columns[0])
            # Rimuove spazi dai valori dei paesi per match precisi
            df_c[col_p] = df_c[col_p].astype(str).str.strip()
            df_c = df_c.sort_values(by=col_p)
            
        if not df_a.empty:
            df_a.columns = df_a.columns.str.lower().str.strip()
            col_cod = next((c for c in df_a.columns if 'code' in c or 'codice' in c), df_a.columns[0])
            df_a = df_a.sort_values(by=col_cod)
            
        return df_c, df_a
    except: return pd.DataFrame(), pd.DataFrame()

# --- 6. APP PRINCIPALE ---
def main_app():
    with st.sidebar:
        st.write(f"Utente: **{st.session_state['username']}**")
        st.button("Logout", on_click=logout)

    # HEADER CON LOGO
    col_logo, col_title = st.columns([1, 3])
    with col_logo:
        try:
            st.image("icon_RGB-01.png", width=130)
        except:
            st.warning("Logo 'icon_RGB-01.png' mancante")
    with col_title:
        st.title("SSH Annual Report")
        st.caption("Financial Data Entry System")

    df_countries, df_accounts = load_config_data()
    if df_countries.empty: st.stop()

    st.markdown("---")

    # --- SELEZIONE PAESE E DATA ---
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        # Trova la colonna paese
        col_p = next((c for c in df_countries.columns if 'paese' in c or 'country' in c), df_countries.columns[0])
        lista_paesi = df_countries[col_p].unique().tolist()
        sel_country = st.selectbox("Seleziona Paese", [""] + lista_paesi)
    
    with col2:
        d_chius = st.date_input("Data di Chiusura", date.today())

    # --- LOGICA VALUTA (Migliorata) ---
    val_code, tasso, note = "", "", ""
    
    if sel_country:
        try:
            # Filtra il dataframe per il paese selezionato
            row = df_countries[df_countries[col_p] == sel_country].iloc[0]
            
            # Cerca la colonna valuta (molto flessibile)
            possible_cols = [c for c in df_countries.columns if 'curr' in c or 'val' in c or 'sym' in c or 'moneta' in c]
            if possible_cols:
                col_v = possible_cols[0] # Prende la prima che trova
                val_code = str(row[col_v]).strip()
            else:
                val_code = "EUR" # Default se non trova colonna
            
            # Calcolo Tasso
            if val_code and val_code != 'EUR':
                api = st.secrets["EXCHANGERATE_API_KEY"]
                try:
                    # Tenta storico
                    url = f"https://v6.exchangerate-api.com/v6/{api}/history/{val_code}/{d_chius.year}/{d_chius.month}/{d_chius.day}"
                    res = requests.get(url)
                    if res.status_code == 403: raise Exception
                    tasso = res.json()['conversion_rates']['EUR']
                except:
                    # Fallback Oggi
                    try: 
                        tasso = requests.get(f"https://v6.exchangerate-api.com/v6/{api}/latest/{val_code}").json()['conversion_rates']['EUR']
                        note = "⚠️ Cambio Odierno"
                    except: 
                        tasso = 0.0
                        note = "Errore API"
            elif val_code == 'EUR':
                tasso = 1.0
                
        except Exception as e:
            val_code = "Errore"
            note = f"Dati mancanti: {e}"

    # Visualizzazione Valuta e Tasso
    with col3: st.text_input("Valuta", value=val_code, disabled=True)
    with col4: st.text_input("Tasso vs EUR", value=f"{tasso:.6f}" if isinstance(tasso, float) else str(tasso), disabled=True, help=note)

    # --- TABELLA INPUT ---
    st.subheader("Inserimento Dati")
    col_cod = next((c for c in df_accounts.columns if 'code' in c or 'codice' in c), df_accounts.columns[0])
    col_desc = next((c for c in df_accounts.columns if 'desc' in c), df_accounts.columns[1])
    
    in_df = df_accounts[[col_cod, col_desc]].copy()
    in_df.columns = ['Codice', 'Descrizione']
    in_df['Importo'] = 0.00
    
    edited_df = st.data_editor(in_df, column_config={
        "Codice": st.column_config.TextColumn(disabled=True),
        "Descrizione": st.column_config.TextColumn(disabled=True),
        "Importo": st.column_config.NumberColumn("Importo", format="%.2f")
    }, use_container_width=True, hide_index=True, height=500)

    # --- SALVATAGGIO ---
    if st.button("REGISTRA NEL DATABASE", type="primary"):
        if not sel_country: 
            st.error("Seleziona Paese"); return
        
        to_save = edited_df[edited_df['Importo'] != 0]
        if to_save.empty: st.warning("Inserisci importo"); return

        with st.spinner("Salvataggio..."):
            try:
                recs = []
                for _, r in to_save.iterrows():
                    recs.append({
                        "ID": datetime.now().isoformat(),
                        "PAESE": sel_country,
                        "ANNO": int(d_chius.year),
                        "VALUTA": val_code,
                        "TASSO DI CAMBIO": float(tasso) if isinstance(tasso, (int, float)) else 0.0,
                        "DATA CHIUSURA": d_chius.isoformat(),
                        "CODICE CONTO": str(r['Codice']),
                        "IMPORTO": float(r['Importo'])
                    })
                supabase.table('DATABASE').insert(recs).execute()
                st.success("✅ Dati salvati!"); time.sleep(2); st.rerun()
            except Exception as e: st.error(f"Errore: {e}")

# --- 7. PAGINA LOGIN ---
if not st.session_state['logged_in']:
    st.markdown("<br><br>", unsafe_allow_html=True)
    try:
        st.image("icon_RGB-01.png", width=200)
    except:
        st.header("SSH FINANCIAL")
        
    st.markdown("### Accesso Riservato")
    
    with st.form("login_form"):
        st.text_input("USERNAME", key="input_user")
        st.text_input("PASSWORD", type="password", key="input_pwd")
        submit = st.form_submit_button("ENTRA")
        if submit:
            check_login()
            if st.session_state['logged_in']: st.rerun()
else:
    main_app()
