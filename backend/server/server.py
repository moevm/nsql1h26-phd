from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import Response
from typing import Optional

import uvicorn

from backend.database.arango import DatabaseManager
from backend.parser.parser import VakParser

app = FastAPI(
    title="Dissertation API",
    version="1.0.0"
)

from fastapi.middleware.cors import CORSMiddleware

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

db = DatabaseManager().connect()


@app.get("/")
def root():
    return {
        "service": "dissertation-api",
        "status": "ok"
    }


@app.get("/api/dissertations")
def get_dissertations(
    year_from: Optional[int] = Query(None),
    year_to: Optional[int] = Query(None),
    organization: Optional[str] = Query(None),
    specialty_code: Optional[str] = Query(None),
    processing_status: Optional[str] = Query(None),
    author_name: Optional[str] = Query(None),
    keywords: Optional[str] = Query(None),
    sort_field: Optional[str] = Query(None),
    sort_order: str = Query("asc"),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100)
):
    filters = {}

    if year_from is not None:
        filters["year_from"] = year_from
    if year_to is not None:
        filters["year_to"] = year_to
    if organization:
        filters["organization"] = organization
    if specialty_code:
        filters["specialty_code"] = specialty_code
    if processing_status:
        filters["processing_status"] = processing_status
    if author_name:
        filters["author_name"] = author_name
    if keywords:
        filters["keywords"] = keywords

    result = db.search_dissertations(
        filters=filters,
        sort_field=sort_field,
        sort_order=sort_order,
        page=page,
        page_size=page_size
    )

    if not result:
        raise HTTPException(
            status_code=404,
            detail="dissertation not found"
        )

    return result


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


@app.get("/api/export")
def export_dissertations(
    year_from: Optional[int] = Query(None),
    year_to: Optional[int] = Query(None),
    organization: Optional[str] = Query(None),
    specialty_code: Optional[str] = Query(None),
    processing_status: Optional[str] = Query(None),
    author_name: Optional[str] = Query(None),
    keywords: Optional[str] = Query(None),
    format: str = Query("json")
):

    filters = {}

    if year_from is not None:
        filters["year_from"] = year_from

    if year_to is not None:
        filters["year_to"] = year_to

    if organization:
        filters["organization"] = organization

    if specialty_code:
        filters["specialty_code"] = specialty_code

    if processing_status:
        filters["processing_status"] = processing_status

    if author_name:
        filters["author_name"] = author_name

    if keywords:
        filters["keywords"] = keywords

    content = db.export_dissertations(
        filters=filters,
        format=format,
    )

    if format == "csv":
        media_type = "text/csv"
        filename = "dissertations.csv"
    else:
        media_type = "application/json"
        filename = "dissertations.json"

    return Response(
        content=content,
        media_type=media_type,
        headers={
            "Content-Disposition": f"attachment; filename={filename}"
        }
    )
