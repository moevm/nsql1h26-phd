from fastapi import FastAPI, HTTPException, Query
from arango import DatabaseManager

app = FastAPI(
    title="",
    version="1.0.0"
)
