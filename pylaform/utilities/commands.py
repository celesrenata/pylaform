import re

from werkzeug.datastructures.structures import ImmutableMultiDict


def fatten(full_list: list[dict[str, str | int | bool]]) -> dict[str, list[dict[str, str | bool]], str, list[str]]:
    """
    Takes 'id/attr/value/state' and compresses it into a single dictionary.
    :param list[dict[str, str | int | bool]] full_list: Decompiled attribute list.
    :return dict: Payload passed to templates.
    """

    result = []
    attrs = []
    for item in full_list:
        sub_result = {}
        attrs.append(item["attr"])
        for sub_key in item:
            sub_result.update({sub_key: item[sub_key]})
        result.append(sub_result)

    return {"payload": listify(result), "attrs": attrs}


def slim(full_list: list[dict[str, str | int | bool]]) -> list[dict[str, str | bool]]:
    """
    Extracts 'id/attr/value/state' and drops items with false states for latex writing.
    :param list[dict[str, str | int | bool]] full_list: Decompiled attribute list.
    :return dict: Payload passed to templates.
    """

    bloated = [{"id": sub["id"], "attr": sub["attr"], "value": sub["value"], "state": sub["state"]}
               for sub in full_list]
    for item in bloated:
        if not bloated["state"]:
            bloated.remove(item)
    return listify(bloated)


def contact_flatten(full_list: list[dict[str, str | int | bool]]) -> dict[any, dict[str, any]]:
    """
    Flattens the list into a FLAT dictionary of contact details for latex
    :param list[dict[str, str|int|bool]] full_list: Decompiled attribute list.
    :return dict: Payload passed to latex
    """

    result = {}
    for item in full_list:
        sub_result = {}
        for sub_key in item:
            sub_result.update({sub_key: item[sub_key]})
        result.update({sub_result["attr"]: {"value": sub_result["value"], "state": sub_result["state"]}})
    return result


def listify(full_list: list[dict[str, str | int | bool]]) -> list[dict[str, str | bool]]:
    """
    Converts decompiled attribute list into structured list for latex and flask templates.
    :param list[dict[str, str | bool]] full_list: Decompiled attribute list.
    :return list: Compiled attribute list.
    """

    attrs = unique([sub["attr"] for sub in full_list])
    attrs_per_id = 0

    # Setup variables.
    sub_mask_group_count = []
    result = []
    count = 1
    sub_mask = []
    working_result = {}
    for item in full_list:
        # If current_id and
        # (isalpha(current_id) == isalpha(previous_loop_id)
        # or isnumeber(current_id) != isnumber(previous_loop_id).
        if (count != item["id"]
                and (re.sub(r'\d+', '', str(item["id"])) == re.sub(r'\d+', '', str(count))
                     or re.sub(r'\D', '', str(item["id"])) != re.sub(r'\D', '', str(count)))):
            # Split current ID for nested detection.
            if isinstance(item["id"], int):
                item_split = str(item["id"])
            else:
                item_split = item["id"].split("_")
            if item["id"] not in sub_mask and len(item_split) == 1:
                sub_mask.append(item["id"])

        # Get list of attributes associated with current ID.
        if isinstance(item["id"], int):
            attrs_per_id = len(unique([sub["attr"] if sub["id"] == item["id"] else "" for sub in full_list]))
            item_split = str(item["id"])
        else:
            item_split = item["id"].split("_")

        # NESTED Update working result.
        if len(item_split) == 2:
            working_result.update({item_split[0]: item_split[1], item["attr"]: item["value"],
                                   item_split[0].replace("id", "") + "state": False})

        # REGULAR Update working result
        else:
            working_result.update({"id": item["id"], item["attr"]: item["value"], "state": False})
        # Update state from int to bool.
        if item["state"] == 1 and len(item_split) == 2:
            working_result.update({item_split[0].replace("id", "") + "state": True})
        elif item["state"] == 1 and len(item_split) == 1:
            working_result.update({"state": True})

        # NESTED Update result
        if len(item_split) == 2:
            if item["id"] not in sub_mask:
                sub_mask.append(item["id"])
                sub_mask_group_count.append(re.sub("[^A-Za-z]", "", item["id"]))
            if all(x in working_result for x in attrs):
                result.append(working_result)
                working_result = {}

        # REGULAR Update result
        if len(item_split) == 1 and len(working_result) == attrs_per_id + 2:
            result.append(working_result)
            working_result = {}

    return result


def transform_get_id(form_data: ImmutableMultiDict) -> list[dict[str, str | bool]]:
    """
    Transforms data by stripping id data and creating a new dictionary field for nested and regular items.
    Used for DB actions: INSERT INTO, DELETE FROM, UPDATE.
    :param ImmutableMultiDict form_data: Data response from templates.
    :return list:
    """

    result = []
    for item in form_data:
        item_split = str(item).split("_")
        if "_enabled" in item:
            result[-1].update({"state": True})
        if "_enabled" not in item:
            result.append({"id": item_split[0], "attr": item_split[1], "value": form_data[item], "state": False})

    return result


def unique(list1: list) -> list:
    """
    Returns only unique values from a list.
    :param list list1: source list.
    :return list: Dedupped list.
    """

    unique_list = []

    for x in list1:
        if x == "":
            continue
        if x not in unique_list:
            unique_list.append(x)

    return unique_list
