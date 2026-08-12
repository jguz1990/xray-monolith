from pathlib import Path
import sys

if len(sys.argv) != 2:
    raise SystemExit("usage: apply_pass3.py <xray-engine-root>")

root = Path(sys.argv[1])
actor_menu = root / "src/xrGame/ui/UIActorMenu.cpp"


def replace_exact(path: Path, old: str, new: str, expected: int = 1) -> None:
    text = path.read_text(encoding="utf-8")
    count = text.count(old)
    if count != expected:
        raise RuntimeError(
            f"{path}: expected {expected} exact match(es), found {count}. "
            "Pinned source no longer matches the Pass 3 transform."
        )
    path.write_text(text.replace(old, new), encoding="utf-8")


# The actor state panel performs substantially more work than the visible health
# bars suggest: protection aggregation, booster map inspection, equipment/bone
# lookups and zone-state refreshes. Running that work at render frequency is not
# useful. Keep the UI responsive at 10 Hz while Show(true) still forces an
# immediate refresh on menu open.
replace_exact(
    actor_menu,
    "\t{\n"
    "\t\t// all mode\n"
    "\t\tm_last_time = Device.dwTimeGlobal;\n"
    "\t\tm_ActorStateInfo->UpdateActorInfo(m_pActorInvOwner);\n"
    "\t}\n\n"
    "\tswitch (m_currMenuMode)\n",
    "\t{\n"
    "\t\t// GCS Pass 3: actor-state protection calculations are expensive and do not\n"
    "\t\t// need to run at render frequency. Keep the panel responsive at 10 Hz.\n"
    "\t\t// Show() still forces an immediate refresh when the menu opens.\n"
    "\t\tconst u32 now = Device.dwTimeGlobal;\n"
    "\t\tif (now - m_last_time >= 100)\n"
    "\t\t{\n"
    "\t\t\tm_last_time = now;\n"
    "\t\t\tm_ActorStateInfo->UpdateActorInfo(m_pActorInvOwner);\n"
    "\t\t}\n"
    "\t}\n\n"
    "\tswitch (m_currMenuMode)\n",
)

# Prevent an unnecessary second full actor-state refresh directly after opening
# the actor menu by aligning the throttle timestamp with Show(true)'s forced
# refresh.
replace_exact(
    actor_menu,
    "\t\tm_ActorStateInfo->UpdateActorInfo(m_pActorInvOwner);\n"
    "\t}\n"
    "\telse\n",
    "\t\tm_ActorStateInfo->UpdateActorInfo(m_pActorInvOwner);\n"
    "\t\tm_last_time = Device.dwTimeGlobal;\n"
    "\t}\n"
    "\telse\n",
)

print("GCS Pass 3 source transforms applied successfully (actor-state UI throttle).")
