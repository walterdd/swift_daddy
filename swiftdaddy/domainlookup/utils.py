import re

def splitIntoAlphanum(string):
    string_split = re.sub('[^0-9a-zA-Z]+', ' ', string)
    return string_split.split(' ')

def removeNonAlphanum(string):
    string_list = splitIntoAlphanum(string)
    return ''.join(string_list)
