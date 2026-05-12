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
        result = self.search_dissertations(filters, page=1, page_size=10000)
        data = result["data"]
        if export_format == "csv":
            output = io.StringIO()
            if data:
                writer = csv.DictWriter(output, fieldnames=data[0].keys())
                writer.writeheader()
                writer.writerows(data)
            return output.getvalue()
        return json.dumps(data, ensure_ascii=False, indent=2)

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
        LET dissertations = (
            FOR ho IN has_organization
            FILTER ho._to == o._id
            FOR d IN dissertation
            FILTER d._id == ho._from
            RETURN d
        )
        RETURN MERGE(o, { dissertations: dissertations })
        """
        bind_vars = {"org_coll": self.org_col_name, "key": org_id}
        cursor = self.db.aql.execute(query, bind_vars=bind_vars)
        return next(cursor, None)

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
        spec_total = next(self.db.aql.execute(spec_query, bind_vars={"@diss": self.diss_col_name}))
        return {
            "totalDissertations": diss_total,
            "totalAuthors": author_total,
            "totalOrganizations": org_total,
            "totalSpecialties": spec_total
        }
