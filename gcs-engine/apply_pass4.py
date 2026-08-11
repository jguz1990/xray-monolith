from pathlib import Path
import sys

if len(sys.argv) != 2:
    raise SystemExit("usage: apply_pass4.py <xray-engine-root>")

root = Path(sys.argv[1])
header = root / "src/xrGame/ui/UIActorMenu.h"
inv = root / "src/xrGame/ui/UIActorMenuInventory.cpp"
trade = root / "src/xrGame/ui/UIActorMenuTrade.cpp"


def replace_exact(path: Path, old: str, new: str, expected: int = 1) -> None:
    text = path.read_text(encoding="utf-8")
    count = text.count(old)
    if count != expected:
        raise RuntimeError(
            f"{path}: expected {expected} exact match(es), found {count}. "
            "Pinned source no longer matches the Pass 4 transform."
        )
    path.write_text(text.replace(old, new), encoding="utf-8")


# Trade eligibility is evaluated for every actor item while trade lists are built.
# The selected actor/partner trade-list weights are identical for every item in
# that build, so calculate them once and pass them through instead of rescanning
# the same UI lists for every visible inventory item.
replace_exact(
    header,
    "\tbool CanMoveToPartner(PIItem pItem);\n",
    "\tbool CanMoveToPartner(PIItem pItem);\n"
    "\tbool CanMoveToPartnerWithWeights(PIItem pItem, float actor_trade_weight, float partner_trade_weight);\n",
)

# InitInventoryContents is also used to build the actor side when trade opens.
replace_exact(
    inv,
    "\titb = ruck_list.begin();\n"
    "\tite = ruck_list.end();\n\n"
    "\tfor (; itb != ite; ++itb)\n",
    "\titb = ruck_list.begin();\n"
    "\tite = ruck_list.end();\n\n"
    "\tfloat actor_trade_weight = 0.0f;\n"
    "\tfloat partner_trade_weight = 0.0f;\n"
    "\tif (m_currMenuMode == mmTrade && m_pPartnerInvOwner)\n"
    "\t{\n"
    "\t\tactor_trade_weight = CalcItemsWeight(m_pTradeActorList);\n"
    "\t\tpartner_trade_weight = CalcItemsWeight(m_pTradePartnerList);\n"
    "\t}\n\n"
    "\tfor (; itb != ite; ++itb)\n",
    expected=1,
)
replace_exact(
    inv,
    "\t\tif (m_currMenuMode == mmTrade && m_pPartnerInvOwner)\n"
    "\t\t\tColorizeItem(itm, !CanMoveToPartner(*itb));\n",
    "\t\tif (m_currMenuMode == mmTrade && m_pPartnerInvOwner)\n"
    "\t\t\tColorizeItem(itm, !CanMoveToPartnerWithWeights(*itb, actor_trade_weight, partner_trade_weight));\n",
    expected=1,
)

# Pass 1 has already hoisted show_all/kinds at this point in the build pipeline.
replace_exact(
    trade,
    "\tconst bool show_all = (0 == xr_strcmp(m_sort_kinds[mode], \"s_all\"));\n"
    "\tconst int kinds = show_all ? 0 : _GetItemCount(m_sort_kinds[mode]);\n"
    "\tTIItemContainer::iterator itb = ruck_list.begin();\n",
    "\tconst bool show_all = (0 == xr_strcmp(m_sort_kinds[mode], \"s_all\"));\n"
    "\tconst int kinds = show_all ? 0 : _GetItemCount(m_sort_kinds[mode]);\n"
    "\tconst float actor_trade_weight = CalcItemsWeight(m_pTradeActorList);\n"
    "\tconst float partner_trade_weight = CalcItemsWeight(m_pTradePartnerList);\n"
    "\tTIItemContainer::iterator itb = ruck_list.begin();\n",
    expected=1,
)
replace_exact(
    trade,
    "ColorizeItem(itm, !CanMoveToPartner(iitm));",
    "ColorizeItem(itm, !CanMoveToPartnerWithWeights(iitm, actor_trade_weight, partner_trade_weight));",
    expected=2,
)

# Pass 2 has already changed CalcTotalWeight() to the maintained TotalWeight()
# cache before this transform runs.
old_can_move = """bool CUIActorMenu::CanMoveToPartner(PIItem pItem)
{
\tif (!pItem->CanTrade())
\t\treturn false;

\tif (!m_pPartnerInvOwner->trade_parameters().enabled(
\t\tCTradeParameters::action_buy(0), pItem->object().cNameSect()))
\t{
\t\treturn false;
\t}

\tbool has_max_uses = pItem->cast_eatable_item() && pItem->cast_eatable_item()->GetMaxUses();
\tif (!has_max_uses && (pItem->GetCondition() < m_pPartnerInvOwner->trade_parameters().buy_item_condition_factor))
\t\treturn false;

\tfloat r1 = CalcItemsWeight(m_pTradeActorList); // actor
\tfloat r2 = CalcItemsWeight(m_pTradePartnerList); // partner
\tfloat itmWeight = pItem->Weight();
\tfloat partner_inv_weight = m_pPartnerInvOwner->inventory().TotalWeight();
\tfloat partner_max_weight = m_pPartnerInvOwner->MaxCarryWeight();

\tif (partner_inv_weight - r2 + r1 + itmWeight > partner_max_weight)
\t{
\t\treturn false;
\t}
\treturn true;
}
"""
new_can_move = """bool CUIActorMenu::CanMoveToPartner(PIItem pItem)
{
\treturn CanMoveToPartnerWithWeights(
\t\tpItem,
\t\tCalcItemsWeight(m_pTradeActorList),
\t\tCalcItemsWeight(m_pTradePartnerList));
}

bool CUIActorMenu::CanMoveToPartnerWithWeights(PIItem pItem, float actor_trade_weight, float partner_trade_weight)
{
\tif (!pItem->CanTrade())
\t\treturn false;

\tif (!m_pPartnerInvOwner->trade_parameters().enabled(
\t\tCTradeParameters::action_buy(0), pItem->object().cNameSect()))
\t{
\t\treturn false;
\t}

\tCEatableItem* eatable_item = pItem->cast_eatable_item();
\tconst bool has_max_uses = eatable_item && eatable_item->GetMaxUses();
\tif (!has_max_uses && (pItem->GetCondition() < m_pPartnerInvOwner->trade_parameters().buy_item_condition_factor))
\t\treturn false;

\tconst float itmWeight = pItem->Weight();
\tconst float partner_inv_weight = m_pPartnerInvOwner->inventory().TotalWeight();
\tconst float partner_max_weight = m_pPartnerInvOwner->MaxCarryWeight();

\tif (partner_inv_weight - partner_trade_weight + actor_trade_weight + itmWeight > partner_max_weight)
\t{
\t\treturn false;
\t}
\treturn true;
}
"""
replace_exact(trade, old_can_move, new_can_move)

print("GCS Pass 4 source transforms applied successfully (trade eligibility weight caching).")
