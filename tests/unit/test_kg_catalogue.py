"""Live KG selection/preview against SQLite and real artifacts; no external services."""
import json
from pathlib import Path
import shlex
import subprocess

import pytest
from sqlalchemy import event, update

from src.api.kg import catalogue as live, jobs
from src.api.kg.artifacts import VerifiedReader
from src.api.kg.settings import KGSettings
from src.api.papers.arxiv import Paper
from src.api.papers.catalogue import Catalogue, papers, builds
from src.api.papers.artifacts import ArtifactStore


@pytest.fixture
def corpus(tmp_path):
    settings=KGSettings(_env_file=None,PAPERS_DATABASE_URL=f"sqlite:///{tmp_path}/catalogue.db",
        PAPERS_ARTIFACT_DIR=tmp_path/"artifacts",LANGFUSE_ENABLED=False)
    catalogue=Catalogue(settings.PAPERS_DATABASE_URL)
    catalogue.initialize()
    yield catalogue,settings
    catalogue.close()


def ready(corpus,number=1,*,title=None,abstract="A globular cluster study",source="arxiv",artifacts=False):
    catalogue,settings=corpus
    paper=Paper(f"2610.{number:05d}",1,title or f"M22 star cluster study {number}",abstract,[],
                ["astro-ph.GA"],"2026-10-01","2026-10-01")
    if source=="arxiv":
        build=catalogue.get_build(catalogue.discover(paper,settings))
    else:
        build=catalogue.upload(f"upload-{number}",dict(title=paper.title,authors=[]),settings.QDRANT_COLLECTION_NAME,
                               settings.EMBEDDING_MODEL,"upload-pipeline")
    manifest=dict(artifact=dict(sha256="a"*64),chunk_order=dict(count=3))
    if artifacts:
        store=ArtifactStore(settings)
        raw=[dict(chunk_index=i,page_number=1,section_header="Results",text=f"M22 distance is {i+3} kpc.") for i in range(3)]
        manifest=dict(collection=build["collection"],embedding_model=build["embedding_model"],pipeline_id=build["pipeline_id"],
            extraction=dict(version="fixture"),chunk_count=3,
            chunk_order=dict(count=3,field="chunk_index",starts_at=0,contiguous=True,scope="text_chunks"),
            text=store.put_json(build["id"],"chunks.json",raw),pages=store.put_json(build["id"],"pages.json",[dict(page_number=1,text="Markdown")]),
            markdown=store.put(build["id"],"document.md",b"Markdown"))
        manifest["artifact"]=store.put_json(build["id"],"manifest.json",manifest)
    catalogue.update_build(build["id"],status="ready",manifest=manifest)
    with catalogue.engine.begin() as connection:
        connection.execute(update(papers).where(papers.c.id==build["paper_id"]).values(active_build=build["id"],active_version=1))
    return catalogue.get_build(build["id"])


def test_browse_live_metadata_without_snapshot_or_full_corpus_load(corpus,monkeypatch):
    catalogue,settings=corpus
    row=ready(corpus)
    monkeypatch.setattr(catalogue,"all_builds",lambda:pytest.fail("Must not load all builds"))
    monkeypatch.setattr(catalogue,"inventory",lambda:pytest.fail("Must not load inventory"))
    statements=[]
    event.listen(catalogue.engine,"before_cursor_execute",lambda conn,cursor,sql,params,context,many:statements.append(sql))
    result=live.browse(catalogue,settings,term="M22")
    assert result["papers"][0]["paper_id"]==row["paper_id"]
    assert result["model_calls"]==result["database_writes"]==0
    assert result["artifacts_verified"] is False
    assert all("LIMIT" in sql.upper() and "OFFSET 0" not in sql.upper() for sql in statements)
    assert all(sql.lstrip().upper().startswith("SELECT") for sql in statements)


def test_keyset_paging_no_duplicates_and_search_filter(corpus):
    catalogue,settings=corpus
    ids={ready(corpus,i)["paper_id"] for i in range(1,8)}
    found,after=[],None
    while True:
        page=live.browse(catalogue,settings,limit=2,after=after)
        found.extend(p["paper_id"] for p in page["papers"])
        if not page["has_more"]:
            break
        assert page["next_after"]==page["papers"][-1]["paper_id"]
        after=page["next_after"]
    assert set(found)==ids and len(found)==len(ids) and found==sorted(found)


