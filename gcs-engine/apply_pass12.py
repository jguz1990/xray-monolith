from pathlib import Path
import sys

if len(sys.argv) != 2:
    raise SystemExit("usage: apply_pass12.py <xray-engine-root>")

root = Path(sys.argv[1])


def ensure_replaced(rel, old, new):
    path = root / rel
    text = path.read_text(encoding="utf-8")
    if new in text:
        return
    count = text.count(old)
    if count != 1:
        raise RuntimeError(f"{rel}: expected 1 exact old match or existing new block, found {count}")
    path.write_text(text.replace(old, new), encoding="utf-8")


ensure_replaced(
    "src/xrGame/ui/UIScriptWnd.cpp",
    "bool CUIDialogWndEx::OnKeyboardAction(int dik, EUIMessages keyboard_action)\n{\n\treturn inherited::OnKeyboardAction(dik, keyboard_action);\n}\n\nvoid CUIDialogWndEx::Update()\n",
    "bool CUIDialogWndEx::OnKeyboardAction(int dik, EUIMessages keyboard_action)\n{\n\treturn inherited::OnKeyboardAction(dik, keyboard_action);\n}\n\nbool CUIDialogWndEx::OnMouseAction(float x, float y, EUIMessages mouse_action)\n{\n\treturn inherited::OnMouseAction(x, y, mouse_action);\n}\n\nvoid CUIDialogWndEx::Update()\n",
)

ensure_replaced(
    "src/xrGame/ui/UIScriptWnd.h",
    "\tvirtual void Update();\n\tvirtual bool OnKeyboardAction(int dik, EUIMessages keyboard_action);\n",
    "\tvirtual void Update();\n\tvirtual bool OnMouseAction(float x, float y, EUIMessages mouse_action);\n\tvirtual bool OnKeyboardAction(int dik, EUIMessages keyboard_action);\n",
)

ensure_replaced(
    "src/xrGame/ui/UIWindow_script.cpp",
    "\t\t\tvalue(\"WINDOW_MOUSE_MOVE\", int(WINDOW_MOUSE_MOVE)),\n\t\t\tvalue(\"WINDOW_LBUTTON_DB_CLICK\", int(WINDOW_LBUTTON_DB_CLICK)),\n",
    "\t\t\tvalue(\"WINDOW_MOUSE_MOVE\", int(WINDOW_MOUSE_MOVE)),\n\t\t\tvalue(\"WINDOW_MOUSE_WHEEL_UP\", int(WINDOW_MOUSE_WHEEL_UP)),\n\t\t\tvalue(\"WINDOW_MOUSE_WHEEL_DOWN\", int(WINDOW_MOUSE_WHEEL_DOWN)),\n\t\t\tvalue(\"WINDOW_LBUTTON_DB_CLICK\", int(WINDOW_LBUTTON_DB_CLICK)),\n",
)

ensure_replaced(
    "src/xrGame/ui/uiscriptwnd_script.h",
    "\tstatic bool OnKeyboard_static(inherited* ptr, int dik, EUIMessages keyboard_action)\n\t{\n\t\treturn ptr->self_type::inherited::OnKeyboardAction(dik, keyboard_action);\n\t}\n\n\tvirtual void Update()\n",
    "\tstatic bool OnKeyboard_static(inherited* ptr, int dik, EUIMessages keyboard_action)\n\t{\n\t\treturn ptr->self_type::inherited::OnKeyboardAction(dik, keyboard_action);\n\t}\n\n\tvirtual bool OnMouseAction(float x, float y, EUIMessages mouse_action)\n\t{\n\t\treturn call_member<bool>(this, \"OnMouse\", x, y, mouse_action);\n\t}\n\n\tstatic bool OnMouse_static(inherited* ptr, float x, float y, EUIMessages mouse_action)\n\t{\n\t\treturn ptr->self_type::inherited::OnMouseAction(x, y, mouse_action);\n\t}\n\n\tvirtual void Update()\n",
)

ensure_replaced(
    "src/xrGame/ui/uiscriptwnd_script2.cpp",
    "\treturn std::move(instance)\n\t\t.def(\"OnKeyboard\", &BaseType::OnKeyboardAction, &WrapType::OnKeyboard_static)\n\t\t.def(\"Update\", &BaseType::Update, &WrapType::Update_static)\n",
    "\treturn std::move(instance)\n\t\t.def(\"OnKeyboard\", &BaseType::OnKeyboardAction, &WrapType::OnKeyboard_static)\n\t\t.def(\"OnMouse\", &BaseType::OnMouseAction, &WrapType::OnMouse_static)\n\t\t.def(\"Update\", &BaseType::Update, &WrapType::Update_static)\n",
)

print("GCS Pass 12 ready: upstream 1662b502 Lua mouse-wheel exposure is present.")
