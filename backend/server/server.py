from fastapi import FastAPI, HTTPException, Query

from database.arango import DatabaseManager
from parser.parser import VakParser

app = FastAPI(
    title="Dissertation API",
    version="1.0.0"
)

db = DatabaseManager().connect()

