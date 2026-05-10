import os
import re
import hashlib
from datetime import datetime, timezone

from arango import ArangoClient
from arango.exceptions import DocumentInsertError


class DatabaseManager:
    def __init__(self, host=None, user=None, password=None, database=None):
        self.host = host or os.getenv("ARANGO_HOST", "http://arangodb:8529")
        self.user = user or os.getenv("ARANGO_USER", "root")
        self.password = password or os.getenv("ARANGO_PASSWORD", "password")
        self.database_name = database or os.getenv("ARANGO_DATABASE", "dissertation_db")
        self.client = None
        self.db = None
        self.diss_col_name = "dissertation"
        self.author_col_name = "author"
        self.file_col_name = "file"
        self.writes_edge_name = "writes"
        self.has_file_edge_name = "has_file"

    def connect(self):
        self.client = ArangoClient(hosts=self.host)
        sys_db = self.client.db("_system", username=self.user, password=self.password)
        if not sys_db.has_database(self.database_name):
            sys_db.create_database(self.database_name)
        self.db = self.client.db(self.database_name, username=self.user, password=self.password)

        self._ensure_vertex_collection(self.diss_col_name)
        self._ensure_vertex_collection(self.author_col_name)
        self._ensure_vertex_collection(self.file_col_name)
        self._ensure_edge_collection(self.writes_edge_name)
        self._ensure_edge_collection(self.has_file_edge_name)

        self.db.collection(self.diss_col_name).add_index(
            {"type": "hash", "fields": ["vak_url"], "unique": True}
        )
        self.db.collection(self.author_col_name).add_index(
            {"type": "hash", "fields": ["full_name"], "unique": True, "sparse": False}
        )
        self.db.collection(self.file_col_name).add_index(
            {"type": "hash", "fields": ["dissertation_key"], "unique": False}
        )
        return self

    def _ensure_vertex_collection(self, name):
        if self.db.has_collection(name):
            return self.db.collection(name)
        return self.db.create_collection(name)

    def _ensure_edge_collection(self, name):
        if self.db.has_collection(name):
            return self.db.collection(name)
        return self.db.create_collection(name, edge=True)

    def _slugify_author_key(self, full_name: str):
        name = full_name.strip()
        name = re.sub(r'\s+', '_', name)
        name = re.sub(r'[^a-zA-Z0-9_]', '', name)
        if name:
            if name.startswith('_'):
                name = name.lstrip('_')
            if not name:
                name = "a_" + hashlib.md5(full_name.encode()).hexdigest()[:16]
            return name
        else:
            return "a_" + hashlib.md5(full_name.encode()).hexdigest()[:16]

    def _extract_dissertation_key(self, vak_url: str):
        parts = vak_url.rstrip('/').split('/')
        raw = parts[-1] if parts else "unknown"
        clean = re.sub(r'[^a-zA-Z0-9_\-:.@()+,=;$!*\'%]', '', raw)
        return clean or hashlib.md5(vak_url.encode()).hexdigest()[:16]

    def save_parsed_data(self, details_list: list):
        if not self.db:
            self.connect()

        diss_coll = self.db.collection(self.diss_col_name)
        author_coll = self.db.collection(self.author_col_name)
        file_coll = self.db.collection(self.file_col_name)
        writes_coll = self.db.collection(self.writes_edge_name)
        has_file_coll = self.db.collection(self.has_file_edge_name)

        now = datetime.now(timezone.utc).isoformat()

        for item in details_list:
            full_name = item.get("applicant_name", "")
            vak_url = item.get("vak_url", "")
            if not vak_url:
                continue

            diss_key = self._extract_dissertation_key(vak_url)
            author_key = self._slugify_author_key(full_name)

            if not author_coll.has(author_key):
                author_doc = {
                    "_key": author_key,
                    "full_name": full_name,
                    "dissertations_count": 1,
                    "first_seen": now
                }
                author_coll.insert(author_doc)
            else:
                self.db.aql.execute(
                    "FOR a IN @@coll FILTER a._key == @key UPDATE a WITH { dissertations_count: a.dissertations_count + 1 } IN @@coll",
                    bind_vars={"@coll": self.author_col_name, "key": author_key}
                )

            diss_doc = {
                "_key": diss_key,
                "title": item.get("title", ""),
                "type": item.get("type", ""),
                "science_branch": item.get("science_branch", ""),
                "defense_date": item.get("defense_date", ""),
                "primary_published_at": item.get("primary_published_at", ""),
                "last_edited_at": item.get("last_edited_at", ""),
                "specialty_code": item.get("specialty_code", ""),
                "defense_council_code": item.get("defense_council_code", ""),
                "defense_organization_name": item.get("defense_organization_name", ""),
                "organization_address": item.get("organization_address", ""),
                "organization_phone_number": item.get("organization_phone_number", ""),
                "vak_url": vak_url,
                "organization_advert_url": item.get("organization_advert_url", ""),
                "processing_status": "completed",
                "created_at": now,
                "updated_at": now
            }
            diss_coll.insert(diss_doc, overwrite=True)

            edge_key = f"{author_key}_{diss_key}"
            edge_doc = {
                "_key": edge_key,
                "_from": f"{self.author_col_name}/{author_key}",
                "_to": f"{self.diss_col_name}/{diss_key}"
            }
            try:
                writes_coll.insert(edge_doc, overwrite=True)
            except DocumentInsertError:
                pass

            file_content = item.get("file_content", "")
            if file_content:
                file_key = f"{diss_key}_file"
                file_doc = {
                    "_key": file_key,
                    "dissertation_key": diss_key,
                    "content": file_content,
                    "size_bytes": len(file_content.encode("utf-8")),
                    "created_at": now
                }
                file_coll.insert(file_doc, overwrite=True)

                has_file_edge_key = f"{diss_key}_{file_key}"
                has_file_edge = {
                    "_key": has_file_edge_key,
                    "_from": f"{self.diss_col_name}/{diss_key}",
                    "_to": f"{self.file_col_name}/{file_key}"
                }
                try:
                    has_file_coll.insert(has_file_edge, overwrite=True)
                except DocumentInsertError:
                    pass

        print(f"saved/updated {len(details_list)} dissertations, authors, files and edges.")
