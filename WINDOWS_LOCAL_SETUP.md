# Scan2Stage — локальная установка на Windows 10

Эта инструкция рассчитана на обычную локальную рабочую станцию Windows 10 x64. Colab и облачная среда для основного workflow больше не используются.

## 1. Требования

Рекомендуется:

- Windows 10 x64;
- Python 3.11 x64;
- Git for Windows;
- 32 GB RAM минимум, 64 GB предпочтительно для крупных галерей;
- NVMe SSD;
- 8–16 производительных CPU-ядер;
- GPU не обязателен для текущего structural-first pipeline.

Python 3.13 пока не рекомендуется из-за совместимости Open3D.

## 2. Клонирование

Откройте PowerShell или cmd:

~~~bat
git clone https://github.com/6564200/Scan2Stage.git
cd Scan2Stage
~~~

## 3. Создание venv и установка

Самый простой способ:

~~~bat
scripts\setup_windows.bat
~~~

Скрипт создаёт .venv через Python 3.11, обновляет pip и устанавливает Scan2Stage в editable-режиме.

Ручной эквивалент:

~~~bat
py -3.11 -m venv .venv
.venv\Scripts\python.exe -m pip install --upgrade pip
.venv\Scripts\python.exe -m pip install -e ".[dev]"
~~~

Проверка:

~~~bat
.venv\Scripts\python.exe -m pytest -q
~~~

## 4. Запуск web-интерфейса

~~~bat
scripts\start_windows.bat
~~~

После запуска открыть:

~~~text
http://127.0.0.1:8765
~~~

Сервер слушает только localhost и по умолчанию не доступен из внешней сети.

## 5. Где хранятся данные

По умолчанию:

~~~text
%USERPROFILE%\Scan2StageData
~~~

Структура:

~~~text
Scan2StageData/
  scan2stage.db
  settings.json
  galleries/
    <gallery-id>/
      scans/
        <scan-id>/
          original.glb
  runs/
    <run-id>/
      scans/
        <scan-id>/
          sampled_colored.ply
          room_normalized.ply
          room_geometry.json
          object_candidates.json
          structural_scene.json
          topview_layers.npz
          semantic_topview.png
          report.json
          run_manifest.json
  logs/
    <run-id>.log
~~~

Путь можно изменить системной переменной:

~~~bat
set SCAN2STAGE_HOME=D:\Scan2StageData
~~~

Для постоянной настройки используйте Windows Environment Variables.

## 6. Основной workflow

1. Открыть страницу Загрузка.
2. Создать Gallery.
3. Загрузить один или несколько GLB/ZIP/FBX/OBJ.
4. Открыть Gallery и выбрать сканы, участвующие в Run.
5. Нажать Запустить выбранные сканы.
6. Следить за прогрессом на странице Run.
7. Смотреть логи при ошибках.
8. После завершения открыть Результаты и скачать доступные artifacts.

На текущем milestone несколько сканов одной Gallery хранятся и обрабатываются как отдельные наблюдения. Автоматическая регистрация/fusion нескольких сканов в одну геометрию — следующий отдельный этап.

## 7. Настройки

В web-интерфейсе:

- Sample count — плотность глобального surface sampling;
- Source up — вертикальная ось входного mesh;
- Unit scale — ручной override масштаба;
- Top-view resolution — coarse structural grid;
- Blender executable — путь к blender.exe для будущего clean-scene exporter;
- Max parallel runs — лимит тяжёлых задач на одной машине.

Начальные значения:

~~~text
Sample count: 300000
Source up: y
Top-view: 0.05 m
Parallel runs: 1
~~~

## 8. Blender

FBX/GLB clean-scene exporter пока является следующим milestone. Не следует считать исходный scan GLB финальным результатом.

Когда exporter будет подключён, укажите путь, например:

~~~text
C:\Program Files\Blender Foundation\Blender 4.5\blender.exe
~~~

Интерфейс уже умеет показывать и отдавать result.glb / result.fbx, если pipeline их создаёт.

## 9. Обновление проекта

~~~bat
git pull origin main
.venv\Scripts\python.exe -m pip install -e ".[dev]"
~~~

## 10. CLI остаётся доступным

~~~bat
.venv\Scripts\scan2stage.exe scan.glb --output-dir outputs\test --samples 300000 --source-up y
~~~

Основным пользовательским интерфейсом считается локальное web-приложение.
