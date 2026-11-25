from pathlib import Path
import hashlib,json,zipfile
p=Path("docs/ceb/v3")
d=json.loads((p/"engineering-delivery.json").read_text())
archive=p/d["archive"]
actual=hashlib.sha256(archive.read_bytes()).hexdigest()
assert actual==d["expected_sha256"],("Published archive changed; update mirrors deliberately",actual,d["expected_sha256"])
with zipfile.ZipFile(archive) as z:
    m=json.loads(z.read("engineering.json"))
    assert m["dataset_id"]==d["dataset_id"]
    assert z.testzip() is None
    assert len(m["tasks"])==100
s=(p/"engineering-start-header.txt").read_text()+"\nИСТОЧНИКИ ТОЧНОГО ПАКЕТА\nSHA-256: "+actual+"\n"
for x in d["sources"]: s+=x["kind"]+": "+x["url"]+"\n"
for k in ("google_drive","yandex_disk"):
    if d[k]: s+=k+": "+d[k]["url"]+"\n"
    else: s+=k+": зеркало пока не подключено.\n"
if d["yandex_disk"]:
    y=d["yandex_disk"]
    s+="Яндекс.Диск: имя файла "+y["filename"]+"; ожидаемый размер "+str(y["expected_bytes"])+" байт; API метаданных "+y["metadata_api"]+"; API скачивания "+y["download_api"]+"\n"
u=d["unpacked"]; s+="Распакованные файлы: "+u["raw_base"]+"; GitHub: "+u["repository"]+", ветка "+u["branch"]+", папка "+u["path"]+"\n"
s+=(p/"engineering-start-format.txt").read_text()+"\nПЕРЕЧЕНЬ 100 ЗАДАНИЙ (номер / ID / необходимые файлы; пусто = условие полностью встроено ниже)\n"
for t in m["tasks"]:
    s+=f'{t["number"]:02} | {t["id"]} | {", ".join(t["input_files"]) or "встроено"}\n'
short=s.replace("в конце этого промпта встроены полные условия 63 самостоятельных заданий","в полном промпте встроены условия 63 самостоятельных заданий").replace("сохрани код из конца полного промпта как engineering-runner.py","получи engineering-runner.py отдельно или реализуй эквивалент") + "\nКомпактный режим: только с приложенным ZIP и ledger. Если архив недоступен, используй полный промпт со встроенными условиями.\n"
(p/"engineering-start-compact.txt").write_text(short)
s+="\nПОЛНЫЕ УСЛОВИЯ САМОСТОЯТЕЛЬНЫХ ЗАДАНИЙ. Если ZIP недоступен, решай их без ожидания.\n"
count=0
for t in m["tasks"]:
    if t["input_files"]: continue
    count+=1
    s+=f'\nЗАДАНИЕ {t["number"]:02} — {t["id"]} — {t["title"]}\n{t["question"]}\nРезультат: {t["result_requirements"]}\nПроверка: {t["acceptance"]}\nВыходные файлы: {", ".join(t["artifacts"]) or "только запись ответа"}\n'
assert count==63
s+="\nПЕРЕЧЕНЬ ОБЯЗАТЕЛЬНЫХ ВЫХОДНЫХ ФАЙЛОВ ДЛЯ ВСЕХ 100 ЗАДАНИЙ (JSON, для восстановления локального каталога при отсутствии ZIP)\n"
s+=json.dumps({"dataset_id":m["dataset_id"],"tasks":[{"number":t["number"],"id":t["id"],"artifacts":t["artifacts"]} for t in m["tasks"]]},ensure_ascii=False,separators=(",",":"))+"\n"
s+="\nУСЛОВИЯ ЗАДАНИЙ С ОТДЕЛЬНЫМИ ВХОДАМИ. Используй при получении отдельных материалов; недостающие факты не угадывай.\n"
for t in m["tasks"]:
    if not t["input_files"]: continue
    s+=f'\nЗАДАНИЕ {t["number"]:02} — {t["id"]} — {t["title"]}\n{t["question"]}\nВходы: {", ".join(t["input_files"])}\nРезультат: {t["result_requirements"]}\nПроверка: {t["acceptance"]}\nВыходы: {", ".join(t["artifacts"]) or "запись ответа"}\n'
s+="\nНАЧАЛО КОДА engineering-runner.py (служебный инструмент, не эталоны)\n"+(p/"engineering-runner.py").read_text()+"\nКОНЕЦ КОДА engineering-runner.py\n"
(p/"engineering-start.txt").write_text(s)
assert all(f'ЗАДАНИЕ {t["number"]:02} — {t["id"]}' in s for t in m["tasks"] if not t["input_files"])
print("CEB delivery:",count,"embedded tasks;",len(s),"characters; archive SHA verified:",actual)
