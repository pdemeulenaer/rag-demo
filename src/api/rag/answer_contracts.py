"""Shared structured answer schema; baseline provider format is unchanged."""
from pydantic import BaseModel, ConfigDict, Field


class RAGClaim(BaseModel):
    """One atomic answer statement and the retrieved chunks that support it."""

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    text: str = Field(min_length=1, max_length=4000)
    cited_context_ids: list[str] = Field(min_length=1, max_length=20)
    need_ids: list[str] = Field(max_length=20)


class RAGGenerationResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    claims: list[RAGClaim] = Field(max_length=30)

    @property
    def answer(self) -> str:
        """Flatten atomic claims while preserving readable paragraph boundaries."""
        return "\n\n".join(claim.text for claim in self.claims)

    @property
    def retrieved_context_ids(self) -> list[str]:
        """Return unique supporting point IDs in first-use order."""
        return list(dict.fromkeys(
            context_id for claim in self.claims
            for context_id in claim.cited_context_ids
        ))
