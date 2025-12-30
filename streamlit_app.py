import streamlit as st
import pandas as pd
import requests
from supabase import create_client, Client
from datetime import date

# --- 1. CONFIGURAZIONE PAGINA E STILE ---
st.set_page_config(page_title="SSH Financial", page_icon="💰", layout="wide")

st.markdown("""
    <style>
    :root { --ssh-red: #A9093B; --ssh-aqua: #058097; --ssh-gray: #525252; }
    h1, h2, h3 { color: var(--ssh-aqua) !important; }
    .stButton>button { background-color: var(--ssh-red); color: white; border: none; width: 100%; padding: 12px; }
    .stButton>button:hover { background-color: #80052b; color: white; }
    </style>
""", unsafe_allow_html=True)

# --- 2. CONNESSIONE SUPABASE (MODALITÀ API) ---
@st.cache_resource
def init_connection():
    url = st.secrets["SUPABASE_URL"]
    key = st.secrets["SUPABASE_KEY"]
    return create_client(url, key)

supabase = init_connection()

# --- 3. CARICAMENTO DATI ---
@st.cache_data(ttl=600)
def load_config_data():
    try:
        # Chiamata API invece di SQL: molto più veloce e stabile
        response_c = supabase.table('countries_config').select("*").execute()
        response_a = supabase.table('accounts_config').select("*").execute()
        
        df_c = pd.DataFrame(response_c.data)
        df_a = pd.DataFrame(response_a.data)
        
        # Ordina se i dati esistono
        if not df_c.empty: df_c = df_c.sort_values('paese')
        if not df_a.empty: df_a = df_a.sort_values('code')
        
        return df_c, df_a
    except Exception as e:
        st.error(f"Errore connessione Supabase: {e}")
        return pd.DataFrame(), pd.DataFrame()

# --- 4. MAIN APP ---
def main():
    col_logo, col_title = st.columns([1, 4])
    with col_logo:
        st.image("https://via.placeholder.com/150x80/A9093B/ffffff?text=SSH+LOGO", width=150)
    with col_title:
        st.title("SSH Financial System")
        st.caption("Powered by Supabase API")

    df_countries, df_accounts = load_config_data()

    if df_countries.empty:
        st.warning("Nessun dato trovato su Supabase. Controlla i nomi delle tabelle.")
        st.stop()

    st.divider()

    # INPUT
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        lista_paesi = df_countries['paese'].unique().tolist()
        selected_country = st.selectbox("Seleziona Paese", [""] + lista_paesi)
    with col2:
        data_chiusura = st.date_input("Data di Chiusura", date.today())

    # VALUTA E CAMBIO
    valuta_code = "EUR"
    tasso = 1.0
    note = ""

    if selected_country:
        row = df_countries[df_countries['paese'] == selected_country].iloc[0]
        # Adatta i nomi se diversi su Supabase (es. currency_code)
        valuta_code = row.get('currency_code', 'EUR')
        
        if valuta_code != 'EUR':
            api_key = st.secrets["EXCHANGERATE_API_KEY"]
            try:
                # API History
                url = f"https://v6.exchangerate-api.com/v6/{api_key}/history/{valuta_code}/{data_chiusura.year}/{data_chiusura.month}/{data_chiusura.day}"
                res = requests.get(url)
                if res.status_code == 403: raise Exception("Free Plan")
                data = res.json()
                if data['result'] == 'success': tasso = data['conversion_rates']['EUR']
            except:
                try: # API Latest (Fallback)
                    url = f"https://v6.exchangerate-api.com/v6/{api_key}/latest/{valuta_code}"
                    res = requests.get(url).json()
                    tasso = res['conversion_rates']['EUR']
                    note = "⚠️ Cambio Odierno"
                except:
                    note = "Errore API"

    with col3: st.text_input("Valuta", value=valuta_code, disabled=True)
    with col4: st.text_input("Tasso vs EUR", value=f"{tasso:.6f}", disabled=True, help=note)

    # TABELLA
    st.subheader("Inserimento Saldi")
    input_df = df_accounts.copy()[['code', 'description']]
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

    # SALVATAGGIO VIA API
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
                for _, row in to_save.iterrows():
                    records.append({
                        "paese": selected_country,
                        "anno": int(data_chiusura.year),
                        "valuta": valuta_code,
                        "tasso": float(tasso),
                        "data_chiusura": data_chiusura.isoformat(),
                        "codice": row['code'],
                        "descrizione": row['description'],
                        "importo": float(row['Importo']),
                        "tipo": "Input"
                    })
                
                # Insert API Call
                supabase.table('financial_entries').insert(records).execute()
                
                st.success("✅ Dati salvati con successo!")
                st.balloons()
            except Exception as e:
                st.error(f"Errore salvataggio: {e}")

if __name__ == "__main__":
    main()
