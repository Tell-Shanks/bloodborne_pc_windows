"""Fetch pinned NVIDIA DLSS 4 SDK/runtime, checking every SHA-256 digest."""
from pathlib import Path
import hashlib,json,urllib.request
root=Path(__file__).resolve().parents[1]
manifest=json.loads((root/'tools/dlss_manifest.json').read_text(encoding='utf-8'))
for remote,digest in manifest['files'].items():
    name=Path(remote).name
    target=root/('dlss' if name=='nvngx_dlss.dll' else 'gpu/third_party/dlss-sdk')/name
    if target.exists() and hashlib.sha256(target.read_bytes()).hexdigest()==digest:
        continue
    url=f'https://raw.githubusercontent.com/NVIDIA/DLSS/{manifest["commit"]}/{remote}'
    with urllib.request.urlopen(url,timeout=90) as response: data=response.read()
    if hashlib.sha256(data).hexdigest()!=digest: raise RuntimeError(f'SHA-256 mismatch: {remote}')
    target.parent.mkdir(parents=True,exist_ok=True)
    temporary=target.with_suffix(target.suffix+'.download')
    temporary.write_bytes(data);temporary.replace(target)
print('DLSS 4 SDK/runtime verified; see gpu/third_party/dlss-sdk/LICENSE.txt')
