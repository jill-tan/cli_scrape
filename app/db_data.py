from database import get_db
from models import Transaction
from sqlalchemy import or_
from contextlib import contextmanager
from scraper import m_scraper

class DBData:

    @contextmanager
    def session_scope(self):
        db_gen = get_db()
        db = next(db_gen)
        try:
            yield db
        finally:
            db.rollback()
            db.close()

    def transaction_count(self):
        with self.session_scope() as db:
            return db.query(Transaction).count()

    def filter_transactions(self, block=None, hash=None, method=None, amount=None, limit=20):
        with self.session_scope() as db:
            query = db.query(Transaction)

            if block:
                query = query.filter(Transaction.block == block)

            if hash:
                query = query.filter(Transaction.hash == hash)

            if method:
                if isinstance(method, str):
                    method = [method]
                method_filters = [
                    Transaction.transaction_action.ilike(f"%{m}%")
                    for m in method
                ]
                query = query.filter(or_(*method_filters))

            if amount:
                if amount == '0':
                    query = query.filter(Transaction.value == 0)
                elif amount == 'not-0':
                    query = query.filter(Transaction.value != 0)
                else:
                    raise ValueError("Invalid amount filter. Use '0' or 'not-0'.")

            return query.limit(limit).all()

    def _passes_filter(self, tx_details: dict, method=None, amount=None) -> bool:
        if method:
            action = tx_details.get('transaction_action')
            if not action or not any(m.lower() in action.lower() for m in method):
                return False

        if amount:
            value = tx_details.get('value')
            if value is None:
                return False
            if amount == '0' and value != 0:
                return False
            if amount == 'not-0' and value == 0:
                return False

        return True

    def _save_transaction(self, tx_details: dict) -> bool:
        with self.session_scope() as db:
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

    def process_blocks(self, start_block: int, end_block: int, method=None, amount=None) -> dict:
        total_scraped = 0
        total_saved = 0

        for block_num in range(start_block, end_block + 1):
            print(f"Processing block: {block_num}")
            tx_hashes = m_scraper.get_block_transactions_from_web3(block_num)

            for tx_hash in tx_hashes:
                tx_details = m_scraper.scrape_transaction_details_from_api(tx_hash)
                if not tx_details:
                    continue

                total_scraped += 1

                if self._passes_filter(tx_details, method, amount):
                    if self._save_transaction(tx_details):
                        total_saved += 1
                        print(f"Saved transaction {tx_hash} (Block: {block_num})")
                    else:
                        print(f"Failed to save transaction {tx_hash}")
                else:
                    print(f"Transaction {tx_hash} (Block: {block_num}) skipped due to filter.")

        return {
            "scraped": total_scraped,
            "saved": total_saved
        }
m_db_data = DBData()