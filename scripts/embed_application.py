"""Embed app/app.py into the CloudFormation EC2 user data."""

from __future__ import annotations

import base64
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
template = ROOT / "infra" / "template.yaml"
source = ROOT / "app" / "app.py"
text = template.read_text(encoding="utf-8")
encoded = base64.b64encode(source.read_bytes()).decode("ascii")
payload = re.compile(
    r"            APP_PAYLOAD='[^']*'\r?\n"
    r"            printf '%s' \"\$APP_PAYLOAD\" \| base64 -d > /opt/scalelab/app.py"
)
replacement = (
    f"            APP_PAYLOAD='{encoded}'\n"
    "            printf '%s' \"$APP_PAYLOAD\" | base64 -d > /opt/scalelab/app.py"
)
updated, count = payload.subn(replacement, text, count=1)
if count == 0:
    old_block = re.compile(
        r"            cat > /opt/scalelab/app.py.b64 <<'APP_B64'\r?\n"
        r"            [A-Za-z0-9+/=]+\r?\n"
        r"            APP_B64\r?\n"
        r"            base64 -d /opt/scalelab/app.py.b64 > /opt/scalelab/app.py"
    )
    updated, count = old_block.subn(replacement, text, count=1)
if count != 1:
    raise SystemExit("Expected exactly one EC2 application payload in infra/template.yaml")
template.write_text(updated, encoding="utf-8")
print("Embedded app/app.py into the EC2 launch template user data.")
