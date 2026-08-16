from pathlib import Path
import sys

if len(sys.argv) != 2:
    raise SystemExit("usage: apply_pass13.py <xray-engine-root>")

root = Path(sys.argv[1])
path = root / "src/xrGame/UIGameCustom.cpp"
text = path.read_text(encoding="utf-8")


def replace_exact(old: str, new: str, expected: int = 1) -> None:
    global text
    count = text.count(old)
    if count != expected:
        raise RuntimeError(
            f"{path}: expected {expected} exact match(es), found {count}. "
            "Pinned source no longer matches Pass 13."
        )
    text = text.replace(old, new)


# ui_lock is defined by HUDManager.cpp and already guards RenderUI().
replace_exact(
    '#include "xrEngine/x_ray.h"\n',
    '#include "xrEngine/x_ray.h"\n\n// GCS Pass 13: guard the actual CUIGameCustom ownership boundary, not only known callers.\nextern xrCriticalSection ui_lock;\n',
)

# Any caller that destroys the in-game UI must synchronize with RenderUI().
# Windows CRITICAL_SECTION is recursive, so this remains safe when Pass 11 callers
# already hold ui_lock.
replace_exact(
    'void CUIGameCustom::UnLoad()\n{\n\txr_delete(MsgConfig);\n',
    'void CUIGameCustom::UnLoad()\n{\n\t// GCS Pass 13: prevent UIMainIngameWnd destruction while the render thread is using it.\n\txrCriticalSectionGuard guard(&ui_lock);\n\txr_delete(MsgConfig);\n',
)

# Load/rebuild owns the same pointers and must share the lifetime boundary too.
replace_exact(
    'void CUIGameCustom::Load()\n{\n\tif (!g_pGameLevel)\n',
    'void CUIGameCustom::Load()\n{\n\t// GCS Pass 13: serialize UI construction/rebuild with RenderUI().\n\txrCriticalSectionGuard guard(&ui_lock);\n\tif (!g_pGameLevel)\n',
)

path.write_text(text, encoding="utf-8")
print("GCS Pass 13 applied: CUIGameCustom Load/UnLoad now share the RenderUI lifetime lock.")
