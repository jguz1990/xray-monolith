from pathlib import Path
import sys

if len(sys.argv) != 2:
    raise SystemExit("usage: apply_pass9.py <xray-engine-root>")

root = Path(sys.argv[1])
threading_cpp = root / "src/xrEngine/EngineThreading.cpp"


def replace_exact(path: Path, old: str, new: str, expected: int = 1) -> None:
    text = path.read_text(encoding="utf-8")
    count = text.count(old)
    if count != expected:
        raise RuntimeError(
            f"{path}: expected {expected} exact match(es), found {count}. "
            "Pinned source no longer matches the MT Pass 9 transform."
        )
    path.write_text(text.replace(old, new), encoding="utf-8")


# ISpatialShared is intrusive_ptr<ISpatial>, and ISpatial uses the atomic strict
# refcount policy. The old constructor accepted the pointer by value and then
# copied it into the member, causing an avoidable atomic add/sub pair per
# snapshot. Borrow the source reference and perform only the one ownership copy
# required by the snapshot itself.
replace_exact(
    threading_cpp,
    "    SpatialSnapshot(ISpatialShared _ptr, IKinematics* _pKin, float _distSq) : ptr(_ptr), pKin(_pKin), distSq(_distSq) {};\n",
    "    SpatialSnapshot(const ISpatialShared& _ptr, IKinematics* _pKin, float _distSq) : ptr(_ptr), pKin(_pKin), distSq(_distSq) {};\n",
)

# The spatial query vector already owns each intrusive pointer for the duration
# of this loop. Iterate by const reference instead of making another temporary
# intrusive_ptr copy (and therefore another pair of atomic refcount operations).
replace_exact(
    threading_cpp,
    "\t\tfor (ISpatialShared spatial : spatials)\n",
    "\t\tfor (const ISpatialShared& spatial : spatials)\n",
)

# On the first large scene, reserve enough snapshot storage once instead of
# growing the vector geometrically while collecting visible kinematics. The
# static vector retains that capacity for following frames.
replace_exact(
    threading_cpp,
    "\tstatic xr_vector<SpatialSnapshot> spatialsSnapshot;\n\tspatialsSnapshot.clear();\n\t{\n",
    "\tstatic xr_vector<SpatialSnapshot> spatialsSnapshot;\n"
    "\tspatialsSnapshot.clear();\n"
    "\tif (spatialsSnapshot.capacity() < spatials.size())\n"
    "\t\tspatialsSnapshot.reserve(spatials.size());\n"
    "\t{\n",
)

print("GCS MT Pass 9 applied: reduced atomic spatial refcount churn in bone worker.")
