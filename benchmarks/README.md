# Benchmark records

Каждый запуск — отдельный JSON в results/YYYY/. Схема: schema/benchmark.schema.json.

Статусы: planned, running, exploratory, validated, failed, incomplete.

Сохранять параметры запроса, версии модели/движка, GPU, контекст, фактические input/output tokens, TTFT до первого события и первого видимого текста, prefill/decode, полное время, VRAM, температуру, мощность, ошибки и качество.

Неизмеренное значение — null, не оценка. Сырые логи сохранять отдельно, если они доступны и очищены от секретов. JSON результата — источник данных для HTML и dashboard.
