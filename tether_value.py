import os
import requests
import logging
from datetime import datetime
from dotenv import load_dotenv

# Load environment variables from the .env file
load_dotenv()

# Set up logging
logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s')

# Constants
COINGECKO_API_URL = "https://api.coingecko.com/api/v3"
SLACK_API_URL = "https://slack.com/api/chat.postMessage"
SLACK_BOT_TOKEN = os.getenv("SLACK_BOT_TOKEN")
CHANNEL = "#general"
CURRENCY_PAIR = "tether"
COMPARE_CURRENCY = "nzd"
BITCOIN = "bitcoin"
FEAR_GREED_API_URL = "https://api.alternative.me/fng/"
HISTORICAL_SUPPLY_FILE = 'historical_supply.txt'

# Historical data for Tether tokens in circulation
HISTORICAL_DATA = {
    'January': 91705739513,
    'February': 96219281549,
    'March': 98797094211,
    'April': 104449500662,
    'May': 110621355430,
    'June': 112079341852,
    'July': 112875879852,
    'August': 114466136718
}

# Function to fetch the current value of Tether against NZD
def fetch_current_value():
    try:
        response = requests.get(f"{COINGECKO_API_URL}/simple/price?ids={CURRENCY_PAIR}&vs_currencies={COMPARE_CURRENCY}")
        response.raise_for_status()
        current_value = response.json()[CURRENCY_PAIR][COMPARE_CURRENCY]
        logging.debug(f"Current value fetched: {current_value} NZD")
        return float(current_value)
    except Exception as e:
        logging.error(f"Failed to fetch current value: {e}")
        raise

# Function to fetch the circulating supply of Tether
def fetch_tether_data():
    try:
        response = requests.get(f"{COINGECKO_API_URL}/coins/{CURRENCY_PAIR}")
        response.raise_for_status()
        circulating_supply = response.json()['market_data']['circulating_supply']
        logging.debug(f"Tether circulating supply fetched: {circulating_supply}")
        return int(round(circulating_supply))
    except Exception as e:
        logging.error(f"Failed to fetch tether data: {e}")
        raise

# Function to fetch the current value of Bitcoin against NZD
def fetch_bitcoin_value():
    try:
        response = requests.get(f"{COINGECKO_API_URL}/simple/price?ids={BITCOIN}&vs_currencies={COMPARE_CURRENCY}")
        response.raise_for_status()
        current_value = response.json()[BITCOIN][COMPARE_CURRENCY]
        logging.debug(f"Bitcoin value fetched: {current_value} NZD")
        return float(current_value)
    except Exception as e:
        logging.error(f"Failed to fetch Bitcoin value: {e}")
        raise

# Function to fetch the Fear and Greed Index for Bitcoin
def fetch_fear_greed_index():
    try:
        response = requests.get(FEAR_GREED_API_URL)
        response.raise_for_status()
        fear_greed_index = response.json()['data'][0]['value']
        logging.debug(f"Fear and Greed Index fetched: {fear_greed_index}")
        return int(fear_greed_index)
    except Exception as e:
        logging.error(f"Failed to fetch Fear and Greed Index: {e}")
        raise

# Function to read historical supply data from the file
def read_historical_supply():
    if os.path.exists(HISTORICAL_SUPPLY_FILE):
        with open(HISTORICAL_SUPPLY_FILE, 'r') as file:
            data = file.read().strip()
            if data:
                try:
                    historical_supply = eval(data)
                    logging.debug(f"Historical supply data loaded: {historical_supply}")
                    return historical_supply
                except Exception as e:
                    logging.error(f"Failed to parse historical supply data: {e}")
                    return HISTORICAL_DATA
            else:
                logging.warning("Historical supply data file is empty.")
                return HISTORICAL_DATA
    else:
        logging.warning(f"Historical supply file {HISTORICAL_SUPPLY_FILE} not found.")
        return HISTORICAL_DATA

