from pathlib import Path
import sys

root=Path(sys.argv[1] if len(sys.argv)>1 else 'work/MedicalRecord2026')
if not root.exists(): raise SystemExit(f'Source root not found: {root}')

def rw(rel,*pairs):
    p=root/rel; s=p.read_text(encoding='utf-8')
    for a,b in pairs: s=s.replace(a,b)
    p.write_text(s,encoding='utf-8')

# Native-CI compile fixes validated in RC 0.4.1.
rw('Directory.Build.props',('<Deterministic>true</Deterministic>','<Deterministic>true</Deterministic>\n    <AvaloniaUseCompiledBindingsByDefault>false</AvaloniaUseCompiledBindingsByDefault>'))
for p in (root/'src/MedicalRecord.Desktop').rglob('*.axaml'):
    s=p.read_text(encoding='utf-8')
    if 'x:CompileBindings=' not in s:
        n='xmlns:x="http://schemas.microsoft.com/winfx/2006/xaml"'; i=s.find(n)
        if i>=0:
            e=i+len(n); s=s[:e]+'\n             x:CompileBindings="False"'+s[e:]
    p.write_text(s,encoding='utf-8')
rw('src/MedicalRecord.Desktop/App.axaml',('avares://MedicalRecord.Desktop/Styles/ClinicalTheme.axaml','avares://MedicalRecord2026/Styles/ClinicalTheme.axaml'))
rw('src/MedicalRecord.Api/Endpoints/ScheduleEndpoints.cs',('SingleAsync(x=>x.Id=request.PatientId,ct)','SingleAsync(x=>x.Id==request.PatientId,ct)'),('details=item.Status','details:item.Status'))
for rel in ['src/MedicalRecord.Api/Endpoints/PapEndpoints.cs','src/MedicalRecord.Api/Endpoints/DocumentEndpoints.cs']:
    rw(rel,('details=','details:'))

# Personal/Internal 1.0 is a distribution-channel label, not a regulatory certification claim.
rw('src/MedicalRecord.Desktop/MedicalRecord.Desktop.csproj',('<Version>0.4.0</Version>','<Version>1.0.0</Version>'),('<Version>0.4.1</Version>','<Version>1.0.0</Version>'))
(root/'VERSION').write_text('1.0.0-internal\n',encoding='utf-8')
rw('src/MedicalRecord.Desktop/MainWindow.axaml',('Text="RC 0.4"','Text="Personal/Internal 1.0"'))
rw('src/MedicalRecord.Desktop/Views/DashboardView.axaml',('RC 0.4: рабочее место подключено','Personal/Internal 1.0: рабочее место подключено'))
rw('src/MedicalRecord.Desktop/Views/LoginView.axaml',('Medical Record 2026 · Release Candidate 0.4','Medical Record 2026 · Personal/Internal 1.0'))
rw('src/MedicalRecord.Desktop/Views/DiagnosticStudyEditorView.axaml',('Расширенное структурированное диагностическое исследование · RC 0.4','Расширенное структурированное диагностическое исследование · Personal/Internal 1.0'))
rw('src/MedicalRecord.Desktop/Views/DocumentPreviewView.axaml',('рабочее представление RC 0.4','рабочее представление Personal/Internal 1.0'))
rw('src/MedicalRecord.Api/Endpoints/SystemEndpoints.cs',('"0.4.0-rc1"','"1.0.0-internal"'))
rw('src/MedicalRecord.Infrastructure/Documents/Form025uRenderer.cs',('274n-2025/rc-0.4','274n-2025/internal-1.0'),('Структурированное рабочее представление RC 0.4','Структурированное рабочее представление Personal/Internal 1.0'))

# Windows Internal: unsigned personal installer. Production remains fail-closed and signed.
rw('packaging/windows/build-installer.ps1',
   ("[string]$Version = '0.4.0'","[string]$Version = '1.0.0'"),
   ("[ValidateSet('Development','Production')][string]$ReleaseChannel = 'Development'","[ValidateSet('Development','Internal','Production')][string]$ReleaseChannel = 'Internal'"),
   ("$Suffix=if($ReleaseChannel -eq 'Production'){'production'}else{'development'}","$Suffix=if($ReleaseChannel -eq 'Production'){'production'}elseif($ReleaseChannel -eq 'Internal'){'internal'}else{'development'}"),
   ('} else {\n  "DEVELOPMENT INSTALLER - NOT A TRUSTED PRODUCTION RELEASE" | Set-Content -Encoding UTF8 (Join-Path $Out "MedicalRecord2026-$Version-$Runtime-DEVELOPMENT.txt")\n}', '} elseif($ReleaseChannel -eq \'Internal\') {\n  "PERSONAL/INTERNAL INSTALLER - UNSIGNED - FOR THE OWNER\'S OWN DEVICES ONLY" | Set-Content -Encoding UTF8 (Join-Path $Out "MedicalRecord2026-$Version-$Runtime-PERSONAL-INTERNAL.txt")\n} else {\n  "DEVELOPMENT INSTALLER - NOT A TRUSTED PRODUCTION RELEASE" | Set-Content -Encoding UTF8 (Join-Path $Out "MedicalRecord2026-$Version-$Runtime-DEVELOPMENT.txt")\n}'))
