# Java ToolApi 映射

本文件只冻结接口映射，不提供 Java 源码。一个 Tool 对应一个 Java 接口方法；同一 Domain 的方法聚合在一个 ToolApi 接口中，而不是为每个 Tool 创建 Service/Class。

| Tool | Java interface method |
| --- | --- |
| `work.create_work` | `WorkToolApi.createWork()` |
| `work.get_work` | `WorkToolApi.getWork()` |
| `work.save_work` | `WorkToolApi.saveWork()` |
| `work.list_works` | `WorkToolApi.listWorks()` |
| `work.search_works` | `WorkToolApi.searchWorks()` |
| `script.create_script` | `ScriptToolApi.createScript()` |
| `script.get_script` | `ScriptToolApi.getScript()` |
| `script.save_script` | `ScriptToolApi.saveScript()` |
| `script.list_scripts` | `ScriptToolApi.listScripts()` |
| `episode.create_episode` | `EpisodeToolApi.createEpisode()` |
| `episode.get_episode` | `EpisodeToolApi.getEpisode()` |
| `episode.save_episode` | `EpisodeToolApi.saveEpisode()` |
| `episode.list_episodes` | `EpisodeToolApi.listEpisodes()` |
| `scene.create_scene` | `SceneToolApi.createScene()` |
| `scene.get_scene` | `SceneToolApi.getScene()` |
| `scene.save_scene` | `SceneToolApi.saveScene()` |
| `scene.list_scenes` | `SceneToolApi.listScenes()` |
| `scene.search_scenes` | `SceneToolApi.searchScenes()` |
| `shot.create_shot` | `ShotToolApi.createShot()` |
| `shot.get_shot` | `ShotToolApi.getShot()` |
| `shot.save_shot` | `ShotToolApi.saveShot()` |
| `shot.list_shots` | `ShotToolApi.listShots()` |
| `shot.search_shots` | `ShotToolApi.searchShots()` |
| `asset.create_asset` | `AssetToolApi.createAsset()` |
| `asset.get_asset` | `AssetToolApi.getAsset()` |
| `asset.save_asset` | `AssetToolApi.saveAsset()` |
| `asset.list_assets` | `AssetToolApi.listAssets()` |
| `asset.search_assets` | `AssetToolApi.searchAssets()` |
| `media.create_media` | `MediaToolApi.createMedia()` |
| `media.get_media` | `MediaToolApi.getMedia()` |
| `media.save_media` | `MediaToolApi.saveMedia()` |
| `media.list_media` | `MediaToolApi.listMedia()` |

Java Request DTO 直接以 Tool catalog 的 snake_case 输入 Schema 为依据。Repository 将 Stable Envelope 映射为普通列，将 `content` 映射为 JSON；数据库 Entity、MyBatis/JPA Model 或物理列名不得反向决定 Skill Schema。生产、研究和 Context Tool 不属于本轮七类长期记忆表映射。
