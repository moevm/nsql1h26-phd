from backend.database.arango import DatabaseManager
from backend.parser.parser import VakParser

import uvicorn

if __name__ == "__main__":
    db = DatabaseManager().connect()
    parser = VakParser()
    all_details = parser.parse()
    if all_details:
        db.save_parsed_data(all_details)
        print(f"Saved {len(all_details)} records to ArangoDB")
    else:
        print("No data collected")

    uvicorn.run(
        "backend.server.server:app",
        host="0.0.0.0",
        port=8080,
        reload=True
    )
