# RISK_MATRIX.md — ERoom Backend

## Severity: 🔴 Critical (P0) · 🟠 High (P1) · 🟡 Medium (P2) · 🟢 Low (P3)
## Likelihood: 5 (almost certain) → 1 (rare)

---

### 1. Authentication & Authorization
| Risk | Sev | Like | Score | Scenario | Test Coverage |
|------|-----|------|-------|----------|---------------|
| Token forgery / JWT tampering | 🔴 | 2 | 8 | Attacker crafts modified JWT; `decode_token` catches PyJWTError but edge cases exist | test_security.py: test_decode_tampered |
| Token expiry not enforced | 🔴 | 3 | 12 | Clock skew or missing exp check allows expired token use | test_security.py: test_expired_token |
| Refresh token reuse attack | 🔴 | 2 | 8 | Same refresh token used twice; first succeeds, second must fail (revoked) | test_auth_api.py: test_refresh_reuse |
| Brute-force login | 🟠 | 4 | 16 | No rate limiting on /login; attacker can guess passwords | test_error_handling.py: test_login_brute_force |
| Cookie injection via header | 🟠 | 2 | 8 | Attacker sends both Cookie + Authorization header; precedence matters | test_security.py: test_dual_auth |
| Blacklist bypass (Redis down) | 🟠 | 3 | 12 | TokenStore.is_blacklisted fails silently; revoked token accepted | test_security.py: test_blacklist_failure |
| Weak secret_key in production | 🔴 | 4 | 16 | "change-me" default allows anyone to sign tokens | test_config.py: test_secret_key_prod |

### 2. WebSocket & Real-time
| Risk | Sev | Like | Score | Scenario | Test Coverage |
|------|-----|------|-------|----------|---------------|
| Message ordering corruption | 🔴 | 3 | 12 | Audio chunks arrive out of order; heap-based reordering loses chunks | test_audio_pipeline.py: test_out_of_order |
| Buffer overflow (long session) | 🟠 | 3 | 12 | User speaks continuously >30s; buffer exceeds max_buffer_ms | test_audio_pipeline.py: test_buffer_overflow |
| Speech detection false positive | 🟡 | 4 | 8 | Background noise triggers speech_start; wasted transcription | test_audio_pipeline.py: test_noise_floor |
| Speech detection false negative | 🟠 | 3 | 12 | Quiet speaker never triggers speech_start; missed transcription | test_audio_pipeline.py: test_quiet_speaker |
| WebSocket disconnect mid-speech | 🟠 | 4 | 16 | User disconnects while buffer has partial speech; data lost | test_audio_pipeline.py: test_disconnect_mid_speech |
| Race: 2 users same room_id | 🟡 | 2 | 4 | Concurrent WebSocket connections to /ws/audio/{room_id} | test_audio_pipeline.py: test_concurrent_ws |

### 3. Room Management & Matching
| Risk | Sev | Like | Score | Scenario | Test Coverage |
|------|-----|------|-------|----------|---------------|
| Room full but join succeeds | 🔴 | 2 | 8 | Race condition: 2 users join at max-1 simultaneously | test_room_api.py: test_join_race |
| Room state machine violation | 🟠 | 3 | 12 | Invalid transition (e.g. ACTIVE→IDLE); state corrupted | test_room_api.py: test_state_transitions |
| Matching fairness / starvation | 🟡 | 3 | 6 | Same users matched repeatedly; others starve | test_room_api.py: test_match_fairness |
| Orphaned participants | 🟠 | 3 | 12 | Room ends but participant records remain; DB bloat | test_room_api.py: test_leave_cleanup |
| max_participants out of range | 🟡 | 2 | 4 | API accepts values outside 3-5 due to missing validation | test_models.py: test_room_validation |
| Creator leaves → room broken | 🟡 | 4 | 8 | Room has no owner; cannot be moderated | test_room_lifecycle.py: test_creator_leave |

### 4. AI Agent Pipeline
| Risk | Sev | Like | Score | Scenario | Test Coverage |
|------|-----|------|-------|----------|---------------|
| LLM API timeout / hang | 🔴 | 4 | 16 | DeepSeek queue delay stalls correction; user waits forever | test_agent.py: test_api_timeout |
| Agent returns malformed JSON | 🟠 | 4 | 16 | Corrector returns non-JSON; parsing crashes | test_agent.py: test_malformed_response |
| Prompt injection via user text | 🟠 | 3 | 12 | User text contains "ignore previous instructions"; agent hijacked | test_agent.py: test_prompt_injection |
| Expert uses outdated knowledge | 🟡 | 3 | 6 | RAG returns stale chunks; agent gives wrong info | test_agent.py: test_stale_rag |
| Heartbeat spam (many rooms) | 🟡 | 3 | 6 | 100 simultaneous rooms all triggering heartbeat; rate limit hit | test_agent.py: test_heartbeat_throttle |