rw('packaging/windows/test-installer.ps1',
   ("[ValidateSet('Development','Production')][string]$ReleaseChannel = 'Development'","[ValidateSet('Development','Internal','Production')][string]$ReleaseChannel = 'Internal'"),
   ('& $exe --self-test\nif($LASTEXITCODE -ne 0){throw "Installed application self-test failed with $LASTEXITCODE."}','$selfTest=Start-Process -FilePath $exe -ArgumentList @("--self-test") -Wait -PassThru\nif($selfTest.ExitCode -ne 0){throw "Installed application self-test failed with $($selfTest.ExitCode)."}'))

# macOS Internal: unsigned/unnotarized personal bundle. Production remains Developer-ID-only.
p=root/'packaging/macos/build-installer.sh'; s=p.read_text(encoding='utf-8')
s=s.replace('VERSION="${VERSION:-0.4.0}"','VERSION="${VERSION:-1.0.0}"').replace('RELEASE_CHANNEL="${RELEASE_CHANNEL:-Development}"','RELEASE_CHANNEL="${RELEASE_CHANNEL:-Internal}"')
s=s.replace('SUFFIX="development"\n[[ "$RELEASE_CHANNEL" == "Production" ]] && SUFFIX="production"','SUFFIX="development"\n[[ "$RELEASE_CHANNEL" == "Internal" ]] && SUFFIX="internal"\n[[ "$RELEASE_CHANNEL" == "Production" ]] && SUFFIX="production"')
s=s.replace('APP="$OUT/Medical Record 2026-$RID.app"','APP="$OUT/Medical Record 2026.app"')
a=s.index('sign_native(){'); marker='codesign --verify --strict --verbose=2 "$APP"\n'; b=s.index(marker,a)+len(marker)
replacement='''if [[ "$RELEASE_CHANNEL" == "Production" ]]; then
  while IFS= read -r -d '' f; do
    if [[ "$f" != "$APP/Contents/MacOS/MedicalRecord2026" ]] && file "$f" | grep -q 'Mach-O'; then
      codesign --force --timestamp --options runtime --sign "$APP_IDENTITY" "$f"
      codesign --verify --strict --verbose=1 "$f"
    fi
  done < <(find "$APP/Contents" -type f -print0)
  codesign --force --timestamp --options runtime --entitlements "$ENTITLEMENTS" --sign "$APP_IDENTITY" "$APP"
  codesign --verify --strict --verbose=2 "$APP"
else
  echo 'Internal/Development app bundle intentionally unsigned; Developer ID is Production-only.'
fi
'''
s=s[:a]+replacement+s[b:]
s=s.replace('pkgbuild --component "$APP" --install-location /Applications --identifier ru.medicalrecord2026.desktop --version "$VERSION" "$PKG"','productbuild --component "$APP" /Applications --identifier ru.medicalrecord2026.desktop --version "$VERSION" "$PKG"')
s=s.replace("else\n  printf '%s\\n' 'DEVELOPMENT INSTALLER - AD-HOC/UNSIGNED FOR DISTRIBUTION - NOT A TRUSTED PRODUCTION RELEASE' > \"$OUT/MedicalRecord2026-$VERSION-$RID-DEVELOPMENT.txt\"\nfi","elif [[ \"$RELEASE_CHANNEL\" == \"Internal\" ]]; then\n  printf '%s\\n' \"PERSONAL/INTERNAL INSTALLER - UNSIGNED/UNNOTARIZED - FOR THE OWNER'S OWN DEVICES ONLY\" > \"$OUT/MedicalRecord2026-$VERSION-$RID-PERSONAL-INTERNAL.txt\"\nelse\n  printf '%s\\n' 'DEVELOPMENT INSTALLER - UNSIGNED/UNNOTARIZED - NOT A TRUSTED PRODUCTION RELEASE' > \"$OUT/MedicalRecord2026-$VERSION-$RID-DEVELOPMENT.txt\"\nfi")
p.write_text(s,encoding='utf-8')
rw('packaging/macos/test-installer.sh',
   ('CHANNEL="${4:-Development}"','CHANNEL="${4:-Internal}"'),
   ('"$APP/Contents/MacOS/MedicalRecord2026" --self-test\ncodesign --verify --strict --verbose=2 "$APP"\n\nif [[ "$CHANNEL" == Production ]]; then','"$APP/Contents/MacOS/MedicalRecord2026" --self-test\n\nif [[ "$CHANNEL" == Production ]]; then\n  codesign --verify --strict --verbose=2 "$APP"'),
   ('codesign --verify --strict --verbose=2 "$MOUNT/Medical Record 2026.app"\nhdiutil detach "$MOUNT"','if [[ "$CHANNEL" == Production ]]; then codesign --verify --strict --verbose=2 "$MOUNT/Medical Record 2026.app"; fi\nhdiutil detach "$MOUNT"'))

(root/'packaging/PERSONAL_INTERNAL.ru.md').write_text('''# Medical Record 2026 — Personal/Internal 1.0

Internal предназначен для личного использования владельцем на собственных компьютерах. Платные code-signing сертификаты не требуются. Internal-пакеты не предназначены для распространения.

Windows x64:
`./packaging/windows/build-installer.ps1 -Runtime win-x64 -Version 1.0.0 -ApiUrl http://localhost:5186/ -ReleaseChannel Internal`

macOS Apple Silicon:
`VERSION=1.0.0 RELEASE_CHANNEL=Internal MEDICALRECORD_API_URL=http://localhost:5186/ ./packaging/macos/build-installer.sh osx-arm64`

Production-путь с Authenticode / Developer ID сохранён и остаётся fail-closed.
''',encoding='utf-8')
print('Medical Record 2026 Personal/Internal 1.0 patch applied')
