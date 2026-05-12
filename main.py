import os
import uvicorn

from backend.database.arango import DatabaseManager
from backend.parser.parser import VakParser

if __name__ == "__main__":
    db = DatabaseManager().connect()

    if os.getenv("PARSE", "false").lower() == "true":
        try:
            max_pages = int(os.getenv("MAX_PAGES", 1))
        except ValueError:
            print("MAX_PAGES must be an integer. Using default 1.")
            max_pages = 1

        parser = VakParser(max_pages=max_pages)
        all_details = parser.parse()
        if all_details:
            db.save_parsed_data(all_details)
            print(f"Saved {len(all_details)} records to ArangoDB")
        else:
            print("No data collected")
    else:
        print("Skipping parser (set PARSE=true to run)")

    uvicorn.run(
        "backend.server.server:app",
        host="0.0.0.0",
        port=8080,
        reload=True
    )
