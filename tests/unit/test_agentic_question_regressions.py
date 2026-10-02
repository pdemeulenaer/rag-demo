"""Regressions from the q0030/q0054 evaluation failures."""

from unittest.mock import Mock

from evals.run_benchmark import _missing_required_numeric_values, apply_judge_safeguards
from src.api.rag.answer_contracts import RAGGenerationResponse
from src.api.rag.modes.agentic.answering import (
    AnswerReview, ClaimCheck, EvidenceQuote, _assess, _contains_quote,
    _normalize_extracted_numbers, _numeric_evidence_error, _numeric_tokens,
    _rank_requirement_evidence, _screen_claims, _unit_markers, generate_agentic_answer,
)
from src.api.rag.modes.agentic.contracts import AnswerRequirement
from src.api.rag.modes.agentic.policies import scoped_requirement_query
from src.api.rag.question_coverage import (
    has_explicit_comparison, original_question_parts, requests_explicit_comparison,
)


def test_resolved_paper_title_and_build_id_become_filter_not_search_text():
    build_id = "bd741810-69a6-56af-b2dd-4a8f3c409cb4"
    description = (
        'In “A new clump-based star formation model for galaxy simulations: '
        'implications for high-redshift compact star clusters” '
        f'(required_build_id={build_id}), report the global star formation '
        'efficiency at three disc rotations.'
    )
    query, builds = scoped_requirement_query(description, [build_id])
    assert builds == [build_id]
    assert "global star formation efficiency" in query
    assert "clump-based star formation model" not in query
    assert build_id not in query



def test_q0054_compound_paper_hint_becomes_a_scoped_factual_query():
    build_id = "857f03f5-5a9d-5259-9c13-3fb2366b96f1"
    paper_id = "0cfebf74-be71-5769-b950-6ed045b3bdb0"
    title = "SPURS: An Ultra-deep View Inside the Compact, Nitrogen-Enriched Nuclei of Little Red Dots"
    description = (
        "FWHM ranges for broad [O III] components and best-fit broad N IV] FWHM "
        f"as reported in {title} (paper_id={paper_id}; required_build_id={build_id})."
    )
    query, builds = scoped_requirement_query(description, [build_id], {build_id: title})
    assert builds == [build_id]
    assert "FWHM ranges for broad [O III]" in query
    assert "best-fit broad N IV] FWHM" in query
    assert title not in query
    assert paper_id not in query
    assert build_id not in query


def test_compound_hint_cannot_select_an_unapproved_build():
    description = "Report the FWHM (paper_id=paper-1; required_build_id=outside)."
    query, builds = scoped_requirement_query(description, ["approved"])
    assert builds == []
    assert "FWHM" in query
    assert "paper_id" not in query
    assert "outside" not in query


def test_q0030_ocr_fraction_and_units_are_normalized():
    extracted = (
        "The fraction rises from 0 _._ 25 to 0 _._ 34 and 0 _._ 38 above "
        "300 M☉ pc[[−][2]][[2]]. After three disc rotations, "
        "the efficiency is 5 × 10[−][3] to 2 × 10[−][1]."
    )
    numbers = _numeric_tokens(extracted)
    assert {"0.25", "0.34", "0.38", "300", "0.005", "0.2", "3"} <= numbers
    assert "pc^-2" in _unit_markers(extracted)


def test_q0030_direct_conclusion_outranks_abstract_and_picture_ocr():
    requirement = AnswerRequirement(
        id="r1", description="Report exact maximum clump mass and surface density.",
    )
    contexts = {
        "abstract": {"text": "Maximum mass rises from about 10^5 to 10^7."},
        "picture": {"text": "Start of picture text. Maximum mass 10^5.1, density 10^2.9. End of picture text."},
        "conclusion": {"text": "The maximum clump mass rises from 10^5.1 to 10^7.4, "
                               "and surface density from 10^2.9 to >10^4.0."},
    }
    assert _rank_requirement_evidence(requirement, tuple(contexts), contexts)[0] == "conclusion"


def test_q0030_benchmark_requires_precise_values_not_rounded_exponents():
    question = {"id": "q0030", "required_numeric_values": ["5.1", "7.4", "0.005", "0.2"]}
    precise = "10^5.1 to 10^7.4; 5 × 10^-3 to 2 × 10^-1"
    rounded = "10^5 to 10^7; 0.005 to 0.2"
    assert _missing_required_numeric_values(question, precise) == []
    assert _missing_required_numeric_values(question, rounded) == ["5.1", "7.4"]


