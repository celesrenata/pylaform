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


def slim(summary_data):
    """
    Convert the raw summary data to a format expected by the templates.
    """
    # If empty data, return empty list
    if not summary_data:
        return []

    # Debug info
    print(f"Processing {len(summary_data)} summary items")

    # Create dictionary to group items by ID
    result = {}

    # Process each item in the summary data
    for item in summary_data:
        item_id = item.get('id')

        # Initialize the item in our result dict if not present
        if item_id not in result:
            result[item_id] = {
                'id': item_id,
                'shortdesc': '',
                'longdesc': '',
                'state': item.get('state', 0)
            }

        # Update fields based on the attribute name
        attr = item.get('attr')
        if attr == 'shortdesc':
            result[item_id]['shortdesc'] = item.get('value', '')
        elif attr == 'longdesc':
            result[item_id]['longdesc'] = item.get('value', '')

    # Filter for only active items (state = 1)
    active_items = [item for item in result.values() if item['state'] == 1]

    # Debug the output
    print(f"Found {len(active_items)} active summary items")
    for item in active_items:
        print(f"Active summary: {item['shortdesc']}")

    return active_items


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
            if len(item_split) == 2 and type(item_split) == list:
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
        if len(item_split) == 2 and type(item_split) == list:
            working_result.update({item_split[0]: item_split[1], item["attr"]: item["value"],
                                   item_split[0].replace("id", "") + "state": dynamic_state})

        # REGULAR Update working result
        else:
            working_result.update({"id": item["id"], item["attr"]: item["value"], "state": dynamic_state})

        # NESTED Update result
        if len(item_split) == 2 and type(item_split) == list:
            if item["id"] not in sub_mask:
                sub_mask.append(item["id"])
                sub_mask_group_count.append(re.sub("[^A-Za-z]", "", item["id"]))
            if all(x in working_result for x in attrs):
                result.append(working_result)
                working_result = {}

        # REGULAR Update result
        if len(item_split) == 1 and len(working_result) >= attrs_per_id + 2:
            # All required attributes are present
            result.append(working_result)
            working_result = {}

    return result


def transform_get_id(form_data: ImmutableMultiDict) -> list[dict[str, str | bool]]:
    """
    Transforms data by stripping id data and creating a new dictionary field for nested and regular items.
    Used for DB actions: INSERT INTO, DELETE FROM, UPDATE.
    :param ImmutableMultiDict form_data: Data response from templates.
    :return list: List of dictionaries with standardized structure.
    """
    result: list[dict[str, str | bool]] = []
    item_count = sum('_dropdown' in key for key in list(form_data))

    # First pass: Process and transform each form item
    for item in form_data:
        item_split = str(item).split("_")

        # Handle keys with no underscore
        if len(item_split) == 1:
            result.append({
                "id": "0",
                "attr": item,
                "value": form_data[item],
                "state": False
            })
            continue

        # Handle items with at least one underscore
        if "dropdown" in item_split[-1]:
            result.append({
                "id": item_split[0],
                "attr": item_split[1] + "_dropdown",
                "value": form_data[item],
                "state": False
            })
        elif "enabled" in item_split[-1]:
            # For enabled items, use the first part as ID and full attr name
            result.append({
                "id": item_split[0],
                "attr": "_".join(item_split[1:]),
                "value": bool(form_data[item]),
                "state": False
            })
        elif len(item_split) < 3:
            result.append({
                "id": item_split[0],
                "attr": item_split[1],
                "value": form_data[item],
                "state": False
            })
        else:
            result.append({
                "id": item_split[0],
                "attr": "_".join(item_split[1:]),
                "value": form_data[item],
                "state": False
            })

    # Second pass: Update state based on enabled flags
    for item in form_data:
        item_split = str(item).split("_")
        if len(item_split) >= 2 and item_split[-1] == "enabled":
            # If this is an enabled checkbox field
            item_id = item_split[0]
            # Convert checkbox value to boolean - form checkboxes are either present (on) or absent (off)
            enabled = item in form_data and form_data[item] == 'on'

            # Update all entries with this ID
            for entry in result:
                if entry["id"] == item_id:
                    entry["state"] = enabled

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
            if str(item[key]).startswith(value):
                result.append(i)

    if type(key) == list:
        for i, item in enumerate(input_list):
            count = 0
            for sub_i, k in enumerate(key):
                if str(item[key[sub_i]]).startswith(value[sub_i]):
                    count = count + 1
                if count == len(key):
                    result.append(i)

    return result


def process_date_form_fields(form_data):
    """
    Process date fields from forms to handle the hidden actual date values
    and convert them to the proper database format.

    :param form_data: The form data from the request
    :return: Updated form data with properly formatted dates
    """
    updated_form_data = form_data.copy()

    # Find all fields with _actual suffix (hidden date fields)
    for key in form_data.keys():
        if key.endswith('_actual'):
            # Get the base field name without _actual suffix
            base_name = key[:-7]
            # Get the value from the hidden field
            date_value = form_data[key]

            # Apply date_adapter to ensure proper format
            formatted_date = date_adapter(date_value)

            # Update the original field with the formatted date
            updated_form_data[base_name] = formatted_date

            # Remove the _actual field to avoid duplicates
            updated_form_data.pop(key, None)

    return updated_form_data


def process_form_dates(form_data):
    """
    Process all date fields in form data to ensure they're in the correct format
    for database storage.

    :param dict form_data: The form data from request.form
    :return dict: Processed form data with dates in YYYY-MM-DD format
    """
    processed_data = {}

    for key, value in form_data.items():
        if key.endswith('_actual') and value:
            # Get the base field name (without _actual)
            base_key = key[:-7]

            # Process the date value
            processed_date = date_adapter(value)

            # Store with the original field name (not the _actual version)
            processed_data[base_key] = processed_date
        elif not key.endswith('_actual'):
            # For non-date fields or if no _actual field is found, keep as is
            processed_data[key] = value

    return processed_data


def date_adapter(value: str) -> str:
    """
    Updates text overloaded dates to be accepted by the DB with static dates.
    :param str value: YYYY-MM-DD format as string, but also handles other formats like MM/YYYY.
    :return str: YYYY-MM-DD only
    """
    import re

    # Handle None value
    if value is None:
        return None

    # TODO: Add present checkbox to academic and employment templates.
    result: str = value

    # Handle empty strings
    if value == "":
        return "9999-01-01"
    elif value == "hidden":
        return "0001-01-01"
    elif value == "Present":
        return "9999-01-01"

    # Handle MM/YYYY format (e.g., "05/2023")
    mm_yyyy_pattern = re.compile(r'^(\d{1,2})/(\d{4})$')
    mm_yyyy_match = mm_yyyy_pattern.match(value)
    if mm_yyyy_match:
        month, year = mm_yyyy_match.groups()
        # Pad month with leading zero if needed
        month = month.zfill(2)
        return f"{year}-{month}-01"

    # Handle partial dates (YYYY-MM) - convert to expected format
    elif len(value) == 7 and value[4] == '-':
        return f"{value}-01"

    # Handle year only (YYYY)
    elif len(value) == 4 and value.isdigit():
        return f"{value}-01-01"

    # If already in YYYY-MM-DD format, return as is
    elif len(value) == 10 and value[4] == '-' and value[7] == '-':
        return value

    # Handle invalid dates gracefully
    else:
        print(f"WARNING: Invalid date format: '{value}', using default")
        return "9999-01-01"  # Use same value as empty string for invalid input