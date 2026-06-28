#!/usr/bin/env python3
"""Splice a freshly esbuild-compiled bundle into the single big <script>
block of docs/exhibits/stakeholder-network.html (the first <script>...</script>
pair after <div id="root">; the second <script> later in the file is an
unrelated inline error-recovery handler and must NOT be touched).

Run after scripts/189 has rewritten the .jsx and you've compiled it with
esbuild.

IMPORTANT: stakeholder-network.jsx only exports the component
(`export default function StakeholderNetwork()`) -- it has no mount call.
esbuild must be pointed at a separate entry file that imports it and calls
ReactDOM.createRoot(...).render(...), e.g.:

    cat > /tmp/sn_build/entry.jsx <<'EOF'
    import React from "react";
    import { createRoot } from "react-dom/client";
    import StakeholderNetwork from "<absolute-path-to>/docs/exhibits/stakeholder-network.jsx";
    createRoot(document.getElementById("root")).render(<StakeholderNetwork />);
    EOF
    NODE_PATH=/tmp/sn_build/node_modules /tmp/sn_build/node_modules/.bin/esbuild \
      /tmp/sn_build/entry.jsx --bundle --minify --format=iife --charset=utf8 \
      --define:process.env.NODE_ENV='"production"' --jsx=automatic --legal-comments=eof \
      --outfile=/tmp/sn_build/bundle.js

Bundling stakeholder-network.jsx directly (no entry wrapper) compiles
without error but never renders anything -- the page silently shows the
<noscript>-style nojs fallback forever, which looks exactly like "JavaScript
isn't running" in the browser.

    .venv312/bin/python scripts/191_splice_stakeholder_bundle.py /tmp/sn_build/bundle.js
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
HTML = ROOT / "docs" / "exhibits" / "stakeholder-network.html"


def main(bundle_path: str) -> None:
    bundle = Path(bundle_path).read_text(encoding="utf-8").strip()
    html = HTML.read_text(encoding="utf-8")

    pattern = re.compile(r"(<script>\n)(.*?)(\n</script>)", re.DOTALL)
    matches = list(pattern.finditer(html))
    if len(matches) < 1:
        print("ERROR: no <script> block found", file=sys.stderr)
        sys.exit(1)

    m = matches[0]
    if "ownerless_decree" not in m.group(2) and "react" not in m.group(2).lower():
        print("WARNING: first <script> block doesn't look like the React "
              "bundle -- check by hand before trusting this splice.",
              file=sys.stderr)

    new_html = html[:m.start(2)] + bundle + html[m.end(2):]
    HTML.write_text(new_html, encoding="utf-8")
    print(f"Spliced {len(bundle):,} bytes into {HTML} (replaced "
          f"{m.end(2) - m.start(2):,} bytes)")
    print("Now: open the file in a browser and visually verify the graph "
          "renders (node/edge counts, judge tier) before committing.")


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print(__doc__)
        sys.exit(1)
    main(sys.argv[1])
