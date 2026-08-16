from pathlib import Path
import sys

if len(sys.argv) != 2:
    raise SystemExit("usage: apply_pass14.py <xray-engine-root>")

root = Path(sys.argv[1])
main_cpp = root / "src/xrGame/ui/UIMainIngameWnd.cpp"
game_cpp = root / "src/xrGame/UIGameCustom.cpp"


def replace_exact(path: Path, old: str, new: str, expected: int = 1) -> None:
    text = path.read_text(encoding="utf-8")
    count = text.count(old)
    if count != expected:
        raise RuntimeError(
            f"{path}: expected {expected} exact match(es), found {count}. "
            "Pinned source no longer matches Pass 14."
        )
    path.write_text(text.replace(old, new), encoding="utf-8")


# The dump proves CUIGameCustom can retain a non-null CUIMainIngameWnd pointer
# after the object's CUIWindow::csUi has already been destroyed. That means the
# object can be destroyed through a reference other than CUIGameCustom's owning
# member. Make the object's own destructor authoritative: synchronize with
# RenderUI and invalidate the owner's pointer before releasing the lifetime lock.
replace_exact(
    main_cpp,
    '#include "../UIGameSP.h"\n',
    '#include "../UIGameSP.h"\n#include "../UIGameCustom.h"\n',
)

replace_exact(
    main_cpp,
    'using namespace InventoryUtilities;\n',
    'using namespace InventoryUtilities;\n\n// GCS Pass 14: shared HUD lifetime/render boundary from HUDManager.cpp.\nextern xrCriticalSection ui_lock;\n',
)

replace_exact(
    main_cpp,
    'CUIMainIngameWnd::~CUIMainIngameWnd()\n'
    '{\n'
    '\tDestroyFlashingIcons();\n',
    'CUIMainIngameWnd::~CUIMainIngameWnd()\n'
    '{\n'
    '\t// GCS Pass 14: any destruction path must invalidate the owner before\n'
    '\t// CUIWindow base teardown destroys csUi. Windows CRITICAL_SECTION is\n'
    '\t// recursive, so this is safe when Pass 11/13 already hold ui_lock.\n'
    '\txrCriticalSectionGuard lifetime_guard(&ui_lock);\n'
    '\tif (CUIGameCustom* game_ui = CurrentGameUI(); game_ui && game_ui->UIMainIngameWnd == this)\n'
    '\t{\n'
    '\t\tgame_ui->UIMainIngameWnd = nullptr;\n'
    '\t\tMsg("[GCS Pass14] invalidated CUIMainIngameWnd owner pointer before destruction: %p", this);\n'
    '\t}\n'
    '\n'
    '\tDestroyFlashingIcons();\n',
)

# Once the destructor invalidates the owner pointer, both frame update and render
# must tolerate the short teardown/rebuild window instead of calling through null.
replace_exact(
    game_cpp,
    '\tif (GameIndicatorsShown() && psHUD_Flags.is(HUD_DRAW | HUD_DRAW_RT))\n'
    '\t\tUIMainIngameWnd->Update();\n',
    '\tif (UIMainIngameWnd && GameIndicatorsShown() && psHUD_Flags.is(HUD_DRAW | HUD_DRAW_RT))\n'
    '\t\tUIMainIngameWnd->Update();\n',
)

replace_exact(
    game_cpp,
    '\t\tif (GameIndicatorsShown() && psHUD_Flags.is(HUD_DRAW | HUD_DRAW_RT))\n'
    '\t\t\tUIMainIngameWnd->Draw();\n',
    '\t\tif (UIMainIngameWnd && GameIndicatorsShown() && psHUD_Flags.is(HUD_DRAW | HUD_DRAW_RT))\n'
    '\t\t\tUIMainIngameWnd->Draw();\n',
)

print("GCS Pass 14 applied: direct CUIMainIngameWnd destruction invalidates owner before base csUi teardown.")