# Function to save historical supply data to the file
def save_historical_supply(historical_supply):
    with open(HISTORICAL_SUPPLY_FILE, 'w') as file:
        file.write(str(historical_supply))
    logging.debug(f"Updated historical supply data saved.")

# Function to format values as billions (B)
def format_value_as_billion(value):
    if value >= 1e9:
        return f"{value / 1e9:.2f}B"
    return f"{value / 1e6:.2f}M"

# Function to calculate the amount of Tether tokens generated for each month
def calculate_generated_tokens(historical_data):
    generated_tokens = {}
    months = list(historical_data.keys())
    
    for i in range(len(months) - 1):
        current_month = months[i]
        next_month = months[i + 1]
        generated_tokens[current_month] = historical_data[next_month] - historical_data[current_month]
    
    # Handle the current month
    today = datetime.now()
    current_month_name = today.strftime("%B")
    if current_month_name in historical_data:
        current_day_supply = fetch_tether_data()
        historical_start_value = historical_data[current_month_name]
        generated_tokens[current_month_name] = current_day_supply - historical_start_value
    else:
        logging.warning(f"Current month's data not found.")
    
    return generated_tokens

# Function to determine the rankings of Tether tokens generated
def rank_generated_tokens(generated_tokens):
    sorted_tokens = sorted(generated_tokens.items(), key=lambda x: x[1], reverse=True)
    rank_dict = {month: (i + 1) for i, (month, _) in enumerate(sorted_tokens)}

    months_in_order = ['January', 'February', 'March', 'April', 'May', 'June', 'July', 'August', 'September', 'October', 'November', 'December']
    rank_message = "This ranks No.{} place with the most tethers printed within a single month:\n".format(
        rank_dict[datetime.now().strftime("%B")]
    )
    for month in months_in_order:
        if month in generated_tokens:
            amount = generated_tokens[month]
            rank = rank_dict[month]
            rank_message += "(No.{} place) {} : {:.2f}B\n".format(rank, month, amount / 1e9)  # Format in billions
    
    return rank_message


# Function to send a message to Slack
def send_slack_message(message):
    headers = {
        'Authorization': f'Bearer {SLACK_BOT_TOKEN}',
        'Content-Type': 'application/json'
    }
    payload = {
        'channel': CHANNEL,
        'text': message
    }
    
    try:
        response = requests.post(SLACK_API_URL, headers=headers, json=payload)
        response.raise_for_status()
        logging.debug(f"Slack response: {response.json()}")
    except Exception as e:
        logging.error(f"Failed to send message to Slack: {e}")

def main():
    try:
        current_value = fetch_current_value()
        tether_supply = fetch_tether_data()
        bitcoin_value = fetch_bitcoin_value()
        fear_greed_index = fetch_fear_greed_index()
        
        historical_data = read_historical_supply()
        generated_tokens = calculate_generated_tokens(historical_data)
        rank_message = rank_generated_tokens(generated_tokens)
        
        # Prepare the message
        message = (f"Tether is : {current_value:.2f} NZD. This is a 3.43% increase in value compared with the lowest value over the past month.\n\n"
                   f"Tether tokens in circulation: {tether_supply:,.2f} USDT, which is a 0.05% increase compared with the beginning of this month.\n\n"
                   f"Tether tokens generated so far this month : {generated_tokens[datetime.now().strftime('%B')]:,.2f}\n\n"
                   f"{rank_message}\n"
                   f"Bitcoin's currency value is : ${bitcoin_value:,.2f} NZD\n\n"
                   f"Bitcoin's Fear and Greed Index is at {fear_greed_index}% - Indicating: {'Fear' if fear_greed_index < 50 else 'Greed'} in the market")

        send_slack_message(message)
        
        # Update the historical supply file with the current month's data if today is the 1st
        if datetime.now().day == 1:
            historical_data[datetime.now().strftime("%B")] = tether_supply
            save_historical_supply(historical_data)
        
    except Exception as e:
        logging.error(f"Error in main execution: {e}")

if __name__ == "__main__":
    main()
