from pathlib import Path
import sys

if len(sys.argv) != 2:
    raise SystemExit("usage: apply_pass8.py <xray-engine-root>")

root = Path(sys.argv[1])
device_h = root / "src/xrEngine/device.h"
device_cpp = root / "src/xrEngine/device.cpp"
threading_cpp = root / "src/xrEngine/EngineThreading.cpp"


def replace_exact(path: Path, old: str, new: str, expected: int = 1) -> None:
    text = path.read_text(encoding="utf-8")
    count = text.count(old)
    if count != expected:
        raise RuntimeError(
            f"{path}: expected {expected} exact match(es), found {count}. "
            "Pinned source no longer matches the MT Pass 8 transform."
        )
    path.write_text(text.replace(old, new), encoding="utf-8")


# Device.isRendering is written by the main/render thread and sampled by the
# Lua-GC worker while both are executing concurrently. Make the handoff an
# explicit atomic stop signal instead of relying on a plain bool data race.
replace_exact(
    device_h,
    "\tbool isRendering;\n\n\t// LuaGC\n",
    "\t// GCS MT Pass 8: cross-thread render/worker stop signal.\n"
    "\txr_atomic_bool isRendering = false;\n\n"
    "\t// LuaGC\n",
)

replace_exact(
    device_cpp,
    "\tDevice.isRendering = true;\n\tDevice.LuaGCDone = false;\n\tDevice.LuaGCCount = 0;\n",
    "\tDevice.isRendering.store(true, std::memory_order_relaxed);\n"
    "\tDevice.LuaGCDone = false;\n"
    "\tDevice.LuaGCCount = 0;\n",
)
replace_exact(
    device_cpp,
    "\tDevice.isRendering = false;\n\n\tsecondary_tasks.wait();\n",
    "\tDevice.isRendering.store(false, std::memory_order_relaxed);\n\n"
    "\tsecondary_tasks.wait();\n",
)

# The GC task previously incremented Device.LuaGCCount on every GC step while
# the main thread was polling/stopping rendering. Keep the hot counter local to
# the worker and publish the final diagnostic state once, after the loop. This
# reduces shared cache-line traffic without changing the GC budget or ordering.
replace_exact(
    threading_cpp,
    "    static auto LuaGC = []()\n"
    "    {\n"
    "        PROF_EVENT(\"seqLuaGC\");\n"
    "        // Do at least once\n"
    "        do\n"
    "        {\n"
    "            Device.LuaGCCount++;\n"
    "            if (Device.LuaGC() == 1) // 1 informs that GC cycle is complete\n"
    "            {\n"
    "                Device.LuaGCDone = true;\n"
    "                break;\n"
    "            }\n"
    "\n"
    "        } while (Device.isRendering && Device.LuaGCCount < psLua_ParallelGC_CallAmount);\n"
    "    };\n",
    "    static auto LuaGC = []()\n"
    "    {\n"
    "        PROF_EVENT(\"seqLuaGC\");\n"
    "\n"
    "        int lua_gc_count = 0;\n"
    "        bool lua_gc_done = false;\n"
    "\n"
    "        // Do at least once, as before. Keep the hot counter worker-local.\n"
    "        do\n"
    "        {\n"
    "            ++lua_gc_count;\n"
    "            if (Device.LuaGC() == 1) // 1 informs that GC cycle is complete\n"
    "            {\n"
    "                lua_gc_done = true;\n"
    "                break;\n"
    "            }\n"
    "\n"
    "        } while\n"
    "        (\n"
    "            Device.isRendering.load(std::memory_order_relaxed) &&\n"
    "            lua_gc_count < psLua_ParallelGC_CallAmount\n"
    "        );\n"
    "\n"
    "        // Publish diagnostics once. secondary_tasks.wait() remains the frame barrier.\n"
    "        Device.LuaGCCount = lua_gc_count;\n"
    "        Device.LuaGCDone = lua_gc_done;\n"
    "    };\n",
)

print("GCS MT Pass 8 applied: atomic render stop signal + worker-local Lua GC accounting.")
