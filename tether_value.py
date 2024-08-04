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
FEAR_GREED_API_URL = "https://api.alternative.me/fng/"  # Example endpoint for Fear and Greed Index
HISTORICAL_SUPPLY_FILE = 'historical_supply.txt'  # A file to store historical supply data for ranking

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

# Function to fetch the Fear and Greed Index for Bitcoin
def fetch_fear_greed_index():
    try:
        response = requests.get(FEAR_GREED_API_URL)
        response.raise_for_status()
        fear_greed_index = response.json()['data'][0]['value']
        logging.debug(f"Fear and Greed Index fetched: {fear_greed_index}")
        return fear_greed_index
    except Exception as e:
        logging.error(f"Failed to fetch Fear and Greed Index: {e}")
        raise

# Function to fetch historical supply data for ranking
def fetch_historical_supply():
    if not os.path.exists(HISTORICAL_SUPPLY_FILE):
        # If the file doesn't exist, create it with some dummy data
        historical_supply = {
            "January": 49324574.36,
            "February": 49324573.22,
            "March": 49324577.36,
            "April": 49324575.53,
            "May": 49324578.32,
            "June": 49324572.11,
            "July": 49324576.33,
            "August": 0.0  # Placeholder for current month's data
        }
        save_historical_supply(historical_supply)
    else:
        with open(HISTORICAL_SUPPLY_FILE, 'r') as file:
            historical_supply = eval(file.read().strip())
    return historical_supply

# Function to save historical supply data
def save_historical_supply(historical_supply):
    with open(HISTORICAL_SUPPLY_FILE, 'w') as file:
        file.write(str(historical_supply))

# Function to calculate the rank of the current month
def calculate_ranking(historical_supply, current_month, current_supply):
    historical_supply[current_month] = current_supply
    sorted_supply = sorted(historical_supply.items(), key=lambda item: item[1], reverse=True)
    ranking = {month: rank+1 for rank, (month, _) in enumerate(sorted_supply)}
    return ranking, sorted_supply

# Function to generate the message for Slack
def generate_message(current_value, percentage_change, current_circulating_supply, supply_percentage_change, dollar_difference, ranking, sorted_supply, fear_greed_index):
    formatted_circulating_supply = "{:,.0f}".format(current_circulating_supply)
    formatted_dollar_difference = "{:,.2f}".format(abs(dollar_difference))
    
    message = (
        f"Tether is : {current_value:.2f} NZD. "
        f"This is a {percentage_change:.2f}% {'increase' if percentage_change > 0 else 'decrease'} "
        f"in value compared with the lowest value over the past month.\n\n"
        f"Tether tokens in circulation: {formatted_circulating_supply} USDT, "
        f"which is a {supply_percentage_change:.2f}% "
        f"{'increase' if supply_percentage_change > 0 else 'decrease'} compared with the beginning of this month.\n\n"
        f"Tether tokens generated so far this month: {formatted_dollar_difference}\n"
        f"This ranks August {ranking['August']} place with the most tethers printed within the month:\n\n"
    )
    
    for rank, (month, supply) in enumerate(sorted_supply, 1):
        formatted_supply = "{:,.2f}".format(supply)
        message += f"({rank}th place) {month} : {formatted_supply}\n"
    
    message += f"\nBitcoin's Fear and Greed Index is at {fear_greed_index}% - Indicating: {'Fear' if int(fear_greed_index) < 50 else 'Greed'} in the market"
    
    return message

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
        
        # Read the circulating supply from the beginning of the month
        start_of_month_supply = fetch_historical_supply().get("August", current_circulating_supply)
        
        # Calculate the percentage change in circulating supply
        supply_percentage_change = ((current_circulating_supply - start_of_month_supply) / start_of_month_supply) * 100
        
        # Calculate the difference in dollar value
        dollar_difference = (current_circulating_supply - start_of_month_supply) * current_value
        
        # Fetch the historical supply data
        historical_supply = fetch_historical_supply()
        
        # Calculate the ranking
        current_month = datetime.now().strftime("%B")
        ranking, sorted_supply = calculate_ranking(historical_supply, current_month, dollar_difference)
        
        # Save the updated historical supply data
        save_historical_supply(historical_supply)
        
        # Fetch the Fear and Greed Index for Bitcoin
        fear_greed_index = fetch_fear_greed_index()
        
        percentage_change = ((current_value - lowest_value) / lowest_value) * 100
        message = generate_message(current_value, percentage_change, current_circulating_supply, supply_percentage_change, dollar_difference, ranking, sorted_supply, fear_greed_index)
        
        send_slack_alert(SLACK_BOT_TOKEN, CHANNEL, message)
    except Exception as e:
        logging.error(f"Error in main execution: {e}")

if __name__ == "__main__":
    main()
