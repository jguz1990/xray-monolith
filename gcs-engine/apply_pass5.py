from pathlib import Path
import sys

if len(sys.argv) != 2:
    raise SystemExit("usage: apply_pass5.py <xray-engine-root>")

root = Path(sys.argv[1])
inv = root / "src/xrGame/ui/UIActorMenuInventory.cpp"
trade = root / "src/xrGame/ui/UIActorMenuTrade.cpp"


def replace_exact(path: Path, old: str, new: str, expected: int = 1) -> None:
    text = path.read_text(encoding="utf-8")
    count = text.count(old)
    if count != expected:
        raise RuntimeError(
            f"{path}: expected {expected} exact match(es), found {count}. "
            "Pinned source no longer matches the Pass 5 transform."
        )
    path.write_text(text.replace(old, new), encoding="utf-8")


# Pass 1 hoisted the filter item-count query out of the inventory loops, but each
# item still reparses the same comma-separated kind strings. Parse the selected
# tab's kinds once per filter rebuild and compare against the cached shared_strs.
old_header = (
    "\tconst bool show_all = (0 == xr_strcmp(m_sort_kinds[mode], \"s_all\"));\n"
    "\tconst int kinds = show_all ? 0 : _GetItemCount(m_sort_kinds[mode]);\n"
)
new_header = (
    "\tconst bool show_all = (0 == xr_strcmp(m_sort_kinds[mode], \"s_all\"));\n"
    "\txr_vector<shared_str> filter_kinds;\n"
    "\tif (!show_all)\n"
    "\t{\n"
    "\t\tconst int kinds = _GetItemCount(m_sort_kinds[mode]);\n"
    "\t\tfilter_kinds.reserve(kinds);\n"
    "\t\tfor (int i = 0; i < kinds; ++i)\n"
    "\t\t{\n"
    "\t\t\tstring256 kind;\n"
    "\t\t\t_GetItem(m_sort_kinds[mode], i, kind);\n"
    "\t\t\tfilter_kinds.push_back(kind);\n"
    "\t\t}\n"
    "\t}\n"
)
replace_exact(inv, old_header, new_header, expected=1)
replace_exact(trade, old_header, new_header, expected=2)

old_loop = (
    "\t\t\tfor (int i = 0; i < kinds; i++)\n"
    "\t\t\t{\n"
    "\t\t\t\tstring256 kind;\n"
    "\t\t\t\t_GetItem(m_sort_kinds[mode], i, kind);\n\n"
    "\t\t\t\tif (iitm->m_kind != NULL && iitm->m_kind.equal(kind))\n"
)
new_loop = (
    "\t\t\tfor (const shared_str& kind : filter_kinds)\n"
    "\t\t\t{\n"
    "\t\t\t\tif (iitm->m_kind != NULL && iitm->m_kind.equal(kind))\n"
)
replace_exact(inv, old_loop, new_loop, expected=1)
replace_exact(trade, old_loop, new_loop, expected=2)

print("GCS Pass 5 source transforms applied successfully (cached inventory category parsing).")
