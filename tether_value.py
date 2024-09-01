import os
import requests
import logging
from datetime import datetime
from dotenv import load_dotenv
from bs4 import BeautifulSoup

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

# Function to fetch the lowest value of Tether against NZD in the past month
def fetch_lowest_value():
    try:
        response = requests.get(f"{COINGECKO_API_URL}/coins/{CURRENCY_PAIR}/market_chart?vs_currency={COMPARE_CURRENCY}&days=30")
        response.raise_for_status()
        prices = response.json()['prices']
        lowest_value = min(price[1] for price in prices)
        logging.debug(f"Lowest value in the past month fetched: {lowest_value} NZD")
        return float(lowest_value)
    except Exception as e:
        logging.error(f"Failed to fetch lowest value: {e}")
        raise

# Function to fetch the circulating supply of Tether
def fetch_tether_data():
    try:
        response = requests.get(f"{COINGECKO_API_URL}/coins/{CURRENCY_PAIR}")
        response.raise_for_status()
        circulating_supply = response.json()['market_data']['circulating_supply']
        logging.debug(f"Tether circulating supply fetched: {circulating_supply}")
        return float(circulating_supply)
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
        fear_greed_data = response.json()['data'][0]
        fear_greed_index = fear_greed_data['value']
        value_classification = fear_greed_data['value_classification']
        logging.debug(f"Fear and Greed Index fetched: {fear_greed_index} - {value_classification}")
        return int(fear_greed_index), value_classification
    except Exception as e:
        logging.error(f"Failed to fetch Fear and Greed Index: {e}")
        raise

# Function to fetch the VIX from Yahoo Finance
def fetch_vix_yahoo():
    try:
        url = "https://finance.yahoo.com/quote/%5EVIX/"
        response = requests.get(url)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, 'html.parser')
        vix_span = soup.find('fin-streamer', {'data-symbol': '^VIX', 'data-field': 'regularMarketPrice'})
        if vix_span:
            vix_value = vix_span.text
            logging.debug(f"VIX fetched: {vix_value}")
            return float(vix_value)
        else:
            raise Exception("VIX value not found on Yahoo Finance")
    except Exception as e:
        logging.error(f"Failed to fetch VIX: {e}")
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
    rank_mapping = {month: rank for rank, (month, _) in enumerate(sorted_tokens, start=1)}
    sorted_months = sorted(generated_tokens.keys(), key=lambda x: datetime.strptime(x, '%B'))

    rank_message = "This ranks {} place with the most tethers printed within the month:\n\n".format(
        rank_mapping[datetime.now().strftime("%B")]
    )

    for month in sorted_months:
        amount = generated_tokens[month]
        rank = rank_mapping[month]
        formatted_amount = f"{amount / 1e9:.2f}B" if amount >= 1e9 else f"{amount / 1e6:.2f}M"
        rank_message += "( No.{} place ) {} : {}\n".format(rank, month, formatted_amount)
    
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
        lowest_value = fetch_lowest_value()
        tether_supply = fetch_tether_data()
        bitcoin_value = fetch_bitcoin_value()
        fear_greed_index, value_classification = fetch_fear_greed_index()
        vix_value = fetch_vix_yahoo()

        historical_data = read_historical_supply()

        # Update historical data if today is the 1st of the month
        today = datetime.now()
        current_month = today.strftime("%B")

        if today.day == 1:
            logging.debug(f"Updating historical data for {current_month}.")
            historical_data[current_month] = round(tether_supply)
            save_historical_supply(historical_data)
            logging.debug(f"Historical supply data updated with {current_month}: {tether_supply}")

        generated_tokens = calculate_generated_tokens(historical_data)
        rank_message = rank_generated_tokens(generated_tokens)

        percentage_increase_value = ((current_value - lowest_value) / lowest_value) * 100
        percentage_increase_supply = ((tether_supply - historical_data[current_month]) / historical_data[current_month]) * 100

        # Prepare the message
        message = (f"Tether is : {current_value:.2f} NZD. This is a {percentage_increase_value:.2f}% increase in value compared with the lowest value over the past month.\n\n"
                   f"Tether tokens in circulation: {tether_supply:,.2f} USDT, which is a {percentage_increase_supply:.2f}% increase compared with the beginning of this month.\n\n"
                   f"Tether tokens generated so far this month : {generated_tokens[current_month]:,.0f}\n\n"
                   f"{rank_message}\n"
                   f"Bitcoin's currency value is : ${bitcoin_value:,.2f} NZD\n\n"
                   f"Bitcoin's Fear and Greed Index is at {fear_greed_index}% - Indicating: {value_classification} in the market\n\n"
                   f"The Stock Market VIX is : {vix_value}")

        send_slack_message(message)

        # Save the historical data
        save_historical_supply(historical_data)
    except Exception as e:
        logging.error(f"An error occurred in the main process: {e}")


if __name__ == "__main__":
    main()
