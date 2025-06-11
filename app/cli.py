import click
import time
from sqlalchemy.exc import IntegrityError
from sqlalchemy import or_
from database import get_db
from models import Transaction, Base
from scraper import get_block_transactions_from_web3, scrape_transaction_details_from_api, w3
from datetime import datetime
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

@click.group()
def cli():
    """A CLI tool to scrape Ethereum transaction data from Etherscan API and Web3.py."""
    pass

@cli.command()
@click.option(
    '--start-block', 
    type=int, 
    required=True, 
    help='Starting block number (inclusive).'
)
@click.option(
    '--end-block', 
    type=int, 
    required=True, 
    help='Ending block number (inclusive). Max 100 block range.'
)
@click.option(
    '--method', 
    type=str, 
    multiple=True, 
    help='Filter by specific transaction method (e.g., "Transfer", "Swap"). Can be repeated.'
)
@click.option(
    '--amount', 
    type=str, 
    default=None, 
    help='Filter by amount: "0" for zero value, "not-0" for non-zero value.'
)
def scrape(start_block, end_block, method, amount):
    """
    Scrapes transaction details for a specified block range using Web3.py and Etherscan API.
    Filters by method and/or amount if provided.
    """
    if not (1 <= (end_block - start_block + 1) <= 100):
        click.echo(click.style(f"Error: Block range must be between 1 and 100 blocks. "
                                f"Provided range: {start_block}-{end_block} ({end_block - start_block + 1} blocks).", fg='red'))
        return

    if w3 is None:
        click.echo(click.style("Error: Web3 provider not connected. Cannot proceed. Check WEB3_PROVIDER_URL in .env", fg='red'))
        return

    click.echo(f"Starting Etherscan API scraping from block {start_block} to {end_block}...")
    
    if method:
        click.echo(f"Filtering by method(s): {', '.join(method)}")
    if amount:
        click.echo(f"Filtering by amount: {amount}")

    total_scraped_txs = 0
    total_saved_txs = 0

    db_gen = get_db()
    db = next(db_gen) # Get the session

    try:
        for block_num in range(start_block, end_block + 1):
            logging.info(f"Processing block: {block_num}")
            
            tx_hashes = get_block_transactions_from_web3(block_num)
            
            for tx_hash in tx_hashes:
                tx_details = scrape_transaction_details_from_api(tx_hash)
                if tx_details:
                    total_scraped_txs += 1
                    
                    passes_filter = True
                    
                    if method:
                        if tx_details.get('transaction_action') is None or \
                           not any(m.lower() in tx_details['transaction_action'].lower() for m in method):
                            passes_filter = False
                    
                    if passes_filter and amount:
                        tx_value = tx_details.get('value')
                        if tx_value is None:
                            passes_filter = False
                        elif amount == '0' and tx_value != 0:
                            passes_filter = False
                        elif amount == 'not-0' and tx_value == 0:
                            passes_filter = False

                    if passes_filter:
                        try:
                            tx_obj = Transaction(
                                hash=tx_details['hash'],
                                status=tx_details['status'],
                                block=tx_details['block'],
                                timestamp=tx_details['timestamp'],
                                transaction_action=tx_details['transaction_action'],
                                _from=tx_details['_from'],
                                to=tx_details['to'],
                                value=tx_details['value'],
                                transaction_fee=tx_details['transaction_fee'],
                                gas_price=tx_details['gas_price'],
                                gas_used=tx_details['gas_used'],
                                cumulative_gas_used=tx_details['cumulative_gas_used'],
                                input_data=tx_details['input_data']
                            )
                            db.add(tx_obj)
                            db.commit()
                            total_saved_txs += 1
                            logging.info(f"Saved transaction {tx_hash} (Block: {block_num})")
                        except IntegrityError:
                            db.rollback()
                            logging.warning(f"Transaction {tx_hash} already exists. Skipping.")
                        except Exception as e:
                            db.rollback()
                            logging.error(f"Error saving transaction {tx_hash}: {e}")
                    else:
                        logging.info(f"Transaction {tx_hash} (Block: {block_num}) skipped due to filter.")
                
                time.sleep(0.3) 
            time.sleep(1) 

        click.echo(click.style(f"\nScraping complete for blocks {start_block}-{end_block}.", fg='green'))
        click.echo(f"Total transactions scraped (after API calls): {total_scraped_txs}")
        click.echo(f"Total transactions saved to DB (after filters and uniqueness check): {total_saved_txs}")

    except Exception as e:
        logging.error(f"An unexpected error occurred during scraping: {e}")
        click.echo(click.style(f"An error occurred: {e}", fg='red'))
    finally:
        db.close()
        try:
            next(db_gen)
        except StopIteration:
            pass

@cli.command()
def count_transactions():
    """Counts the total number of transactions in the database."""
    db_gen = get_db()
    db = next(db_gen)
    try:
        count = db.query(Transaction).count()
        click.echo(f"Total transactions in database: {count}")
    except Exception as e:
        click.echo(click.style(f"Error counting transactions: {e}", fg='red'))
    finally:
        db.close()
        try:
            next(db_gen)
        except StopIteration:
            pass

@cli.command()
@click.option('--block', type=int, help='Filter by block number.')
@click.option('--hash', type=str, help='Filter by transaction hash.')
@click.option('--method', type=str, multiple=True, help='Filter by transaction method.')
@click.option('--amount', type=str, default=None, help='Filter by amount: "0" for zero value, "not-0" for non-zero value.')
def show_transactions(block, hash, method, amount):
    """
    Displays transactions from the database with optional filters.
    """
    db_gen = get_db()
    db = next(db_gen)
    try:
        query = db.query(Transaction)

        if block:
            query = query.filter(Transaction.block == block)
        if hash:
            query = query.filter(Transaction.hash == hash)
        if method:
            method_filters = [Transaction.transaction_action.ilike(f"%{m}%") for m in method]
            query = query.filter(or_(*method_filters))
        if amount:
            if amount == '0':
                query = query.filter(Transaction.value == 0)
            elif amount == 'not-0':
                query = query.filter(Transaction.value != 0)
            else:
                click.echo(click.style("Invalid --amount filter. Use '0' or 'not-0'.", fg='red'))
                return

        transactions = query.limit(20).all() 

        if not transactions:
            click.echo("No transactions found with the specified criteria.")
            return

        click.echo("\n--- Transactions ---")
        for tx in transactions:
            click.echo(f"Hash: {tx.hash}")
            click.echo(f"  Status: {'Success' if tx.status == '1' else 'Fail'}")
            click.echo(f"  Block: {tx.block}")
            click.echo(f"  Timestamp: {datetime.fromtimestamp(tx.timestamp).strftime('%Y-%m-%d %H:%M:%S UTC') if tx.timestamp else 'N/A'}")
            click.echo(f"  Action: {tx.transaction_action}")
            click.echo(f"  From: {tx._from}")
            click.echo(f"  To: {tx.to}")
            click.echo(f"  Value: {tx.value} ETH")
            click.echo(f"  Fee: {tx.transaction_fee} ETH")
            click.echo(f"  Gas Price: {tx.gas_price} ETH (or Gwei converted from Wei)")
            click.echo(f"  Gas Used: {tx.gas_used}")
            click.echo(f"  Cumulative Gas Used: {tx.cumulative_gas_used}")
            click.echo("-" * 30)

    except Exception as e:
        click.echo(click.style(f"Error displaying transactions: {e}", fg='red'))
    finally:
        db.close()
        try:
            next(db_gen)
        except StopIteration:
            pass