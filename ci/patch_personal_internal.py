from pathlib import Path
import subprocess, sys

root=Path(sys.argv[1] if len(sys.argv)>1 else 'work/MedicalRecord2026')
if not root.exists(): raise SystemExit(f'Source root not found: {root}')
subprocess.run([sys.executable,str(Path(__file__).with_name('patch_rc041.py')),str(root)],check=True)

def rw(rel,*pairs):
    p=root/rel; s=p.read_text(encoding='utf-8')
    for a,b in pairs: s=s.replace(a,b)
    p.write_text(s,encoding='utf-8')

# Software channel/version only. Clinical template version remains RC 0.4 until separate validation.
rw('src/MedicalRecord.Desktop/MedicalRecord.Desktop.csproj',('<Version>0.4.1</Version>','<Version>1.0.0</Version>'))
(root/'VERSION').write_text('1.0.0-internal\n',encoding='utf-8')
rw('src/MedicalRecord.Desktop/MainWindow.axaml',('Text="RC 0.4"','Text="Personal/Internal 1.0"'))
rw('src/MedicalRecord.Desktop/Views/DashboardView.axaml',('RC 0.4: рабочее место подключено','Personal/Internal 1.0: рабочее место подключено'))
rw('src/MedicalRecord.Desktop/Views/LoginView.axaml',('Medical Record 2026 · Release Candidate 0.4','Medical Record 2026 · Personal/Internal 1.0'))
rw('src/MedicalRecord.Desktop/Views/DiagnosticStudyEditorView.axaml',('Расширенное структурированное диагностическое исследование · RC 0.4','Расширенное структурированное диагностическое исследование · Personal/Internal 1.0'))
rw('src/MedicalRecord.Desktop/Views/DocumentPreviewView.axaml',('рабочее представление RC 0.4','рабочее представление Personal/Internal 1.0'))
rw('src/MedicalRecord.Api/Endpoints/SystemEndpoints.cs',('"0.4.0-rc1"','"1.0.0-internal"'))
rw('src/MedicalRecord.Infrastructure/Documents/Form025uRenderer.cs',('Структурированное рабочее представление RC 0.4','Структурированное рабочее представление Personal/Internal 1.0'))

# Windows Internal: unsigned personal channel; Production remains signed/fail-closed.
rw('packaging/windows/build-installer.ps1',
   ("[string]$Version = '0.4.0'","[string]$Version = '1.0.0'"),
   ("[ValidateSet('Development','Production')][string]$ReleaseChannel = 'Development'","[ValidateSet('Development','Internal','Production')][string]$ReleaseChannel = 'Internal'"),
   ("$Suffix=if($ReleaseChannel -eq 'Production'){'production'}else{'development'}","$Suffix=if($ReleaseChannel -eq 'Production'){'production'}elseif($ReleaseChannel -eq 'Internal'){'internal'}else{'development'}"),
   ('} else {\n  "DEVELOPMENT INSTALLER - NOT A TRUSTED PRODUCTION RELEASE" | Set-Content -Encoding UTF8 (Join-Path $Out "MedicalRecord2026-$Version-$Runtime-DEVELOPMENT.txt")\n}', '} elseif($ReleaseChannel -eq \'Internal\') {\n  "PERSONAL/INTERNAL INSTALLER - UNSIGNED - FOR THE OWNER\'S OWN DEVICES ONLY" | Set-Content -Encoding UTF8 (Join-Path $Out "MedicalRecord2026-$Version-$Runtime-PERSONAL-INTERNAL.txt")\n} else {\n  "DEVELOPMENT INSTALLER - NOT A TRUSTED PRODUCTION RELEASE" | Set-Content -Encoding UTF8 (Join-Path $Out "MedicalRecord2026-$Version-$Runtime-DEVELOPMENT.txt")\n}'))
rw('packaging/windows/test-installer.ps1',
   ("[ValidateSet('Development','Production')][string]$ReleaseChannel = 'Development'","[ValidateSet('Development','Internal','Production')][string]$ReleaseChannel = 'Internal'"))

# macOS Internal: unsigned/unnotarized personal channel; Production remains Developer ID/notarized.
rw('packaging/macos/build-installer.sh',
   ('VERSION="${VERSION:-0.4.0}"','VERSION="${VERSION:-1.0.0}"'),
   ('RELEASE_CHANNEL="${RELEASE_CHANNEL:-Development}"','RELEASE_CHANNEL="${RELEASE_CHANNEL:-Internal}"'),
   ('SUFFIX="development"\n[[ "$RELEASE_CHANNEL" == "Production" ]] && SUFFIX="production"','SUFFIX="development"\n[[ "$RELEASE_CHANNEL" == "Internal" ]] && SUFFIX="internal"\n[[ "$RELEASE_CHANNEL" == "Production" ]] && SUFFIX="production"'),
   ("else\n  printf '%s\\n' 'DEVELOPMENT INSTALLER - AD-HOC/UNSIGNED FOR DISTRIBUTION - NOT A TRUSTED PRODUCTION RELEASE' > \"$OUT/MedicalRecord2026-$VERSION-$RID-DEVELOPMENT.txt\"\nfi","elif [[ \"$RELEASE_CHANNEL\" == \"Internal\" ]]; then\n  printf '%s\\n' \"PERSONAL/INTERNAL INSTALLER - UNSIGNED/UNNOTARIZED - FOR THE OWNER'S OWN DEVICES ONLY\" > \"$OUT/MedicalRecord2026-$VERSION-$RID-PERSONAL-INTERNAL.txt\"\nelse\n  printf '%s\\n' 'DEVELOPMENT INSTALLER - UNSIGNED/UNNOTARIZED - NOT A TRUSTED PRODUCTION RELEASE' > \"$OUT/MedicalRecord2026-$VERSION-$RID-DEVELOPMENT.txt\"\nfi"))
rw('packaging/macos/test-installer.sh',('CHANNEL="${4:-Development}"','CHANNEL="${4:-Internal}"'))

(root/'packaging/PERSONAL_INTERNAL.ru.md').write_text('''# Medical Record 2026 — Personal/Internal 1.0

Internal предназначен для личного использования владельцем на собственных компьютерах. Платные code-signing сертификаты не требуются. Internal-пакеты не предназначены для распространения.

Windows x64: `build-installer.ps1 ... -ReleaseChannel Internal`.
macOS Apple Silicon: `RELEASE_CHANNEL=Internal ... build-installer.sh osx-arm64`.

Production-путь с Authenticode / Developer ID сохранён и остаётся fail-closed.
''',encoding='utf-8')
print('Medical Record 2026 Personal/Internal 1.0 patch applied')
