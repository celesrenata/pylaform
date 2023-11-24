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
    for item in full_list:
        seen = []
        sub_result = {}
        for sub_key in item:
            if sub_key == "state":
                if item[sub_key] == 1:
                    item[sub_key] = True
                else:
                    item[sub_key] = False
            if item[sub_key] in seen:
                working_result.append(sub_result)
                seen = [item[sub_key]]
            seen.append(item[sub_key])
            sub_result.update({"name" if sub_key == "attr" else sub_key: item[sub_key]})

        seen = []
        working_dict = {}
        for item in working_result:
            for sub_key in item:
                if sub_key in seen:
                    continue
                else:
                    working_dict.update({sub_key: item[sub_key]})
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
    count = 1
    for i, item in enumerate(form_data, 1):
        item_split = str(item).split("_")
        if count != int(item_split[0]):
            result.append(sub_result)
            sub_result = {}
            count = count + 1
        if "_enabled" in item:
            if form_data[item] == 'on':
                sub_result.update({"state": True})
            else:
                sub_result.update({"state": False})
        else:
            sub_result.update({"value": form_data[item]})
        if "id" not in sub_result:
            sub_result.update({"id": int(item_split[0])})
        if i == form_data_len:
            result.append(sub_result)

    return result
