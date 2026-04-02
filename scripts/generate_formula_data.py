#!/usr/bin/env python3
"""Generate formula_data.py from registry formula YAMLs.

Reads all formula YAML files and outputs a Python module with a
FORMULAS list that can be imported by the Worker.

Usage:
    python generate_formula_data.py --input ./stacks --output src/registry/formula_data.py
"""

import argparse
import pathlib
import json

import yaml


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", required=True, help="Path to stacks/ directory")
    parser.add_argument("--output", required=True, help="Output Python file path")
    args = parser.parse_args()

    stacks_dir = pathlib.Path(args.input)
    formulas = []

    for f in sorted(stacks_dir.rglob("*.yaml")):
        data = yaml.safe_load(f.read_text())
        if data and "name" in data:
            if not data.get("skills"):
                continue
            formulas.append(data)

    formulas.sort(key=lambda f: f.get("name", ""))

    output = pathlib.Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)

    with open(output, "w") as out:
        out.write('"""Auto-generated formula data — do not edit manually."""\n\n')
        out.write(f"FORMULAS = {json.dumps(formulas, indent=2, ensure_ascii=False)}\n")

    print(f"Generated {output} with {len(formulas)} formula(s)")


if __name__ == "__main__":
    main()
