from pathlib import Path
import sys

if len(sys.argv) != 2:
    raise SystemExit("usage: apply_pass2.py <xray-engine-root>")

root = Path(sys.argv[1])
trade = root / "src/xrGame/ui/UIActorMenuTrade.cpp"
cells = root / "src/xrGame/ui/UICellCustomItems.cpp"


def replace_exact(path: Path, old: str, new: str, expected: int = 1) -> None:
    text = path.read_text(encoding="utf-8")
    count = text.count(old)
    if count != expected:
        raise RuntimeError(f"{path}: expected {expected} exact match(es), found {count}. Pinned source no longer matches the optimization transform.")
    path.write_text(text.replace(old, new), encoding="utf-8")


# Trader eligibility runs for every visible actor item while the trade UI is built.
# Reuse CInventory's maintained cached total instead of walking the trader inventory
# again for every actor item.
replace_exact(
    trade,
    "\tfloat partner_inv_weight = m_pPartnerInvOwner->inventory().CalcTotalWeight();\n",
    "\tfloat partner_inv_weight = m_pPartnerInvOwner->inventory().TotalWeight();\n",
)

# Reuse one parsed actor_menu_item.xml document for all condition-bearing cells.
replace_exact(
    cells,
    "namespace detail\n{\n",
    "namespace\n{\n"
    "\tCUIXml& ActorMenuItemXml()\n"
    "\t{\n"
    "\t\tstatic CUIXml xml;\n"
    "\t\tstatic bool loaded = false;\n"
    "\t\tif (!loaded)\n"
    "\t\t{\n"
    "\t\t\txml.Load(CONFIG_PATH, UI_PATH, \"actor_menu_item.xml\");\n"
    "\t\t\tloaded = true;\n"
    "\t\t}\n"
    "\t\treturn xml;\n"
    "\t}\n"
    "}\n\n"
    "namespace detail\n{\n",
)
replace_exact(
    cells,
    "\tif (condbar)\n\t{\n\t\tCUIXml uiXml;\n\t\tuiXml.Load(CONFIG_PATH, UI_PATH, \"actor_menu_item.xml\");\n\t\tCUIXmlInit::InitProgressBar(uiXml, condbar, 0, m_pConditionState);\n\t}\n",
    "\tif (condbar)\n\t{\n\t\tCUIXmlInit::InitProgressBar(ActorMenuItemXml(), condbar, 0, m_pConditionState);\n\t}\n",
)

print("GCS Pass 2 source transforms applied successfully.")
