from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import Response

import uvicorn

from database.arango import DatabaseManager
from parser.parser import VakParser

app = FastAPI(
    title="Dissertation API",
    version="1.0.0"
)

db = DatabaseManager().connect()


@app.get("/")
def root():
    return {
        "service": "dissertation-api",
        "status": "ok"
    }


@app.get("/api/dissertations")
def get_dissertations():
    pass


@app.get("/api/dissertations/{diss_id}")
def get_dissertation_details(diss_id: str):
    result = db.get_dissertation_details(diss_id)

    if not result:
        raise HTTPException(
            status_code=404,
            detail="dissertation not found"
        )

    return result


@app.get("/api/authors/{author_id}")
def get_author_details(author_id: str):
    result = db.get_author_details(author_id) # нужен метод

    if not result:
        raise HTTPException(
            status_code=404,
            detail="author not found"
        )
    
    return result


@app.get("/api/organizations/{org_id}")
def get_organization_details(org_id: str):
    result = db.get_organization_details(org_id) # нужен метод

    if not result:
        raise HTTPException(
            status_code=404,
            detail="organization not found"
        )
    
    return result


if __name__ == "__main__":
    uvicorn.run(
        "server.server:app",
        host="0.0.0.0",
        port=3000,
        reload=True
    )