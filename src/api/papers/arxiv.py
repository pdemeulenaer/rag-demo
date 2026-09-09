"""Polite, serial arXiv metadata access; no LLM calls here."""
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
import re
import time
from urllib.parse import urlparse
import xml.etree.ElementTree as ET

import httpx

ATOM = "{http://www.w3.org/2005/Atom}"
ARXIV = "{http://arxiv.org/schemas/atom}"
OAI = "{http://www.openarchives.org/OAI/2.0/}"
META = "{http://arxiv.org/OAI/arXiv/}"


@dataclass
class Paper:
    arxiv_id: str
    version: int
    title: str
    abstract: str
    authors: list[str]
    categories: list[str]
    published: str
    updated: str
    doi: str | None = None
    license: str | None = None

    @property
    def source_url(self):
        return f"https://arxiv.org/abs/{self.arxiv_id}v{self.version}"

    @property
    def pdf_url(self):
        return f"https://arxiv.org/pdf/{self.arxiv_id}v{self.version}"

    def to_dict(self):
        return asdict(self)


def normalize(text):
    return re.sub(r"[\W_]+", " ", text.casefold()).strip()


def matches_scope(categories, title, abstract, settings):
    if not set(categories).intersection(settings.categories):
        return False
    text = normalize(title + " " + abstract)
    return not settings.terms or any(
        re.search(r"\b" + re.escape(normalize(term)) + r"s?\b", text)
        for term in settings.terms
    )


def parse_atom(xml):
    root = ET.fromstring(xml)
    papers = []
    for entry in root.findall(f"{ATOM}entry"):
        identifier = entry.findtext(f"{ATOM}id", "").split("/abs/")[-1]
        match = re.fullmatch(r"(\d{4}\.\d{4,5}|[a-z-]+(?:\.[A-Z]{2})?/\d{7})v(\d+)", identifier)
        if not match:
            raise ValueError(f"Invalid or unversioned arXiv response ID: {identifier}")
        papers.append(Paper(
            arxiv_id=match[1], version=int(match[2]),
            title=" ".join(entry.findtext(f"{ATOM}title", "").split()),
            abstract=" ".join(entry.findtext(f"{ATOM}summary", "").split()),
            authors=[a.findtext(f"{ATOM}name", "") for a in entry.findall(f"{ATOM}author")],
            categories=[c.attrib["term"] for c in entry.findall(f"{ATOM}category")],
            published=entry.findtext(f"{ATOM}published", ""),
            updated=entry.findtext(f"{ATOM}updated", ""),
            doi=entry.findtext(f"{ARXIV}doi"),
        ))
    total = int(root.findtext("{http://a9.com/-/spec/opensearch/1.1/}totalResults", str(len(papers))))
    return papers, total


