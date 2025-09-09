#!/usr/bin/env python3
"""
validate_cards.py

Usage:
  python validate_cards.py cards.json
  python validate_cards.py cards.json --fix
  python validate_cards.py cards.json --fix --out fixed_cards.json
  python validate_cards.py cards.json --report report.json

This script validates the cards JSON schema and suggests (and optionally applies)
safe fixes for common mistakes (case, typos, booleans-as-strings, category hyphenation).
"""

import json
import sys
import argparse
import re
from datetime import datetime
from difflib import get_close_matches
from copy import deepcopy
from pathlib import Path

ALLOWED_DIFFICULTIES = ["easy", "medium", "hard"]
ALLOWED_USEFULNESS = ["useful", "dangerous", "information"]
ID_RE = re.compile(r"^[a-z0-9\-\._]+$")
ISO8601_RE = re.compile(r"^\d{4}-\d{2}-\d{2}(?:[Tt ]\d{2}:\d{2}:\d{2}(?:\.\d+)?(?:Z|[+\-]\d{2}:\d{2})?)?$")

COLOR = {
  "red": "\033[31m", "green": "\033[32m", "yellow": "\033[33m", "blue": "\033[34m", "reset": "\033[0m"
}

def color(text, col):
    return f"{COLOR.get(col,'')}{text}{COLOR['reset']}"

def load_json(path):
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except json.JSONDecodeError as e:
        print(color(f"JSON parse error: {e}", "red"))
        sys.exit(2)
    except FileNotFoundError:
        print(color(f"File not found: {path}", "red"))
        sys.exit(2)

def is_bool_like(v):
    if isinstance(v, bool): return True
    if isinstance(v, str) and v.lower() in ("true","false","yes","no","0","1"): return True
    return False

def to_bool(v):
    if isinstance(v, bool): return v
    s = str(v).strip().lower()
    return s in ("true","yes","1")

def suggest_from_list(value, choices):
    if not isinstance(value, str): return None
    val = value.strip().lower()
    if val in choices: return val
    # fuzzy match
    matches = get_close_matches(val, choices, n=1, cutoff=0.6)
    return matches[0] if matches else None

def fix_category_name(cat):
    # convert spaces to hyphens, lowercase, strip punctuation edges
    if not isinstance(cat, str): return cat
    c = cat.strip().lower()
    c = re.sub(r"\s+", "-", c)
    return c

def check_iso8601(s):
    if not isinstance(s, str): return False
    if ISO8601_RE.match(s): 
        # try parsing loosely
        try:
            # accept simple date or full datetime
            if "t" in s.lower() or " " in s:
                datetime.fromisoformat(s.replace("Z","+00:00"))
            else:
                datetime.fromisoformat(s)
            return True
        except Exception:
            return False
    return False

