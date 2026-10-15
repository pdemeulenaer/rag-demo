"""Citation-window fidelity without configuration, providers or graph services."""
import pytest

from src.api.kg.spans import source_spans


@pytest.mark.parametrize("text", ["", "  \n\t  ", "M22 at 3.27 ± 0.14 kpc.",
    "## **Results**\n\n[Fe∕H] = −1.73 ± 0.17 dex.\n\n𝑓0.61∕𝑓1O = 0.6152",
    "α\u0301−𝑑=3.27\\pm0.14 " * 80, "formula" * 100, "x\n\nx\n\nx",
    "leading " + "word " * 200 + " trailing", "word\n" * 100,
    "  Results\r\n\r\nEquation: [Fe/H] = −1.73 ± 0.17 dex.  "])
def test_source_spans_preserve_exact_substrings_and_all_non_whitespace(text):
    spans = source_spans(text)
    assert [span.id for span in spans] == [f"s{i + 1:03d}" for i in range(len(spans))]
    assert all(span.text == text[span.start:span.end] for span in spans)
    assert all(span.text and span.text == span.text.strip() for span in spans)
    assert all(a.end <= b.start for a, b in zip(spans, spans[1:]))
    assert "".join(c for s in spans for c in s.text if not c.isspace()) == "".join(
        c for c in text if not c.isspace())
    assert spans == source_spans(text)


def test_long_formula_is_not_split_inside_its_token():
    formula = "\\frac{alpha}{beta}" * 40
    text = "Result " + formula + " remains uncertain."
    assert any(formula in span.text for span in source_spans(text))