def test_q0054_question_parts_and_missing_comparison_safeguard():
    question = {
        "kind": "cross_paper", "question": "Compare (a) line widths; (b) bar speed; "
        "(c) is the minimum bar speed within, below, or above typical estimates?",
    }
    assert [item[0] for item in original_question_parts(question["question"])] == [
        "q_a", "q_b", "q_c",
    ]
    assert requests_explicit_comparison(original_question_parts(question["question"])[2][1])
    assert not has_explicit_comparison("The minimum is 26 and typical estimates are 30–45.")
    assert has_explicit_comparison("The minimum 26 is below typical estimates of 30–45.")
    metrics = {"all_required_papers_retrieved": 1.0}
    scores, safeguards = apply_judge_safeguards(
        question, metrics, ["a", "b"], {"correctness": 1.0},
        answer="The minimum is 26; typical estimates are 30–45.",
    )
    assert scores["correctness"] == 0.5
    assert any(item["reason"] == "missing_explicit_comparison" for item in safeguards)


def test_agentic_verifier_rejects_a_missing_comparison_despite_model_approval():
    claims = RAGGenerationResponse(claims=[{
        "text": "The required minimum is 26; typical estimates are 30–45.",
        "cited_context_ids": ["a"], "need_ids": ["r1"],
    }]).claims
    requirement = AnswerRequirement(
        id="q_c", description="Is the minimum below, within, or above typical estimates?",
    )
    review = AnswerReview.model_validate({
        "claims": [{"claim_index": 0, "supported": True, "feedback": ""}],
        "requirements": [{"requirement_id": "q_c", "status": "satisfied",
                          "claim_indices": [0], "feedback": ""}],
        "unplanned_requests": [],
    })
    _, coverage, _ = _assess(review, claims, [requirement], 0)
    assert coverage[0]["status"] == "partial"
    assert "does not state their comparison" in coverage[0]["feedback"]


def test_q0030_ocr_equivalent_quote_keeps_a_real_numeric_claim():
    source = (
        "The fraction of clumps exceeding Σc _,_ th = 300 M⊙ pc[−][2] rises "
        "from 0 _._ 25 at _𝑧_ = 0 to 0 _._ 34 at _𝑧_ = 6 and 0 _._ 38 "
        "at _𝑧_ = 10 in 10[10] M⊙ haloes."
    )
    quote = (
        "The fraction of clumps exceeding Σc, th = 300 M⊙ pc^-2 rises "
        "from 0.25 at z = 0 to 0.34 at z = 6 and 0.38 "
        "at z = 10 in 10^10 M⊙ haloes."
    )
    assert _contains_quote(source, quote)
    claim = RAGGenerationResponse(claims=[{
        "text": "The fraction above 300 M⊙ pc^-2 rises from 0.25 at z=0 "
                "to 0.34 at z=6 and 0.38 at z=10 in 10^10 M⊙ haloes.",
        "cited_context_ids": ["paper-chunk"], "need_ids": ["r1"],
    }]).claims[0]
    check = ClaimCheck(
        claim_index=0, supported=True, feedback="",
        evidence_quotes=[EvidenceQuote(context_id="paper-chunk", quote=quote)],
    )
    assert _numeric_evidence_error(claim, check, {"paper-chunk": {"text": source}}) is None


def test_q0030_exact_percentage_conversions_need_the_cited_fractions():
    source = (
        "In 10[10] M⊙ haloes after three disc rotations, the global SFE "
        "increases from 5 × 10[−][3] at z = 0 to 2 × 10[−][1] at z = 10."
    )
    claim = RAGGenerationResponse(claims=[{
        "text": "In 10^10 M⊙ haloes after 3 disc rotations, SFE grows "
                "from 5 × 10^-3 (0.5%) at z=0 to 2 × 10^-1 (20%) at z=10.",
        "cited_context_ids": ["paper-chunk"], "need_ids": ["r1"],
    }]).claims[0]
    check = ClaimCheck(
        claim_index=0, supported=True, feedback="",
        evidence_quotes=[EvidenceQuote(
            context_id="paper-chunk", quote=_normalize_extracted_numbers(source),
        )],
    )
    assert _numeric_evidence_error(claim, check, {"paper-chunk": {"text": source}}) is None


def test_internal_chunk_id_is_removed_from_claim_prose_before_number_check():
    chunk_id = "e557fa8e-c92a-54a4-a25e-4cf277df7a40"
    claim = RAGGenerationResponse(claims=[{
        "text": "The fraction is 0.38, as supported by the excerpt from context ID "
                f"{chunk_id}.",
        "cited_context_ids": [chunk_id], "need_ids": ["r1"],
    }]).claims[0]
    cleaned, rejected = _screen_claims([claim], {chunk_id: {"text": "fraction 0.38"}})
    assert rejected == []
    assert cleaned[0].text == "The fraction is 0.38."
    assert _numeric_tokens(claim.text) == {"0.38"}


