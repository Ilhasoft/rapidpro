# -*- coding: utf-8 -*-

__author__ = 'teehamaral'

from unidecode import unidecode


def to_ascii(text):
    return unidecode(text.decode('UTF-8'))
