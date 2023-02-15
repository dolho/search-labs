import os
from dotenv import find_dotenv, load_dotenv

load_dotenv(find_dotenv())


ELASTIC_USER = os.environ.get("ELASTIC_USER")
ELASTIC_PASSWORD = os.environ.get("ELASTIC_PASSWORD")
INDEX = "lab_index"
