"""Query model for searching and filtering stored activity objects."""

from typing import Optional, Union

from pydantic import BaseModel, Field, field_validator


class Query(BaseModel):
    """Pydantic model representing a query against the activity store."""

    text: Optional[str] = None
    keywords: Optional[str] = Field(
        None,
        description=(
            "Backend-interpreted filter field. Each backend may read this differently — "
            "for example, as keyword search terms, key:value filter pairs, or tag matches."
        ),
    )
    sort: Optional[str] = None
    size: int = 10
    after: Optional[str] = None
    collection: Optional[str] = None
    type: Optional[Union[str, list[str]]] = None

    @field_validator("size")
    @classmethod
    def size_must_be_positive(cls, v: int) -> int:
        if v < 1:
            raise ValueError("size must be a positive integer")
        return v

    def to_dict(self) -> dict:
        """Return a dict excluding fields with None values."""
        return {k: v for k, v in self.model_dump().items() if v is not None}
