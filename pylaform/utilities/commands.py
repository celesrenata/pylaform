import re

from werkzeug.datastructures.structures import ImmutableMultiDict


def fatten(full_list: list[dict[str, str | int | bool]]) -> dict[str, list[dict[str, str | bool]], str, list[str]]:
    """
    Takes 'id/attr/value/state' and compresses it into a single dictionary.
    :param list[dict[str, str | int | bool]] full_list: Decompiled attribute list.
    :return dict: Payload passed to templates.
    """

    result: list[dict[str, str | int | bool]] = []
    attrs: list[str] = []
    for item in full_list:
        sub_result: dict[str, str | int | bool] = {}
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
        if not item["state"]:
            bloated.remove(item)
    return listify(bloated)


def contact_flatten(full_list: list[dict[str, str | int | bool]]) -> dict[any, dict[str, any]]:
    """
    Flattens the list into a FLAT dictionary of contact details for latex
    :param list[dict[str, str|int|bool]] full_list: Decompiled attribute list.
    :return dict: Payload passed to latex
    """

    result: dict[str, dict[str, str | int | bool]] = {}
    for item in full_list:
        sub_result: dict[str, str | int | bool] = {}
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

    attrs: list[str] = unique([sub["attr"] for sub in full_list])
    attrs_per_id: int = 0

    # Setup variables.
    sub_mask_group_count: list[str] = []
    result: list[dict[str, str | bool]] = []
    count: int = 1
    sub_mask: list[str] = []
    working_result: dict[str, str | bool] = {}
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
        # Dynamically set state
        if "state" not in item:
            if len(item_split) == 2:
                if item_split[0].replace("id", "") + "state" not in working_result:
                    dynamic_state: bool = False
                else:
                    dynamic_state: bool = bool(working_result[item_split[0].replace("id", "") + "state"])
            else:
                if "state" not in working_result:
                    dynamic_state: bool = False
                else:
                    dynamic_state: bool = bool(working_result["state"])
        else:
            dynamic_state: bool = bool(item["state"])

        # NESTED Update working result.
        if len(item_split) == 2:
            working_result.update({item_split[0]: item_split[1], item["attr"]: item["value"],
                                   item_split[0].replace("id", "") + "state": dynamic_state})

        # REGULAR Update working result
        else:
            working_result.update({"id": item["id"], item["attr"]: item["value"], "state": dynamic_state})

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

    result: list[dict[str, str | bool]] = []
    for item in form_data:
        item_split = str(item).split("_")
        if len(item_split) == 3:
            if item_split[2] == "dropdown":
                result.append({"id": item_split[0], "attr": item_split[1] + "_dropdown", "value": form_data[item], "state": False})
            if item_split[2] == "enabled":
                indexes = find_nested_indexes(result, 'id', item_split[0])
                if len(indexes) > 0:
                    for index in indexes:
                        result[index].update({"state": True})
        else:
            result.append({"id": item_split[0], "attr": item_split[1], "value": form_data[item], "state": False})

    return result


def unique(list1: list) -> list:
    """
    Returns only unique values from a list.
    :param list list1: source list.
    :return list: Dedupped list.
    """

    unique_list: list = []

    for x in list1:
        if x == "":
            continue
        if x not in unique_list:
            unique_list.append(x)

    return unique_list


def find_nested_indexes(input_list: list[dict[str, str | bool]], key: str | list[str], value: str | list) -> list[int]:
    """
    Find nested indexes of a list of dictionaries.
    :param list[dict[str, str | bool]] input_list: List of dictionaries.
    :param str | list[str] key: dictionary keys to search.
    :param str | list value: dictionary values to find.
    :return list[int]: list of indexes where keyvals match.
    """

    result: list = []
    if type(key) == str:
        for i, item in enumerate(input_list):
            if item[key] == value:
                result.append(i)

    if type(key) == list:
        for i, item in enumerate(input_list):
            count = 0
            for sub_i, k in enumerate(key):
                if item[key[sub_i]] == value[sub_i]:
                    count = count + 1
                if count == len(key):
                    result.append(i)

    return result
