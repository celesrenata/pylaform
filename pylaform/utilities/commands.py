from datetime import datetime


def fatten(full_list):
    """
    Flattens the list into a F A T dictionary for kwargs
    :param full_list:
    :return:dict
    """

    result = []
    for item in full_list:
        sub_result = {}
        for sub_key in item:
            sub_result.update({sub_key: item[sub_key]})
        result.append(sub_result)
    return {"payload": result}


def contact_flatten(full_list):
    """
    Flattens the list into a F L A T dictionary of contact details for latex
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

    result = []
    working_result = []
    wait = int()
    item_count = []
    for item in full_list:
        item_count.append(item["attr"])

    last_run = len(unique(item_count))
    for i, item in enumerate(full_list, 1):
        sub_result = {}
        flagged = False

        for i_sub, sub_key in enumerate(item, 1):
            if sub_key == "state":
                if item[sub_key] == 1:
                    item[sub_key] = True
                else:
                    item[sub_key] = False
            sub_result.update({"name" if sub_key == "attr" else sub_key: item[sub_key]})
            if "name" in sub_result and "value" in sub_result:
                if not flagged:
                    working_result.append({sub_result["name"]: sub_result["value"]})
                    flagged = True

        working_dict = {}
        for sub_item in working_result:
            for sub_key in sub_item:
                working_dict.update({sub_key: sub_item[sub_key]})
        wait = len(working_dict)
        if i % last_run == 0:
            result.append(working_dict)

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
    for i, item in enumerate(form_data, 1):
        if len(sub_result) == 4:
            result.append(sub_result)
            sub_result = {}
        item_split = str(item).split("_")
        if "_enabled" in item:
            if form_data[item] == 'on':
                sub_result.update({"state": True})
            else:
                sub_result.update({"state": False})
        else:
            sub_result.update({"value": form_data[item]})
        if "id" not in sub_result:
            sub_result.update({"id": int(item_split[0])})
        if "name" not in sub_result:
            sub_result.update({"attr": item_split[1]})
        if i == form_data_len:
            result.append(sub_result)

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
        if x not in unique_list:
            unique_list.append(x)

    return unique_list