class ArxivClient:
    def __init__(self, user_agent, client=None, sleep=time.sleep, clock=time.monotonic):
        self.client = client or httpx.Client(headers={"User-Agent": user_agent}, timeout=90)
        self.sleep, self.clock = sleep, clock
        self.last_request = None

    def close(self):
        self.client.close()

    def _pace(self):
        if self.last_request is not None:
            self.sleep(max(0, 3.1 - (self.clock() - self.last_request)))
        self.last_request = self.clock()

    def get(self, url, params=None):
        for attempt in range(5):
            self._pace()
            try:
                response = self.client.get(url, params=params)
            except httpx.TransportError:
                if attempt == 4:
                    raise
                self.sleep(3 * 2 ** attempt)
                continue
            if response.status_code in {429, 500, 502, 503, 504} and attempt < 4:
                retry = response.headers.get("Retry-After", "")
                try:
                    delay = float(retry)
                except ValueError:
                    try:
                        delay = (parsedate_to_datetime(retry) - datetime.now(timezone.utc)).total_seconds()
                    except (ValueError, TypeError):
                        delay = 3 * 2 ** attempt
                if delay > 300:
                    raise RuntimeError("arXiv requested a long pause; retry this job later")
                self.sleep(max(3.1, delay))
                continue
            response.raise_for_status()
            return response.content
        raise RuntimeError("arXiv request retry budget exhausted")

    def backfill(self, settings, since, until):
        # Fetch category metadata, then apply ONE shared local topic filter to API/OAI.
        categories = " OR ".join(f"cat:{c}" for c in settings.categories)
        query = f"({categories}) AND submittedDate:[{since:%Y%m%d%H%M} TO {until:%Y%m%d%H%M}]"
        start = 0
        while True:
            papers, total = parse_atom(self.get("https://export.arxiv.org/api/query", {
                "search_query": query, "start": start, "max_results": 100,
                "sortBy": "submittedDate", "sortOrder": "ascending",
            }))
            if total > 1000:
                raise ValueError("Backfill window has >1000 category papers; use a shorter date range")
            if not papers and start < total:
                raise RuntimeError("Incomplete arXiv pagination; backfill can be retried safely")
            for paper in papers:
                if matches_scope(paper.categories, paper.title, paper.abstract, settings):
                    yield paper
            start += len(papers)
            if start >= total:
                break

    def resolve(self, identifiers):
        if not identifiers:
            return []
        papers, _ = parse_atom(self.get("https://export.arxiv.org/api/query", {
            "id_list": ",".join(identifiers), "max_results": len(identifiers),
        }))
        if {p.arxiv_id for p in papers} != set(identifiers):
            raise RuntimeError("Search API did not resolve all OAI records; checkpoint not advanced")
        return papers

    def oai_sets(self, categories):
        """Discover exact setSpecs instead of inventing a category-to-set mapping."""
        found = {}
        params = {"verb": "ListSets"}
        while True:
            root = ET.fromstring(self.get("https://oaipmh.arxiv.org/oai", params))
            self._check_oai(root)
            for item in root.findall(f"{OAI}ListSets/{OAI}set"):
                spec = item.findtext(f"{OAI}setSpec", "")
                parts = spec.split(":")
                category = parts[1] + ("." + parts[2] if len(parts) > 2 else "") if len(parts) > 1 else ""
                if category in categories:
                    found[category] = spec
            token = root.findtext(f"{OAI}ListSets/{OAI}resumptionToken")
            if not token:
                break
            params = {"verb": "ListSets", "resumptionToken": token}
        if set(found) != set(categories):
            raise ValueError(f"Cannot resolve OAI sets for {set(categories) - set(found)}")
        return found

    @staticmethod
    def _check_oai(root):
        error = root.find(f"{OAI}error")
        if error is not None and error.get("code") != "noRecordsMatch":
            raise RuntimeError(f"OAI error: {error.get('code')}: {error.text}")

    def changes(self, set_spec, since):
        params = {"verb": "ListRecords", "metadataPrefix": "arXiv", "set": set_spec, "from": since}
        while True:
            root = ET.fromstring(self.get("https://oaipmh.arxiv.org/oai", params))
            self._check_oai(root)
            records = []
            for record in root.findall(f"{OAI}ListRecords/{OAI}record"):
                header = record.find(f"{OAI}header")
                identifier = header.findtext(f"{OAI}identifier", "").removeprefix("oai:arXiv.org:")
                meta = record.find(f"{OAI}metadata/{META}arXiv")
                if header.get("status") == "deleted":
                    records.append({"id": identifier, "deleted": True})
                elif meta is None:
                    raise ValueError("Missing arXiv metadata in OAI record")
                else:
                    records.append({
                        "id": identifier, "deleted": False,
                        "title": meta.findtext(f"{META}title", ""),
                        "abstract": meta.findtext(f"{META}abstract", ""),
                        "categories": meta.findtext(f"{META}categories", "").split(),
                        "license": meta.findtext(f"{META}license"),
                    })
            yield root.findtext(f"{OAI}responseDate"), records
            token = root.findtext(f"{OAI}ListRecords/{OAI}resumptionToken")
            if not token:
                break
            params = {"verb": "ListRecords", "resumptionToken": token}

    def download_pdf(self, paper, max_bytes):
        # Constructed from a validated arXiv ID, never follow arbitrary feed URLs.
        url = paper.pdf_url
        for _ in range(4):
            parsed = urlparse(url)
            if parsed.scheme != "https" or parsed.hostname not in {"arxiv.org", "export.arxiv.org"}:
                raise ValueError("Unexpected PDF redirect host")
            self._pace()
            with self.client.stream("GET", url) as response:
                if response.is_redirect:
                    url = str(response.url.join(response.headers["location"]))
                    continue
                response.raise_for_status()
                chunks, size = [], 0
                for chunk in response.iter_bytes():
                    size += len(chunk)
                    if size > max_bytes:
                        raise ValueError("PDF exceeds configured download size limit")
                    chunks.append(chunk)
                data = b"".join(chunks)
                if not data.startswith(b"%PDF-"):
                    raise ValueError("arXiv response is not a PDF")
                return data
        raise ValueError("Too many PDF redirects")
