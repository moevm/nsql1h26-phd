import os

from arango import ArangoClient

ARANGO_HOST = os.getenv("ARANGO_HOST", "http://localhost:8529")
ARANGO_USER = os.getenv("ARANGO_USER", "root")
ARANGO_PASSWORD = os.getenv("ARANGO_PASSWORD", "password")
DATABASE_NAME = os.getenv("ARANGO_DATABASE", "dissertation_db")
COLLECTION_NAME = "dissertations"


def main():
    client = ArangoClient(hosts=ARANGO_HOST)
    sys_db = client.db("_system", username=ARANGO_USER, password=ARANGO_PASSWORD)
    print("Подключение к ArangoDB установлено")

    if not sys_db.has_database(DATABASE_NAME):
        sys_db.create_database(DATABASE_NAME)
    db = client.db(DATABASE_NAME, username=ARANGO_USER, password=ARANGO_PASSWORD)
    print(f"База данных '{DATABASE_NAME}' готова")

    if not db.has_collection(COLLECTION_NAME):
        db.create_collection(COLLECTION_NAME)
    collection = db.collection(COLLECTION_NAME)
    print(f"Коллекция '{COLLECTION_NAME}' готова")

    doc = {
        "_key": "test",
        "title": "Тестовая диссертация",
        "author": "Иванов И.И.",
        "year": 2026,
    }
    if collection.has(doc["_key"]):
        collection.delete(doc["_key"])
    collection.insert(doc)
    print(f"Документ вставлен: {doc['_key']}")

    result = collection.get("test")
    print(f"Документ прочитан: {result['title']} ({result['author']})")

    collection.delete("test")
    print("Тестовые данные удалены")


if __name__ == "__main__":
    main()
