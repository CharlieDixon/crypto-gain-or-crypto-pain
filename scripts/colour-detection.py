"""Script which uses ColorThief package to find the dominant colour in a list of cryptocurrency png images and 
then converts the resulting rgb value to a hex value for use in graph elements representing a given coin.
Writes a json file containing these pairings."""
from colorthief import ColorThief
from os import listdir
from os.path import isfile, join
import json

filelist = [f for f in listdir("pngs") if isfile(join("pngs", f))]


def rgb_to_hex(rgb):
    r, g, b = rgb
    return "#{:02x}{:02x}{:02x}".format(r, g, b)


colours = {}
for coin in filelist:
    color_thief = ColorThief("pngs/" + coin)
    dominant_colour = color_thief.get_color()
    hex_colour = rgb_to_hex(dominant_colour)
    coin_name = coin.replace(".png", "").upper()
    colours[coin_name] = hex_colour

json_file = open("../resources/crypto-colours.json", "w")
json.dump(colours, json_file)
json_file.close()
