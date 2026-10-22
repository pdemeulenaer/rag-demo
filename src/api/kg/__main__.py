"""KG CLI: preview/schema are offline; prepare reads services; extract is explicitly paid."""
import argparse
import json
from pathlib import Path

from pydantic import ValidationError

from .record_schema import ExtractionBatch
from .preview import DEFAULT_PILOT, preview


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    selection = commands.add_parser("preview", help="Read saved paper identities only")
    selection.add_argument("--snapshot", required=True, type=Path)
    selection.add_argument("--selection", choices=("pilot", "all"), default="pilot")
    selection.add_argument("--pilot", type=Path, default=DEFAULT_PILOT)
    commands.add_parser("schema", help="Print the scientific extraction JSON schema")
    browse = commands.add_parser("catalogue",help="Read paged active/ready metadata from PostgreSQL; no files or model calls")
    browse.add_argument("--source",choices=("arxiv","uploads","all"),default="arxiv")
    browse.add_argument("--term",help="Literal title/abstract substring; not full-text search")
    browse.add_argument("--limit",type=int,default=20)
    browse.add_argument("--after",help="paper_id cursor from the previous page")
    choose = commands.add_parser("select",help="Pin explicit active paper/build IDs in a new local KG manifest")
    choose.add_argument("--paper-id",action="append",default=[])
    choose.add_argument("--include-pilot",type=Path,help="Include these explicit paper IDs/group labels as well")
    choose.add_argument("--output",required=True,type=Path,help="Local selection.json path; never overwritten")
    for name in ("prepare", "prepare-preview"):
        prepare = commands.add_parser(name,help="Verify selected full artifacts; preview writes nothing, prepare freezes plan.json")
        inputs = prepare.add_mutually_exclusive_group(required=True)
        inputs.add_argument("--snapshot",type=Path)
        inputs.add_argument("--selection-file",type=Path,help="Independent live-catalogue KG manifest")
        prepare.add_argument("--selection",choices=("pilot","all"),default="pilot")
        prepare.add_argument("--pilot",type=Path,default=DEFAULT_PILOT)
        prepare.add_argument("--papers",type=int)
        if name == "prepare":
            prepare.add_argument("--output",required=True,type=Path)
        else:
            prepare.add_argument("--chunks-per-paper",type=int)
            prepare.add_argument("--max-calls",type=int)
    extract = commands.add_parser("extract", help="PAID extraction; resume pending chunks, with a per-invocation cap")
    extract.add_argument("--output", required=True, type=Path)
    extract.add_argument("--max-calls", type=int)
    extract.add_argument("--retry-failed", action="store_true")
    extract.add_argument("--failed-only", action="store_true", help="Explicitly retry failed/interrupted chunks only")
    extract.add_argument("--chunks-per-paper", type=int,
                         help="Sample up to N distinct attempted chunks per paper across this directory; pending only")
    validate = commands.add_parser("validate", help="Check saved candidates/provenance; no model calls")
    validate.add_argument("--output", required=True, type=Path)
    for name in ("review-prepare", "review-validate", "review-export", "review-set"):
        command = commands.add_parser(name, help="Local scientific review; no model/database calls")
        command.add_argument("--output", required=True, type=Path)
        command.add_argument("--review", default="review.json", help="JSON sidecar filename within the KG directory")
        if name == "review-set":
            command.add_argument("--record-id", required=True)
            command.add_argument("--decision", required=True, choices=("needs_review", "approved", "excluded"))
            command.add_argument("--reviewer", required=True)
            command.add_argument("--reason", choices=("presentation_only", "unsupported", "incorrect_type", "duplicate", "other"))
            command.add_argument("--notes", default="")
    for name in ("publish-preview", "publish", "publication-verify", "activate", "publication-status"):
        command = commands.add_parser(name, help="Neo4j publication; no model calls (publish/activate write)")
        if name != "publication-status":
            command.add_argument("--output", required=True, type=Path)
            command.add_argument("--review", default="review.json")
        command.add_argument("--graph-name")
        if name == "activate":
            command.add_argument("--expect-active", default="none",
                                 help="Expected current publication ID, or none for first activation")
    args = parser.parse_args(argv)
    try:
        if args.command == "schema":
            result = ExtractionBatch.model_json_schema()
        elif args.command == "preview":
            result = preview(args.snapshot, selection=args.selection, pilot_path=args.pilot)
        elif args.command in {"catalogue","select"}:
            from .settings import KGSettings
            from . import catalogue as live
            from src.api.papers.catalogue import Catalogue
            settings = KGSettings()
            catalogue = Catalogue(settings.PAPERS_DATABASE_URL)
            try:
                catalogue.require_schema()
                if args.command == "catalogue":
                    result = live.browse(catalogue,settings,source=args.source,term=args.term,after=args.after,limit=args.limit)
                else:
                    selected = live.select_papers(catalogue,settings,paper_ids=args.paper_id,pilot_path=args.include_pilot)
                    result = live.save_selection(selected,args.output,catalogue,settings)
            finally:
                catalogue.close()
        elif args.command.startswith("review-"):
            from . import review
            if args.command == "review-prepare":
                result = review.prepare(args.output, filename=args.review)
            elif args.command == "review-set":
                result = review.set_decision(args.output, args.record_id, args.decision,
                    reviewer=args.reviewer, reason=args.reason, notes=args.notes, filename=args.review)
            else:
                result = review.validate(args.output, filename=args.review, export=args.command == "review-export")
        elif args.command in {"publish-preview", "publish", "publication-verify", "activate", "publication-status"}:
            from .settings import KGSettings
            settings = KGSettings()
            if args.graph_name:
                settings = KGSettings.model_validate(settings.model_dump() | dict(KG_GRAPH_NAME=args.graph_name))
            from .neo4j_store import Neo4jStore
            store = None
            try:
                if args.command != "publish-preview":
                    store = Neo4jStore.connect(settings)
                if args.command == "publication-status":
                    result = store.status(settings.KG_GRAPH_NAME)
                else:
                    from .publication import run
                    from .artifacts import VerifiedReader
                    from src.api.papers.catalogue import Catalogue
                    catalogue = Catalogue(settings.PAPERS_DATABASE_URL)
                    try:
                        catalogue.require_schema()
                        action = {"publish-preview": "preview", "publish": "stage", "publication-verify": "verify", "activate": "activate"}[args.command]
                        result = run(args.output, settings, catalogue, VerifiedReader(settings), action=action,
                                     filename=args.review, store=store,
                                     expect_active=None if getattr(args, "expect_active", "none") == "none" else args.expect_active)
                    finally:
                        catalogue.close()
            finally:
                if store:
                    store.close()
        else:
            from . import jobs
            if args.command == "validate":
                result = jobs.validate(args.output)
            else:
                from .settings import KGSettings
                settings = KGSettings()
                if args.command == "extract":
                    result = jobs.extract(args.output, settings, max_calls=args.max_calls,
                                          retry_failed=args.retry_failed, failed_only=args.failed_only,
                                          chunks_per_paper=args.chunks_per_paper)
                else:
                    from .artifacts import VerifiedReader
                    from src.api.papers.catalogue import Catalogue
                    catalogue = Catalogue(settings.PAPERS_DATABASE_URL)
                    try:
                        catalogue.require_schema()
                        if args.selection_file:
                            from .catalogue import load_selection
                            selected = load_selection(args.selection_file).model_dump(mode="json")
                        else:
                            selected = preview(args.snapshot,selection=args.selection,pilot_path=args.pilot)
                        if args.command == "prepare-preview":
                            result = jobs.prepare_preview(selected,catalogue,VerifiedReader(settings),settings,
                                paper_limit=args.papers,chunks_per_paper=args.chunks_per_paper,max_calls=args.max_calls)
                        else:
                            result = jobs.prepare(args.output,selected,catalogue,VerifiedReader(settings),settings,
                                                  paper_limit=args.papers)
                    finally:
                        catalogue.close()
    except ValidationError:
        parser.exit(1, "KG command failed: invalid typed fields; check configuration and input files.\n")
    except (OSError, ValueError) as exc:
        # Paths/titles are local non-secret inputs; do not print raw JSON payloads.
        message = str(exc) if isinstance(exc, ValueError) else "Input file cannot be read"
        parser.exit(1, f"KG command failed: {message}\n")
    except Exception as exc:
        parser.exit(1, f"KG command failed ({type(exc).__name__}); check services, artifacts and saved checkpoints.\n")
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
