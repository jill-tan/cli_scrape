import os
import requests
import time
from decimal import Decimal
from web3 import Web3 
import logging
from dotenv import load_dotenv

load_dotenv()

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

ETHERSCAN_API_KEY = os.getenv('ETHERSCAN_API_KEY')
ETHERSCAN_API_URL = os.getenv('ETHERSCAN_API_URL', 'https://api.etherscan.io/api')
WEB3_PROVIDER_URL = os.getenv('WEB3_PROVIDER_URL') # e.g., Infura or Alchemy URL

try:
    w3 = Web3(Web3.HTTPProvider(WEB3_PROVIDER_URL))
    if not w3.is_connected():
        logging.error("Failed to connect to Web3 provider. Check WEB3_PROVIDER_URL in .env")
        w3 = None 
except Exception as e:
    logging.error(f"Error initializing Web3 provider: {e}. Check WEB3_PROVIDER_URL in .env")
    w3 = None

def wei_to_ether(wei_value: int) -> Decimal:
    """Converts Wei to Ether."""
    return Decimal(wei_value) / Decimal('1e18')

def hex_to_int(hex_str: str) -> int:
    """Converts a hexadecimal string (like '0x...') to an integer."""
    if hex_str:
        return int(hex_str, 16)
    return 0

def get_block_transactions_from_web3(block_number: int) -> list:
    """
    Gets all transaction hashes for a given block number using Web3.py.
    This is the standard way to get all transactions in a block.
    """
    if w3 is None:
        logging.error("Web3 provider not connected. Cannot fetch block transactions.")
        return []

    try:
        block = w3.eth.get_block(block_number, full_transactions=False) # Only get hashes
        tx_hashes = [tx.hex() for tx in block.transactions]
        logging.info(f"Found {len(tx_hashes)} transactions in block {block_number} via Web3.")
        return tx_hashes
    except Exception as e:
        logging.error(f"Error fetching block {block_number} transactions via Web3: {e}")
        return []

def scrape_transaction_details_from_api(tx_hash: str) -> dict or None:
    """
    Scrapes transaction details for a single transaction hash using Etherscan API.
    API documentation: https://etherscan.io/apis#transactions
    Module: transaction, Action: gettxinfo
    """
    params = {
        'module': 'proxy', # Using 'proxy' module for get transaction receipt
        'action': 'eth_getTransactionReceipt',
        'txhash': tx_hash,
        'apikey': ETHERSCAN_API_KEY
    }
    
    tx_params = {
        'module': 'proxy',
        'action': 'eth_getTransactionByHash',
        'txhash': tx_hash,
        'apikey': ETHERSCAN_API_KEY
    }

    try:
        # Get transaction details (from, to, value, input)
        tx_response = requests.get(ETHERSCAN_API_URL, params=tx_params, timeout=10)
        tx_response.raise_for_status()
        tx_data = tx_response.json()

        if tx_data.get('status') == '0' or tx_data.get('result') is None:
            logging.error(f"Etherscan API error for eth_getTransactionByHash {tx_hash}: {tx_data.get('message', 'Unknown error')}")
            return None
        
        tx_result = tx_data['result']

        # Get transaction receipt (status, gasUsed, cumulativeGasUsed)
        receipt_response = requests.get(ETHERSCAN_API_URL, params=params, timeout=10)
        receipt_response.raise_for_status()
        receipt_data = receipt_response.json()

        if receipt_data.get('status') == '0' or receipt_data.get('result') is None:
            logging.error(f"Etherscan API error for eth_getTransactionReceipt {tx_hash}: {receipt_data.get('message', 'Unknown error')}")
            return None
        
        receipt_result = receipt_data['result']
        
        # Parse data
        details = {
            'hash': tx_hash,
            'status': '1' if receipt_result.get('status') == '0x1' else '0', # '0x1' for success, '0x0' for fail
            'block': hex_to_int(tx_result.get('blockNumber')),
            'timestamp': None, 
            'transaction_action': 'Contract Call' if tx_result.get('input') != '0x' else 'Transfer', # Basic inference
            'input_data': tx_result.get('input', '0x'),
            '_from': tx_result.get('from', 'N/A'),
            'to': tx_result.get('to', 'N/A'),
            'value': wei_to_ether(hex_to_int(tx_result.get('value', '0x0'))),
            'gas_price': wei_to_ether(hex_to_int(tx_result.get('gasPrice', '0x0'))), # Gas Price in Wei
            'gas_used': hex_to_int(receipt_result.get('gasUsed', '0x0')),
            'cumulative_gas_used': hex_to_int(receipt_result.get('cumulativeGasUsed', '0x0')),
        }
        
        # Calculate transaction fee
        details['transaction_fee'] = details['gas_price'] * Decimal(details['gas_used'])


        if w3 and details['block'] is not None:
            try:
                block_info = w3.eth.get_block(details['block'])
                details['timestamp'] = block_info.timestamp
            except Exception as e:
                logging.warning(f"Could not get timestamp for block {details['block']} via Web3: {e}")
                details['timestamp'] = None
        
    except requests.exceptions.RequestException as e:
        logging.error(f"Error fetching transaction {tx_hash} from Etherscan API: {e}")
        return None
    except Exception as e:
        logging.error(f"Error parsing transaction {tx_hash} API response: {e}")
        return None
        
    return details
