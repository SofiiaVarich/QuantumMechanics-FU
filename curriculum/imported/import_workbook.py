"""Extract user-supplied formula records and images without guessing equations.

Usage: python curriculum/imported/import_workbook.py /path/to/workbook.xlsx
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import posixpath
import xml.etree.ElementTree as ET
from zipfile import ZipFile

NS = {
    "s": "http://schemas.openxmlformats.org/spreadsheetml/2006/main",
    "d": "http://schemas.openxmlformats.org/drawingml/2006/spreadsheetDrawing",
    "a": "http://schemas.openxmlformats.org/drawingml/2006/main",
    "r": "http://schemas.openxmlformats.org/officeDocument/2006/relationships",
}


def extract(source: Path, destination: Path) -> int:
    destination.mkdir(parents=True, exist_ok=True)
    images = destination / "images"
    images.mkdir(exist_ok=True)
    with ZipFile(source) as archive:
        strings = []
        if "xl/sharedStrings.xml" in archive.namelist():
            strings = [
                "".join(node.itertext())
                for node in ET.fromstring(archive.read("xl/sharedStrings.xml"))
            ]
        relationships = {
            node.attrib["Id"]: node.attrib["Target"]
            for node in ET.fromstring(archive.read("xl/drawings/_rels/drawing1.xml.rels"))
        }
        row_images = {}
        drawing = ET.fromstring(archive.read("xl/drawings/drawing1.xml"))
        for anchor in drawing:
            row = anchor.find("d:from/d:row", NS)
            blip = anchor.find(".//a:blip", NS)
            if row is None or blip is None:
                continue
            target = relationships[blip.attrib[f"{{{NS['r']}}}embed"]]
            member = target.lstrip("/") if target.startswith("/") else posixpath.normpath(
                posixpath.join("xl/drawings", target)
            )
            name = Path(member).name
            (images / name).write_bytes(archive.read(member))
            row_images[int(row.text or "0") + 1] = f"images/{name}"

        records = []
        sheet = ET.fromstring(archive.read("xl/worksheets/sheet1.xml"))
        for row in sheet.findall("s:sheetData/s:row", NS)[1:]:
            values = {}
            for cell in row.findall("s:c", NS):
                column = "".join(c for c in cell.attrib["r"] if c.isalpha())
                value = cell.find("s:v", NS)
                text = value.text or "" if value is not None else ""
                if cell.attrib.get("t") == "s":
                    text = strings[int(text)]
                elif cell.attrib.get("t") == "inlineStr":
                    text = "".join(cell.find("s:is", NS).itertext())
                values[column] = text
            if not values.get("C"):
                continue
            row_number = int(row.attrib["r"])
            records.append({
                "id": f"workbook-row-{row_number}",
                "source_chapter": values.get("A", ""),
                "equation_number": values.get("B", ""),
                "name_de": values.get("C", ""),
                "name": values.get("D", ""),
                "equation_image": row_images.get(row_number),
                "when_to_use": values.get("F", ""),
                "principle": values.get("G", ""),
                "application": values.get("H", ""),
                "lecture_reference": values.get("I", ""),
                "source_type": "user_supplied_workbook",
                "reviewed": False,
            })
        payload = {
            "schema_version": 1,
            "source_file": source.name,
            "status": "staged; not yet enabled in bot",
            "source_note": "Lecture references are supplied by the workbook, not independently verified. Experimental formulas may be textbook-based.",
            "records": records,
        }
        (destination / "formulas.json").write_text(
            json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
        )
    return len(records)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("workbook", type=Path)
    args = parser.parse_args()
    count = extract(args.workbook, Path(__file__).parent)
    print(f"Extracted {count} formula records with equation-image references.")
