from pathlib import Path
import sys

root = Path(sys.argv[1] if len(sys.argv) > 1 else 'work/MedicalRecord2026')
if not root.exists():
    raise SystemExit(f'RC source root not found: {root}')

p = root / 'Directory.Build.props'
s = p.read_text(encoding='utf-8')
if '<AvaloniaUseCompiledBindingsByDefault>' not in s:
    s = s.replace('<Deterministic>true</Deterministic>', '<Deterministic>true</Deterministic>\n    <AvaloniaUseCompiledBindingsByDefault>false</AvaloniaUseCompiledBindingsByDefault>')
p.write_text(s, encoding='utf-8')

for p in (root / 'src/MedicalRecord.Desktop').rglob('*.axaml'):
    s = p.read_text(encoding='utf-8')
    if 'x:CompileBindings=' not in s:
        needle = 'xmlns:x="http://schemas.microsoft.com/winfx/2006/xaml"'
        i = s.find(needle)
        if i >= 0:
            end = i + len(needle)
            s = s[:end] + '\n             x:CompileBindings="False"' + s[end:]
    p.write_text(s, encoding='utf-8')

p = root / 'src/MedicalRecord.Desktop/App.axaml'
p.write_text(p.read_text(encoding='utf-8').replace('avares://MedicalRecord.Desktop/Styles/ClinicalTheme.axaml', 'avares://MedicalRecord2026/Styles/ClinicalTheme.axaml'), encoding='utf-8')
p = root / 'src/MedicalRecord.Desktop/MedicalRecord.Desktop.csproj'
p.write_text(p.read_text(encoding='utf-8').replace('<Version>0.4.0</Version>', '<Version>0.4.1</Version>'), encoding='utf-8')

p = root / 'src/MedicalRecord.Api/Endpoints/ScheduleEndpoints.cs'
s = p.read_text(encoding='utf-8').replace('SingleAsync(x=>x.Id=request.PatientId,ct)', 'SingleAsync(x=>x.Id==request.PatientId,ct)').replace('details=item.Status', 'details:item.Status')
p.write_text(s, encoding='utf-8')
for rel in ['src/MedicalRecord.Api/Endpoints/PapEndpoints.cs', 'src/MedicalRecord.Api/Endpoints/DocumentEndpoints.cs']:
    p = root / rel
    p.write_text(p.read_text(encoding='utf-8').replace('details=', 'details:'), encoding='utf-8')

# macOS Development artifacts are intentionally unsigned. Trusted Production alone uses
# Developer ID, hardened runtime, notarization and stapling.
p = root / 'packaging/macos/build-installer.sh'
s = p.read_text(encoding='utf-8')
s = s.replace('APP="$OUT/Medical Record 2026-$RID.app"', 'APP="$OUT/Medical Record 2026.app"')
start = s.index('sign_native(){')
end_marker = 'codesign --verify --strict --verbose=2 "$APP"\n'
end = s.index(end_marker, start) + len(end_marker)
replacement = '''if [[ "$RELEASE_CHANNEL" == "Production" ]]; then
  while IFS= read -r -d '' f; do
    if [[ "$f" != "$APP/Contents/MacOS/MedicalRecord2026" ]] && file "$f" | grep -q 'Mach-O'; then
      codesign --force --timestamp --options runtime --sign "$APP_IDENTITY" "$f"
      codesign --verify --strict --verbose=1 "$f"
    fi
  done < <(find "$APP/Contents" -type f -print0)
  codesign --force --timestamp --options runtime --entitlements "$ENTITLEMENTS" --sign "$APP_IDENTITY" "$APP"
  codesign --verify --strict --verbose=2 "$APP"
else
  echo 'Development app bundle intentionally unsigned; trusted signing is Production-only.'
fi
'''
s = s[:start] + replacement + s[end:]
p.write_text(s, encoding='utf-8')

p = root / 'packaging/macos/test-installer.sh'
s = p.read_text(encoding='utf-8')
s = s.replace('"$APP/Contents/MacOS/MedicalRecord2026" --self-test\ncodesign --verify --strict --verbose=2 "$APP"\n\nif [[ "$CHANNEL" == Production ]]; then', '"$APP/Contents/MacOS/MedicalRecord2026" --self-test\n\nif [[ "$CHANNEL" == Production ]]; then\n  codesign --verify --strict --verbose=2 "$APP"')
s = s.replace('codesign --verify --strict --verbose=2 "$MOUNT/Medical Record 2026.app"\nhdiutil detach "$MOUNT"', 'if [[ "$CHANNEL" == Production ]]; then codesign --verify --strict --verbose=2 "$MOUNT/Medical Record 2026.app"; fi\nhdiutil detach "$MOUNT"')
p.write_text(s, encoding='utf-8')

# Windows: WinExe can leave LASTEXITCODE unset in pwsh; inspect the started process directly.
p = root / 'packaging/windows/test-installer.ps1'
s = p.read_text(encoding='utf-8')
s = s.replace('& $exe --self-test\nif($LASTEXITCODE -ne 0){throw "Installed application self-test failed with $LASTEXITCODE."}', '$selfTest=Start-Process -FilePath $exe -ArgumentList @("--self-test") -Wait -PassThru\nif($selfTest.ExitCode -ne 0){throw "Installed application self-test failed with $($selfTest.ExitCode)."}')
p.write_text(s, encoding='utf-8')

print('RC 0.4.1 compile/installer patch applied')
