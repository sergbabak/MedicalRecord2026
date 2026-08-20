from pathlib import Path
import sys

root = Path(sys.argv[1] if len(sys.argv) > 1 else 'work/MedicalRecord2026')
if not root.exists():
    raise SystemExit(f'RC source root not found: {root}')

# RC 0.4.1 was authored with runtime bindings; Avalonia 12 attempted to compile them.
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
s = p.read_text(encoding='utf-8').replace('avares://MedicalRecord.Desktop/Styles/ClinicalTheme.axaml', 'avares://MedicalRecord2026/Styles/ClinicalTheme.axaml')
p.write_text(s, encoding='utf-8')

p = root / 'src/MedicalRecord.Desktop/MedicalRecord.Desktop.csproj'
s = p.read_text(encoding='utf-8').replace('<Version>0.4.0</Version>', '<Version>0.4.1</Version>')
p.write_text(s, encoding='utf-8')

p = root / 'src/MedicalRecord.Api/Endpoints/ScheduleEndpoints.cs'
s = p.read_text(encoding='utf-8').replace('SingleAsync(x=>x.Id=request.PatientId,ct)', 'SingleAsync(x=>x.Id==request.PatientId,ct)').replace('details=item.Status', 'details:item.Status')
p.write_text(s, encoding='utf-8')

for rel in ['src/MedicalRecord.Api/Endpoints/PapEndpoints.cs', 'src/MedicalRecord.Api/Endpoints/DocumentEndpoints.cs']:
    p = root / rel
    p.write_text(p.read_text(encoding='utf-8').replace('details=', 'details:'), encoding='utf-8')

# Development-only macOS signing: sign the complete bundle ad-hoc in one pass.
# Production path intentionally stays strict: nested Mach-O first, then Developer ID bundle signing.
p = root / 'packaging/macos/build-installer.sh'
s = p.read_text(encoding='utf-8')
old = '''sign_native(){ local target="$1"; if [[ "$APP_IDENTITY" == "-" ]]; then codesign --force --sign - "$target"; else codesign --force --timestamp --options runtime --sign "$APP_IDENTITY" "$target"; fi; }
while IFS= read -r -d '' f; do if file "$f" | grep -q 'Mach-O'; then sign_native "$f"; codesign --verify --strict --verbose=1 "$f"; fi; done < <(find "$APP/Contents" -type f -print0)
if [[ "$APP_IDENTITY" == "-" ]]; then codesign --force --entitlements "$ENTITLEMENTS" --sign - "$APP"; else codesign --force --timestamp --options runtime --entitlements "$ENTITLEMENTS" --sign "$APP_IDENTITY" "$APP"; fi
codesign --verify --strict --verbose=2 "$APP"
'''
new = '''if [[ "$APP_IDENTITY" == "-" ]]; then
  codesign --force --deep --entitlements "$ENTITLEMENTS" --sign - "$APP"
else
  while IFS= read -r -d '' f; do
    if [[ "$f" != "$APP/Contents/MacOS/MedicalRecord2026" ]] && file "$f" | grep -q 'Mach-O'; then
      codesign --force --timestamp --options runtime --sign "$APP_IDENTITY" "$f"
      codesign --verify --strict --verbose=1 "$f"
    fi
  done < <(find "$APP/Contents" -type f -print0)
  codesign --force --timestamp --options runtime --entitlements "$ENTITLEMENTS" --sign "$APP_IDENTITY" "$APP"
fi
codesign --verify --strict --verbose=2 "$APP"
'''
if old not in s:
    raise SystemExit('Expected macOS signing block not found')
p.write_text(s.replace(old, new), encoding='utf-8')

print('RC 0.4.1 compile/packaging patch applied')
