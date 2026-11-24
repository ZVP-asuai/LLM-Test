# Qwen3.8 Flash Next — инвентаризация и план A/B, 2026-11-24

**Статус: подготовка, новая серия не выполнена.** Запуск нового испытательного скрипта через удалённый инструмент отклонён защитой. Повторная проверка GPU показала 1 MiB VRAM, 34,28 °C, PL 300 W, агент active. Не записывать исторические числа как новую серию.

## Проверенные артефакты

- UD-Q4_K_XL, четыре GGUF-шарда, 111 334 614 784 байт, отдельно BF16 mmproj 907 543 008 байт.
- GGUF: qwen4exp, 512 experts, top-10, context_length=262144. Название Qwen3.8 Flash Next. Локальный pack называется unsloth-ud-q4_k_xl-ablm06. Имена и размеры всех четырёх исходных шардов совпали с conversions.json; проверены SHA256 12 тензоров. Это выборочная проверка, не полная идентификация ревизии/варианта весов.
- Установлен официальный Strata 0.2.21 / engine 0.1.67, подтверждено соответствие официальному релизу 24 ноября: https://github.com/Niko1221/Strata/releases/tag/v0.2.21
- Отдельная экспериментальная сборка 0.1.67p SM86, CUDA 13.0, build_id v0.2.21-d46f5f268f8e-sm86-p1p2-pr6249-ct128; SHA256 бинарника d0dd83c2e486b2ceccc9a553deabdccd8192ff012107748da735254c0f8d3753 совпал с manifest.
- Исходники d46f5f2, локально модифицированы. Патчи P1 staging blobs (STRATA_STAGING_BLOBS default 16, clamp 4..64); P2 FS retry (не доказанный прирост скорости); PR6249 equal tail (opt-in STRATA_PREFILL_EQUAL_TAIL). Также существует отдельный diff PR6196 (prefix trie/pin registry), не считать установленным.
- Исторический campaign: max-context 262144, expert-cache 4900, prefill auto, KV int8, kv-resident 32768, PLE ram, DFlash2 selq4, spec 6, draft-conf 0.7, draft-fallback none, conversation-cache-slots 12, conversation-cache-mib 16384, aux-cpus auto; vision enabled. Переносить в новую копию с соответствующим engine и loopback; не изменять рабочий профиль. STRATA_ROUTE_TAIL_SKIP=0 (не пропускать экспертов).

## Исторические измерения из локальных журналов

| Контекст | Режим | N | Prefill tok/s | Decode tok/s |
|---|---|---:|---:|---:|
| 29–36K | ct128-equal-prod, engine 0.1.60 (журнал предыдущей кампании) | 45 | 2709.9 | 86.9 |
| 249778 | base | 1 | 1778.4 | 67.3 |
| 249778 | MTP | 1 | 1777.6 | 84.0 |
| 240–262K | DFlash2 | 6 | 1768.15 | 79.25 |
| 249778 | DFlash2 k8v4 | 1 | 1589.7 | 80.5 |

Медианы для N>1, фильтр reused=0 и output>=64. Разные задания, длины ответа, настройки и версии; температура и PL каждой исторической записи не восстановлены. Числа не являются актуальными измерениями новой сборки или доказательством качества.

## Порядок испытаний

1. Baseline официальной 0.1.67 и отдельно 0.1.67p на одной конфигурации с max-context=262144, concurrency=1, PL<=300 W, xhigh. 32768 фактических входных токенов, без reuse; одно задание, одинаковый sampling и выходной бюджет. Защита по доступным датчикам, предупредительный порог Core 68 °C.
2. A/B prefill auto, auto:16384, auto:32768 (если поддерживает реальный runtime), equal tail off/порог по исходникам, затем staging blobs 16/24/32 при наличии VRAM. Не включать аппроксимацию routing tail skip.
3. KV int8: kv-resident 32768 / 65536 (и выше при реальном запасе VRAM), kv-grow только при подтверждённой совместимости. Замерять expert hit rate, KV streaming, transfer и свободную VRAM. k8v4 только отдельной проверкой качества.
4. DFlash2 и MTP, spec 4/6/8 в поддерживаемых режимах, draft confidence 0.5/0.7/0.85, draft acceptance и фактическая скорость. Нельзя менять режим reasoning или снижать качество. Оригинальный draft pack доступен; MTP pack проверить, не обращаться к production.
5. Сравнить prompt-cache-every, prompt-cache-tail/spread, conversation-cache-min-tokens / park-gain / rewind-keep; тестировать продолжение диалога и переключение ветки отдельно от fresh prompt. PR6196 проверять против свежего исходного кода и тестов, не накладывать вслепую.
6. CPU pool workers / tasks / aux affinity и PCIe transfer; проверить prefill CPU share и адаптивный cache. Не менять параметры хоста.
7. Лучшие конфигурации перепроверить на 131072 и near-262144 с местом для ответа, >=3 повтора, retrieval начало/середина/конец, reasoning, code, tool calling, Vision; остановка при перегреве/ошибках. Не повышать PL.