@pytest.mark.parametrize("fault",["deleted","nonready","legacy_collection","wrong_model","no_manifest","outside_topic","inactive"])
def test_browse_and_selection_exclude_ineligible_papers(corpus,fault):
    catalogue,settings=corpus
    row=ready(corpus,abstract="unrelated" if fault=="outside_topic" else "globular cluster")
    if fault=="outside_topic":
        meta=dict(row["metadata"],title="Unrelated work")
        catalogue.update_build(row["id"],metadata=meta)
    elif fault in {"deleted","inactive"}:
        with catalogue.engine.begin() as connection:
            connection.execute(update(papers).where(papers.c.id==row["paper_id"]).values(
                **(dict(deleted=1) if fault=="deleted" else dict(active_build=None))))
    else:
        change={"nonready":dict(status="failed"),"legacy_collection":dict(collection="old_dense"),
                "wrong_model":dict(embedding_model="other"),"no_manifest":dict(manifest=None)}[fault]
        catalogue.update_build(row["id"],**change)
    assert not live.browse(catalogue,settings)["papers"]
    with pytest.raises(ValueError,match="not eligible"):
        live.select_papers(catalogue,settings,paper_ids=[row["paper_id"]])


def test_upload_and_arxiv_collection_boundaries(corpus):
    catalogue,settings=corpus
    a=ready(corpus)
    b=ready(corpus,2,source="uploads")
    assert [p["paper_id"] for p in live.browse(catalogue,settings,source="uploads")["papers"]]==[b["paper_id"]]
    assert {p["paper_id"] for p in live.browse(catalogue,settings,source="all")["papers"]}=={a["paper_id"],b["paper_id"]}
    doc=live.select_papers(catalogue,settings,paper_ids=[a["paper_id"],b["paper_id"]])
    assert len(doc.papers)==2


def test_literal_percent_and_underscore_not_sql_wildcards(corpus):
    catalogue,settings=corpus
    row=ready(corpus,title="A globular cluster %_ marker")
    ready(corpus,2,title="A globular cluster ordinary marker")
    assert [p["paper_id"] for p in live.browse(catalogue,settings,term="%_")["papers"]]==[row["paper_id"]]
    assert not live.browse(catalogue,settings,term="' OR 1=1 --")["papers"]


def test_select_includes_explicit_pilot_ids_and_groups_without_alias_inference(corpus,tmp_path):
    catalogue,settings=corpus
    a,b=ready(corpus),ready(corpus,2)
    pilot=tmp_path/"pilot.json"
    pilot.write_text(json.dumps(dict(schema_version=1,name="explicit",papers=[dict(paper_id=a["paper_id"],title="Display label",group="M22")])) )
    doc=live.select_papers(catalogue,settings,pilot_path=pilot,paper_ids=[a["paper_id"],b["paper_id"]])
    assert len(doc.papers)==2
    assert next(p for p in doc.papers if str(p.paper_id)==a["paper_id"]).group=="M22"
    assert all(p.title.startswith("M22") for p in doc.papers)  # Catalogue title, never copied pilot label.
    assert doc==live.select_papers(catalogue,settings,pilot_path=pilot,paper_ids=[b["paper_id"],a["paper_id"]])


def test_selection_file_is_repeat_safe_but_not_overwritten(corpus,tmp_path):
    catalogue,settings=corpus
    a,b=ready(corpus),ready(corpus,2)
    doc=live.select_papers(catalogue,settings,paper_ids=[a["paper_id"]])
    path=tmp_path/"batch"/"selection.json"
    first=live.save_selection(doc,path,catalogue,settings)
    raw=path.read_bytes()
    assert live.save_selection(doc,path,catalogue,settings)==first and path.read_bytes()==raw
    with pytest.raises(ValueError,match="differs"):
        live.save_selection(live.select_papers(catalogue,settings,paper_ids=[a["paper_id"],b["paper_id"]]),path,catalogue,settings)
    assert path.read_bytes()==raw
    assert not (path.parent/"plan.json").exists()


@pytest.mark.parametrize("field,value",[("manifest",dict(artifact=dict(sha256="b"*64),chunk_order=dict(count=3))),
    ("status","failed"),("metadata",dict(title="Changed globular cluster paper",abstract="",categories=["astro-ph.GA"]))])
