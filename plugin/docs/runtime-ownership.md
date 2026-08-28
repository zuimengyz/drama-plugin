# Runtime Configuration Ownership

Runtime files are deployment state and stay outside Git:

| Component owner | External file | Loaded by |
| --- | --- | --- |
| `MCP_HOST` | `~/.config/historical-plugin/mcp-host.env` | `drama-mcp-service` launcher |
| `PLUGIN` | `~/.config/historical-plugin/drama-plugin.env` | same MCP process, for the embedded Plugin |
| `DRAMA_SERVICE` | `~/.config/historical-plugin/drama-service.env` | Java service launcher only |

`mcp-host.env` and `drama-plugin.env` share one OS process because the Plugin is
embedded. That physical fact does not merge their configuration ownership.
`drama-service.env` must never enter that process.

## MCP Host

| Variable | Secret | Purpose |
| --- | ---: | --- |
| `DRAMA_MCP_HOST` | no | MCP bind host |
| `DRAMA_MCP_PORT` | no | MCP listen port |
| `DRAMA_MCP_URL` | no | integration-client MCP endpoint |
| `DRAMA_PLUGIN_ROOT` | no | hosted Plugin root override |
| `DRAMA_PLUGIN_CONFIG` | no | hosted Plugin YAML path |

## Drama Plugin

| Variable | Secret | Purpose |
| --- | ---: | --- |
| `DRAMA_PLUGIN_PROVIDER_MEMORY_MODE` | no | Memory provider selection |
| `DRAMA_PLUGIN_PROVIDER_ASSET_MODE` | no | Asset provider selection |
| `DRAMA_PLUGIN_PROVIDER_RESEARCH_MODE` | no | Research provider selection |
| `DRAMA_PLUGIN_PROVIDER_PRODUCTION_MODE` | no | Production provider selection |
| `DRAMA_PLUGIN_PROVIDER_MEDIA_MODE` | no | Media provider selection |
| `DRAMA_PLUGIN_PROVIDER_CONTEXT_MODE` | no | Context provider selection |
| `DRAMA_PLUGIN_PROVIDER_VOICE_MODE` | no | Voice provider selection |
| `DRAMA_PLUGIN_SERVICE_MEMORY_BASE_URL` | no | Drama Service HTTP origin for Memory |
| `DRAMA_PLUGIN_SERVICE_MEMORY_API_TOKEN` | yes | Memory HTTP provider credential |
| `DRAMA_PLUGIN_SERVICE_MEMORY_TIMEOUT_SECONDS` | no | Memory HTTP timeout |
| `DRAMA_PLUGIN_SERVICE_ASSET_BASE_URL` | no | Drama Service HTTP origin for Asset |
| `DRAMA_PLUGIN_SERVICE_ASSET_API_TOKEN` | yes | Asset HTTP provider credential |
| `DRAMA_PLUGIN_SERVICE_ASSET_TIMEOUT_SECONDS` | no | Asset HTTP timeout |
| `DRAMA_PLUGIN_SERVICE_RESEARCH_BASE_URL` | no | Research service HTTP origin |
| `DRAMA_PLUGIN_SERVICE_RESEARCH_API_TOKEN` | yes | Research HTTP provider credential |
| `DRAMA_PLUGIN_SERVICE_RESEARCH_TIMEOUT_SECONDS` | no | Research HTTP timeout |
| `DRAMA_PLUGIN_SERVICE_PRODUCTION_BASE_URL` | no | Production service HTTP origin |
| `DRAMA_PLUGIN_SERVICE_PRODUCTION_API_TOKEN` | yes | Production HTTP provider credential |
| `DRAMA_PLUGIN_SERVICE_PRODUCTION_TIMEOUT_SECONDS` | no | Production HTTP timeout |
| `DRAMA_PLUGIN_SERVICE_MEDIA_BASE_URL` | no | Drama Service HTTP origin for Media |
| `DRAMA_PLUGIN_SERVICE_MEDIA_API_TOKEN` | yes | Media HTTP provider credential |
| `DRAMA_PLUGIN_SERVICE_MEDIA_TIMEOUT_SECONDS` | no | Media HTTP timeout |
| `DRAMA_PLUGIN_SERVICE_CONTEXT_BASE_URL` | no | Context service HTTP origin |
| `DRAMA_PLUGIN_SERVICE_CONTEXT_API_TOKEN` | yes | Context HTTP provider credential |
| `DRAMA_PLUGIN_SERVICE_CONTEXT_TIMEOUT_SECONDS` | no | Context HTTP timeout |
| `DRAMA_PLUGIN_SERVICE_VOICE_BASE_URL` | no | Drama Service HTTP origin for Voice |
| `DRAMA_PLUGIN_SERVICE_VOICE_API_TOKEN` | yes | Voice HTTP provider credential |
| `DRAMA_PLUGIN_SERVICE_VOICE_TIMEOUT_SECONDS` | no | Voice HTTP timeout |
| `DRAMA_PLUGIN_MEDIA_IMPORT_ALLOWED_ROOTS` | no | Host-local import allowlist |
| `DRAMA_PLUGIN_ROLE_DUBBING_OUTPUT_DIRECTORY` | no | Host-local Role Dubbing work/output root |
| `DRAMA_PLUGIN_ROLE_DUBBING_TIMEOUT_SECONDS` | no | Fish Role Dubbing request timeout |
| `FISH_AUDIO_API_KEY` | yes | Fish Audio credential |
| `FISH_AUDIO_BASE_URL` | no | Fish Audio HTTPS origin |
| `FISH_TTS_MODEL` | no | Fish TTS model selection |

