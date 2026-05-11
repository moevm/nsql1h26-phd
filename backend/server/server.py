from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import Response

from database.arango import DatabaseManager
from parser.parser import VakParser

app = FastAPI(
    title="Dissertation API",
    version="1.0.0"
)

db = DatabaseManager().connect()

@app.get("/api/dissertations/{diss_id}")
def get_dissertation_details(diss_id: str):
    result = db.get_dissertation_details(diss_id)

    if not result:
        raise HTTPException(
            status_code=404,
            detail="dissertation not found"
        )

    return result

