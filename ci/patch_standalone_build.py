from pathlib import Path
import sys

root = Path(sys.argv[1] if len(sys.argv) > 1 else 'work/MedicalRecord2026')
p = root / 'src/MedicalRecord.Api/Endpoints/BackupEndpoints.cs'
s = p.read_text(encoding='utf-8')
old = 'await ApiSecurity.AuditAsync(db,user,"BACKUP_CREATE","Backup",record.Id.ToString(),http.Connection.RemoteIpAddress?.ToString());'
new = 'await ApiSecurity.AuditAsync(db,user,"BACKUP_CREATE","Backup",record.Id.ToString(),null,details:http.Connection.RemoteIpAddress?.ToString());'
if old in s:
    s = s.replace(old, new)
elif new not in s:
    raise SystemExit('Expected standalone backup audit call not found')
p.write_text(s, encoding='utf-8')
print('Standalone native-build patch applied')