The Plugin does not consume `DB_*`, `MYSQL_*`, `MINIO_*`, `S3_*`, or
`DRAMA_MEDIA_STORAGE_*`. Voice and Media bytes are downloaded only from a URL
owned by the configured Drama Service HTTP origin.

## Drama Service

| Variable | Secret | Purpose |
| --- | ---: | --- |
| `DB_HOST` | no | MySQL host |
| `DB_PORT` | no | MySQL port |
| `DB_NAME` | no | MySQL database |
| `DB_USERNAME` | yes | MySQL user identity |
| `DB_PASSWORD` | yes | MySQL password |
| `DRAMA_TOOL_SECRET` | yes | `/api/tool/**` service authentication and content-token signing |
| `SERVER_PORT` | no | Java HTTP port |
| `CORS_ALLOWED_ORIGINS` | no | trusted browser origins |
| `DRAMA_MEDIA_STORAGE_ENDPOINT` | no | S3-compatible endpoint, Java-only |
| `DRAMA_MEDIA_STORAGE_BUCKET` | no | object bucket, Java-only |
| `DRAMA_MEDIA_STORAGE_ACCESS_KEY` | yes | object-storage access key |
| `DRAMA_MEDIA_STORAGE_SECRET_KEY` | yes | object-storage secret |
| `DRAMA_MEDIA_STORAGE_REGION` | no | S3-compatible region |
| `DRAMA_MEDIA_RESOLVE_TTL_SECONDS` | no | service-owned content token TTL |
| `DRAMA_MEDIA_MAX_FILE_SIZE` | no | multipart file limit |
| `DRAMA_MEDIA_MAX_REQUEST_SIZE` | no | multipart request limit |

The service does not consume `FISH_*`, `DRAMA_MCP_*`, `DRAMA_PLUGIN_*`,
`OPENAI_API_KEY`, or `DASHSCOPE_API_KEY`.

## Launch discipline

```bash
scripts/start-drama-service.sh
scripts/start-drama-mcp.sh
```

Both launchers validate ownership before loading. `load-env.sh` remains generic,
requires an explicit file, and rejects executable shell syntax. No `.env`,
`.env.example`, or combined runtime file is an active source.

The retired aggregate also contained `OPENAI_API_KEY`, `DASHSCOPE_API_KEY`,
`VITE_API_BASE_URL`, `HARNESS_MODEL`, and `DRAMA_E2E_PREFIX_FAMILY`; current
runtime code has no owner/consumer for them in this three-process topology, so
they were removed from active runtime. Frontend-specific deployment, if used,
must own its configuration separately rather than re-enter this runtime set.
