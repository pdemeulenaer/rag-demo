"""Generic assertion targeting with synthetic records, never benchmark gold values."""
from types import SimpleNamespace
from uuid import uuid4
import subprocess
import sys

import pytest

from src.api.kg.fact_matching import requested_fact_matches
from src.api.kg.scientific_schema import Entity, Observation


def test_fact_matcher_import_is_configuration_free_in_a_fresh_process():
    script = """
import sys
from pydantic_settings import DotEnvSettingsSource
def forbidden(*args, **kwargs):
    raise AssertionError('Fact matching must not read environment files')
DotEnvSettingsSource._read_env_file = forbidden
from src.api.kg.fact_matching import requested_fact_matches
assert requested_fact_matches({}, 'What is the tracer flux?', []) == {}
assert 'src.api.core.config' not in sys.modules
"""
    result = subprocess.run([sys.executable,"-c",script],capture_output=True,text=True)
    assert result.returncode == 0, result.stderr


@pytest.fixture
def facts():
    source = dict(collection="papers",build_id=str(uuid4()),paper_id=str(uuid4()),
                  point_id=str(uuid4()),source="arxiv",page_number=1)
    props = dict(collection="papers",build_id=source["build_id"])
    paper = SimpleNamespace(**props,title="Synthetic Flux Survey in Region Delta")

    def assertion(statement="The tracer flux increases with pressure.",quantity="tracer flux",
                  quotes=None,**kwargs):
        return Observation(id="assertion",subject_id="subject",kind="qualitative_finding",
            statement=statement,quantity=quantity,
            evidence=[dict(**source,quote=q) for q in (quotes or [statement])],**kwargs)

    return SimpleNamespace(source=source,props=props,paper=paper,assertion=assertion)


def test_requested_measurement_in_named_paper_does_not_need_an_object_path(facts):
    record = facts.assertion()
    parsed = {"record":(facts.props,record)}
    result = requested_fact_matches(parsed,'In "Synthetic Flux Survey in Region Delta", how does tracer flux vary with pressure?',
                                    [facts.paper])
    assert result["record"]["source_matches"][0]["matched_terms"] == ["flux","pressure","tracer"]
    assert record.statement == "The tracer flux increases with pressure."
    assert record.evidence[0].quote == record.statement


@pytest.mark.parametrize("papers",[(),("wrong-build",),("wrong-collection",)])
def test_fact_path_requires_the_exact_named_collection_build(facts,papers):
    requested = [SimpleNamespace(collection="other" if v=="wrong-collection" else "papers",
        build_id=v if v=="wrong-build" else facts.source["build_id"]) for v in papers]
    assert not requested_fact_matches({"r":(facts.props,facts.assertion())},"Report tracer flux pressure",requested)


@pytest.mark.parametrize("query",[
    'What does "Synthetic Flux Survey in Region Delta" report?',
    'What does "Synthetic Flux Survey in Region Delta" report about stars and populations?',
    'What does "Synthetic Flux Survey in Region Delta" report about tracer?',
])
def test_titles_boilerplate_and_one_topic_word_cannot_license_promotion(facts,query):
    assert not requested_fact_matches({"r":(facts.props,facts.assertion())},query,[facts.paper])


def test_entity_names_alone_cannot_license_population_promotion(facts):
    record = facts.assertion(statement="The Copper Silver population is present.",quantity=None)
    entity = Entity(id="subject",kind="stellar_population",name="Copper Silver population",
                    evidence=[dict(**facts.source,quote=record.statement)])
    parsed = {"e":(facts.props,entity),"r":(facts.props,record)}
    assert not requested_fact_matches(parsed,"What is reported about the Copper Silver population?",[facts.paper])


def test_assertion_quantity_cannot_borrow_terms_missing_from_its_own_quote(facts):
    record = facts.assertion(quotes=["The population is present."])
    assert not requested_fact_matches({"r":(facts.props,record)},"Report tracer flux pressure",[facts.paper])


def test_fact_terms_cannot_be_stitched_across_separate_quotes(facts):
    record = facts.assertion(statement="The flux depends on pressure.",quantity=None,
                             quotes=["The flux is measured.","The pressure is measured."])
    assert not requested_fact_matches({"r":(facts.props,record)},"Report flux pressure",[facts.paper])


def test_qualifying_quote_does_not_license_another_evidence_point(facts):
    record = facts.assertion(quotes=["The tracer flux increases with pressure.","The population is present."])
    second_point = uuid4()
    record.evidence[1].point_id = second_point
    matches = requested_fact_matches({"r":(facts.props,record)},"Report tracer flux pressure",[facts.paper])
    assert [r["id"] for r in matches["r"]["source_matches"]] == [facts.source["point_id"]]


@pytest.mark.parametrize("query",["Report binary precision and completeness",
                                  "Report binary precision and completeness in the test set"])
def test_metric_matching_does_not_treat_accuracy_as_precision(facts,query):
    record = facts.assertion(statement="The binary classifier accuracy is measured in the test set.",quantity="accuracy")
    assert not requested_fact_matches({"r":(facts.props,record)},query,[facts.paper])


def test_quarantined_observation_cannot_qualify(facts):
    record = facts.assertion(quality_flags=["incomplete_evidence"])
    assert not requested_fact_matches({"r":(facts.props,record)},"Report tracer flux pressure",[facts.paper])


def test_numbers_and_identifiers_are_not_fact_overlap(facts):
    record = facts.assertion(statement="The pressure is 37 in 2042.",quantity=None)
    assert not requested_fact_matches({"r":(facts.props,record)},"Report pressure at 37 in 2042",[facts.paper])
