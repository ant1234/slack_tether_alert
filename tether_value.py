import os
import requests
import logging
from datetime import datetime, timedelta
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

# Function to fetch the current value of Tether against NZD
def fetch_current_value():
    try:
        response = requests.get(f"{COINGECKO_API_URL}/simple/price?ids={CURRENCY_PAIR}&vs_currencies={COMPARE_CURRENCY}")
        response.raise_for_status()
        current_value = response.json()[CURRENCY_PAIR][COMPARE_CURRENCY]
        logging.debug(f"Current value fetched: {current_value} NZD")
        return current_value
    except Exception as e:
        logging.error(f"Failed to fetch current value: {e}")
        raise

# Function to fetch the historical values of Tether against NZD for the past month
def fetch_historical_values():
    end_date = datetime.now()
    start_date = end_date - timedelta(days=30)
    try:
        response = requests.get(
            f"{COINGECKO_API_URL}/coins/{CURRENCY_PAIR}/market_chart/range",
            params={
                "vs_currency": COMPARE_CURRENCY,
                "from": int(start_date.timestamp()),
                "to": int(end_date.timestamp())
            }
        )
        response.raise_for_status()
        prices = response.json()["prices"]
        logging.debug(f"Historical prices fetched: {prices}")
        return prices
    except Exception as e:
        logging.error(f"Failed to fetch historical values: {e}")
        raise

# Function to find the lowest value in the past month
def find_lowest_value(prices):
    try:
        lowest = min(prices, key=lambda x: x[1])
        logging.debug(f"Lowest value found: {lowest[1]} NZD")
        return lowest[1]
    except Exception as e:
        logging.error(f"Failed to find lowest value: {e}")
        raise

# Function to fetch the circulating supply of Tether
def fetch_tether_data():
    try:
        response = requests.get(f"{COINGECKO_API_URL}/coins/{CURRENCY_PAIR}")
        response.raise_for_status()
        circulating_supply = response.json()['market_data']['circulating_supply']
        logging.debug(f"Tether circulating supply fetched: {circulating_supply}")
        return circulating_supply
    except Exception as e:
        logging.error(f"Failed to fetch tether data: {e}")
        raise

# Function to send an alert to Slack
def send_slack_alert(token, channel, message):
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {token}"
    }
    data = {
        "channel": channel,
        "text": message
    }
    try:
        response = requests.post(SLACK_API_URL, headers=headers, json=data)
        response.raise_for_status()
        if not response.json().get('ok'):
            logging.error(f"Slack API error: {response.json()}")
        logging.debug(f"Slack message sent: {message}")
    except Exception as e:
        logging.error(f"Failed to send Slack alert: {e}")
        raise

def main():
    try:
        current_value = fetch_current_value()
        historical_values = fetch_historical_values()
        lowest_value = find_lowest_value(historical_values)
        
        # Fetch current circulating supply of Tether
        current_circulating_supply = fetch_tether_data()
        
        # Read the circulating supply from three days ago
        three_days_ago_file = 'three_days_ago_supply.txt'
        if os.path.exists(three_days_ago_file):
            with open(three_days_ago_file, 'r') as file:
                three_days_ago_supply = float(file.read().strip())
        else:
            three_days_ago_supply = current_circulating_supply
        
        # Calculate the percentage change in circulating supply
        supply_percentage_change = ((current_circulating_supply - three_days_ago_supply) / three_days_ago_supply) * 100
        
        # Update the circulating supply from three days ago
        with open(three_days_ago_file, 'w') as file:
            file.write(str(current_circulating_supply))
        
        # Format circulating supply as number
        formatted_circulating_supply = "{:,.0f}".format(current_circulating_supply)
        
        percentage_change = ((current_value - lowest_value) / lowest_value) * 100
        message = (f"Today's value of Tether is : {current_value:.2f} NZD. "
                   f"This is a {percentage_change:.2f}% {'increase' if percentage_change > 0 else 'decrease'} "
                   f"in value compared with the lowest value over the past month.\n"
                   f"Tether tokens in circulation: {formatted_circulating_supply} USDT, "
                   f"which is a {supply_percentage_change:.2f}% "
                   f"{'increase' if supply_percentage_change >= 0 else 'decrease'} compared with three days ago.")
        
        if supply_percentage_change > 5:
            message += "\nAlert: The number of Tether tokens in circulation has increased by more than 5% in the last three days."
        
        send_slack_alert(SLACK_BOT_TOKEN, CHANNEL, message)
    except Exception as e:
        logging.error(f"Error in main execution: {e}")

if __name__ == "__main__":
    main()
