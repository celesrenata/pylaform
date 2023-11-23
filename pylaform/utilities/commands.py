def flatten(full_list):
    """
    Flattens the list into a fat dictionary for kwargs
    :param full_list:
    :return:
    """
    result = {}
    for item in full_list:
        result.update({list(item.values())[0]: {
            "value": list(item.values())[1],
            "state": list(item.values())[2],
        }})
    return result
