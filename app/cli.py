import click
from datetime import datetime
from db_data import m_db_data


@click.group()
def cli():
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
    
    if not (1 <= (end_block - start_block + 1) <= 100):
        click.echo(click.style(f"Error: Block range must be between 1 and 100 blocks. "
                                f"Provided range: {start_block}-{end_block} ({end_block - start_block + 1} blocks).", fg='red'))
        return

    click.echo(f"Starting Etherscan API scraping from block {start_block} to {end_block}...")
    
    if method:
        click.echo(f"Filtering by method(s): {', '.join(method)}")
    if amount:
        click.echo(f"Filtering by amount: {amount}")


    state = m_db_data.process_blocks(start_block, end_block, method, amount)
    click.echo(click.style(f"\nScraping complete for blocks {start_block}-{end_block}.", fg='green'))
    click.echo(f"Total transactions scraped (after API calls): {state["scraped"]}")
    click.echo(f"Total transactions saved to DB (after filters and uniqueness check): {state["saved"]}")


@cli.command()
def count_transactions():
    """Counts the total number of transactions in the database."""
    count = m_db_data.transaction_count()
    click.echo(f"Total transactions in database: {count}")


@cli.command()
@click.option('--block', type=int, help='Filter by block number.')
@click.option('--hash', type=str, help='Filter by transaction hash.')
@click.option('--method', type=str, multiple=True, help='Filter by transaction method.')
@click.option('--amount', type=str, default=None, help='Filter by amount: "0" for zero value, "not-0" for non-zero value.')
def show_transactions(block, hash, method, amount):
    if amount not in ('0', 'not-0'):
        click.echo(click.style("Invalid --amount filter. Use '0' or 'not-0'.", fg='red'))
        return 
    
    transactions = m_db_data.filter_transactions(block, hash, method, amount)
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