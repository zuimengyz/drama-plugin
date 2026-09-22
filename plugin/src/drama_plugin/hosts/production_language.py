"""Write-once Work language pins in the existing artifact store; no domain writes."""
from pathlib import Path
from typing import Sequence
from drama_plugin.config.models import DramaPluginConfig
from drama_plugin.contracts.base import dump_contract
from drama_plugin.contracts.creative_source import SourceArtifact
from drama_plugin.contracts.production_language import ProductionLanguageProfile,SourceLanguageMetadata
from drama_plugin.hosts.director_artifacts import DirectorArtifactStore
from drama_plugin.production_language import resolve_profile,validate_profile,resolve_source_language

class ProductionLanguageHost:
    def __init__(self,root: str | Path):
        self.store=DirectorArtifactStore(root)

    def bind_work(self,work_id: str,config: DramaPluginConfig,artifacts: Sequence[SourceArtifact],metadata: Sequence[SourceLanguageMetadata],designated: str) -> ProductionLanguageProfile:
        path=self.store._path('work-language',work_id)
        with self.store._writer():
            if path.exists():
                profile=ProductionLanguageProfile.model_validate(self.store._read(path))
                if profile.work_id!=work_id:raise ValueError('WORK_LANGUAGE_BINDING_MISMATCH')
                validate_profile(profile)
                _,current_metadata=resolve_source_language(artifacts,metadata,designated)
                if current_metadata!=profile.source_language_metadata:raise ValueError("WORK_SOURCE_LANGUAGE_BINDING_STALE")
            else:
                profile=resolve_profile(work_id,config,artifacts,metadata,designated)
                self.store._write(path,dump_contract(profile))
        self.store.put('production-language:'+work_id,dump_contract(profile))
        return profile
