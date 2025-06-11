import sys
import os


project_root = os.path.dirname(__file__)
if project_root not in sys.path:
    sys.path.append(project_root)

from cli import cli 

if __name__ == "__main__":
    cli()