def test_quote_match_never_accepts_a_number_from_the_wrong_passage():
    correct = ("Most recent bar-speed estimates are 30 − 45 km s[−][1] kpc[−][1]; "
               "our upper bound is 26 km s[−][1] kpc[−][1], much slower.")
    wrong = "The broad [O III] line has FWHM 1627 km s[−][1]."
    quote = "Most recent bar-speed estimates are 30 - 45 km s^-1 kpc^-1"
    assert _contains_quote(correct, quote)
    assert not _contains_quote(wrong, quote)


def test_agentic_synthesis_sees_later_direct_passages_and_citation_guidance():
    contexts = [{"id": f"c{index}", "text": f"Measurement {index}.",
                 "paper_id": "paper", "title": "A paper", "page": index}
                for index in range(8)]
    request = Mock(side_effect=[
        RAGGenerationResponse(claims=[{
            "text": "Measurement 7.", "cited_context_ids": ["c7"], "need_ids": ["r1"],
        }]),
        AnswerReview.model_validate({
            "claims": [{"claim_index": 0, "supported": True, "feedback": ""}],
            "requirements": [{"requirement_id": need_id, "status": "satisfied",
                              "claim_indices": [0], "feedback": ""}
                             for need_id in ("r1", "q_original")],
            "unplanned_requests": [],
        }),
    ])
    result = generate_agentic_answer(
        question="Report measurement.",
        requirements=[AnswerRequirement(id="r1", description="Report measurement.")],
        contexts=contexts, prompt=[], request=request,
        evidence_by_requirement={"r1": tuple(row["id"] for row in contexts)},
    )
    instruction = request.call_args_list[0].args[0][-1]["content"]
    assert '"context_id": "c7"' in instruction
    assert "broad versus narrow" in instruction
    assert result.diagnostics["status"] == "complete"

def test_q0030_ignores_question_context_but_requires_reported_values():
    question = 'For 10^10 M☉ haloes, compare z=0 and z=10 surface densities.'
    source = ('Maximum surface densities reach 10[2] _[.]_[9] and '
              '> 10[4] _[.]_[0] M⊙ pc[−][2] for z=0 and z=10.')
    claim = RAGGenerationResponse(claims=[{
        'text': 'For 10^10 M☉ haloes, the maximum surface density rises '
                'from 10^2.9 to >10^4.0 M☉ pc^-2 at z=0 and z=10.',
        'cited_context_ids': ['paper-chunk'], 'need_ids': [],
    }]).claims[0]
    check = ClaimCheck(claim_index=0, supported=True, feedback='', evidence_quotes=[])
    assert _numeric_evidence_error(
        claim, check, {'paper-chunk': {'text': source}}, question=question,
    ) is None
    unsupported = source.replace('10[4] _[.]_[0]', '10[3] _[.]_[0]')
    error = _numeric_evidence_error(
        claim, check, {'paper-chunk': {'text': unsupported}}, question=question,
    )
    assert error['missing_values'] == ['10000']


def test_q0054_ocr_figure_can_verify_range_without_verbatim_quote():
    source = ('Data FWHMbroad = 1627 km s [−] [1]; '
              'Data FWHMbroad = 1130 km s [−] [1].')
    claim = RAGGenerationResponse(claims=[{
        'text': 'The broad [O III] FWHM spans 1130–1627 km s^-1.',
        'cited_context_ids': ['figure'], 'need_ids': [],
    }]).claims[0]
    check = ClaimCheck(claim_index=0, supported=True, feedback='', evidence_quotes=[])
    assert _numeric_evidence_error(claim, check, {'figure': {'text': source}}) is None


def test_q0030_snapshot_only_requires_requested_redshift_endpoints():
    import json
    from pathlib import Path

    root = Path(__file__).resolve().parents[2] / 'data/evaluation/markdown-mini-v4'
    for name in ('questions.reviewed.json', 'questions.split.json'):
        dataset = json.loads((root / name).read_text())
        question = next(row for row in dataset['questions'] if row['id'] == 'q0030')
        assert '0.34' not in question['required_numeric_values']
        assert 'z = 6' not in question['reference_answer']

def test_q0030_plural_fraction_in_cited_ocr_chunk_is_accepted():
    question = 'For 10^10 M☉ haloes, compare the z=0 and z=10 clump fractions.'
    source = ('The fractions of gas clumps above Σc,th = 300 M⊙ pc[−][2] '
              'are 0 _._ 25, 0 _._ 34, and 0 _._ 38 for z=0, 6, and 10.')
    claim = RAGGenerationResponse(claims=[{
        'text': 'For 10^10 M☉ haloes, the fraction of clumps above '
                '300 M⊙ pc^-2 rises from 0.25 at z=0 to 0.38 at z=10.',
        'cited_context_ids': ['paper-chunk'], 'need_ids': [],
    }]).claims[0]
    check = ClaimCheck(claim_index=0, supported=True, feedback='', evidence_quotes=[])
    assert _numeric_evidence_error(
        claim, check, {'paper-chunk': {'text': source}}, question=question,
    ) is None
