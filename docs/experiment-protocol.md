# Методика испытаний

## До запуска
1. Убедиться, что тест выполняется только в CT128.
2. Снять исходные nvidia-smi, процессы, VRAM, температуры, Power Limit и версии драйвера/движка.
3. Зафиксировать точный файл модели, quantization и checksum, если доступна.
4. Сохранить исходный профиль запуска.
5. Проверить отсутствие посторонних процессов на GPU.
6. Присвоить Run ID. Не менять одновременно несколько факторов.

## Обязательные параметры
Дата; модель и файл; quantization; движок и версии; CUDA/runtime; GPU, PCI Bus ID, VBIOS, VRAM, Power Limit; batch/concurrency; KV-cache и dtype; заданный и фактический prompt token count; temperature, sampling, max output, reasoning effort; cold/warm; точный prompt или ID.

## Метрики
- TTFT engine event — время до первого события движка.
- TTFT visible text — время до первого непустого пользовательского текста.
- Prefill tok/s — входные токены / время prefill; записывать число токенов и метод.
- Decode tok/s — выходные токены / чистое время decode.
- End-to-end — полное время запроса.
- VRAM baseline/peak/residual.
- GPU utilization, core, hotspot, memory junction (если датчики доступны), power draw и power limit.
- CPU/RAM, RSS.
- Качество: точность, полнота, русский язык, reasoning, код, function calling, Vision и длинный контекст.

## Контекстная матрица
Для поддерживаемых моделью режимов: 8K, 32K, 64K, 128K, 192K и 262144 токена. Считать tokenizer'ом. Указанный в конфиге context length не доказывает работу на полном контексте.

## Повторяемость
Cold start и warm run отдельно. Для итогового сравнения — не менее трёх одинаковых прогонов и медиана. Отдельно проверять одиночную и параллельную нагрузку. Сравниваемые модели тестировать на одинаковых заданиях.

## Остановка
Прекратить тест при температуре выше целевых 70 °C, CUDA error, OOM, нестабильности питания или риске воздействия на production. Не превышать заводские пределы.

## Публикация
Сохранить JSON по schema, HTML в docs/reports/YYYY/, запись в journal/YYYY/ и обновить docs/data/dashboard.json. Неполные результаты помечать exploratory/incomplete.
