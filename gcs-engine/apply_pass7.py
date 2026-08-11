from pathlib import Path
import sys

if len(sys.argv) != 2:
    raise SystemExit("usage: apply_pass7.py <xray-engine-root>")

root = Path(sys.argv[1])
trade = root / "src/xrGame/ui/UIActorMenuTrade.cpp"


def replace_exact(path: Path, old: str, new: str, expected: int = 1) -> None:
    text = path.read_text(encoding="utf-8")
    count = text.count(old)
    if count != expected:
        raise RuntimeError(
            f"{path}: expected {expected} exact match(es), found {count}. "
            "Pinned source no longer matches the Pass 7 transform."
        )
    path.write_text(text.replace(old, new), encoding="utf-8")


# Building filtered trade lists currently walks the selected drag/drop list for
# every candidate inventory item. Snapshot selected object IDs once, sort them,
# and use binary_search for membership during the rebuild.
replace_exact(
    trade,
    "\treturn false;\n"
    "}\n\n"
    "#include \"../MPPlayersBag.h\"\n",
    "\treturn false;\n"
    "}\n\n"
    "void collect_item_ids_in_list(CUIDragDropListEx* pList, xr_vector<u16>& ids)\n"
    "{\n"
    "\tids.clear();\n"
    "\tfor (u32 i = 0; i < pList->ItemsCount(); ++i)\n"
    "\t{\n"
    "\t\tCUICellItem* cell_item = pList->GetItemIdx(i);\n"
    "\t\tPIItem item = (PIItem)cell_item->m_pData;\n"
    "\t\tif (item)\n"
    "\t\t\tids.push_back(item->object_id());\n"
    "\t\tfor (u32 k = 0; k < cell_item->ChildsCount(); ++k)\n"
    "\t\t{\n"
    "\t\t\tPIItem child = (PIItem)cell_item->Child(k)->m_pData;\n"
    "\t\t\tif (child)\n"
    "\t\t\t\tids.push_back(child->object_id());\n"
    "\t\t}\n"
    "\t}\n"
    "\tstd::sort(ids.begin(), ids.end());\n"
    "}\n\n"
    "bool item_id_in_sorted_list(const xr_vector<u16>& ids, PIItem item)\n"
    "{\n"
    "\treturn item && std::binary_search(ids.begin(), ids.end(), item->object_id());\n"
    "}\n\n"
    "#include \"../MPPlayersBag.h\"\n",
)

replace_exact(
    trade,
    "\truck_list = m_pActorInvOwner->inventory().m_ruck;\n"
    "\tstd::sort(ruck_list.begin(), ruck_list.end(), InventoryUtilities::GreaterRoomInRuck);\n\n"
    "\tconst bool show_all =",
    "\truck_list = m_pActorInvOwner->inventory().m_ruck;\n"
    "\tstd::sort(ruck_list.begin(), ruck_list.end(), InventoryUtilities::GreaterRoomInRuck);\n\n"
    "\txr_vector<u16> selected_actor_trade_ids;\n"
    "\tcollect_item_ids_in_list(m_pTradeActorList, selected_actor_trade_ids);\n\n"
    "\tconst bool show_all =",
    expected=1,
)
replace_exact(
    trade,
    "\t\tif (!is_item_in_list(m_pTradeActorList, *itb))\n",
    "\t\tif (!item_id_in_sorted_list(selected_actor_trade_ids, *itb))\n",
    expected=1,
)

replace_exact(
    trade,
    "void CUIActorMenu::InitPartnerInventoryContents()\n"
    "{\n"
    "\tm_pTradePartnerBagList->ClearAll(true);\n\n"
    "\tTIItemContainer items_list;\n"
    "\tm_pPartnerInvOwner->inventory().AddAvailableItems(items_list, true);\n"
    "\tstd::sort(items_list.begin(), items_list.end(), InventoryUtilities::GreaterRoomInRuck);\n\n"
    "\tTIItemContainer::iterator itb = items_list.begin();\n",
    "void CUIActorMenu::InitPartnerInventoryContents()\n"
    "{\n"
    "\tm_pTradePartnerBagList->ClearAll(true);\n\n"
    "\tTIItemContainer items_list;\n"
    "\tm_pPartnerInvOwner->inventory().AddAvailableItems(items_list, true);\n"
    "\tstd::sort(items_list.begin(), items_list.end(), InventoryUtilities::GreaterRoomInRuck);\n\n"
    "\txr_vector<u16> selected_partner_trade_ids;\n"
    "\tcollect_item_ids_in_list(m_pTradePartnerList, selected_partner_trade_ids);\n\n"
    "\tTIItemContainer::iterator itb = items_list.begin();\n",
)
replace_exact(
    trade,
    "\t\tif (!is_item_in_list(m_pTradePartnerList, *itb))\n",
    "\t\tif (!item_id_in_sorted_list(selected_partner_trade_ids, *itb))\n",
    expected=2,
)

# FilterTraderList gets its own snapshot because it can be called independently
# after the trade selection changes.
replace_exact(
    trade,
    "void CUIActorMenu::FilterTraderList(int mode)\n"
    "{\n"
    "\tm_pTradePartnerBagList->ClearAll(true);\n\n"
    "\tTIItemContainer items_list;\n"
    "\tm_pPartnerInvOwner->inventory().AddAvailableItems(items_list, true);\n"
    "\tstd::sort(items_list.begin(), items_list.end(), InventoryUtilities::GreaterRoomInRuck);\n\n"
    "\tconst bool show_all =",
    "void CUIActorMenu::FilterTraderList(int mode)\n"
    "{\n"
    "\tm_pTradePartnerBagList->ClearAll(true);\n\n"
    "\tTIItemContainer items_list;\n"
    "\tm_pPartnerInvOwner->inventory().AddAvailableItems(items_list, true);\n"
    "\tstd::sort(items_list.begin(), items_list.end(), InventoryUtilities::GreaterRoomInRuck);\n\n"
    "\txr_vector<u16> selected_partner_trade_ids;\n"
    "\tcollect_item_ids_in_list(m_pTradePartnerList, selected_partner_trade_ids);\n\n"
    "\tconst bool show_all =",
)

print("GCS Pass 7 source transforms applied successfully (trade-list membership snapshots).")
