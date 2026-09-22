"""One conservative BCP-47-compatible tag surface (not an ISO registry lookup)."""
import re
from typing import Annotated, Any, Literal, Self
from pydantic import BaseModel, ConfigDict, BeforeValidator, field_validator, model_validator


def language_tag(value: Any) -> str:
    if not isinstance(value,str):raise ValueError('INVALID_LANGUAGE_TAG')
    value=value.strip()
    if not re.fullmatch(r'[A-Za-z]{2,3}(?:-[A-Za-z]{4})?(?:-(?:[A-Za-z]{2}|[0-9]{3}))?(?:-(?:[A-Za-z0-9]{5,8}|[0-9][A-Za-z0-9]{3}))*',value):
        raise ValueError('INVALID_LANGUAGE_TAG')
    parts=value.split('-');result=[parts[0].lower()]
    for part in parts[1:]:
        result.append(part.title() if len(part)==4 and part.isalpha() else part.upper() if len(part)==2 else part.lower())
    return '-'.join(result)

LanguageTag=Annotated[str,BeforeValidator(language_tag)]

class ProductionLanguageSettings(BaseModel):
    model_config=ConfigDict(extra='forbid')
    spoken_language_policy: Literal['source_original','explicit']='source_original'
    spoken_language: LanguageTag | None=None
    creative_review_language: LanguageTag='zh'
    subtitles_enabled: bool=False
    subtitle_languages: tuple[LanguageTag,...]=()

    @field_validator('subtitle_languages',mode='before')
    @classmethod
    def normalize_languages(cls,value: Any) -> tuple[str,...]:
        raw=value.split(',') if isinstance(value,str) else value
        return tuple(dict.fromkeys(language_tag(x) for x in raw if not isinstance(x,str) or x.strip()))

    @model_validator(mode='after')
    def consistency(self) -> Self:
        if self.spoken_language_policy=='explicit' and self.spoken_language is None:
            raise ValueError('EXPLICIT_SPOKEN_LANGUAGE_REQUIRED')
        if self.subtitles_enabled and not self.subtitle_languages:
            raise ValueError('SUBTITLE_LANGUAGES_REQUIRED')
        return self