### 5. RAG / Document Processing
| Risk | Sev | Like | Score | Scenario | Test Coverage |
|------|-----|------|-------|----------|---------------|
| Embedding API failure | 🟠 | 3 | 12 | OpenAI embedding API down; document indexing fails silently | test_rag.py: test_embedding_failure |
| Chunk boundary splits sentence | 🟡 | 4 | 8 | Sentence split across chunks; retrieval returns gibberish | test_rag.py: test_chunk_boundaries |
| Duplicate document indexing | 🟡 | 3 | 6 | Same doc indexed twice; vector store has duplicates | test_rag.py: test_dedup |
| Vector store corruption | 🔴 | 1 | 4 | SQLite VSS database corrupted; all retrieval fails | test_rag.py: test_vs_corruption |
| Large file (>100MB) timeout | 🟠 | 3 | 12 | Celery task times out on large PDF; document stuck "indexing" | test_rag.py: test_large_file |
| Unsupported file type | 🟡 | 4 | 8 | User uploads .exe; FileHandler must reject gracefully | test_rag.py: test_bad_filetype |

### 6. Celery Task Queue
| Risk | Sev | Like | Score | Scenario | Test Coverage |
|------|-----|------|-------|----------|---------------|
| Task retry storm | 🔴 | 2 | 8 | Celery task fails with retry; Redis down → infinite retry loop | test_celery.py: test_retry_storm |
| Beat schedule miss | 🟠 | 2 | 8 | Matching tick doesn't fire; rooms stuck in MATCHING | test_celery.py: test_beat_fire |
| Task name mismatch | 🔴 | 1 | 4 | Code uses wrong task name; schedule registers but task 404s | (verified in __init__.py) |
| Dead letter queue overflow | 🟡 | 2 | 4 | Failed tasks accumulate; Redis memory exhausted | test_celery.py: test_dlq |

### 7. Database & Migrations
| Risk | Sev | Like | Score | Scenario | Test Coverage |
|------|-----|------|-------|----------|---------------|
| SQLite concurrent writes | 🟠 | 4 | 16 | Multiple Celery workers write simultaneously; DB locked | test_edge_cases.py: test_concurrent_writes |
| Email uniqueness violation | 🟡 | 3 | 6 | Two register requests with same email race | test_auth_api.py: test_duplicate_email |
| Foreign key cascade delete | 🟠 | 2 | 8 | Delete user → orphaned messages, tokens, participants | test_models.py: test_cascade |
| N+1 query on room detail | 🟡 | 4 | 8 | get_room loads participants + messages; 3 queries minimum | test_performance.py: test_n_plus_one |

### 8. Infrastructure
| Risk | Sev | Like | Score | Scenario | Test Coverage |
|------|-----|------|-------|----------|---------------|
| Redis connection lost | 🔴 | 3 | 12 | Redis goes down; rate limiting, token blacklist, Celery all fail | test_infra.py: test_redis_down |
| LiveKit token generation fails | 🔴 | 2 | 8 | Invalid API key; no user can join rooms | test_room_api.py: test_token_gen |
| Minio upload failure | 🟠 | 3 | 12 | TTS audio caching fails; audio regenerated each time | test_infra.py: test_minio_down |
| CORS misconfiguration | 🟡 | 2 | 4 | Requests from wrong origin succeed; CSRF possible | test_error_handling.py: test_cors |

### 9. Input Validation & Edge Cases
| Risk | Sev | Like | Score | Scenario | Test Coverage |
|------|-----|------|-------|----------|---------------|
| SQL injection via topic/tags | 🔴 | 1 | 4 | User input in room tags not sanitized (JSON field, lower risk) | test_edge_cases.py: test_sql_injection |
| XSS in display_name | 🟠 | 3 | 12 | Display name contains <script>; rendered in frontend | test_edge_cases.py: test_xss_display_name |
| Unicode normalization | 🟡 | 4 | 8 | Vietnamese "đ" vs "d" mismatch; search fails | test_edge_cases.py: test_unicode_search |
| Zero-length inputs | 🟡 | 3 | 6 | Empty topic, empty tags, empty password → crashes | test_edge_cases.py: test_empty_inputs |
| Extremely long inputs | 🟠 | 3 | 12 | 10KB topic name → DB overflow or performance hit | test_edge_cases.py: test_long_inputs |
| Negative pagination | 🟡 | 2 | 4 | skip=-1 → unexpected behavior | test_error_handling.py: test_negative_skip |
| UUID injection | 🟡 | 2 | 4 | "not-a-uuid" passed as room_id → 422 or 500? | test_error_handling.py: test_bad_uuid |

---

## Summary: Top 10 Risks by Score
| # | Risk | Score |
|---|------|-------|
| 1 | Brute-force login (no rate limit) | 16 |
| 2 | Weak secret_key in production | 16 |
| 3 | LLM API timeout | 16 |
| 4 | Agent malformed JSON response | 16 |
| 5 | SQLite concurrent writes | 16 |
| 6 | WebSocket disconnect mid-speech | 16 |
| 7 | Token expiry not enforced | 12 |
| 8 | Audio buffer overflow | 12 |
| 9 | Room state machine violation | 12 |
| 10 | Embedding API failure | 12 |

## Test Coverage Matrix
| Module | Unit | Integration | Pipeline | Edge Cases |
|--------|------|-------------|----------|------------|
| Auth | ✅ | ✅ | ✅ | ✅ |
| Security | ✅ | - | - | ✅ |
| Room | ✅ | ✅ | ✅ | ✅ |
| Audio | ✅ | - | ✅ | ✅ |
| Agent | ✅ | - | - | ✅ |
| RAG | ✅ | - | - | ✅ |
| Models | ✅ | - | - | ✅ |
| Error handling | - | ✅ | - | ✅ |
| Infrastructure | - | ✅ | - | ✅ |
