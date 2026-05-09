import os
from arango import ArangoClient

class DatabaseManager:
    def __init__(self, host=None, user=None, password=None, database=None):
        self.host = host or os.getenv("ARANGO_HOST", "http://arangodb:8529")
        self.user = user or os.getenv("ARANGO_USER", "root")
        self.password = password or os.getenv("ARANGO_PASSWORD", "password")
        self.database_name = database or os.getenv("ARANGO_DATABASE", "dissertation_db")
        self.collection_name = "dissertations"
        self.client = None
        self.db = None
        self.collection = None

    def connect(self):
        self.client = ArangoClient(hosts=self.host)
        sys_db = self.client.db("_system", username=self.user, password=self.password)
        if not sys_db.has_database(self.database_name):
            sys_db.create_database(self.database_name)
        self.db = self.client.db(self.database_name, username=self.user, password=self.password)
        if not self.db.has_collection(self.collection_name):
            self.collection = self.db.create_collection(self.collection_name)
        else:
            self.collection = self.db.collection(self.collection_name)
        self.collection.add_index({"type": "hash", "fields": ["vak_url"], "unique": True})
        return self

    def save_dissertation(self, doc):
        if not self.collection:
            self.connect()
        try:
            self.collection.insert(doc, overwrite=True)
        except Exception as e:
            print(f"Error saving dissertation {doc.get('vak_url')}: {e}")

    def save_dissertations(self, docs):
        if not self.collection:
            self.connect()
        for doc in docs:
            self.save_dissertation(doc)
