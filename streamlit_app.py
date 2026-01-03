import streamlit as st
import pandas as pd
import requests
from supabase import create_client
from datetime import date, datetime
import time
import streamlit_shadcn_ui as ui 

# --- 1. CONFIGURAZIONE PAGINA ---
st.set_page_config(page_title="SSH Annual Report", page_icon="📊", layout="wide")

# --- 2. CSS MINIMO (Solo per layout e sidebar) ---
st.markdown("""
    <style>
    .stApp { background-color: #ffffff; }
    .block-container { padding-top: 2rem !important; padding-bottom: 2rem !important; }
    
    /* Sidebar Scura */
    [data-testid="stSidebar"] { background-color: #525252 !important; }
    [data-testid="stSidebar"] p, [data-testid="stSidebar"] span, [data-testid="stSidebar"] div { color: white !important; }
    </style>
""", unsafe_allow_html=True)

# --- 3. CONNESSIONE ---
@st.cache_resource
def init_connection():
    try: return create_client(st.secrets["SUPABASE_URL"], st.secrets["SUPABASE_KEY"])
    except: return None

supabase = init_connection()

# --- 4. LOGIN ---
if 'logged_in' not in st.session_state: st.session_state['logged_in'] = False
if 'username' not in st.session_state: st.session_state['username'] = ""

def check_login():
    user = st.session_state.get('input_user', '')
    pwd = st.session_state.get('input_pwd', '')
    try:
        response = supabase.table('UTENTI').select("*").eq('UTENTE', user).eq('PWD', pwd).execute()
        if len(response.data) > 0:
            st.session_state['logged_in'] = True
            st.session_state['username'] = user
            # Toast notifica (nativo Streamlit)
            st.toast("Accesso eseguito!", icon="✅")
            time.sleep(0.5)
        else:
            st.error("Credenziali errate.")
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
        if ui.button("Logout", key="btn_logout", variant="outline"):
            logout()
            st.rerun()

    # HEADER
    col_logo, col_title = st.columns([1, 6]) 
    with col_logo:
        try: st.image("icon_RGB-01.png", width=140)
        except: st.warning("No Logo")
    with col_title:
        st.title("SSH Annual Report")
        st.caption("Financial Data Entry System")

    df_countries, df_accounts = load_config_data()
    if df_countries.empty: st.stop()

    # --- SEZIONE CONFIGURAZIONE ---
    st.markdown("### Configurazione") # Sostituito ui.table_header
    st.markdown("---")

    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        col_p = next((c for c in df_countries.columns if 'paese' in c or 'country' in c), df_countries.columns[0])
        lista_paesi = df_countries[col_p].unique().tolist()
        
        st.markdown("**Paese**")
        sel_country = ui.select(options=[""] + lista_paesi, key="sel_country_shadcn")
        
    with col2:
        st.markdown("**Data Chiusura**")
        d_chius = st.date_input("Data", date.today(), label_visibility="collapsed")

    # Logica Valute
    val_code, tasso, note = "", 0.0, ""
    if sel_country:
        try:
            row = df_countries[df_countries[col_p] == sel_country].iloc[0]
            possible_cols = [c for c in df_countries.columns if 'curr' in c or 'val' in c or 'sym' in c]
            val_code = str(row[possible_cols[0]]).strip() if possible_cols else "EUR"
            if val_code in ['nan', '']: val_code = "EUR"

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

    with col3:
        ui.metric_card(title="Valuta", content=val_code, description="Codice ISO")
    with col4:
        ui.metric_card(title="Tasso vs EUR", content=f"{tasso:.4f}", description=note if note else "Storico")

    # --- CALCOLO TOTALI ---
    col_cod = next((c for c in df_accounts.columns if 'code' in c or 'codice' in c), df_accounts.columns[0])
    other_cols = [c for c in df_accounts.columns if c != col_cod]
    col_desc = next((c for c in other_cols if 'desc' in c), other_cols[0] if other_cols else col_cod)
    col_tipo = next((c for c in df_accounts.columns if 'type' in c or 'tipo' in c), None)
    col_classe = next((c for c in df_accounts.columns if 'class' in c or 'classe' in c), None)
    
    calc_df = df_accounts.copy()
    calc_df['classe_calc'] = calc_df[col_classe] if col_classe else calc_df[col_cod].astype(str).str[0]
    calc_df['tipo_calc'] = calc_df[col_tipo] if col_tipo else "Generico"

    display_df = calc_df[[col_cod, col_desc]].copy()
    display_df.columns = ['Codice', 'Descrizione']
    display_df['Importo'] = 0.00
    
    st.markdown("### Inserimento Dati") # Sostituito ui.table_header
    
    edited_df = st.data_editor(
        display_df,
        column_config={
            "Codice": st.column_config.TextColumn(disabled=True),
            "Descrizione": st.column_config.TextColumn(disabled=True),
            "Importo": st.column_config.NumberColumn("Importo", format="%.2f")
        },
        use_container_width=True, hide_index=True, height=400
    )

    if not edited_df.empty:
        active_rows = edited_df[edited_df['Importo'] != 0].copy()
        if not active_rows.empty:
            active_rows['classe'] = calc_df.loc[active_rows.index, 'classe_calc']
            active_rows['tipo'] = calc_df.loc[active_rows.index, 'tipo_calc']
            
            st.markdown("### Riepilogo") # Sostituito ui.table_header
            st.caption("Dati pronti per il salvataggio")
            
            c_tot1, c_tot2, c_tot3 = st.columns(3)
            with c_tot1:
                ui.metric_card(title="Totale", content=f"{active_rows['Importo'].sum():,.2f}", description="EUR")
            with c_tot2: st.dataframe(active_rows.groupby('classe')['Importo'].sum().reset_index(), hide_index=True)
            with c_tot3: st.dataframe(active_rows.groupby('tipo')['Importo'].sum().reset_index(), hide_index=True)

    st.markdown("<br>", unsafe_allow_html=True)

    # --- BOTTONE SALVATAGGIO ---
    if ui.button("REGISTRA NEL DATABASE", key="btn_save", variant="default"):
        if not sel_country: 
            st.error("Seleziona Paese")
        else:
            to_save = edited_df[edited_df['Importo'] != 0]
            if to_save.empty: 
                st.warning("Inserisci importo")
            else:
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
                        st.balloons()
                        ui.badges(badge_list=[("Dati Salvati", "default")], key="badge_ok")
                        time.sleep(2)
                        st.rerun()
                    except Exception as e: st.error(f"Errore: {e}")

# --- 7. LOGIN PAGE ---
if not st.session_state['logged_in']:
    col_c = st.columns([1,2,1])
    with col_c[1]:
        try: st.image("icon_RGB-01.png", width=220)
        except: st.header("SSH FINANCIAL")
        
        st.markdown("### Login") # Sostituito ui.table_header
        st.caption("Accesso Riservato")
        
        user_in = st.text_input("USERNAME", key="input_user")
        pwd_in = st.text_input("PASSWORD", type="password", key="input_pwd")
        
        if ui.button("ENTRA", key="btn_login", variant="default"):
            check_login()
            if st.session_state['logged_in']: st.rerun()
else:
    main_app()