def test_changed_selection_fails_before_writing(corpus,tmp_path,field,value):
    catalogue,settings=corpus
    row=ready(corpus)
    doc=live.select_papers(catalogue,settings,paper_ids=[row["paper_id"]])
    catalogue.update_build(row["id"],**{field:value})
    path=tmp_path/"new"/"selection.json"
    with pytest.raises(ValueError,match="stale"):
        live.save_selection(doc,path,catalogue,settings)
    assert not path.exists()


def test_selection_rejects_tampering_empty_and_old_extraction_directory(corpus,tmp_path):
    catalogue,settings=corpus
    row=ready(corpus)
    with pytest.raises(ValueError,match="explicit"):
        live.select_papers(catalogue,settings)
    doc=live.select_papers(catalogue,settings,paper_ids=[row["paper_id"]])
    value=doc.model_dump(mode="json")
    value["papers"][0]["title"]="tampered"
    with pytest.raises(ValueError,match="integrity"):
        live.CatalogueSelection.model_validate(value)
    (tmp_path/"plan.json").write_text("legacy extraction run")
    with pytest.raises(ValueError,match="Existing extraction"):
        live.save_selection(doc,tmp_path/"selection.json",catalogue,settings)


def test_caps_validation_and_invalid_cursor(corpus):
    catalogue,settings=corpus
    a,b=ready(corpus),ready(corpus,2)
    for limit in (0,101):
        with pytest.raises(ValueError,match="page size"):
            live.browse(catalogue,settings,limit=limit)
    with pytest.raises(ValueError):
        live.browse(catalogue,settings,after="invalid")
    settings.KG_PREPARE_MAX_PAPERS=1
    with pytest.raises(ValueError,match="MAX_PAPERS"):
        live.select_papers(catalogue,settings,paper_ids=[a["paper_id"],b["paper_id"]])


def test_prepare_preview_verifies_full_artifacts_and_counts_without_writes(corpus,tmp_path):
    catalogue,settings=corpus
    a,b=ready(corpus,artifacts=True),ready(corpus,2,artifacts=True)
    selection=live.select_papers(catalogue,settings,paper_ids=[a["paper_id"],b["paper_id"]]).model_dump(mode="json")
    result=jobs.prepare_preview(selection,catalogue,VerifiedReader(settings),settings,chunks_per_paper=2,max_calls=3)
    assert result["papers"]==2 and result["maximum_first_pass_calls"]==6
    assert result["sample_first_pass_calls"]==4 and result["maximum_calls_next_fresh_invocation"]==3
    assert result["model_calls"]==result["database_writes"]==result["local_writes"]==0
    assert result["artifacts_verified"] and not list(tmp_path.rglob("plan.json"))
    with pytest.raises(ValueError,match="already fixes"):
        jobs.prepare_preview(selection,catalogue,VerifiedReader(settings),settings,paper_limit=1)


def test_prepare_preview_detects_corrupt_artifacts_and_public_limits(corpus):
    catalogue,settings=corpus
    row=ready(corpus,artifacts=True)
    selection=live.select_papers(catalogue,settings,paper_ids=[row["paper_id"]]).model_dump(mode="json")
    settings.KG_PREPARE_MAX_CHUNKS=2
    with pytest.raises(ValueError,match="MAX_CHUNKS"):
        jobs.prepare_preview(selection,catalogue,VerifiedReader(settings),settings)
    settings.KG_PREPARE_MAX_CHUNKS=20
    Path(row["manifest"]["text"]["uri"]).write_text("bad hash")
    with pytest.raises(ValueError,match="integrity"):
        jobs.prepare_preview(selection,catalogue,VerifiedReader(settings),settings)


def test_live_prepare_uses_current_schema_and_preserves_plan_on_repeat(corpus,tmp_path):
    pytest.importorskip("neo4j_graphrag")
    catalogue,settings=corpus
    row=ready(corpus,artifacts=True)
    selection=live.select_papers(catalogue,settings,paper_ids=[row["paper_id"]]).model_dump(mode="json")
    directory=tmp_path/"batch"
    first=jobs.prepare(directory,selection,catalogue,VerifiedReader(settings),settings)
    assert jobs.prepare(directory,selection,catalogue,VerifiedReader(settings),settings)==first
    plan,chunks=jobs.read_plan(directory,settings)
    assert len(plan["chunks"])==3 and plan["papers"][0]["manifest_sha256"]==selection["papers"][0]["manifest_sha256"]
    assert plan["corpus_fingerprint"]==selection["corpus_fingerprint"]