def validate_cards(cards, apply_fixes=False):
    errors = []
    suggestions = []
    fixed = deepcopy(cards) if apply_fixes else None

    if not isinstance(cards, list):
        errors.append({"loc": [], "err": "top_level", "msg": "Top-level JSON must be an array of card objects."})
        return errors, suggestions, fixed

    seen_ids = {}
    categories_seen = {}

    for idx, c in enumerate(cards):
        loc = f"cards[{idx}]"
        if not isinstance(c, dict):
            errors.append({"loc":[loc], "err":"not_object", "msg":"Card entry must be a JSON object."})
            continue

        # id
        cid = c.get("id")
        if not cid or not isinstance(cid, str) or cid.strip()=="":
            errors.append({"loc":[loc,"id"], "err":"missing_id", "msg":"Missing or empty 'id' (recommended pattern: rt-0001)."})
        else:
            if not ID_RE.match(cid):
                # suggest sanitized id
                suggested = re.sub(r"[^a-z0-9\-\._]", "-", cid.strip().lower())
                suggestions.append({"loc":[loc,"id"], "msg":f"id contains disallowed chars. Suggested id: '{suggested}'"})
                if apply_fixes:
                    fixed[idx]["id"] = suggested
                    suggestions[-1]["applied"] = True
            if cid in seen_ids:
                errors.append({"loc":[loc,"id"], "err":"duplicate_id", "msg":f"Duplicate id '{cid}' also at {seen_ids[cid]}"})
            else:
                seen_ids[cid] = loc

        # question
        q = c.get("question")
        if not q or not isinstance(q, str) or q.strip()=="":
            errors.append({"loc":[loc,"question"], "err":"missing_question", "msg":"Missing or empty 'question'."})

        # answer
        a = c.get("answer")
        if not a or not isinstance(a, str) or a.strip()=="":
            errors.append({"loc":[loc,"answer"], "err":"missing_answer", "msg":"Missing or empty 'answer'."})

        # hints
        if "hints" in c and c["hints"] is not None:
            if not isinstance(c["hints"], list):
                errors.append({"loc":[loc,"hints"], "err":"hints_not_array", "msg":"'hints' must be an array of strings."})
            else:
                for j, h in enumerate(c["hints"]):
                    if not isinstance(h, str):
                        errors.append({"loc":[loc,"hints",j], "err":"hint_not_string", "msg":"Each hint must be a string."})

        # categories
        if "categories" in c and c["categories"] is not None:
            if not isinstance(c["categories"], list):
                errors.append({"loc":[loc,"categories"], "err":"categories_not_array", "msg":"'categories' must be an array of strings."})
            else:
                fixed_cat_list = []
                for j, cat in enumerate(c["categories"]):
                    if not isinstance(cat, str):
                        errors.append({"loc":[loc,"categories",j], "err":"category_not_string", "msg":"Each category must be a string."})
                        fixed_cat_list.append(cat)
                    else:
                        # detect spaces and inconsistent formatting
                        if " " in cat:
                            suggestions.append({"loc":[loc,"categories",j], "msg":f"Category '{cat}' contains spaces; consider hyphenation (e.g. 'privilege-escalation')."})
                            if apply_fixes:
                                fixed_val = fix_category_name(cat)
                                fixed_cat_list.append(fixed_val)
                                suggestions[-1]["applied"] = True
                            else:
                                fixed_cat_list.append(cat)
                        else:
                            fixed_cat_list.append(cat.strip().lower())

                    # collect for global similarity checks
                    if isinstance(cat, str):
                        categories_seen.setdefault(cat.strip().lower(), []).append(loc)

                if apply_fixes:
                    fixed[idx]["categories"] = fixed_cat_list

        # difficulty
        if "difficulty" not in c or c["difficulty"] is None:
            suggestions.append({"loc":[loc,"difficulty"], "msg":"missing 'difficulty' — recommended value: 'medium' (or easy/medium/hard)."})
            if apply_fixes: fixed[idx]["difficulty"] = "medium"
        else:
            diff = c["difficulty"]
            if not isinstance(diff, str):
                errors.append({"loc":[loc,"difficulty"], "err":"difficulty_not_string", "msg":"'difficulty' must be a string: easy, medium, or hard."})
            else:
                val = diff.strip().lower()
                if val not in ALLOWED_DIFFICULTIES:
                    suggestion = suggest_from_list(val, ALLOWED_DIFFICULTIES)
                    if suggestion:
                        suggestions.append({"loc":[loc,"difficulty"], "msg":f"Unknown difficulty '{diff}'. Suggest '{suggestion}'."})
                        if apply_fixes:
                            fixed[idx]["difficulty"] = suggestion
                            suggestions[-1]["applied"] = True
                    else:
                        errors.append({"loc":[loc,"difficulty"], "err":"invalid_difficulty", "msg":f"Invalid difficulty '{diff}'. Allowed: {ALLOWED_DIFFICULTIES}."})

        # grasped
        if "grasped" in c:
            g = c["grasped"]
            if not is_bool_like(g):
                # common error: "false" string
                if isinstance(g, str) and g.strip().lower() in ("true","false","yes","no","0","1"):
                    suggestions.append({"loc":[loc,"grasped"], "msg":f"'grasped' looks string-like ('{g}'). Consider boolean true/false."})
                    if apply_fixes:
                        fixed[idx]["grasped"] = to_bool(g)
                        suggestions[-1]["applied"] = True
                else:
                    errors.append({"loc":[loc,"grasped"], "err":"grasped_not_bool", "msg":"'grasped' must be a boolean (true/false)."})
        # usefulness
        if "usefulness" in c and c["usefulness"] is not None:
            u = c["usefulness"]
            if not isinstance(u, str):
                errors.append({"loc":[loc,"usefulness"], "err":"usefulness_not_string", "msg":"'usefulness' must be a string if present."})
            else:
                val = u.strip().lower()
                if val not in ALLOWED_USEFULNESS:
                    suggestion = suggest_from_list(val, ALLOWED_USEFULNESS)
                    if suggestion:
                        suggestions.append({"loc":[loc,"usefulness"], "msg":f"Unknown usefulness '{u}'. Suggest '{suggestion}'."})
                        if apply_fixes:
                            fixed[idx]["usefulness"] = suggestion
                            suggestions[-1]["applied"] = True
                    else:
                        errors.append({"loc":[loc,"usefulness"], "err":"invalid_usefulness", "msg":f"Invalid usefulness '{u}'. Allowed: {ALLOWED_USEFULNESS}."})

        # created_at
        if "created_at" in c and c["created_at"] is not None:
            ca = c["created_at"]
            if not isinstance(ca, str) or not check_iso8601(ca):
                suggestions.append({"loc":[loc,"created_at"], "msg":f"'created_at' looks malformed ('{ca}'). Suggest ISO8601 'YYYY-MM-DD' or full timestamp."})
                # do not auto-fix unless it's a plain date like YYYY-MM-DD
                if apply_fixes and isinstance(ca, str):
                    m = re.match(r"^(\d{4})[-/](\d{2})[-/](\d{2})$", ca.strip())
                    if m:
                        fixed_val = f"{m.group(1)}-{m.group(2)}-{m.group(3)}"
                        fixed[idx]["created_at"] = fixed_val
                        suggestions[-1]["applied"] = True

        # meta
        if "meta" in c and c["meta"] is not None and not isinstance(c["meta"], dict):
            errors.append({"loc":[loc,"meta"], "err":"meta_not_object", "msg":"'meta' must be an object if present."})

    # global category similarity suggestions (typos / near duplicates)
    category_list = list(categories_seen.keys())
    for i, a in enumerate(category_list):
        for b in category_list[i+1:]:
            if a != b:
                # consider them similar if difflib says so
                matches = get_close_matches(a, [b], n=1, cutoff=0.85)
                if matches:
                    suggestions.append({"loc":[],"msg":f"Categories '{a}' and '{b}' look similar. Consider normalizing (e.g., use '{a}' consistently). Occurrences: {categories_seen[a][:3]}... vs {categories_seen[b][:3]}..."})

    return errors, suggestions, fixed

