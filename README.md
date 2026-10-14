# Nova Office

PDF-редактор, презентации (.pptx), документы (.docx/.md/.txt/.html), печать, лента новостей. Qt (PySide6).

## Сборка
Push в `main` или Actions → `build-installer` → Run workflow. Результат: `NovaOffice-Setup.exe`
(артефакт + пререлиз `build-<N>`). Версию меняй в `app/version.py`.

## Обновления
Приложение проверяет последние успешные сборки в Actions, сравнивает номер сборки и коммит с установленными
(уже стоящую версию не предлагает), качает установщик и ставит поверх.
Порядок скачивания: артефакт Actions (если в Настройках указан токен GitHub) → релиз `build-N` → nightly.link.

## Установщик
`installer/setup.py` — свой мастер, ставит в `%LOCALAPPDATA%\Programs` без прав администратора, ярлыки,
«Открыть с помощью», запись в «Программы и компоненты». Ключи: `/UPDATE` или `/S` — тихо, `/UNINSTALL` — удалить.

## Запуск из исходников
    pip install -r requirements.txt
    python app/main.py [файл]

Ctrl+K — быстрые команды.
