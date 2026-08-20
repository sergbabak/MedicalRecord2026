from pathlib import Path
import subprocess, sys

root=Path(sys.argv[1] if len(sys.argv)>1 else 'work/MedicalRecord2026')
if not root.exists(): raise SystemExit(f'Source root not found: {root}')
subprocess.run([sys.executable,str(Path(__file__).with_name('patch_macos_autonomous.py')),str(root)],check=True)

p=root/'packaging/macos/build-installer.sh'
s=p.read_text(encoding='utf-8')
old='''else
  productbuild --component "$APP" /Applications --identifier ru.medicalrecord2026.desktop --version "$VERSION" "$PKG"
fi'''
new='''else
  PKGROOT="$(mktemp -d)"
  mkdir -p "$PKGROOT/Applications"
  cp -R "$APP" "$PKGROOT/Applications/Medical Record 2026.app"
  chmod +x "$PKGROOT/Applications/Medical Record 2026.app/Contents/MacOS/MedicalRecord2026"
  chmod +x "$PKGROOT/Applications/Medical Record 2026.app/Contents/Resources/Server/MedicalRecord.Api"
  pkgbuild --root "$PKGROOT" --identifier ru.medicalrecord2026.desktop --version "$VERSION" "$PKG"
  rm -rf "$PKGROOT"
fi'''
if old not in s: raise SystemExit('Expected Internal productbuild branch not found')
s=s.replace(old,new)
p.write_text(s,encoding='utf-8')
print('Autonomous macOS deterministic PKG root payload applied')
