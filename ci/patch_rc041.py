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

print('RC 0.4.1 compile patch applied')
