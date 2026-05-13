from fastapi import FastAPI, File, HTTPException, Query, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import Response

from backend.database.arango import DatabaseManager

app = FastAPI(
    title="Dissertation API",
    version="1.0.0"
)

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
    year_from: int | None = Query(None),
    year_to: int | None = Query(None),
    organization: str | None = Query(None),
    specialty_code: str | None = Query(None),
    processing_status: str | None = Query(None),
    author_name: str | None = Query(None),
    keywords: str | None = Query(None),
    sort_field: str | None = Query(None),
    sort_order: str = Query("asc"),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=1000)
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


@app.get("/api/dissertations/export")
def export_dissertation_by_id(
    diss_id: str = Query(..., description="Dissertation ID"),
    export_format: str = Query("csv", description="Export format: csv or json")
):

    if export_format not in ["json", "csv"]:
        raise HTTPException(
            status_code=400,
            detail="Unsupported export format. Use 'json' or 'csv'"
        )

    dissertation = db.get_dissertation_details(diss_id)

    if not dissertation:
        raise HTTPException(
            status_code=404,
            detail="dissertation not found"
        )

    content = db.export_single_dissertation(dissertation, export_format)

    if export_format == "csv":
        media_type = "text/csv"
        filename = f"dissertation_{diss_id}.csv"
    else:
        media_type = "application/json"
        filename = f"dissertation_{diss_id}.json"

    return Response(
        content=content,
        media_type=media_type,
        headers={
            "Content-Disposition": f"attachment; filename={filename}"
        }
    )


@app.get("/api/dissertations/{diss_id}")
def get_dissertation_details(diss_id: str):
    result = db.get_dissertation_details(diss_id)

    if not result:
        raise HTTPException(
            status_code=404,
            detail="dissertation not found"
        )

    return result

@app.get("/api/authors")
def get_authors(
    page: int = Query(1, ge=1),
    page_size: int = Query(10, ge=1, le=1000)
):
    result = db.get_all_authors(page=page, page_size=page_size)
    return result

@app.get("/api/authors/{author_id}")
def get_author_details(author_id: str):
    result = db.get_author_details(author_id)

    if not result:
        raise HTTPException(
            status_code=404,
            detail="author not found"
        )

    return result

@app.get("/api/organizations")
def get_organizations(
    page: int = Query(1, ge=1),
    page_size: int = Query(10, ge=1, le=1000)
):
    result = db.get_all_organizations(page=page, page_size=page_size)
    return result

@app.get("/api/organizations/{org_id}")
def get_organization_details(org_id: str):
    result = db.get_organization_details(org_id)

    if not result:
        raise HTTPException(
            status_code=404,
            detail="organization not found"
        )

    return result

@app.get("/api/organizations/{org_id}/dissertations")
def get_org_dissertations(
    org_id: str, page: int = 1, page_size: int = 10,
    year: int | None = None, specialty: str | None = None, search: str | None = None
):
    res = db.get_organization_dissertations(org_id, page, page_size, year, specialty, search)
    if not res: raise HTTPException(404, detail="no dissertations")
    return res

@app.get("/api/export")
def export_dissertations(
    year_from: int | None = Query(None),
    year_to: int | None = Query(None),
    organization: str | None = Query(None),
    specialty_code: str | None = Query(None),
    processing_status: str | None = Query(None),
    author_name: str | None = Query(None),
    keywords: str | None = Query(None),
    export_format: str = Query("json")
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
        export_format=export_format,
    )

    if export_format == "csv":
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


@app.get("/api/stats")
def get_statistics():
    result = db.get_statistics()

    if not result:
        raise HTTPException(
            status_code=404,
            detail="statistics not found"
        )

    return result


@app.get("/api/stats/years")
def get_yearly_distribution():
    result = db.get_yearly_distribution()

    if not result:
        raise HTTPException(
            status_code=404,
            detail="statistics not found"
        )

    return result


@app.get("/api/stats/authors")
def get_author_stats():
    result = db.get_author_stats()

    if not result:
        raise HTTPException(
            status_code=404,
            detail="statistics not found"
        )

    return result


@app.get("/api/stats/organizations")
def get_organization_stats():
    result = db.get_organization_stats()

    if not result:
        raise HTTPException(
            status_code=404,
            detail="statistics not found"
        )

    return result

@app.post("/api/import")
async def import_dissertations_endpoint(
    file: UploadFile = File(...),
    import_format: str = Query("json")
):
    if import_format not in ["json", "csv"]:
        raise HTTPException(status_code=400, detail="Unsupported import format. Use 'json' or 'csv'")
    content = await file.read()
    try:
        data_str = content.decode("utf-8")
    except UnicodeDecodeError:
        raise HTTPException(status_code=400, detail="File must be UTF-8 encoded text")
    try:
        result = db.import_dissertations(data_str, import_format)
    except json.JSONDecodeError:
        raise HTTPException(status_code=400, detail="Invalid JSON data")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Import failed: {e!s}")
    return result

@app.post("/api/authors")
def create_author(data: dict):
    try:
        result = db.create_author(data)
        return result
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.put("/api/authors/{author_id}")
def update_author(author_id: str, data: dict):
    try:
        result = db.update_author(author_id, data)
        return result
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.delete("/api/authors/{author_id}")
def delete_author(author_id: str):
    try:
        result = db.delete_author(author_id)
        return result
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.post("/api/organizations")
def create_organization(data: dict):
    try:
        result = db.create_organization(data)
        return result
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.put("/api/organizations/{org_id}")
def update_organization(org_id: str, data: dict):
    try:
        result = db.update_organization(org_id, data)
        return result
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.delete("/api/organizations/{org_id}")
def delete_organization(org_id: str):
    try:
        result = db.delete_organization(org_id)
        return result
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.post("/api/dissertations")
def create_dissertation(data: dict):
    try:
        result = db.create_dissertation(data)
        return result
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.put("/api/dissertations/{diss_id}")
def update_dissertation(diss_id: str, data: dict):
    try:
        result = db.update_dissertation(diss_id, data)
        return result
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.delete("/api/dissertations/{diss_id}")
def delete_dissertation(diss_id: str):
    try:
        result = db.delete_dissertation(diss_id)
        return result
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.get("/api/stats/organizations/comparison")
def get_organizations_comparison(
    year_from: int | None = Query(None),
    year_to: int | None = Query(None),
    limit: int = Query(10, ge=1, le=100)
):
    result = db.get_organizations_comparison(year_from=year_from, year_to=year_to, limit=limit)
    return result
