import streamlit as st
import pandas as pd
import requests
from supabase import create_client, Client
from datetime import date, datetime
import time

# --- 1. CONFIGURAZIONE PAGINA ---
st.set_page_config(page_title="SSH Annual Report", page_icon="📊", layout="wide") # Layout wide per vedere meglio i totali

# --- 2. CSS DEFINITIVO (NO HOVER & DESIGN) ---
st.markdown("""
    <style>
    /* RESET GENERALE */
    .stApp { background-color: #ffffff; color: #000000; }
    h1, h2, h3, h4, h5, h6, p, label, .stMarkdown { color: #000000 !important; }

    /* SIDEBAR */
    [data-testid="stSidebar"] { background-color: #A9093B !important; }
    [data-testid="stSidebar"] p, [data-testid="stSidebar"] span, [data-testid="stSidebar"] label, [data-testid="stSidebar"] div { color: #ffffff !important; }
    [data-testid="stSidebar"] button { background-color: #ffffff !important; color: #A9093B !important; border: none !important; }

    /* MENU A TENDINA */
    div[data-baseweb="select"] > div { background-color: #e9ecef !important; border: 1px solid #ced4da !important; }
    div[data-baseweb="select"] span { color: #058097 !important; font-weight: 800 !important; }
    div[data-baseweb="select"] svg { fill: #058097 !important; }
    ul[data-baseweb="menu"] { background-color: #ffffff !important; }
    ul[data-baseweb="menu"] li span { color: #058097 !important; }

    /* INPUT FIELDS */
    input { background-color: #e9ecef !important; border: 1px solid #ced4da !important; color: #A9093B !important; font-weight: bold !important; }
    input:disabled { background-color: #e9ecef !important; color: #A9093B !important; -webkit-text-fill-color: #A9093B !important; opacity: 1 !important; border: 1px solid #ced4da !important; }

    /* --- PULSANTI (NO HOVER EFFECT) --- */
    button, div[data-testid="stFormSubmitButton"] > button {
        background-color: #A9093B !important; 
        color: #ffffff !important; 
        border: none !important;
        border-radius: 6px !important;
        font-weight: 800 !important;
        padding: 0.75rem 1.5rem !important;
        text-transform: uppercase;
        letter-spacing: 1px;
        box-shadow: none !important;
        transition: none !important; /* Disabilita animazioni */
    }
    
    /* STATO HOVER IDENTICO ALLA BASE (Blocca il cambio colore) */
    button:hover, div[data-testid="stFormSubmitButton"] > button:hover {
        background-color: #A9093B !important; 
        color: #ffffff !important; 
        box-shadow: none !important;
        border: none !important;
        transform: none !important;
    }

    button:active, button:focus {
        background-color: #A9093B !important;
        color: #ffffff !important;
        outline: none !important;
    }

    /* TABELLA E DATAFRAME */
    [data-testid="stDataFrame"] { background-color: #f8f9fa !important; }
    [data-testid="stDataFrame"] th { background-color: #e0e0e0 !important; color: #000000 !important; }

    /* METRICHE E TOTALI */
    [data-testid="stMetricValue"] { color: #058097 !important; font-weight: bold; }
    [data-testid="stMetricLabel"] { color: #000000 !important; }

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
        else: st.error("Credenziali non valide.")
    except: st.error("Errore connessione.")

def logout(): st.session_state['logged_in'] = False

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

    # HEADER
    col_logo, col_title = st.columns([1.5, 3.5])
    with col_logo:
        try:
            st.image("icon_RGB-01.png", width=200)
        except:
            st.error("Logo mancante")
    with col_title:
        st.title("SSH Annual Report")
        st.caption("Financial Data Entry System")

    df_countries, df_accounts = load_config_data()
    if df_countries.empty: st.stop()

    st.markdown("---")

    # SELEZIONI
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
            val_code = str(row[possible_cols[0]]).strip() if possible_cols else "EUR"
            if val_code == 'nan' or val_code == '': val_code = "EUR"

            if val_code != 'EUR':
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
            else: tasso = 1.0
        except: val_code = "ERR"

    with col3: st.text_input("Valuta", value=val_code, disabled=True)
    with col4: st.text_input("Tasso vs EUR", value=f"{tasso:.6f}", disabled=True, help=note)

    # --- PREPARAZIONE DATI PER EDITOR ---
    col_cod = next((c for c in df_accounts.columns if 'code' in c or 'codice' in c), df_accounts.columns[0])
    other_cols = [c for c in df_accounts.columns if c != col_cod]
    col_desc = next((c for c in other_cols if 'desc' in c), other_cols[0] if other_cols else col_cod)
    
    # Cerchiamo colonne TIPO e CLASSE (se esistono su Supabase)
    col_tipo = next((c for c in df_accounts.columns if 'type' in c or 'tipo' in c), None)
    col_classe = next((c for c in df_accounts.columns if 'class' in c or 'classe' in c), None)
    
    # Prepariamo il DataFrame completo (teniamo Tipo e Classe nascosti ma presenti per i calcoli)
    # Se non esistono, li creiamo artificialmente per evitare errori
    calc_df = df_accounts.copy()
    if not col_classe: 
        # Fallback: Usa la prima cifra del codice come Classe
        calc_df['classe_calc'] = calc_df[col_cod].astype(str).str[0]
    else:
        calc_df['classe_calc'] = calc_df[col_classe]

    if not col_tipo:
        calc_df['tipo_calc'] = "Generico"
    else:
        calc_df['tipo_calc'] = calc_df[col_tipo]

    # DataFrame visibile all'utente (solo Codice, Descrizione, Importo)
    display_df = calc_df[[col_cod, col_desc]].copy()
    display_df.columns = ['Codice', 'Descrizione']
    display_df['Importo'] = 0.00
    
    st.subheader("Inserimento Dati")
    
    # EDITOR
    edited_df = st.data_editor(
        display_df,
        column_config={
            "Codice": st.column_config.TextColumn(disabled=True),
            "Descrizione": st.column_config.TextColumn(disabled=True),
            "Importo": st.column_config.NumberColumn("Importo", format="%.2f")
        },
        use_container_width=True,
        hide_index=True,
        height=400
    )

    # --- CALCOLO TOTALI IN TEMPO REALE ---
    # Uniamo i dati editati con i metadati (Classe e Tipo)
    if not edited_df.empty:
        # Filtra solo righe con importi
        active_rows = edited_df[edited_df['Importo'] != 0].copy()
        
        if not active_rows.empty:
            # Ricostruiamo il link con Tipo e Classe usando l'indice o il codice
            # Poiché l'ordine è lo stesso, usiamo l'indice per velocità
            active_rows['classe'] = calc_df.loc[active_rows.index, 'classe_calc']
            active_rows['tipo'] = calc_df.loc[active_rows.index, 'tipo_calc']
            
            st.markdown("### 📊 Riepilogo in Tempo Reale")
            c_tot1, c_tot2, c_tot3 = st.columns(3)
            
            # 1. Totale Generale
            totale_generale = active_rows['Importo'].sum()
            c_tot1.metric("Totale Inserito", f"{totale_generale:,.2f}")

            # 2. Totali per CLASSE
            with c_tot2:
                st.markdown("**Totali per CLASSE**")
                grp_class = active_rows.groupby('classe')['Importo'].sum().reset_index()
                grp_class.columns = ['Classe', 'Totale']
                st.dataframe(grp_class.style.format({"Totale": "{:,.2f}"}), hide_index=True, use_container_width=True)

            # 3. Totali per TIPO
            with c_tot3:
                st.markdown("**Totali per TIPO**")
                grp_tipo = active_rows.groupby('tipo')['Importo'].sum().reset_index()
                grp_tipo.columns = ['Tipo', 'Totale']
                st.dataframe(grp_tipo.style.format({"Totale": "{:,.2f}"}), hide_index=True, use_container_width=True)

    st.markdown("<br>", unsafe_allow_html=True)

    # PULSANTE DI SALVATAGGIO
    if st.button("REGISTRA NEL DATABASE", type="primary"):
        if not sel_country: st.error("Seleziona Paese"); return
        
        to_save = edited_df[edited_df['Importo'] != 0]
        if to_save.empty: st.warning("Inserisci importo"); return

        with st.spinner("Salvataggio..."):
            try:
                recs = []
                for idx, r in to_save.iterrows():
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

# --- 7. LOGIN PAGE ---
if not st.session_state['logged_in']:
    st.markdown("<br><br>", unsafe_allow_html=True)
    try:
        st.image("icon_RGB-01.png", width=300)
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
