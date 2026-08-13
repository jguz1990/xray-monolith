from pathlib import Path
import sys

if len(sys.argv) != 2:
    raise SystemExit("usage: apply_pass10.py <xray-engine-root>")

root = Path(sys.argv[1])
ui_window_cpp = root / "src/xrGame/ui/UIWindow.cpp"


def replace_exact(path: Path, old: str, new: str, expected: int = 1) -> None:
    text = path.read_text(encoding="utf-8")
    count = text.count(old)
    if count != expected:
        raise RuntimeError(
            f"{path}: expected {expected} exact match(es), found {count}. "
            "Pinned source no longer matches the UI Pass 10 transform."
        )
    path.write_text(text.replace(old, new), encoding="utf-8")


# The render thread walks CUIWindow child trees while the game/update thread can
# detach auto-delete children. m_ChildWndToDelete was mutated outside csUi and
# CollectGarbage() swapped it without csUi, creating a real vector data race.
# Protect only the queue transfer/mutation; perform actual deletion after the
# lock is released so child destructors can safely re-enter UI teardown paths.
replace_exact(
    ui_window_cpp,
    "void CUIWindow::CollectGarbage()\n"
    "{\n"
    "    if (m_ChildWndToDelete.empty())\n"
    "        return;\n"
    "\n"
    "    WINDOW_LIST temp;\n"
    "    temp.swap(m_ChildWndToDelete);\n"
    "    for (CUIWindow* pChild : temp)\n"
    "    {\n"
    "        if (pChild)\n"
    "            xr_delete(pChild);\n"
    "    }\n"
    "}\n",
    "void CUIWindow::CollectGarbage()\n"
    "{\n"
    "    WINDOW_LIST temp;\n"
    "    {\n"
    "        // GCS Pass 10: synchronize deferred-delete queue with DetachChild.\n"
    "        xrCriticalSectionGuard guard(csUi);\n"
    "        if (m_ChildWndToDelete.empty())\n"
    "            return;\n"
    "        temp.swap(m_ChildWndToDelete);\n"
    "    }\n"
    "\n"
    "    // Delete outside csUi: destructors may detach/re-enter UI teardown.\n"
    "    for (CUIWindow* pChild : temp)\n"
    "    {\n"
    "        if (pChild)\n"
    "            xr_delete(pChild);\n"
    "    }\n"
    "}\n",
)

replace_exact(
    ui_window_cpp,
    "\tpChild->SetParent(NULL);\n"
    "\n"
    "    if (pChild->IsAutoDelete())\n"
    "        if (std::find(m_ChildWndToDelete.begin(), m_ChildWndToDelete.end(), pChild) == m_ChildWndToDelete.end())\n"
    "            m_ChildWndToDelete.push_back(pChild);\n",
    "\tpChild->SetParent(NULL);\n"
    "\n"
    "    if (pChild->IsAutoDelete())\n"
    "    {\n"
    "        // GCS Pass 10: this vector is also consumed by CollectGarbage().\n"
    "        xrCriticalSectionGuard guard(csUi);\n"
    "        if (std::find(m_ChildWndToDelete.begin(), m_ChildWndToDelete.end(), pChild) == m_ChildWndToDelete.end())\n"
    "            m_ChildWndToDelete.push_back(pChild);\n"
    "    }\n",
)

print("GCS Pass 10 applied: synchronized CUIWindow deferred-delete queue.")
