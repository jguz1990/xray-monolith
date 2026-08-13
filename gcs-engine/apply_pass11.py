from pathlib import Path
import sys

if len(sys.argv) != 2:
    raise SystemExit("usage: apply_pass11.py <xray-engine-root>")

root = Path(sys.argv[1])
hud_cpp = root / "src/xrGame/HUDManager.cpp"


def replace_exact(path: Path, old: str, new: str, expected: int = 1) -> None:
    text = path.read_text(encoding="utf-8")
    count = text.count(old)
    if count != expected:
        raise RuntimeError(
            f"{path}: expected {expected} exact match(es), found {count}. "
            "Pinned source no longer matches the UI Pass 11 transform."
        )
    path.write_text(text.replace(old, new), encoding="utf-8")


# ui_lock already serializes RenderUI() against mt_ui OnFrameMT(). Promote its
# lifetime so HUD construction/destruction and screen-resolution UI rebuilds can
# use the same lock. Without this, UIMainIngameWnd can be deleted while the
# render thread is inside CUIWindow::Draw(), leaving csUi.pmutex dangling.
replace_exact(
    hud_cpp,
    "//--------------------------------------------------------------------\n"
    "CHUDManager::CHUDManager() : pUIGame(NULL), m_pHUDTarget(xr_new<CHUDTarget>()), b_online(false)\n",
    "//--------------------------------------------------------------------\n"
    "// GCS Pass 11: one lock owns the complete UI lifetime/render boundary.\n"
    "xrCriticalSection ui_lock;\n"
    "\n"
    "CHUDManager::CHUDManager() : pUIGame(NULL), m_pHUDTarget(xr_new<CHUDTarget>()), b_online(false)\n",
)

replace_exact(
    hud_cpp,
    "xrCriticalSection ui_lock;\n"
    "extern BOOL mt_TaskManager;\n",
    "extern BOOL mt_TaskManager;\n",
)

# Destruction must wait for any in-flight RenderUI() call before unloading and
# freeing the UI tree.
replace_exact(
    hud_cpp,
    "CHUDManager::~CHUDManager()\n"
    "{\n"
    "\tOnDisconnected();\n"
    "\n"
    "\tif (pUIGame)\n"
    "\t\tpUIGame->UnLoad();\n"
    "\n"
    "\txr_delete(pUIGame);\n"
    "\txr_delete(m_pHUDTarget);\n"
    "}\n",
    "CHUDManager::~CHUDManager()\n"
    "{\n"
    "\tOnDisconnected();\n"
    "\n"
    "\t// GCS Pass 11: do not tear down UI objects while RenderUI owns them.\n"
    "\txrCriticalSectionGuard guard(&ui_lock);\n"
    "\tif (pUIGame)\n"
    "\t\tpUIGame->UnLoad();\n"
    "\n"
    "\txr_delete(pUIGame);\n"
    "\txr_delete(m_pHUDTarget);\n"
    "}\n",
)

# A resolution/device reset performs UnLoad -> Load -> OnConnected while the
# game is online. Hold ui_lock across the entire transaction so rendering cannot
# observe a partially destroyed or partially rebuilt UI tree.
replace_exact(
    hud_cpp,
    "void CHUDManager::OnScreenResolutionChanged()\n"
    "{\n"
    "\tpUIGame->HideShownDialogs();\n",
    "void CHUDManager::OnScreenResolutionChanged()\n"
    "{\n"
    "\t// GCS Pass 11: serialize the complete UI rebuild against RenderUI().\n"
    "\txrCriticalSectionGuard guard(&ui_lock);\n"
    "\tpUIGame->HideShownDialogs();\n",
)

# CHUDManager::Load can replace/attach the game UI during connection setup.
# Serialize it with RenderUI as well; the lock is uncontended during normal
# startup and does not affect per-frame performance.
replace_exact(
    hud_cpp,
    "void CHUDManager::Load()\n"
    "{\n"
    "\tif (!pUIGame)\n",
    "void CHUDManager::Load()\n"
    "{\n"
    "\t// GCS Pass 11: UI creation shares the render lifetime lock.\n"
    "\txrCriticalSectionGuard guard(&ui_lock);\n"
    "\tif (!pUIGame)\n",
)

print("GCS Pass 11 applied: serialized HUD UI load/reload/destruction with RenderUI.")