def test_selection_creation_failure_leaves_no_partial_manifest(corpus,tmp_path,monkeypatch):
    catalogue,settings=corpus
    row=ready(corpus)
    doc=live.select_papers(catalogue,settings,paper_ids=[row["paper_id"]])
    directory=tmp_path/"new"
    def fail_publish(*args):
        raise OSError("simulated publication failure")
    monkeypatch.setattr(live.os,"link",fail_publish)
    with pytest.raises(OSError):
        live.save_selection(doc,directory/"selection.json",catalogue,settings)
    assert [path.name for path in directory.iterdir()]==[".lock"]


def test_preview_rechecks_build_after_loading_and_rejects_stale_selection(corpus,monkeypatch):
    from src.api.kg import artifacts
    catalogue,settings=corpus
    row=ready(corpus,artifacts=True)
    selection=live.select_papers(catalogue,settings,paper_ids=[row["paper_id"]]).model_dump(mode="json")
    original=artifacts.load_paper
    def load_then_change(*args):
        result=original(*args)
        catalogue.update_build(row["id"],status="failed")
        return result
    monkeypatch.setattr(artifacts,"load_paper",load_then_change)
    with pytest.raises(ValueError,match="stale"):
        jobs.prepare_preview(selection,catalogue,VerifiedReader(settings),settings)


def test_preview_rejects_oversized_input_before_retaining_corpus(corpus,monkeypatch):
    from src.api.kg import artifacts
    catalogue,settings=corpus
    row=ready(corpus,artifacts=True)
    selection=live.select_papers(catalogue,settings,paper_ids=[row["paper_id"]]).model_dump(mode="json")
    chunks,digest=artifacts.load_paper(selection["papers"][0],catalogue,VerifiedReader(settings))
    chunks[0]=chunks[0].model_copy(update=dict(text="x"*11000))
    monkeypatch.setattr(artifacts,"load_paper",lambda *args:(chunks,digest))
    settings.KG_PREPARE_MAX_BYTES=10000
    with pytest.raises(ValueError,match="MAX_BYTES"):
        jobs.prepare_preview(selection,catalogue,VerifiedReader(settings),settings)


def test_cli_live_browse_select_and_preview(corpus,tmp_path,monkeypatch,capsys):
    from src.api.kg.__main__ import main
    catalogue,settings=corpus
    row=ready(corpus,artifacts=True)
    monkeypatch.setattr("src.api.kg.settings.KGSettings",lambda:settings)
    monkeypatch.setattr("src.api.papers.catalogue.Catalogue",lambda url:catalogue)
    main(["catalogue","--term","M22"])
    assert json.loads(capsys.readouterr().out)["returned"]==1
    path=tmp_path/"batch"/"selection.json"
    main(["select","--paper-id",row["paper_id"],"--output",str(path)])
    assert json.loads(capsys.readouterr().out)["papers_selected"]==1
    main(["prepare-preview","--selection-file",str(path),"--chunks-per-paper","2"])
    assert json.loads(capsys.readouterr().out)["sample_first_pass_calls"]==2
    assert not (path.parent/"plan.json").exists()


def test_make_live_and_legacy_inputs_are_explicit_and_quoted(tmp_path):
    root=Path(__file__).resolve().parents[2]
    directory=str(tmp_path/"new batch")
    def command(target,*args):
        result=subprocess.run(["make","--no-print-directory","--dry-run",target,f"KG_DIR={directory}",*args],cwd=root,
            check=True,capture_output=True,text=True)
        return shlex.split(result.stdout.strip())
    selected=command("kg-select","KG_PAPER_IDS=id-one id-two")
    assert selected.count("--paper-id")==2 and selected[selected.index("--output")+1]==directory+"/selection.json"
    assert "--include-pilot" in selected
    assert "--include-pilot" not in command("kg-select","KG_INCLUDE_PILOT=false")
    assert "--snapshot" in command("kg-prepare")
    frozen=command("kg-prepare",f"KG_SELECTION_FILE={directory}/selection.json")
    assert "--selection-file" in frozen and "--snapshot" not in frozen
    preview=command("kg-prepare-preview","KG_CHUNKS_PER_PAPER=3","KG_MAX_CALLS=21")
    assert preview[preview.index("--selection-file")+1]==directory+"/selection.json"
