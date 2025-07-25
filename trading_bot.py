# === BOT DE TRADING EN ARGENT RÉEL AVEC INTERFACE (STREAMLIT) ===
# Objectif : Trader automatiquement des actions avec Alpaca, avec une interface simple pour régler le niveau de risque

# === 📂 trading_bot.py ===
import yfinance as yf
import streamlit as st

# Streamlit nécessite une exécution dans un terminal local ou sur Streamlit Cloud.
# Ce code NE FONCTIONNE PAS dans des environnements de notebooks (Colab, etc.).

# Contrôle de l'environnement
try:
    import alpaca_trade_api as tradeapi
except ModuleNotFoundError:
    st.error("❌ Le module 'alpaca_trade_api' est manquant. Exécute `pip install alpaca-trade-api` dans un terminal local avant de relancer ce script.")
    st.stop()

# === INTERFACE UTILISATEUR ===
st.set_page_config(page_title="Bot Trading", layout="centered")
st.title("💸 Bot de Trading Automatique")
st.sidebar.header("Configuration du bot")

API_KEY = st.sidebar.text_input("Clé API Alpaca", type="password")
SECRET_KEY = st.sidebar.text_input("Secret API Alpaca", type="password")
MODE = st.sidebar.selectbox("Mode de trading", ["paper", "live"], help="'paper' = démo, 'live' = argent réel")
RISK_LEVEL = st.sidebar.slider("Niveau de risque", 0.0, 1.0, 0.3, 0.1)

symbols_input = st.sidebar.text_input("Actions à trader (ex: AAPL, MSFT, TSLA)", "AAPL,MSFT")
symbols = [s.strip().upper() for s in symbols_input.split(",") if s.strip()]

RUN = st.sidebar.button("🌟 Lancer le bot")

# === CONNEXION API ===
if API_KEY and SECRET_KEY:
    BASE_URL = 'https://paper-api.alpaca.markets' if MODE == 'paper' else 'https://api.alpaca.markets'
    try:
        api = tradeapi.REST(API_KEY, SECRET_KEY, base_url=BASE_URL)
        account = api.get_account()
        capital = float(account.cash)
        st.success(f"Connecté à Alpaca en mode {MODE.upper()} avec {capital:.2f} $")
    except Exception as e:
        st.error(f"Erreur de connexion : {e}")
        st.stop()
else:
    st.warning("Entrez vos clés API pour activer le bot.")
    st.stop()

# === LOGIQUE DE STRATÉGIE ===
def should_buy(symbol):
    data = yf.download(symbol, period="6mo", interval="1d")
    if data.empty:
        return False
    ma10 = data['Close'].rolling(10).mean()
    ma50 = data['Close'].rolling(50).mean()
    return ma10.iloc[-1] > ma50.iloc[-1] and ma10.iloc[-2] <= ma50.iloc[-2]

def compute_qty(price, capital, risk_level):
    part = 0.01 + risk_level * 0.04
    return int((capital * part) // price)

# === LANCEMENT DU BOT ===
if RUN:
    logs = []
    try:
        positions = [pos.symbol for pos in api.list_positions()]
    except Exception as e:
        st.error(f"Impossible de récupérer les positions : {e}")
        st.stop()

    for symbol in symbols:
        try:
            if symbol in positions:
                logs.append(f"🔒 Position déjà ouverte pour {symbol}")
                continue

            if should_buy(symbol):
                today_data = yf.download(symbol, period="1d")
                if today_data.empty:
                    logs.append(f"❌ Aucune donnée aujourd'hui pour {symbol}")
                    continue
                price = today_data['Close'].iloc[-1]
                qty = compute_qty(price, capital, RISK_LEVEL)
                if qty <= 0:
                    logs.append(f"⚠️ Capital insuffisant pour acheter {symbol}")
                    continue
                api.submit_order(
                    symbol=symbol,
                    qty=qty,
                    side='buy',
                    type='market',
                    time_in_force='day',
                    order_class='bracket',
                    stop_loss={'stop_price': round(price * 0.97, 2)}
                )
                logs.append(f"🚀 Acheté {qty} actions de {symbol} à {price:.2f} $")
            else:
                logs.append(f"❌ Pas d'opportunité d'achat pour {symbol}")
        except Exception as e:
            logs.append(f"Erreur sur {symbol} : {e}")

    st.subheader("🔔 Journal des actions")
    for l in logs:
        st.write(l)
