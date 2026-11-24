# Strata — действующий профиль Inkling 2 Mini SQ-20

## Установленные версии
- Strata package/server: 0.2.21
- Engine component: 0.1.67
- Runtime: Python 3.12.15
- CUDA UMD: 13.5
- NVIDIA driver: 620.70.06

## Модель и запуск
- Model: Inkling 2 Mini SQ-20
- Model file: /mnt/models-store/Inkling 2 Mini/SQ 20/Inkling-2-Mini-SQ-20.strata
- File size: 19,346,685,952 bytes
- Vision file: Inkling-2-Mini-Vision.strata (636,526,592 bytes)
- Config: /opt/strata-0221/.local/share/strata/install/strata-inkling-2-mini-sq-20.json
- Endpoint: 127.0.0.1:18080
- Offline mode; API key disabled; vision enabled
- max-context: 262144
- vram-experts-gb: 14.66
- draft: off
- prefill chunk: 512
- concurrency: 1
- KV dtype: fp16

## KV-cache allocation from engine startup log
- Global KV window: 262144 tokens
- VRAM-resident KV allocation: 84224 tokens
- Host-mapped KV allocation: 177920 tokens
- Host-mapped capacity: 5560 MiB
- Auto Host KV Offload: enabled
- Experts: 3072 VRAM / 0 host
- Trunk: 3.67 GB
- Runner + KV: 3854 MiB
- Free VRAM after load (engine log): 1566 MiB

The server reports native/max_positions/cache_max_tokens = 262144 and /health reports max_context = 262144. This confirms the configured window and KV allocation plan, not yet successful processing of a near-262144-token prompt.

## Preliminary context results
- ~8K: 8015 prompt tokens, prefill 2028.1 tok/s, decode 78.3 tok/s, total 7.3 s.
- ~32K: 32783 prompt tokens, prefill 1834.9 tok/s, decode 70.1 tok/s, total 21.4 s.
- Both are single exploratory runs with max_tokens=256 and finish_reason=length. See HTML report and JSON records.

## Important limitations
- No verified GPU hotspot or GDDR6X memory-junction temperature is exposed by the current CT128 telemetry path; nvidia-smi reports Memory Current Temp = N/A.
- The 32K thermal sample is only two samples; not a complete peak trace.
- No full-context 262K prompt test or long-context retrieval/recall test has passed yet.
- Do not modify this running profile in place. Copy config and preserve rollback before any A/B test.
