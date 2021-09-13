import re


def remove_html_tags(raw_html):
    cleanr = re.compile("<.*?>")
    cleantext = re.sub(cleanr, "", raw_html)
    return cleantext


def create_description_for_search_results(list_of_descriptions: list) -> str:
    """Removes None values if present from list and returns string which combines correctly formatted description elements from gecko API results."""
    filtered_descriptions = list(filter(None, list_of_descriptions))
    counter = 0
    description = ""
    for item in filtered_descriptions:
        description += item if counter == 0 else "<br>" + item
        counter += 1
    return description
