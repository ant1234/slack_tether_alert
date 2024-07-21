import os
import requests
import datetime
import time
import logging
from dotenv import load_dotenv

# Load environment variables from the .env file
load_dotenv()

# Set up logging
logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s')

# Constants
COINGECKO_API_URL = "https://api.coingecko.com/api/v3"
SLACK_API_URL = "https://slack.com/api/chat.postMessage"
SLACK_BOT_TOKEN = os.getenv("SLACK_BOT_TOKEN")  # Read the token from the environment variable
CHANNEL = "#general"  # Replace with your Slack channel
CURRENCY_PAIR = "tether"
COMPARE_CURRENCY = "nzd"
DATE_FORMAT = "%d-%m-%Y"

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
    end_date = datetime.date.today()
    start_date = end_date - datetime.timedelta(days=30)
    try:
        response = requests.get(
            f"{COINGECKO_API_URL}/coins/{CURRENCY_PAIR}/market_chart/range",
            params={
                "vs_currency": COMPARE_CURRENCY,
                "from": int(time.mktime(start_date.timetuple())),
                "to": int(time.mktime(end_date.timetuple()))
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

# Function to send an alert to Slack
def send_slack_alert(token, channel, current_value, lowest_value):
    percentage_change = ((current_value - lowest_value) / lowest_value) * 100
    message = (f"Today's value of Tether is : {current_value:.2f} NZD. "
               f"This is a {percentage_change:.2f}% {'increase' if percentage_change > 0 else 'decrease'} "
               f"in value compared with the lowest value over the past month.")
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
        send_slack_alert(SLACK_BOT_TOKEN, CHANNEL, current_value, lowest_value)
    except Exception as e:
        logging.error(f"Error in main execution: {e}")

if __name__ == "__main__":
    main()
