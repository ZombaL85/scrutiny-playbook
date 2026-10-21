#!/usr/bin/env python3
"""Turn Ansible 'fatal:' lines from a log into GitHub Actions error annotations.

The annotation (task name + module msg) is visible in the run summary
without opening the job log.
"""
import json
import re
import sys

ANSI = re.compile(r"\x1b\[[0-9;]*m")
title = sys.argv[1]


def escape(text: str) -> str:
    return text.replace("%", "%25").replace("\r", "%0D").replace("\n", "%0A")


for path in sys.argv[2:]:
    try:
        lines = open(path, encoding="utf-8", errors="replace").read().splitlines()
    except FileNotFoundError:
        continue
    task = "?"
    for raw in lines:
        line = ANSI.sub("", raw)
        if line.startswith("TASK ["):
            task = line.split("[", 1)[1].rsplit("]", 1)[0]
        elif line.startswith(("fatal:", "failed:")):
            detail = line
            if "=> " in line:
                try:
                    res = json.loads(line.split("=> ", 1)[1])
                    parts = [str(res.get(k)) for k in ("msg", "stderr", "module_stderr") if res.get(k)]
                    detail = " | ".join(parts) or detail
                except ValueError:
                    pass
            print(f"::error title={escape(title)}::{escape(f'{task}: {detail}'[:1500])}")
