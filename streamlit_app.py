import streamlit as st
import pandas as pd
import requests
from supabase import create_client, Client
from datetime import date, datetime
import time

# --- 1. CONFIGURAZIONE PAGINA ---
st.set_page_config(page_title="SSH Annual Report", page_icon="📊", layout="centered")

# --- 2. CSS DEFINITIVO (PERFETTO) ---
st.markdown("""
    <style>
    /* RESET GENERALE: Sfondo Bianco, Testo Nero */
    .stApp { background-color: #ffffff; color: #000000; }
    h1, h2, h3, h4, h5, h6, p, label, .stMarkdown { color: #000000 !important; }

    /* --- SIDEBAR (Barra Laterale Rossa) --- */
    [data-testid="stSidebar"] {
        background-color: #A9093B !important; /* Rosso SSH */
    }
    /* Testi nella sidebar BIANCHI */
    [data-testid="stSidebar"] p, [data-testid="stSidebar"] span, [data-testid="stSidebar"] label {
        color: #ffffff !important;
    }
    /* Pulsante Logout nella sidebar (Inverso) */
    [data-testid="stSidebar"] button {
        background-color: #ffffff !important;
        color: #A9093B !important;
        border: none !important;
    }

    /* --- MENU A TENDINA (Selectbox) --- */
    /* Contenitore esterno: Grigio Chiaro */
    div[data-baseweb="select"] > div {
        background-color: #e9ecef !important;
        border: 1px solid #ced4da !important;
    }
    /* Testo dell'opzione selezionata: Acquamarina */
    div[data-baseweb="select"] span {
        color: #058097 !important;
        font-weight: 800 !important;
    }
    /* Icona Freccia: Acquamarina */
    div[data-baseweb="select"] svg {
        fill: #058097 !important;
    }
    /* Lista delle opzioni (dropdown aperto) */
    ul[data-baseweb="menu"] {
        background-color: #ffffff !important;
    }
    ul[data-baseweb="menu"] li span {
        color: #058097 !important;
    }

    /* --- CAMPI INPUT (Numeri, Testo, Password, Date) --- */
    input {
        background-color: #e9ecef !important; /* Grigio chiaro */
        border: 1px solid #ced4da !important;
        color: #A9093B !important; /* Rosso SSH */
        font-weight: bold !important;
    }
    
    /* CAMPI DISABILITATI (Fix per vederli bene) */
    input:disabled {
        background-color: #e9ecef !important;
        color: #A9093B !important;
        -webkit-text-fill-color: #A9093B !important;
        opacity: 1 !important;
        border: 1px solid #ced4da !important;
    }

    /* --- PULSANTI (ENTRA, REGISTRA) --- */
    /* Applichiamo lo stile a TUTTI i bottoni, inclusi quelli dei form */
    button, div[data-testid="stFormSubmitButton"] > button {
        background-color: #A9093B !important; /* Rosso SSH */
        color: #ffffff !important; /* TESTO BIANCO */
        border: none !important;
        border-radius: 6px !important;
        font-weight: 800 !important;
        padding: 0.75rem 1.5rem !important;
        text-transform: uppercase;
        letter-spacing: 1px;
        box-shadow: none !important;
    }
    
    /* STATO HOVER (Mouse sopra) - IDENTICO AL NORMALE (Nessun effetto) */
    button:hover, div[data-testid="stFormSubmitButton"] > button:hover {
        background-color: #A9093B !important; /* Rimane Rosso */
        color: #ffffff !important; /* Rimane Bianco */
        box-shadow: none !important;
        border: none !important;
    }

    /* STATO FOCUS/ACTIVE */
    button:focus, div[data-testid="stFormSubmitButton"] > button:focus, button:active {
        background-color: #A9093B !important;
        color: #ffffff !important;
        outline: none !important;
    }

    /* --- TABELLA DATI --- */
    [data-testid="stDataFrame"] { background-color: #f8f9fa !important; }
    [data-testid="stDataFrame"] th { background-color: #e0e0e0 !important; color: #000000 !important; }

    </style>
""", unsafe_allow_html=True)

# --- 3. CONNESSIONE SUPABASE ---
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
        
        if not df_c.empty:
            df_c.columns = df_c.columns.str.lower().str.strip()
            df_c = df_c.apply(lambda x: x.str.strip() if x.dtype == "object" else x)
            col_p = next((c for c in df_c.columns if 'paese' in c or 'country' in c), df_c.columns[0])
            df_c = df_c.sort_values(by=col_p)
            
        if not df_a.empty:
            df_a.columns = df_a.columns.str.lower().str.strip()
            df_a = df_a.apply(lambda x: x.str.strip() if x.dtype == "object" else x)
            col_cod = next((c for c in df_a.columns if 'code' in c or 'codice' in c), df_a.columns[0])
            df_a = df_a.sort_values(by=col_cod)
            
        return df_c, df_a
    except: return pd.DataFrame(), pd.DataFrame()

