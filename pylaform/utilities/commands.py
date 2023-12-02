import re
from datetime import datetime


def fatten(full_list):
    """
    Flattens the list into a FAT dictionary for kwargs
    :param full_list:
    :return:dict
    """

    result = []
    attrs = []
    for item in full_list:
        sub_result = {}
        attrs.append(item['attr'])
        for sub_key in item:
            sub_result.update({sub_key: item[sub_key]})
        result.append(sub_result)

    return {"payload": listify(result), "attrs": attrs}


def contact_flatten(full_list):
    """
    Flattens the list into a FLAT dictionary of contact details for latex
    :param full_list:
    :return: dict
    """

    result = {}
    for item in full_list:
        sub_result = {}
        for sub_key in item:
            sub_result.update({sub_key: item[sub_key]})
        result.update({sub_result['attr']: {"value": sub_result['value'], "state": sub_result['state']}})
    return result


def listify(full_list):
    """
    Converts form data dictionary into a list
    :param full_list:
    :return: list
    """
    attrs = unique([sub["attr"] for sub in full_list])
    attrs_per_id = 0
    sub_mask_working_group = [''.join(x for x in str(sub["id"]) if x.isalpha()) if ''.join(x for x in str(sub["id"]) if x.isalpha()) != "" else "" for sub in full_list]
    sub_mask_group = unique(sub_mask_working_group)
    sub_mask_group_count = []
    result = []
    count = 1
    sub_mask = []
    sub_mask_count = 0
    working_result = {}
    for i, item in enumerate(full_list, 1):
        if count != item["id"] and (re.sub(r'\d+', '', str(item["id"])) == re.sub(r'\d+', '', str(item["id"]))
            or re.sub('\D', '', str(item["id"])) != re.sub('\D', '', str(item["id"]))):
            if isinstance(item["id"], int):
                item_split = str(item["id"])
            else:
                item_split = item["id"].split("_")
            if item["id"] not in sub_mask and len(item_split) == 1:
                sub_mask.append(item["id"])
        if isinstance(item["id"], int):
            attrs_per_id = len(unique([sub["attr"] if sub["id"] == item["id"] else '' for sub in full_list]))
            item_split = str(item["id"])
        else:
            item_split = item["id"].split("_")
        if len(item_split) == 2:
            working_result.update({item_split[0]: item_split[1], item["attr"]: item["value"], item_split[0].replace('id', '') + "state": False})
        else:
            working_result.update({"id": item["id"], item["attr"]: item["value"], "state": False})
        if item['state'] == 1 and len(item_split) == 2:
            working_result.update({item_split[0].replace('id', '') + "state": True})
        elif item['state'] == 1 and len(item_split) == 1:
            working_result.update({"state": True})
        if len(item_split) == 2:
            if item["id"] not in sub_mask:
                sub_mask.append(item["id"])
                sub_mask_group_count.append(re.sub("[^A-Za-z]", "", item["id"]))
            sub_mask_count = len(unique(sub_mask_group_count))
            if all(x in working_result for x in attrs):
                result.append(working_result)
                sub_mask_count = 0
                working_result = {}
        if len(item_split) == 1 and len(working_result) == attrs_per_id + 2:
            result.append(working_result)
            working_result = {}

    return result


def transform_get_id(form_data):
    """
    Transforms data by stripping id data and creating a new dictionary field
    :param form_data: ImmutableMultiDict
    :return: list
    """

    result = []
    sub_result = {}
    form_data_len = len(form_data)
    for item in form_data:
        item_split = str(item).split("_")
        if "_enabled" in item:
            result[-1].update({"state": True})
        if "_enabled" not in item:
            result.append({"id": item_split[0], "attr": item_split[1], "value": form_data[item], "state": False})

    return result


def unique(list1):
    """
    Returns only unique values of a list
    :param list list1: source list
    :return: list
    """
    # initialize a null list
    unique_list = []

    # traverse for all elements
    for x in list1:
        # check if exists in unique_list or not
        if x == '':
            continue
        if x not in unique_list:
            unique_list.append(x)

    return unique_list
