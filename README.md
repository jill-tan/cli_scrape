.
├── docker-compose.yml          
├── .env.example                
├── .env                        
└── app/                        
    ├── main.py                 
    ├── database.py             
    ├── models.py               
    ├── scraper.py              
    ├── cli.py                  
    ├── requirements.txt      
    ├── Dockerfile              
    ├── alembic.ini             
    └── migrations/             
        ├── versions/
        │   └── <timestamp>_initial_migration.py 
        └── env.py              
        └── script.py.mako      

# migration
docker compose run --rm cli alembic init app/migrations
docker compose run --rm cli alembic -c app/alembic.ini revision --autogenerate -m "initial migration"

# cli
# Count transactions in the database
docker compose run --rm cli python main.py count-transactions

# Scrape transaction data
docker compose run --rm cli python main.py scrape --start-block 22682309 --end-block 22682319

docker compose run --rm cli python main.py scrape \
    --start-block 22682300 --end-block 22682310 \
    --method "Transfer" --amount "not-0"

# Display transactions from the database:
docker compose run --rm cli python main.py show-transactions
docker compose run --rm cli python main.py show-transactions --block 22682309 --amount "not-0"