# --- 6. APP PRINCIPALE ---
def main_app():
    with st.sidebar:
        st.write(f"Utente: **{st.session_state['username']}**")
        st.button("Logout", on_click=logout)

    # HEADER APP
    col_logo, col_title = st.columns([1, 4])
    with col_logo:
        try:
            # Larghezza 150px per visualizzazione (il file originale è 2000px, sarà nitidissimo)
            st.image("icon_RGB-01.png", width=150)
        except:
            st.warning("Logo non trovato")
    with col_title:
        st.title("SSH Annual Report")
        st.caption("Financial Data Entry System")

    df_countries, df_accounts = load_config_data()
    if df_countries.empty: st.stop()

    st.markdown("---")

    col1, col2, col3, col4 = st.columns(4)
    with col1:
        col_p = next((c for c in df_countries.columns if 'paese' in c or 'country' in c), df_countries.columns[0])
        lista_paesi = df_countries[col_p].unique().tolist()
        sel_country = st.selectbox("Seleziona Paese", [""] + lista_paesi)
    
    with col2:
        d_chius = st.date_input("Data di Chiusura", date.today())

    val_code, tasso, note = "", 0.0, ""
    
    if sel_country:
        try:
            row = df_countries[df_countries[col_p] == sel_country].iloc[0]
            possible_cols = [c for c in df_countries.columns if 'curr' in c or 'val' in c or 'sym' in c]
            if possible_cols:
                val_code = str(row[possible_cols[0]]).strip()
                if val_code == 'nan': val_code = "EUR"
            else: val_code = "EUR"

            if val_code and val_code != 'EUR':
                api = st.secrets["EXCHANGERATE_API_KEY"]
                try:
                    url = f"https://v6.exchangerate-api.com/v6/{api}/history/{val_code}/{d_chius.year}/{d_chius.month}/{d_chius.day}"
                    res = requests.get(url)
                    if res.status_code == 403: raise Exception
                    tasso = res.json()['conversion_rates']['EUR']
                except:
                    try: 
                        tasso = requests.get(f"https://v6.exchangerate-api.com/v6/{api}/latest/{val_code}").json()['conversion_rates']['EUR']
                        note = "⚠️ Cambio Odierno"
                    except: note = "Errore API"
            elif val_code == 'EUR': tasso = 1.0
        except: val_code = "ERR"

    with col3: st.text_input("Valuta", value=val_code, disabled=True)
    with col4: st.text_input("Tasso vs EUR", value=f"{tasso:.6f}", disabled=True, help=note)

    st.subheader("Inserimento Dati")
    col_cod = next((c for c in df_accounts.columns if 'code' in c or 'codice' in c), df_accounts.columns[0])
    other_cols = [c for c in df_accounts.columns if c != col_cod]
    col_desc = next((c for c in other_cols if 'desc' in c), other_cols[0] if other_cols else col_cod)
    
    in_df = df_accounts[[col_cod, col_desc]].copy()
    in_df.columns = ['Codice', 'Descrizione']
    in_df['Importo'] = 0.00
    
    edited_df = st.data_editor(in_df, column_config={
        "Codice": st.column_config.TextColumn(disabled=True),
        "Descrizione": st.column_config.TextColumn(disabled=True),
        "Importo": st.column_config.NumberColumn("Importo", format="%.2f")
    }, use_container_width=True, hide_index=True, height=500)

    if st.button("REGISTRA NEL DATABASE", type="primary"):
        if not sel_country: st.error("Seleziona Paese"); return
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
                        "TASSO DI CAMBIO": float(tasso),
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
        # LOGO LOGIN: Impostato a 250px. Essendo il file 2000px, sarà nitidissimo.
        st.image("icon_RGB-01.png", width=250)
    except:
        st.header("SSH FINANCIAL")
        
    st.markdown("### Accesso Riservato")
    
    with st.form("login_form"):
        st.text_input("USERNAME", key="input_user")
        st.text_input("PASSWORD", type="password", key="input_pwd")
        
        # Questo pulsante ora sarà ROSSO con testo BIANCO grazie al CSS sopra
        submit = st.form_submit_button("ENTRA")
        
        if submit:
            check_login()
            if st.session_state['logged_in']: st.rerun()
else:
    main_app()