def main():
    parser = argparse.ArgumentParser(description="Validate cards.json and suggest fixes.")
    parser.add_argument("file", help="Path to cards.json")
    parser.add_argument("--fix", action="store_true", help="Apply safe fixes and write output")
    parser.add_argument("--out", help="Output path for fixed JSON (defaults to overwrite with .bak)")
    parser.add_argument("--report", help="Write machine-readable JSON report of errors+suggestions")
    args = parser.parse_args()

    path = Path(args.file)
    cards = load_json(path)

    errors, suggestions, fixed = validate_cards(cards, apply_fixes=args.fix)

    # human-friendly summary
    if not errors and not suggestions:
        print(color("OK — no problems found.", "green"))
        if args.report:
            with open(args.report, "w", encoding="utf-8") as f:
                json.dump({"errors": [], "suggestions": []}, f, indent=2)
        return 0

    print(color("Validation Summary:", "blue"))
    if errors:
        print(color(f"\nErrors ({len(errors)}):", "red"))
        for e in errors:
            loc = " > ".join(e.get("loc", [])) if e.get("loc") else "<root>"
            print(color(f"- {loc}: {e['msg']}", "red"))

    if suggestions:
        print(color(f"\nSuggestions ({len(suggestions)}):", "yellow"))
        for s in suggestions:
            loc = " > ".join(s.get("loc", [])) if s.get("loc") else "<global>"
            applied = s.get("applied", False)
            tag = color("[applied]" , "green") if applied else ""
            print(color(f"- {loc}: {s['msg']} {tag}", "yellow"))

    if args.fix:
        out_path = Path(args.out) if args.out else path
        # make backup if overwriting
        if out_path.resolve() == path.resolve():
            bak = path.with_suffix(path.suffix + ".bak")
            path.rename(bak)
            print(color(f"\nOriginal backed up to: {bak}", "blue"))
            out_path = path
        with open(out_path, "w", encoding="utf-8") as f:
            json.dump(fixed, f, indent=2, ensure_ascii=False)
        print(color(f"Fixed JSON written to: {out_path}", "green"))
    if args.report:
        with open(args.report, "w", encoding="utf-8") as f:
            json.dump({"errors": errors, "suggestions": suggestions}, f, indent=2, ensure_ascii=False)
        print(color(f"Report written to: {args.report}", "blue"))

    # exit non-zero if errors exist
    return 1 if errors else 0

if __name__ == "__main__":
    rc = main()
    sys.exit(rc)
