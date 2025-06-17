import os
import requests
from decimal import Decimal
from web3 import Web3 


class Scraper:
    def __init__(self):
        self.ETHERSCAN_API_KEY = os.getenv('ETHERSCAN_API_KEY')
        self.ETHERSCAN_API_URL = os.getenv('ETHERSCAN_API_URL', 'https://api.etherscan.io/api')
        self.WEB3_PROVIDER_URL = os.getenv('WEB3_PROVIDER_URL') 

        self.w3 = Web3(Web3.HTTPProvider(self.WEB3_PROVIDER_URL))
        if not w3.is_connected():
            print("Failed to connect to Web3 provider. Check WEB3_PROVIDER_URL in .env")
            w3 = None


    def wei_to_ether(self, wei_value: int) -> Decimal:
        return Decimal(wei_value) / Decimal('1e18')

    def hex_to_int(self, hex_str: str) -> int:
        if hex_str:
            return int(hex_str, 16)
        return 0

    def get_block_transactions_from_web3(self, block_number: int) -> list:
        if not self.w3 :
            print("Web3 provider not connected. Cannot fetch block transactions.")
            return []

        block = self.w3.eth.get_block(block_number, full_transactions=False) # Only get hashes
        tx_hashes = [tx.hex() for tx in block.transactions]
        print(f"Found {len(tx_hashes)} transactions in block {block_number} via Web3.")
        return tx_hashes


    def scrape_transaction_details_from_api(self, tx_hash: str) -> dict:
        
        params = {
            'module': 'proxy',
            'action': 'eth_getTransactionReceipt',
            'txhash': tx_hash,
            'apikey': self.ETHERSCAN_API_KEY
        }
        
        tx_params = {
            'module': 'proxy',
            'action': 'eth_getTransactionByHash',
            'txhash': tx_hash,
            'apikey': self.ETHERSCAN_API_KEY
        }

        tx_response = requests.get(self.ETHERSCAN_API_URL, params=tx_params, timeout=10)
        tx_response.raise_for_status()
        tx_data = tx_response.json()

        if tx_data.get('status') == '0' or tx_data.get('result') is None:
            print(f"Etherscan API error for eth_getTransactionByHash {tx_hash}: {tx_data.get('message', 'Unknown error')}")
            return None
        
        tx_result = tx_data['result']

        receipt_response = requests.get(self.ETHERSCAN_API_URL, params=params, timeout=10)
        receipt_response.raise_for_status()
        receipt_data = receipt_response.json()

        if receipt_data.get('status') == '0' or receipt_data.get('result') is None:
            print(f"Etherscan API error for eth_getTransactionReceipt {tx_hash}: {receipt_data.get('message', 'Unknown error')}")
            return None
        
        receipt_result = receipt_data['result']
        
        details = {
            'hash': tx_hash,
            'status': '1' if receipt_result.get('status') == '0x1' else '0', # '0x1' for success, '0x0' for fail
            'block': self.hex_to_int(tx_result.get('blockNumber')),
            'timestamp': None, 
            'transaction_action': 'Contract Call' if tx_result.get('input') != '0x' else 'Transfer', # Basic inference
            'input_data': tx_result.get('input', '0x'),
            '_from': tx_result.get('from', 'N/A'),
            'to': tx_result.get('to', 'N/A'),
            'value': self.wei_to_ether(self.hex_to_int(tx_result.get('value', '0x0'))),
            'gas_price': self.wei_to_ether(self.hex_to_int(tx_result.get('gasPrice', '0x0'))), # Gas Price in Wei
            'gas_used': self.hex_to_int(receipt_result.get('gasUsed', '0x0')),
            'cumulative_gas_used': self.hex_to_int(receipt_result.get('cumulativeGasUsed', '0x0')),
        }
        
        details['transaction_fee'] = details['gas_price'] * Decimal(details['gas_used'])
        if self.w3 and details['block']:
            block_info = self.w3.eth.get_block(details['block'])
            details['timestamp'] = block_info.timestamp 
        return details

m_scraper = Scraper()