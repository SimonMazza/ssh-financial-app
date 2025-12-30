import streamlit as st
import pandas as pd
import requests
from supabase import create_client, Client
from datetime import date, datetime # <--- MODIFICA 1: Aggiunto datetime

# --- 1. CONFIGURAZIONE PAGINA E STILE ---
st.set_page_config(page_title="SSH Financial", page_icon="💰", layout="wide")

st.markdown("""
    <style>
    :root { --ssh-red: #A9093B; --ssh-aqua: #058097; --ssh-gray: #525252; }
    h1, h2, h3 { color: var(--ssh-aqua) !important; }
    .stButton>button { background-color: var(--ssh-red); color: white; border: none; width: 100%; padding: 12px; font-weight: bold;}
    .stButton>button:hover { background-color: #80052b; color: white; }
    [data-testid="stDataFrame"] th { background-color: var(--ssh-gray); color: white; }
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
        st.error("Errore nella configurazione dei Secrets. Controlla SUPABASE_URL e SUPABASE_KEY.")
        return None

supabase = init_connection()

# --- 3. CARICAMENTO DATI ---
@st.cache_data(ttl=600)
def load_config_data():
    if not supabase: return pd.DataFrame(), pd.DataFrame()
    try:
        # Carica tabella COUNTRIES
        res_c = supabase.table('COUNTRIES').select("*").execute()
        df_c = pd.DataFrame(res_c.data)
        
        # Carica tabella CHARTS OF ACCOUNTS
        res_a = supabase.table('CHARTS OF ACCOUNTS').select("*").execute()
        df_a = pd.DataFrame(res_a.data)
        
        # NORMALIZZAZIONE COLONNE
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
        st.error(f"Errore caricamento tabelle da Supabase: {e}")
        return pd.DataFrame(), pd.DataFrame()

# --- 4. APP PRINCIPALE ---
def main():
    col_logo, col_title = st.columns([1, 4])
    with col_logo:
        st.image("https://via.placeholder.com/150x80/A9093B/ffffff?text=SSH+LOGO", width=150)
    with col_title:
        st.title("SSH Financial System")
        st.caption("Database: Supabase SQL")

    df_countries, df_accounts = load_config_data()

    if df_countries.empty or df_accounts.empty:
        st.warning("⚠️ Impossibile caricare i dati.")
        st.stop()

    st.divider()

    # --- INPUT ---
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        col_paese = next((c for c in df_countries.columns if 'paese' in c or 'country' in c), df_countries.columns[0])
        lista_paesi = df_countries[col_paese].unique().tolist()
        selected_country = st.selectbox("Seleziona Paese", [""] + lista_paesi)
    
    with col2:
        data_chiusura = st.date_input("Data di Chiusura", date.today())

    # --- LOGICA VALUTA ---
    valuta_code = "EUR"
    tasso = 1.0
    note = ""

    if selected_country:
        row = df_countries[df_countries[col_paese] == selected_country].iloc[0]
        col_valuta = next((c for c in df_countries.columns if 'currency' in c or 'valuta' in c or 'symbol' in c), None)
        
        if col_valuta: valuta_code = row[col_valuta]
        else: valuta_code = "EUR"
            
        if valuta_code != 'EUR':
            api_key = st.secrets["EXCHANGERATE_API_KEY"]
            try:
                url = f"https://v6.exchangerate-api.com/v6/{api_key}/history/{valuta_code}/{data_chiusura.year}/{data_chiusura.month}/{data_chiusura.day}"
                res = requests.get(url)
                if res.status_code == 403: raise Exception("Plan Limit")
                data = res.json()
                if data['result'] == 'success': tasso = data['conversion_rates']['EUR']
            except:
                try: 
                    url = f"https://v6.exchangerate-api.com/v6/{api_key}/latest/{valuta_code}"
                    res = requests.get(url).json()
                    tasso = res['conversion_rates']['EUR']
                    note = "⚠️ Cambio Odierno"
                except:
                    note = "Errore API"

    with col3: st.text_input("Valuta", value=valuta_code, disabled=True)
    with col4: st.text_input("Tasso vs EUR", value=f"{tasso:.6f}", disabled=True, help=note)

    # --- EDITOR TABELLA ---
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

    # --- SALVATAGGIO ---
    if st.button("REGISTRA NEL DATABASE", type="primary"):
        if not selected_country:
            st.error("Seleziona un Paese.")
            return
            
        to_save = edited_df[edited_df['Importo'] != 0]
        if to_save.empty:
            st.warning("Inserisci almeno un importo.")
            return

        with st.spinner("Salvataggio su Supabase..."):
            try:
                records = []
                # Calcoliamo il timestamp ADESSO per usarlo come ID univoco
                # Attenzione: se inserisci molte righe insieme, è meglio aggiungere un contatore 
                # o usare un UUID, ma per ora usiamo il timestamp corrente
                current_time = datetime.now().isoformat()
                
                for idx, row in to_save.iterrows():
                    # Creiamo un ID univoco aggiungendo l'indice per evitare duplicati esatti al millisecondo
                    unique_id = datetime.now().isoformat()
                    
                    records.append({
                        "ID": unique_id, # <--- MODIFICA 2: Invio l'ID come Timestamp
                        "PAESE": selected_country,
                        "ANNO": int(data_chiusura.year),
                        "VALUTA": valuta_code,
                        "TASSO DI CAMBIO": float(tasso),
                        "DATA CHIUSURA": data_chiusura.isoformat(),
                        "CODICE CONTO": str(row['Codice']),
                        "IMPORTO": float(row['Importo'])
                    })
                
                supabase.table('DATABASE').insert(records).execute()
                
                st.success(f"✅ Dati salvati con successo!")
                st.balloons()
                
            except Exception as e:
                st.error(f"Errore durante il salvataggio: {e}")
                st.write("Dettaglio errore:", e)

if __name__ == "__main__":
    main()
