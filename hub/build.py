"""Build the Benchmark Hub page: hub_template.html + the current dashboard template."""
import json, pathlib, sys
from benchmark.report import _HTML_TEMPLATE

def build(out_path):
    src = pathlib.Path(__file__).with_name("hub_template.html").read_text(encoding="utf-8")
    dumped = json.dumps(_HTML_TEMPLATE).replace("</", "<\\/")
    html = src.replace("__DASH_TEMPLATE__", dumped)
    pathlib.Path(out_path).write_text(html, encoding="utf-8")
    return len(html)

if __name__ == "__main__":
    print(build(sys.argv[1]), "bytes")
