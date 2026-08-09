from __future__ import annotations

from dataclasses import dataclass, field

from drama_plugin.contracts.asset import Asset, AssetLevel, AssetType
from drama_plugin.contracts.generation import GenerationPlan, GenerationState, GenerationStatus, GenerationTarget
from drama_plugin.contracts.history import HistoricalEvidence, HistoricalSource
from drama_plugin.contracts.media import Media, MediaSemanticMetadata, MediaType
from drama_plugin.contracts.project import Character, Episode, Location, Project, Prop, Scene, Shot, Story


@dataclass
class MockDramaData:
    project: Project = field(default_factory=lambda: Project(id="project-1", name="洛阳风云", description="武周时期历史短剧"))
    story: Story = field(default_factory=lambda: Story(id="story-1", project_id="project-1", title="神都密诏", premise="狄仁杰追查一封改变朝局的密诏。"))
    episode: Episode = field(default_factory=lambda: Episode(id="episode-1", story_id="story-1", number=1, title="夜访书房", summary="密诏线索在雨夜浮现。"))
    scene: Scene = field(default_factory=lambda: Scene(id="scene-1", episode_id="episode-1", number=3, heading="内景·狄府书房·夜", location_id="location-study", character_ids=["character-di"], summary="狄仁杰在烛火下审视残缺密诏。"))
    shot: Shot = field(default_factory=lambda: Shot(id="shot-1", scene_id="scene-1", number=2, description="中近景，狄仁杰抬眼看向窗外闪电，手中密诏微颤。", character_ids=["character-di"], duration_seconds=4.0))
    character: Character = field(default_factory=lambda: Character(id="character-di", name="狄仁杰", role="主角", description="沉静、敏锐的唐代重臣"))
    location: Location = field(default_factory=lambda: Location(id="location-study", name="狄府书房", period="武周", description="木构书房，烛火与雨夜冷光交叠"))
    prop: Prop = field(default_factory=lambda: Prop(id="prop-edict", name="残缺密诏", description="边缘焦黑的绢帛诏书"))
    assets: list[Asset] = field(default_factory=lambda: [
        Asset(id="asset-di-base", name="狄仁杰标准造型", asset_type=AssetType.CHARACTER, level=AssetLevel.BASE, entity_type="CHARACTER", entity_id="character-di", semantic_labels=["唐代官服", "狄仁杰"]),
        Asset(id="asset-di-scene", name="狄仁杰雨夜书房造型", asset_type=AssetType.CHARACTER, level=AssetLevel.SCENE, entity_type="CHARACTER", entity_id="character-di", parent_asset_id="asset-di-base", semantic_labels=["湿润外袍", "烛光"]),
        Asset(id="asset-di-shot", name="狄仁杰密诏特写造型", asset_type=AssetType.CHARACTER, level=AssetLevel.SHOT, entity_type="CHARACTER", entity_id="character-di", parent_asset_id="asset-di-scene", semantic_labels=["紧张神情", "手持密诏"]),
        Asset(id="asset-study-base", name="唐代书房基准", asset_type=AssetType.LOCATION, level=AssetLevel.BASE, entity_type="LOCATION", entity_id="location-study", semantic_labels=["唐代", "木构"]),
        Asset(id="asset-study-scene", name="雨夜书房", asset_type=AssetType.LOCATION, level=AssetLevel.SCENE, entity_type="LOCATION", entity_id="location-study", parent_asset_id="asset-study-base", semantic_labels=["雨夜", "烛火"]),
    ])
    source: HistoricalSource = field(default_factory=lambda: HistoricalSource(id="source-1", title="旧唐书·狄仁杰传", citation="《旧唐书》卷八十九", source_type="PRIMARY_TEXT"))
    evidence: HistoricalEvidence = field(default_factory=lambda: HistoricalEvidence(id="evidence-1", source_id="source-1", claim="狄仁杰曾任宰相并以直谏著称", excerpt="契丹扰冀州时，狄仁杰被起用处理军政。", confidence=0.88, tags=["狄仁杰", "武周"] ))
    plan: GenerationPlan = field(default_factory=lambda: GenerationPlan(id="plan-shot-1", generation_target=GenerationTarget.SHOT_VIDEO, resource_id="shot-1", workflow_code="historical-shot-video-v1", parameters={"durationSeconds": 4}))
    generation_state: GenerationState = field(default_factory=lambda: GenerationState(plan_id="plan-shot-1", status=GenerationStatus.DRAFT, progress=0.0, message="Ready to compile"))
    media: Media = field(default_factory=lambda: Media(id="media-di-base", media_type=MediaType.IMAGE, url="mock://media/di-renjie.png", mime_type="image/png", semantic=MediaSemanticMetadata(entity_type="CHARACTER", entity_id="character-di", entity_name="狄仁杰", asset_id="asset-di-base", generation_target=GenerationTarget.ASSET_IMAGE, semantic_labels=["reference", "唐代官服"]), technical_metadata={"width": 1024, "height": 1024}))
