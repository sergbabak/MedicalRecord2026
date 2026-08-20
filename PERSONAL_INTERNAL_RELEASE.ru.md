# Medical Record 2026 — Personal/Internal 1.0

Статус канала: личное внутреннее использование владельцем на собственных компьютерах. Публичное распространение не предполагается. Платные Windows/macOS code-signing сертификаты для этого канала не требуются.

## Windows x64

Основной файл: `MedicalRecord2026-1.0.0-win-x64-internal-setup.exe`.

1. Распакуйте GitHub Actions artifact.
2. При необходимости сверьте SHA-256 с файлом `.sha256`.
3. Запустите Setup EXE.
4. Если Microsoft Defender SmartScreen показывает обычное предупреждение неизвестного издателя, используйте `More info` → `Run anyway`, если эта кнопка доступна и вы устанавливаете именно проверенный артефакт этого репозитория.
5. После запуска укажите адрес API в мастере первого запуска. Для локальной разработки по умолчанию используется `http://localhost:5186/`.

Не отключайте Smart App Control или другие системные средства защиты глобально только ради установки этой программы.

## macOS Apple Silicon

Предпочтительный файл для личной установки: `MedicalRecord2026-1.0.0-osx-arm64-internal.dmg`. Также создаётся `.pkg`.

1. Распакуйте GitHub Actions artifact.
2. При необходимости сверьте SHA-256 с файлом `.sha256`.
3. Откройте DMG и скопируйте `Medical Record 2026.app` в `/Applications`.
4. При первом запуске macOS может заблокировать неподписанное приложение. После первой попытки запуска откройте `System Settings` → `Privacy & Security` и используйте `Open Anyway`, затем подтвердите `Open`.
5. После запуска укажите адрес API в мастере первого запуска.

Internal-сборка намеренно unsigned/unnotarized. Это допустимо для личного использования на собственном Mac, но не является публично доверенным релизом.

## Что проверяет CI

Каждый Internal installer проходит: проверку SHA исходника → `dotnet restore` → `dotnet build Release` → упаковку → реальную установку → запуск установленного приложения с `--self-test` → удаление/очистку → загрузку артефакта.

В артефакт также входит `PERSONAL-INTERNAL-ATTESTATION.json` с commit/run ID и признаком `installSelfTestVerified=true`.

## Важно

Desktop-клиент остаётся рабочим местом архитектуры client + API + PostgreSQL. Internal-инсталлятор устанавливает desktop workstation; API/PostgreSQL должны быть доступны отдельно. Production-путь с Authenticode / Apple Developer ID сохранён в проекте, но для личного Internal-канала не обязателен.
