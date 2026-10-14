# Nova Office

PDF-редактор, презентации (.pptx), документы (.docx/.md/.txt/.html/.odt), печать, лента новостей. Нативный интерфейс на Qt (PySide6).

## Сборка установщика на GitHub
1. Создай репозиторий и залей всё содержимое папки.
2. Вкладка **Actions** → `build-installer` → **Run workflow** (или просто push в `main`).
3. Через ~5 минут в **Artifacts** появится `NovaOffice-Setup` — внутри `NovaOffice-Setup.exe`.

## Запуск без установки
    pip install -r requirements.txt
    python app/main.py [файл]

## Программа по умолчанию
Установщик регистрирует Nova Office для PDF/PPTX/DOCX/TXT/MD. Windows 10/11 не даёт программам
молча менять «по умолчанию», поэтому: ПКМ на файл → «Открыть с помощью» → Nova Office → «Всегда»,
либо кнопка «Программа по умолчанию» в приложении.
