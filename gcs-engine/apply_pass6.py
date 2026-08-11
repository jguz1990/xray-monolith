from pathlib import Path
import sys

if len(sys.argv) != 2:
    raise SystemExit("usage: apply_pass6.py <xray-engine-root>")

root = Path(sys.argv[1])
cells = root / "src/xrGame/ui/UICellCustomItems.cpp"


def replace_exact(path: Path, old: str, new: str, expected: int = 1) -> None:
    text = path.read_text(encoding="utf-8")
    count = text.count(old)
    if count != expected:
        raise RuntimeError(
            f"{path}: expected {expected} exact match(es), found {count}. "
            "Pinned source no longer matches the Pass 6 transform."
        )
    path.write_text(text.replace(old, new), encoding="utf-8")


# The helper check only needs to know whether a helper child exists. Avoid
# scanning the entire stack once a match is found.
replace_exact(
    cells,
    "bool CUIInventoryCellItem::IsHelperOrHasHelperChild()\n"
    "{\n"
    "\treturn std::count_if(m_childs.begin(), m_childs.end(), detail::is_helper_pred()) > 0 || IsHelper();\n"
    "}\n",
    "bool CUIInventoryCellItem::IsHelperOrHasHelperChild()\n"
    "{\n"
    "\treturn IsHelper() || std::find_if(m_childs.begin(), m_childs.end(), detail::is_helper_pred()) != m_childs.end();\n"
    "}\n",
)

# Layered inventory icons are static for the overwhelming majority of frames.
# Upstream re-reads config values and re-lays out every icon layer every UI
# update. Re-run that layout only if the parent cell's heading/geometry changes
# (or the icon has not yet been created). Color propagation already happens in
# CUIInventoryCellItem::SetTextureColor, so do not write the same layer color
# every frame either.
old_update = """void CUIInventoryCellItem::Update()
{
\tbool b = Heading();
\tinherited::Update();

\tinherited::UpdateConditionProgressBar(); //Alundaio
\tUpdateItemText();

\tu32 color = GetTextureColor();
\tif (IsHelper() && !ChildsCount())
\t{
\t\tcolor = 0xbbbbbbbb;
\t}
\telse if (IsHelperOrHasHelperChild())
\t{
\t\tcolor = 0xffffffff;
\t}

\tSetTextureColor(color);

\tfor (xr_vector<SIconLayer*>::iterator it = m_layers.begin(); m_layers.end() != it; ++it)
\t{
\t\t(*it)->m_icon = InitLayer((*it)->m_icon, (*it)->m_name, (*it)->offset, Heading(), (*it)->m_scale);
\t\t(*it)->m_icon->SetTextureColor(color);
\t}
}
"""
new_update = """void CUIInventoryCellItem::Update()
{
\tconst bool heading_before = Heading();
\tconst Fvector2 size_before = GetWndSize();
\tinherited::Update();

\tinherited::UpdateConditionProgressBar(); //Alundaio
\tUpdateItemText();

\tconst bool layout_changed =
\t\t(heading_before != Heading()) ||
\t\t!fsimilar(size_before.x, GetWidth()) ||
\t\t!fsimilar(size_before.y, GetHeight());

\tconst u32 current_color = GetTextureColor();
\tu32 color = current_color;
\tif (IsHelper() && !ChildsCount())
\t{
\t\tcolor = 0xbbbbbbbb;
\t}
\telse if (IsHelperOrHasHelperChild())
\t{
\t\tcolor = 0xffffffff;
\t}

\tif (color != current_color)
\t\tSetTextureColor(color);

\tfor (xr_vector<SIconLayer*>::iterator it = m_layers.begin(); m_layers.end() != it; ++it)
\t{
\t\tif (!(*it)->m_icon || layout_changed)
\t\t\t(*it)->m_icon = InitLayer((*it)->m_icon, (*it)->m_name, (*it)->offset, Heading(), (*it)->m_scale);
\t}
}
"""
replace_exact(cells, old_update, new_update)

print("GCS Pass 6 source transforms applied successfully (inventory cell layered-icon update reduction).")
