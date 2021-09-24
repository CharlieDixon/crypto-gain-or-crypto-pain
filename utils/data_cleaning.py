import re
import random

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

def determine_colour(coin_order, colour_dict, alt_colours_for_graphs):
        colour_order = []
        for coin in coin_order:
            if colour_dict.get(coin):
                colour_order.append(colour_dict.get(coin))
            else:
                colour_order.append(random.choice(alt_colours_for_graphs))
        return colour_order
    
def worst_trade(trades):
        """Find lowest value trade and return it as a float, could use func.min() but column in string format so doesn't work."""
        worst_loss = 0
        worst_coin = None
        worst_coin_quote = None
        for trade in trades: 
            if float(trade[2]) < worst_loss:
                unformatted_worst_loss = trade[2]
                worst_loss = float(trade[2])
                worst_coin = trade[0]
                worst_coin_quote = trade[1]
        worst_loss = str(round(worst_loss, 2))
        return worst_coin, worst_coin_quote, worst_loss, unformatted_worst_loss