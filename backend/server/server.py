from fastapi import FastAPI, HTTPException, Query

from arango import DatabaseManager
from parser import VakParser

app = FastAPI(
    title="",
    version="1.0.0"
)

db = DatabaseManager().connect()

