import sys
import os
from dotenv import load_dotenv


project_root = os.path.dirname(__file__)
if project_root not in sys.path:
    sys.path.append(project_root)

from cli import cli 

if __name__ == "__main__":
    load_dotenv()
    cli()