import contextlib
import csv
import hashlib
import io
import json
import os
import re
from datetime import UTC, datetime

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
        self.org_col_name = "organization"
        self.writes_edge_name = "writes"
        self.has_file_edge_name = "has_file"
        self.has_org_edge_name = "has_organization"

    def connect(self):
        self.client = ArangoClient(hosts=self.host)
        sys_db = self.client.db("_system", username=self.user, password=self.password)
        if not sys_db.has_database(self.database_name):
            sys_db.create_database(self.database_name)
        self.db = self.client.db(
            self.database_name, username=self.user, password=self.password
        )

        self._ensure_vertex_collection(self.diss_col_name)
        self._ensure_vertex_collection(self.author_col_name)
        self._ensure_vertex_collection(self.file_col_name)
        self._ensure_vertex_collection(self.org_col_name)
        self._ensure_edge_collection(self.writes_edge_name)
        self._ensure_edge_collection(self.has_file_edge_name)
        self._ensure_edge_collection(self.has_org_edge_name)

        self.db.collection(self.diss_col_name).add_index(
            {"type": "hash", "fields": ["vak_url"], "unique": True}
        )
        self.db.collection(self.author_col_name).add_index(
            {"type": "hash", "fields": ["full_name"], "unique": True, "sparse": False}
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
        return "a_" + hashlib.md5(full_name.encode()).hexdigest()[:16]

    def _slugify_org_key(self, org_name: str):
        name = org_name.strip()
        name = re.sub(r'\s+', '_', name)
        name = re.sub(r'[^a-zA-Z0-9_]', '', name)
        if name:
            if name.startswith('_'):
                name = name.lstrip('_')
            if not name:
                name = "org_" + hashlib.md5(org_name.encode()).hexdigest()[:16]
            return name
        return "org_" + hashlib.md5(org_name.encode()).hexdigest()[:16]

    def _extract_dissertation_key(self, vak_url: str):
        parts = vak_url.rstrip('/').split('/')
        raw = parts[-1] if parts else "unknown"
        clean = re.sub(r'[^a-zA-Z0-9_\-:.@()+,=;$!*\'%]', '', raw)
        return clean or hashlib.md5(vak_url.encode()).hexdigest()[:16]

    def _parse_date(self, date_str):
        if not date_str:
            return ""
        parts = date_str.strip().split('.')
        if len(parts) == 3:
            day, month, year = parts
            try:
                return f"{year}-{month.zfill(2)}-{day.zfill(2)}"
            except ValueError:
                return date_str
        return date_str

    def _save_organization(self, org_name, org_address, org_phone, now):
        if not org_name:
            return None
        org_key = self._slugify_org_key(org_name)
        org_coll = self.db.collection(self.org_col_name)
        if not org_coll.has(org_key):
            org_doc = {
                "_key": org_key,
                "full_name": org_name,
                "address": org_address or "",
                "phone_number": org_phone or "",
                "city": "",
                "country": "Россия",
                "created_at": now
            }
            org_coll.insert(org_doc)
        else:
            update_fields = {}
            if org_address:
                update_fields["address"] = org_address
            if org_phone:
                update_fields["phone_number"] = org_phone
            if update_fields:
                self.db.aql.execute(
                    "FOR o IN @@coll FILTER o._key == @key UPDATE o WITH @fields "
                    "IN @@coll",
                    bind_vars={
                        "@coll": self.org_col_name,
                        "key": org_key,
                        "fields": update_fields,
                    },
                )
        return org_key

    def save_parsed_data(self, details_list: list):
        if not self.db:
            self.connect()

        diss_coll = self.db.collection(self.diss_col_name)
        author_coll = self.db.collection(self.author_col_name)
        file_coll = self.db.collection(self.file_col_name)
        writes_coll = self.db.collection(self.writes_edge_name)
        has_file_coll = self.db.collection(self.has_file_edge_name)
        has_org_coll = self.db.collection(self.has_org_edge_name)

        now = datetime.now(UTC).isoformat()

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
                    "dissertations_count": 1
                }
                author_coll.insert(author_doc)
            else:
                self.db.aql.execute(
                    "FOR a IN @@coll FILTER a._key == @key UPDATE a WITH "
                    "{ dissertations_count: a.dissertations_count + 1 } IN @@coll",
                    bind_vars={"@coll": self.author_col_name, "key": author_key},
                )

            org_name = item.get("defense_organization_name", "")
            org_address = item.get("organization_address", "")
            org_phone = item.get("organization_phone_number", "")
            org_key = self._save_organization(org_name, org_address, org_phone, now)

            defense_date = self._parse_date(item.get("defense_date", ""))
            primary_pub = self._parse_date(item.get("primary_published_at", ""))
            last_edited = self._parse_date(item.get("last_edited_at", ""))

            diss_doc = {
                "_key": diss_key,
                "title": item.get("title", ""),
                "type": item.get("type", ""),
                "science_branch": item.get("science_branch", ""),
                "defense_date": defense_date,
                "primary_published_at": primary_pub,
                "last_edited_at": last_edited,
                "specialty_code": item.get("specialty_code", ""),
                "defense_council_code": item.get("defense_council_code", ""),
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
                "_to": f"{self.diss_col_name}/{diss_key}",
            }
            with contextlib.suppress(DocumentInsertError):
                writes_coll.insert(edge_doc, overwrite=True)

            if org_key:
                org_edge_key = f"{diss_key}_{org_key}"
                org_edge_doc = {
                    "_key": org_edge_key,
                    "_from": f"{self.diss_col_name}/{diss_key}",
                    "_to": f"{self.org_col_name}/{org_key}",
                }
                with contextlib.suppress(DocumentInsertError):
                    has_org_coll.insert(org_edge_doc, overwrite=True)

            file_content = item.get("file_content", "")
            if file_content:
                file_key = f"{diss_key}_file"
                file_doc = {
                    "_key": file_key,
                    "filename": f"{diss_key}_autoref.pdf",
                    "autoref_text": file_content,
                    "size_bytes": len(file_content.encode("utf-8"))
                }
                file_coll.insert(file_doc, overwrite=True)

                has_file_edge_key = f"{diss_key}_{file_key}"
                has_file_edge = {
                    "_key": has_file_edge_key,
                    "_from": f"{self.diss_col_name}/{diss_key}",
                    "_to": f"{self.file_col_name}/{file_key}",
                }
                with contextlib.suppress(DocumentInsertError):
                    has_file_coll.insert(has_file_edge, overwrite=True)

        print(
            f"saved/updated {len(details_list)} dissertations, authors, "
            "organizations, files and edges."
        )

    def search_dissertations(
        self, filters, sort_field=None, sort_order="asc", page=1, page_size=20
    ):
        if not self.db:
            self.connect()

        bind_vars = {}
        filter_parts = []
        additional_lets = []

        sort_map = {
            "title": "d.title",
            "defense_date": "d.defense_date",
        }

        if "year_from" in filters:
            filter_parts.append("LEFT(d.defense_date, 4) >= @year_from")
            bind_vars["year_from"] = str(filters["year_from"])
        if "year_to" in filters:
            filter_parts.append("LEFT(d.defense_date, 4) <= @year_to")
            bind_vars["year_to"] = str(filters["year_to"])
        if "organization" in filters:
            org_query = (
                "LET org_doc = FIRST(FOR o IN has_organization FILTER "
                "o._from == d._id FOR org IN organization FILTER "
                "org._id == o._to RETURN org)"
            )
            additional_lets.append(org_query)
            filter_parts.append("CONTAINS(LOWER(org_doc.full_name), LOWER(@org))")
            bind_vars["org"] = filters["organization"]
        if "specialty_code" in filters:
            filter_parts.append("CONTAINS(LOWER(d.specialty_code), LOWER(@spec))")
            bind_vars["spec"] = filters["specialty_code"]
        if "processing_status" in filters:
            filter_parts.append("d.processing_status == @status")
            bind_vars["status"] = filters["processing_status"]
        if "author_name" in filters:
            author_query = (
                "LET author_doc = FIRST(FOR w IN writes FILTER "
                "w._to == d._id FOR a IN author FILTER a._id == w._from RETURN a)"
            )
            additional_lets.append(author_query)
            filter_parts.append(
                "CONTAINS(LOWER(author_doc.full_name), LOWER(@author_name))"
            )
            bind_vars["author_name"] = filters["author_name"]
        if "keywords" in filters:
            file_query = (
                "LET file_doc = FIRST(FOR h IN has_file FILTER "
                "h._from == d._id FOR f IN file FILTER f._id == h._to RETURN f)"
            )
            additional_lets.append(file_query)
            kw = filters["keywords"]
            keyword_filter = (
                "(CONTAINS(LOWER(d.title), LOWER(@kw)) OR "
                "(file_doc != null AND CONTAINS(LOWER(file_doc.autoref_text), "
                "LOWER(@kw))))"
            )
            filter_parts.append(keyword_filter)
            bind_vars["kw"] = kw

        let_clause = " ".join(additional_lets) if additional_lets else ""
        filter_clause = " FILTER " + " AND ".join(filter_parts) if filter_parts else ""

        sort_expr = "d.defense_date"
        if sort_field:
            if sort_field == "author_name":
                sort_expr = "author_ext"
            elif sort_field == "organization":
                sort_expr = "org_ext"
            elif sort_field in sort_map:
                sort_expr = sort_map[sort_field]
            else:
                sort_expr = f"d.{sort_field}"
        direction = "ASC" if sort_order.lower() == "asc" else "DESC"

        if sort_field == "author_name":
            author_ext_query = (
                "LET author_ext = FIRST(FOR w IN writes FILTER "
                "w._to == d._id FOR a IN author FILTER a._id == w._from "
                "RETURN a.full_name)"
            )
            additional_lets.append(author_ext_query)
        elif sort_field == "organization":
            org_ext_query = (
                "LET org_ext = FIRST(FOR o IN has_organization FILTER "
                "o._from == d._id FOR org IN organization FILTER org._id == o._to "
                "RETURN org.full_name)"
            )
            additional_lets.append(org_ext_query)
        let_clause = " ".join(additional_lets)

        author_name_query = (
            "FIRST(FOR w IN writes FILTER w._to == d._id FOR a IN author "
            "FILTER a._id == w._from RETURN a.full_name)"
        )
        author_id_query = (
            "FIRST(FOR w IN writes FILTER w._to == d._id FOR a IN author "
            "FILTER a._id == w._from RETURN a._key)"
        )
        organization_name_query = (
            "FIRST(FOR o IN has_organization FILTER o._from == d._id "
            "FOR org IN organization FILTER org._id == o._to RETURN org.full_name)"
        )

        data = list(
            self.db.aql.execute(
                f"""
                FOR d IN {self.diss_col_name}
                {let_clause}
                {filter_clause}
                SORT {sort_expr} {direction}
                LIMIT @offset, @limit
                RETURN MERGE(d, {{
                    author_name: {author_name_query},
                    author_id: {author_id_query},
                    organization_name: {organization_name_query}
                }})
            """,
                bind_vars={
                    **bind_vars,
                    "offset": (page - 1) * page_size,
                    "limit": page_size,
                },
            )
        )

        total = self.db.aql.execute(f"""
            RETURN COUNT(
                FOR d IN {self.diss_col_name}
                {let_clause}
                {filter_clause}
                RETURN 1
            )
        """, bind_vars=bind_vars).next()

        return {"total": total, "data": data}

    def export_dissertations(self, filters, export_format="json"):
        if not self.db:
            self.connect()
        bind_vars = {}
        filter_parts = []
        additional_lets = []

        if "year_from" in filters:
            filter_parts.append("LEFT(d.defense_date, 4) >= @year_from")
            bind_vars["year_from"] = str(filters["year_from"])
        if "year_to" in filters:
            filter_parts.append("LEFT(d.defense_date, 4) <= @year_to")
            bind_vars["year_to"] = str(filters["year_to"])
        if "organization" in filters:
            org_query = (
                "LET org_doc = FIRST(FOR o IN has_organization FILTER "
                "o._from == d._id FOR org IN organization FILTER "
                "org._id == o._to RETURN org)"
            )
            additional_lets.append(org_query)
            filter_parts.append("CONTAINS(LOWER(org_doc.full_name), LOWER(@org))")
            bind_vars["org"] = filters["organization"]
        if "specialty_code" in filters:
            filter_parts.append("CONTAINS(LOWER(d.specialty_code), LOWER(@spec))")
            bind_vars["spec"] = filters["specialty_code"]
        if "processing_status" in filters:
            filter_parts.append("d.processing_status == @status")
            bind_vars["status"] = filters["processing_status"]
        if "author_name" in filters:
            author_query = (
                "LET author_doc = FIRST(FOR w IN writes FILTER "
                "w._to == d._id FOR a IN author FILTER a._id == w._from RETURN a)"
            )
            additional_lets.append(author_query)
            filter_parts.append(
                "CONTAINS(LOWER(author_doc.full_name), LOWER(@author_name))"
            )
            bind_vars["author_name"] = filters["author_name"]
        if "keywords" in filters:
            file_query = (
                "LET file_doc = FIRST(FOR h IN has_file FILTER "
                "h._from == d._id FOR f IN file FILTER f._id == h._to RETURN f)"
            )
            additional_lets.append(file_query)
            kw = filters["keywords"]
            keyword_filter = (
                "(CONTAINS(LOWER(d.title), LOWER(@kw)) OR "
                "(file_doc != null AND CONTAINS(LOWER(file_doc.autoref_text), "
                "LOWER(@kw))))"
            )
            filter_parts.append(keyword_filter)
            bind_vars["kw"] = kw

        let_clause = " ".join(additional_lets) if additional_lets else ""
        filter_clause = " FILTER " + " AND ".join(filter_parts) if filter_parts else ""

        author_name_query = (
            "FIRST(FOR w IN writes FILTER w._to == d._id FOR a IN author "
            "FILTER a._id == w._from RETURN a.full_name)"
        )
        author_id_query = (
            "FIRST(FOR w IN writes FILTER w._to == d._id FOR a IN author "
            "FILTER a._id == w._from RETURN a._key)"
        )
        organization_name_query = (
            "FIRST(FOR o IN has_organization FILTER o._from == d._id "
            "FOR org IN organization FILTER org._id == o._to RETURN org.full_name)"
        )
        file_content_query = (
            "FIRST(FOR h IN has_file FILTER h._from == d._id "
            "FOR f IN file FILTER f._id == h._to RETURN f.autoref_text)"
        )

        data = list(
            self.db.aql.execute(
                f"""
                FOR d IN {self.diss_col_name}
                {let_clause}
                {filter_clause}
                RETURN MERGE(d, {{
                    author_name: {author_name_query},
                    author_id: {author_id_query},
                    organization_name: {organization_name_query},
                    file_content: {file_content_query}
                }})
            """,
                bind_vars=bind_vars,
            )
        )

        if export_format == "csv":
            output = io.StringIO()
            if data:
                writer = csv.DictWriter(output, fieldnames=data[0].keys())
                writer.writeheader()
                writer.writerows(data)
            return output.getvalue()
        return json.dumps(data, ensure_ascii=False, indent=2)

    def import_dissertations(self, data: str, import_format: str = "json"):
        if not self.db:
            self.connect()

        if import_format == "csv":
            reader = csv.DictReader(io.StringIO(data))
            records = list(reader)
        elif import_format == "json":
            records = json.loads(data)
            if isinstance(records, dict):
                records = [records]
        else:
            raise ValueError("Unsupported import format. Use 'json' or 'csv'")

        diss_coll = self.db.collection(self.diss_col_name)
        author_coll = self.db.collection(self.author_col_name)
        writes_coll = self.db.collection(self.writes_edge_name)
        org_coll = self.db.collection(self.org_col_name)
        has_org_coll = self.db.collection(self.has_org_edge_name)
        file_coll = self.db.collection(self.file_col_name)
        has_file_coll = self.db.collection(self.has_file_edge_name)

        now = datetime.now(UTC).isoformat()
        imported = 0

        for item in records:
            vak_url = item.get("vak_url", "").strip()
            if not vak_url:
                continue

            diss_key = self._extract_dissertation_key(vak_url)

            author_name = item.get("author_name", "").strip()
            if author_name:
                author_key = self._slugify_author_key(author_name)
                if not author_coll.has(author_key):
                    author_coll.insert({
                        "_key": author_key,
                        "full_name": author_name,
                        "dissertations_count": 1
                    })
                else:
                    self.db.aql.execute(
                        "FOR a IN @@coll FILTER a._key == @key UPDATE a WITH "
                        "{ dissertations_count: a.dissertations_count + 1 } IN @@coll",
                        bind_vars={"@coll": self.author_col_name, "key": author_key}
                    )
            else:
                author_key = None

            org_name = item.get("organization_name", "").strip()
            if org_name:
                org_key = self._slugify_org_key(org_name)
                if not org_coll.has(org_key):
                    org_coll.insert({
                        "_key": org_key,
                        "full_name": org_name,
                        "address": "",
                        "phone_number": "",
                        "city": "",
                        "country": "Россия",
                        "created_at": now
                    })
            else:
                org_key = None

            defense_date = self._parse_date(item.get("defense_date", ""))
            primary_pub = self._parse_date(item.get("primary_published_at", ""))
            last_edited = self._parse_date(item.get("last_edited_at", ""))

            diss_doc = {
                "_key": diss_key,
                "title": item.get("title", ""),
                "type": item.get("type", ""),
                "science_branch": item.get("science_branch", ""),
                "defense_date": defense_date,
                "primary_published_at": primary_pub,
                "last_edited_at": last_edited,
                "specialty_code": item.get("specialty_code", ""),
                "defense_council_code": item.get("defense_council_code", ""),
                "vak_url": vak_url,
                "organization_advert_url": item.get("organization_advert_url", ""),
                "processing_status": item.get("processing_status", "completed"),
                "created_at": item.get("created_at", now),
                "updated_at": item.get("updated_at", now)
            }
            diss_coll.insert(diss_doc, overwrite=True)

            if author_key:
                edge_key = f"{author_key}_{diss_key}"
                edge_doc = {
                    "_key": edge_key,
                    "_from": f"{self.author_col_name}/{author_key}",
                    "_to": f"{self.diss_col_name}/{diss_key}",
                }
                with contextlib.suppress(DocumentInsertError):
                    writes_coll.insert(edge_doc, overwrite=True)

            if org_key:
                org_edge_key = f"{diss_key}_{org_key}"
                org_edge_doc = {
                    "_key": org_edge_key,
                    "_from": f"{self.diss_col_name}/{diss_key}",
                    "_to": f"{self.org_col_name}/{org_key}",
                }
                with contextlib.suppress(DocumentInsertError):
                    has_org_coll.insert(org_edge_doc, overwrite=True)

            file_content = item.get("file_content", "").strip()
            if file_content:
                file_key = f"{diss_key}_file"
                file_doc = {
                    "_key": file_key,
                    "filename": item.get("file_filename", f"{diss_key}_autoref.pdf"),
                    "autoref_text": file_content,
                    "size_bytes": len(file_content.encode("utf-8"))
                }
                file_coll.insert(file_doc, overwrite=True)

                has_file_edge_key = f"{diss_key}_{file_key}"
                has_file_edge = {
                    "_key": has_file_edge_key,
                    "_from": f"{self.diss_col_name}/{diss_key}",
                    "_to": f"{self.file_col_name}/{file_key}",
                }
                with contextlib.suppress(DocumentInsertError):
                    has_file_coll.insert(has_file_edge, overwrite=True)

            imported += 1

        return {"imported": imported}

    def get_dissertation_details(self, diss_key):
        if not self.db:
            self.connect()
        query = """
        LET d = DOCUMENT(CONCAT(@diss_coll, '/', @key))
        LET author = FIRST(
            FOR w IN writes
            FILTER w._to == d._id
            FOR a IN author
            FILTER a._id == w._from
            RETURN a
        )
        LET file = FIRST(
            FOR h IN has_file
            FILTER h._from == d._id
            FOR f IN file
            FILTER f._id == h._to
            RETURN f
        )
        LET org = FIRST(
            FOR ho IN has_organization
            FILTER ho._from == d._id
            FOR o IN organization
            FILTER o._id == ho._to
            RETURN o
        )
        RETURN MERGE(d, {
            author: author,
            file_content: file != null ? file.autoref_text : null,
            file_filename: file != null ? file.filename : null,
            organization: org
        })
        """
        bind_vars = {"diss_coll": self.diss_col_name, "key": diss_key}
        cursor = self.db.aql.execute(query, bind_vars=bind_vars)
        return next(cursor, None)

    def get_all_authors(self, page=1, page_size=10):
        if not self.db:
            self.connect()
        query = """
            FOR a IN author
                LET cnt = COUNT(
                    FOR w IN writes
                    FILTER w._from == a._id
                    RETURN 1
                )
                SORT a.full_name ASC
                LIMIT @offset, @limit
                RETURN MERGE(a, {dissertations_count: cnt})
        """
        bind_vars = {"offset": (page - 1) * page_size, "limit": page_size}
        data = list(self.db.aql.execute(query, bind_vars=bind_vars))
        total = self.db.collection(self.author_col_name).count()
        return {"total": total, "data": data}

    def get_author_details(self, author_id):
        if not self.db:
            self.connect()
        query = """
        LET a = DOCUMENT(CONCAT(@author_coll, '/', @key))
        LET dissertations = (
            FOR w IN writes
            FILTER w._from == a._id
            FOR d IN dissertation
            FILTER d._id == w._to
            RETURN d
        )
        RETURN MERGE(a, { dissertations: dissertations })
        """
        bind_vars = {"author_coll": self.author_col_name, "key": author_id}
        cursor = self.db.aql.execute(query, bind_vars=bind_vars)
        return next(cursor, None)

    def get_organization_details(self, org_id):
        if not self.db:
            self.connect()
        query = """
        LET o = DOCUMENT(CONCAT(@org_coll, '/', @key))
        LET cnt = COUNT(
            FOR ho IN has_organization FILTER ho._to == o._id RETURN 1
        )
        RETURN MERGE(o, { dissertations_count: cnt })
        """
        bind_vars = {"org_coll": self.org_col_name, "key": org_id}
        cursor = self.db.aql.execute(query, bind_vars=bind_vars)
        return next(cursor, None)

    def get_organization_dissertations(
        self, org_id, page=1, page_size=20, year=None, specialty=None, search=None
    ):
        if not self.db:
            self.connect()

        org_full_id = f"{self.org_col_name}/{org_id}"
        bind_vars = {
            "org_full_id": org_full_id,
            "offset": (page - 1) * page_size,
            "limit": page_size,
        }

        filter_ho = "ho._to == @org_full_id"

        filter_d_parts = []
        if year:
            filter_d_parts.append("LEFT(d.defense_date, 4) == @year")
            bind_vars["year"] = str(year)
        if specialty:
            filter_d_parts.append(
                "CONTAINS(LOWER(d.specialty_code), LOWER(@specialty))"
            )
            bind_vars["specialty"] = specialty
        if search:
            filter_d_parts.append("CONTAINS(LOWER(d.title), LOWER(@search))")
            bind_vars["search"] = search

        filter_d = " AND ".join(filter_d_parts) if filter_d_parts else "true"

        data_query = (
            f"FOR ho IN {self.has_org_edge_name} "
            f"FILTER {filter_ho} "
            f"FOR d IN {self.diss_col_name} "
            f"FILTER d._id == ho._from AND {filter_d} "
            f"SORT d.defense_date DESC "
            f"LIMIT @offset, @limit "
            f"RETURN MERGE(d, {{ author_name: FIRST( FOR w IN {self.writes_edge_name} "
            f"FILTER w._to == d._id FOR a IN {self.author_col_name} "
            f"FILTER a._id == w._from RETURN a.full_name ) }} )"
        )

        count_query = (
            f"RETURN COUNT( FOR ho IN {self.has_org_edge_name} "
            f"FILTER {filter_ho} "
            f"FOR d IN {self.diss_col_name} "
            f"FILTER d._id == ho._from AND {filter_d} RETURN 1 )"
        )

        data = list(self.db.aql.execute(data_query, bind_vars=bind_vars))

        count_bind = {"org_full_id": org_full_id}
        if year:
            count_bind["year"] = str(year)
        if specialty:
            count_bind["specialty"] = specialty
        if search:
            count_bind["search"] = search

        total = next(self.db.aql.execute(count_query, bind_vars=count_bind))

        return {"total": total, "data": data}

    def get_author_stats(self):
        if not self.db:
            self.connect()
        query = """
        FOR a IN author
            LET cnt = COUNT(
                FOR w IN writes
                FILTER w._from == a._id
                RETURN 1
            )
            RETURN { author_name: a.full_name, count: cnt }
        """
        return list(self.db.aql.execute(query))

    def get_organization_stats(self):
        if not self.db:
            self.connect()
        query = """
        FOR o IN organization
            LET cnt = COUNT(
                FOR ho IN has_organization
                FILTER ho._to == o._id
                RETURN 1
            )
            RETURN { organization_name: o.full_name, count: cnt }
        """
        return list(self.db.aql.execute(query))

    def get_organizations_comparison(self, year_from=None, year_to=None, limit=10):
        if not self.db:
            self.connect()
        bind_vars = {"limit": limit}
        filter_parts = []
        if year_from:
            filter_parts.append("LEFT(d.defense_date, 4) >= @year_from")
            bind_vars["year_from"] = str(year_from)
        if year_to:
            filter_parts.append("LEFT(d.defense_date, 4) <= @year_to")
            bind_vars["year_to"] = str(year_to)
        filter_d = " AND ".join(filter_parts) if filter_parts else "true"
        query = f"""
        FOR o IN organization
            LET cnt = COUNT(
                FOR ho IN has_organization
                FILTER ho._to == o._id
                FOR d IN dissertation
                FILTER d._id == ho._from AND {filter_d}
                RETURN 1
            )
            FILTER cnt > 0
            SORT cnt DESC
            LIMIT @limit
            RETURN {{ organization_key: o._key, organization_name: o.full_name, count: cnt }}
        """
        return list(self.db.aql.execute(query, bind_vars=bind_vars))

    def get_yearly_distribution(self):
        if not self.db:
            self.connect()
        query = """
        FOR d IN @@diss
            FILTER d.defense_date != null
            LET year = LEFT(d.defense_date, 4)
            COLLECT y = year WITH COUNT INTO cnt
            SORT y
            RETURN { year: y, count: cnt }
        """
        cursor = self.db.aql.execute(query, bind_vars={"@diss": self.diss_col_name})
        years = []
        counts = []
        for entry in cursor:
            if entry["year"].isdigit():
                years.append(int(entry["year"]))
                counts.append(entry["count"])
        return {"years": years, "counts": counts}

    def get_statistics(self):
        if not self.db:
            self.connect()
        diss_total = self.db.collection(self.diss_col_name).count()
        author_total = self.db.collection(self.author_col_name).count()
        org_total = self.db.collection(self.org_col_name).count()
        spec_query = """
            RETURN LENGTH(
                FOR d IN @@diss
                    COLLECT spec = d.specialty_code
                    RETURN spec
            )
        """
        spec_total = next(
            self.db.aql.execute(spec_query, bind_vars={"@diss": self.diss_col_name})
        )
        return {
            "totalDissertations": diss_total,
            "totalAuthors": author_total,
            "totalOrganizations": org_total,
            "totalSpecialties": spec_total
        }

    def export_single_dissertation(self, dissertation, export_format="json"):
        if export_format == "csv":
            output = io.StringIO()

            csv_data = {
                'title': dissertation.get('title', ''),
                'type': dissertation.get('type', ''),
                'science_branch': dissertation.get('science_branch', ''),
                'defense_date': dissertation.get('defense_date', ''),
                'specialty_code': dissertation.get('specialty_code', ''),
                'defense_council_code': dissertation.get('defense_council_code', ''),
                'vak_url': dissertation.get('vak_url', ''),
                'author_name': (
                    dissertation.get('author', {}).get('full_name', '')
                    if dissertation.get('author') else ''
                ),
                'organization_name': (
                    dissertation.get('organization', {}).get('full_name', '')
                    if dissertation.get('organization') else ''
                ),
                'processing_status': dissertation.get('processing_status', ''),
                'created_at': dissertation.get('created_at', ''),
                'updated_at': dissertation.get('updated_at', ''),
                'file_content': dissertation.get('file_content', ''),
            }

            writer = csv.DictWriter(output, fieldnames=list(csv_data.keys()))
            writer.writeheader()
            writer.writerow(csv_data)
            return output.getvalue()

        return json.dumps(dissertation, ensure_ascii=False, indent=2, default=str)

    def get_all_organizations(self, page=1, page_size=20):
        if not self.db:
            self.connect()
        query = """
            FOR o IN organization
                LET cnt = COUNT(
                    FOR ho IN has_organization
                    FILTER ho._to == o._id
                    RETURN 1
                )
                SORT o.full_name ASC
                LIMIT @offset, @limit
                RETURN MERGE(o, {dissertations_count: cnt})
        """
        bind_vars = {"offset": (page - 1) * page_size, "limit": page_size}
        data = list(self.db.aql.execute(query, bind_vars=bind_vars))
        total = self.db.collection(self.org_col_name).count()
        return {"total": total, "data": data}

    def create_author(self, data: dict):
        if not self.db:
            self.connect()
        full_name = data.get("full_name", "").strip()
        if not full_name:
            raise ValueError("full_name is required")
        author_key = self._slugify_author_key(full_name)
        author_coll = self.db.collection(self.author_col_name)
        if author_coll.has(author_key):
            raise ValueError(f"Author with key '{author_key}' already exists")
        doc = {
            "_key": author_key,
            "full_name": full_name,
            "dissertations_count": 0,
        }
        author_coll.insert(doc)
        return author_coll.get(author_key)

    def update_author(self, author_id: str, data: dict):
        if not self.db:
            self.connect()
        author_coll = self.db.collection(self.author_col_name)
        if not author_coll.has(author_id):
            raise ValueError(f"Author '{author_id}' not found")
        updates = {k: v for k, v in data.items() if k != "_key"}
        if updates:
            self.db.aql.execute(
                "FOR a IN @@coll FILTER a._key == @key UPDATE a WITH @fields IN @@coll",
                bind_vars={
                    "@coll": self.author_col_name,
                    "key": author_id,
                    "fields": updates
                }
            )
        return author_coll.get(author_id)

    def delete_author(self, author_id: str):
        if not self.db:
            self.connect()
        author_coll = self.db.collection(self.author_col_name)
        if not author_coll.has(author_id):
            raise ValueError(f"Author '{author_id}' not found")
        self.db.aql.execute(
            "FOR w IN writes FILTER w._from == CONCAT(@col, '/', @key) "
            "REMOVE w IN writes",
            bind_vars={"col": self.author_col_name, "key": author_id}
        )
        author_coll.delete(author_id)
        return {"deleted": author_id}

    def create_organization(self, data: dict):
        if not self.db:
            self.connect()
        full_name = data.get("full_name", "").strip()
        if not full_name:
            raise ValueError("full_name is required")
        org_key = self._slugify_org_key(full_name)
        org_coll = self.db.collection(self.org_col_name)
        if org_coll.has(org_key):
            raise ValueError(f"Organization with key '{org_key}' already exists")
        now = datetime.now(UTC).isoformat()
        doc = {
            "_key": org_key,
            "full_name": full_name,
            "address": data.get("address", ""),
            "phone_number": data.get("phone_number", ""),
            "city": data.get("city", ""),
            "country": data.get("country", "Россия"),
            "created_at": now,
        }
        org_coll.insert(doc)
        return org_coll.get(org_key)

    def update_organization(self, org_id: str, data: dict):
        if not self.db:
            self.connect()
        org_coll = self.db.collection(self.org_col_name)
        if not org_coll.has(org_id):
            raise ValueError(f"Organization '{org_id}' not found")
        updates = {k: v for k, v in data.items() if k != "_key"}
        if updates:
            self.db.aql.execute(
                "FOR o IN @@coll FILTER o._key == @key UPDATE o WITH @fields IN @@coll",
                bind_vars={"@coll": self.org_col_name, "key": org_id, "fields": updates}
            )
        return org_coll.get(org_id)

    def delete_organization(self, org_id: str):
        if not self.db:
            self.connect()
        org_coll = self.db.collection(self.org_col_name)
        if not org_coll.has(org_id):
            raise ValueError(f"Organization '{org_id}' not found")
        self.db.aql.execute(
            "FOR ho IN has_organization FILTER ho._to == CONCAT(@col, '/', @key) "
            "REMOVE ho IN has_organization",
            bind_vars={"col": self.org_col_name, "key": org_id}
        )
        org_coll.delete(org_id)
        return {"deleted": org_id}

    def create_dissertation(self, data: dict):
        if not self.db:
            self.connect()
        vak_url = data.get("vak_url", "").strip()
        if not vak_url:
            raise ValueError("vak_url is required")
        diss_key = self._extract_dissertation_key(vak_url)
        diss_coll = self.db.collection(self.diss_col_name)
        if diss_coll.has(diss_key):
            raise ValueError(f"Dissertation with key '{diss_key}' already exists")
        now = datetime.now(UTC).isoformat()

        author_name = data.get("author_name", "").strip()
        if author_name:
            author_coll = self.db.collection(self.author_col_name)
            existing = list(self.db.aql.execute(
                "FOR a IN @@coll FILTER a.full_name == @name RETURN a",
                bind_vars={"@coll": self.author_col_name, "name": author_name}
            ))
            if existing:
                author_key = existing[0]["_key"]
                self.db.aql.execute(
                    "FOR a IN @@coll FILTER a._key == @key UPDATE a WITH "
                    "{ dissertations_count: a.dissertations_count + 1 } IN @@coll",
                    bind_vars={"@coll": self.author_col_name, "key": author_key}
                )
            else:
                author_key = self._slugify_author_key(author_name)
                author_coll.insert({
                    "_key": author_key,
                    "full_name": author_name,
                    "dissertations_count": 1
                })
        else:
            author_key = None

        org_name = data.get("organization_name", "").strip()
        if org_name:
            org_coll = self.db.collection(self.org_col_name)
            existing_org = list(self.db.aql.execute(
                "FOR o IN @@coll FILTER o.full_name == @name RETURN o",
                bind_vars={"@coll": self.org_col_name, "name": org_name}
            ))
            if existing_org:
                org_key = existing_org[0]["_key"]
            else:
                org_key = self._slugify_org_key(org_name)
                org_coll.insert({
                    "_key": org_key,
                    "full_name": org_name,
                    "address": "",
                    "phone_number": "",
                    "city": "",
                    "country": "Россия",
                    "created_at": now
                })
        else:
            org_key = None

        diss_doc = {
            "_key": diss_key,
            "title": data.get("title", ""),
            "type": data.get("type", ""),
            "science_branch": data.get("science_branch", ""),
            "defense_date": self._parse_date(data.get("defense_date", "")),
            "primary_published_at": self._parse_date(
                data.get("primary_published_at", "")
            ),
            "last_edited_at": self._parse_date(data.get("last_edited_at", "")),
            "specialty_code": data.get("specialty_code", ""),
            "defense_council_code": data.get("defense_council_code", ""),
            "vak_url": vak_url,
            "organization_advert_url": data.get("organization_advert_url", ""),
            "processing_status": data.get("processing_status", "completed"),
            "created_at": now,
            "updated_at": now,
        }
        diss_coll.insert(diss_doc)

        if author_key:
            writes_coll = self.db.collection(self.writes_edge_name)
            edge_key = f"{author_key}_{diss_key}"
            edge_doc = {
                "_key": edge_key,
                "_from": f"{self.author_col_name}/{author_key}",
                "_to": f"{self.diss_col_name}/{diss_key}",
            }
            with contextlib.suppress(DocumentInsertError):
                writes_coll.insert(edge_doc, overwrite=True)

        if org_key:
            has_org_coll = self.db.collection(self.has_org_edge_name)
            org_edge_key = f"{diss_key}_{org_key}"
            org_edge_doc = {
                "_key": org_edge_key,
                "_from": f"{self.diss_col_name}/{diss_key}",
                "_to": f"{self.org_col_name}/{org_key}",
            }
            with contextlib.suppress(DocumentInsertError):
                has_org_coll.insert(org_edge_doc, overwrite=True)

        return diss_coll.get(diss_key)

    def update_dissertation(self, diss_id: str, data: dict):
        if not self.db:
            self.connect()
        diss_coll = self.db.collection(self.diss_col_name)
        if not diss_coll.has(diss_id):
            raise ValueError(f"Dissertation '{diss_id}' not found")

        current_diss = diss_coll.get(diss_id)
        updates = {}

        if "vak_url" in data and data["vak_url"] != current_diss.get("vak_url"):
            new_vak_url = data["vak_url"].strip()
            if not new_vak_url:
                raise ValueError("vak_url is required")

            new_diss_key = self._extract_dissertation_key(new_vak_url)
            if new_diss_key != diss_id:
                if diss_coll.has(new_diss_key):
                    raise ValueError(
                        f"Dissertation with vak_url '{new_vak_url}' already exists"
                    )

                new_doc = current_diss.copy()
                new_doc["_key"] = new_diss_key
                new_doc["vak_url"] = new_vak_url
                new_doc["updated_at"] = datetime.now(UTC).isoformat()

                self.db.aql.execute(
                    "FOR w IN writes FILTER w._to == CONCAT(@old_coll, '/', @old_key) "
                    "UPDATE w WITH {_to: CONCAT(@coll, '/', @new_key)} IN writes",
                    bind_vars={
                        "old_coll": self.diss_col_name,
                        "old_key": diss_id,
                        "coll": self.diss_col_name,
                        "new_key": new_diss_key
                    }
                )

                self.db.aql.execute(
                    "FOR ho IN has_organization FILTER ho._from == "
                    "CONCAT(@old_coll, '/', @old_key) UPDATE ho WITH "
                    "{_from: CONCAT(@coll, '/', @new_key)} IN has_organization",
                    bind_vars={
                        "old_coll": self.diss_col_name,
                        "old_key": diss_id,
                        "coll": self.diss_col_name,
                        "new_key": new_diss_key
                    }
                )

                self.db.aql.execute(
                    "FOR hf IN has_file FILTER hf._from == "
                    "CONCAT(@old_coll, '/', @old_key) UPDATE hf WITH "
                    "{_from: CONCAT(@coll, '/', @new_key)} IN has_file",
                    bind_vars={
                        "old_coll": self.diss_col_name,
                        "old_key": diss_id,
                        "coll": self.diss_col_name,
                        "new_key": new_diss_key
                    }
                )

                for field in [
                    "title", "type", "science_branch", "specialty_code",
                    "defense_council_code", "organization_advert_url",
                    "processing_status"
                ]:
                    if field in data:
                        new_doc[field] = data[field]

                if "defense_date" in data:
                    new_doc["defense_date"] = self._parse_date(data["defense_date"])
                if "primary_published_at" in data:
                    new_doc["primary_published_at"] = self._parse_date(
                        data["primary_published_at"]
                    )
                if "last_edited_at" in data:
                    new_doc["last_edited_at"] = self._parse_date(data["last_edited_at"])

                new_doc["updated_at"] = datetime.now(UTC).isoformat()

                diss_coll.insert(new_doc)
                diss_coll.delete(diss_id)

                if "author_name" in data:
                    self._update_author_for_dissertation(
                        new_diss_key, data["author_name"]
                    )
                if "organization_name" in data:
                    self._update_organization_for_dissertation(
                        new_diss_key, data["organization_name"]
                    )

                return self.get_dissertation_details(new_diss_key)

        for field in [
            "title", "type", "science_branch", "specialty_code",
            "defense_council_code", "organization_advert_url", "processing_status"
        ]:
            if field in data:
                updates[field] = data[field]

        if "defense_date" in data:
            updates["defense_date"] = self._parse_date(data["defense_date"])
        if "primary_published_at" in data:
            updates["primary_published_at"] = self._parse_date(
                data["primary_published_at"]
            )
        if "last_edited_at" in data:
            updates["last_edited_at"] = self._parse_date(data["last_edited_at"])

        if updates:
            updates["updated_at"] = datetime.now(UTC).isoformat()
            self.db.aql.execute(
                "FOR d IN @@coll FILTER d._key == @key UPDATE d WITH @fields IN @@coll",
                bind_vars={
                "@coll": self.diss_col_name,
                "key": diss_id,
                "fields": updates
            }
            )

        if "author_name" in data:
            self._update_author_for_dissertation(
                diss_id, data["author_name"]
            )
        if "organization_name" in data:
            self._update_organization_for_dissertation(
                diss_id, data["organization_name"]
            )

        return self.get_dissertation_details(diss_id)

    def _update_author_for_dissertation(self, diss_key: str, author_name: str):
        author_name = author_name.strip()
        if not author_name:
            return

        author_coll = self.db.collection(self.author_col_name)
        writes_coll = self.db.collection(self.writes_edge_name)

        current_edges = list(self.db.aql.execute(
            "FOR w IN writes FILTER w._to == CONCAT(@coll, '/', @diss_key) RETURN w",
            bind_vars={"coll": self.diss_col_name, "diss_key": diss_key}
        ))

        if not current_edges:
            raise ValueError("Dissertation has no author assigned")

        old_author_key = None
        for edge in current_edges:
            old_author_key = edge["_from"].split("/")[-1]
            writes_coll.delete(edge["_key"])

        if old_author_key:
            self.db.aql.execute(
                "FOR a IN @@coll FILTER a._key == @key UPDATE a WITH "
                "{dissertations_count: MAX([0, a.dissertations_count - 1])} IN @@coll",
                bind_vars={"@coll": self.author_col_name, "key": old_author_key}
            )

        new_author = list(self.db.aql.execute(
            "FOR a IN author FILTER a.full_name == @name RETURN a",
            bind_vars={"name": author_name}
        ))

        if new_author:
            new_author_key = new_author[0]["_key"]
            self.db.aql.execute(
                "FOR a IN @@coll FILTER a._key == @key UPDATE a WITH "
                "{ dissertations_count: a.dissertations_count + 1 } IN @@coll",
                bind_vars={"@coll": self.author_col_name, "key": new_author_key}
            )
        else:
            new_author_key = self._slugify_author_key(author_name)
            author_coll.insert({
                "_key": new_author_key,
                "full_name": author_name,
                "dissertations_count": 1
            })

        new_edge_key = f"{new_author_key}_{diss_key}"
        edge_doc = {
            "_key": new_edge_key,
            "_from": f"{self.author_col_name}/{new_author_key}",
            "_to": f"{self.diss_col_name}/{diss_key}",
        }
        writes_coll.insert(edge_doc, overwrite=True)

    def _update_organization_for_dissertation(self, diss_key: str, org_name: str):
        org_name = org_name.strip()
        if not org_name:
            return

        org_coll = self.db.collection(self.org_col_name)
        has_org_coll = self.db.collection(self.has_org_edge_name)

        current_edges = list(self.db.aql.execute(
            "FOR ho IN has_organization FILTER ho._from == "
            "CONCAT(@coll, '/', @diss_key) RETURN ho",
            bind_vars={"coll": self.diss_col_name, "diss_key": diss_key}
        ))

        for edge in current_edges:
            has_org_coll.delete(edge["_key"])

        new_org = list(self.db.aql.execute(
            "FOR o IN organization FILTER o.full_name == @name RETURN o",
            bind_vars={"name": org_name}
        ))

        if new_org:
            new_org_key = new_org[0]["_key"]
        else:
            new_org_key = self._slugify_org_key(org_name)
            now = datetime.now(UTC).isoformat()
            org_coll.insert({
                "_key": new_org_key,
                "full_name": org_name,
                "address": "",
                "phone_number": "",
                "city": "",
                "country": "Россия",
                "created_at": now
            })

        new_edge_key = f"{diss_key}_{new_org_key}"
        edge_doc = {
            "_key": new_edge_key,
            "_from": f"{self.diss_col_name}/{diss_key}",
            "_to": f"{self.org_col_name}/{new_org_key}",
        }
        has_org_coll.insert(edge_doc, overwrite=True)

    def delete_dissertation(self, diss_id: str):
        if not self.db:
            self.connect()
        diss_coll = self.db.collection(self.diss_col_name)
        if not diss_coll.has(diss_id):
            raise ValueError(f"Dissertation '{diss_id}' not found")
        self.db.aql.execute(
            "FOR w IN writes FILTER w._to == "
            "CONCAT(@col, '/', @key) REMOVE w IN writes",
            bind_vars={"col": self.diss_col_name, "key": diss_id}
        )
        self.db.aql.execute(
            "FOR ho IN has_organization FILTER ho._from == "
            "CONCAT(@col, '/', @key) REMOVE ho IN has_organization",
            bind_vars={"col": self.diss_col_name, "key": diss_id}
        )
        self.db.aql.execute(
            "FOR hf IN has_file FILTER hf._from == "
            "CONCAT(@col, '/', @key) REMOVE hf IN has_file",
            bind_vars={"col": self.diss_col_name, "key": diss_id}
        )
        file_coll = self.db.collection(self.file_col_name)
        file_key = f"{diss_id}_file"
        if file_coll.has(file_key):
            file_coll.delete(file_key)
        diss_coll.delete(diss_id)
        return {"deleted": diss_id}
