#!/usr/bin/env python
# -*- coding: utf-8 -*-


from unittest import TestCase

from random import randint

from modules import is_without_special_chars


class TestModuleCommonIsWithoutSpecialChars(TestCase):

    # success cases

    def test_module_common_is_without_special_chars__pure_text(self):
        self.assertTrue(is_without_special_chars("text"))

    def test_module_common_is_without_special_chars__with_underscore(self):
        self.assertTrue(is_without_special_chars("underscore_in_the_center"))
        self.assertTrue(is_without_special_chars("underscore_in_the_end_"))
        self.assertTrue(is_without_special_chars("_underscore_at_the_beginning"))

    def test_module_common_is_without_special_chars__number_in_the_end(self):
        # 'number' is a number from 0 to 9
        for number in range(0, 10):
            self.assertTrue(is_without_special_chars("number_in_the_end_" + str(number)))

        # this for iterates 10 times (from 0 to 9)
        for i in range(0, 10):
            # 'randint(1, 1001)' generates a number between 1 and 1000
            self.assertTrue(is_without_special_chars("random_number_in_the_end_" + str(randint(1, 1001))))

    # error cases

    def test_module_common_is_without_special_chars__special_character(self):
        self.assertFalse(is_without_special_chars("special_character_in_the_end_("))
        self.assertFalse(is_without_special_chars(")_special_character_at_the_beginning"))
        self.assertFalse(is_without_special_chars("special_character_*_in_the_center"))

        special_characters = ["&", "¨", "%", "$", "#", "@", "!", "'", "\"", "|", "\\", "-", "+", "=", "§", "`", "´",
                              "^", "~", "{", "}", "[", "]", "ª", "º", "<", ">", ",", ".", ":", ";", "/", "?", "°"]

        for character in special_characters:
            self.assertFalse(is_without_special_chars("special_character_" + character))

    def test_module_common_is_without_special_chars__accent(self):
        special_characters = ["à", "è", "ì", "ò", "ù",
                              "á", "é", "í", "ó", "ú",
                              "â", "ê", "î", "ô", "û",
                              "ã", "ẽ", "ĩ", "õ", "ũ",
                              "ç"]

        for character in special_characters:
            self.assertFalse(is_without_special_chars("special_character_" + character))

    def test_module_common_is_without_special_chars__number_at_the_beginning(self):
        # 'number' is a number from 0 to 9
        for number in range(0, 10):
            self.assertFalse(is_without_special_chars(str(number) + "_number_at_the_beginning"))

        # this for iterates 10 times (from 0 to 9)
        for i in range(0, 10):
            # 'randint(1, 1001)' generates a number between 1 and 1000
            self.assertFalse(is_without_special_chars(str(randint(1, 1001)) + "_random_number_at_the_beginning"))


# It is not necessary to pyt the main() of unittest here,
# because this file will be call by run_tests.py
