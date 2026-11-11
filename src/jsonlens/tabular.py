"""Render query results as CSV or TSV."""

import csv
import io
import json

from .errors import JsonLensError


def rows_from(values, single):
    """Pick the records to tabulate.

    A single (non-wildcard) match that is an array is treated as the list of
    records; otherwise every match is one record.
    """
    if single and len(values) == 1 and isinstance(values[0], list):
        return values[0]
    return values


def _cell(value):
    if value is None:
        return ""
    if value is True:
        return "true"
    if value is False:
        return "false"
    if isinstance(value, (dict, list)):
        return json.dumps(value, ensure_ascii=False, separators=(",", ":"))
    return value


def render(records, fmt):
    """Return CSV/TSV text for RECORDS (all objects, or all non-containers)."""
    if not records:
        raise JsonLensError("nothing to tabulate: the result is an empty list")
    if all(isinstance(r, dict) for r in records):
        header = []
        for rec in records:
            for key in rec:
                if key not in header:
                    header.append(key)
        table = [[_cell(rec.get(k)) for k in header] for rec in records]
    elif not any(isinstance(r, (dict, list)) for r in records):
        header = ["value"]
        table = [[_cell(r)] for r in records]
    else:
        raise JsonLensError(
            f"cannot make {fmt.upper()}: results must be all objects or all plain values"
        )
    out = io.StringIO()
    writer = csv.writer(out, delimiter="\t" if fmt == "tsv" else ",", lineterminator="\n")
    writer.writerow(header)
    writer.writerows(table)
    return out.getvalue()
