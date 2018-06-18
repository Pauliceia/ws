#!/usr/bin/env python
# -*- coding: utf-8 -*-


from unittest import TestCase
from util.tester import UtilTester


class TestAPIImport(TestCase):

    def setUp(self):
        # create a tester passing the unittest self
        self.tester = UtilTester(self)

        # DO LOGIN
        self.tester.auth_login("gabriel@admin.com", "gabriel")

        self.folder_name = "files/"
        self.f_table_name = "points"

        ##################################################
        # create a new layer
        ##################################################
        layer = {
            'type': 'Layer',
            'properties': {'layer_id': -1, 'f_table_name': self.f_table_name, 'name': 'Points',
                           'description': '', 'source_description': '',
                           'reference': [1050], 'keyword': [1041]}
        }
        layer = self.tester.api_layer_create(layer, is_to_create_feature_table=False)
        self.layer_id = layer["properties"]["layer_id"]

        ##################################################
        # create a new changeset
        ##################################################
        changeset = {
            'properties': {'changeset_id': -1, 'layer_id': self.layer_id, 'description': 'Import points.shp'},
            'type': 'Changeset'
        }
        changeset = self.tester.api_changeset_create(changeset)
        self.changeset_id = changeset["properties"]["changeset_id"]

    def tearDown(self):
        ##################################################
        # remove the layer
        ##################################################
        # CLOSE THE CHANGESET
        self.tester.api_changeset_close(changeset_id=self.changeset_id)

        # DELETE THE CHANGESET (the changeset is automatically removed when delete a layer)
        # self.tester.api_changeset_delete(changeset_id=changeset_id)

        # REMOVE THE layer AFTER THE TESTS
        self.tester.api_layer_delete(self.layer_id)

        # it is not possible to find the layer that just deleted
        self.tester.api_layer_error_404_not_found(layer_id=self.layer_id)

        # DO LOGOUT AFTER THE TESTS
        self.tester.auth_logout()

    # import - create

    def test_post_import_shp(self):
        ##################################################
        # import the shapefile with the created layer (the feature table will be the shapefile)
        ##################################################
        file_name = "points.zip"
        with open(self.folder_name + file_name, mode='rb') as file:  # rb = read binary
            binary_file_content = file.read()

            self.tester.api_import_shp_create(binary_file_content, f_table_name=self.f_table_name,
                                              file_name=file_name, changeset_id=self.changeset_id)


class TestAPIImportError(TestCase):

    def setUp(self):
        # create a tester passing the unittest self
        self.tester = UtilTester(self)

        # DO LOGIN
        self.tester.auth_login("gabriel@admin.com", "gabriel")

        self.folder_name = "files/"
        self.f_table_name = "feature_table"

        ##################################################
        # create a new layer
        ##################################################
        layer = {
            'type': 'Layer',
            'properties': {'layer_id': -1, 'f_table_name': self.f_table_name, 'name': 'Addresses in 1930',
                           'description': '', 'source_description': '',
                           'reference': [1050], 'keyword': [1041]}
        }
        layer = self.tester.api_layer_create(layer, is_to_create_feature_table=False)
        self.layer_id = layer["properties"]["layer_id"]

        ##################################################
        # create a new changeset
        ##################################################
        changeset = {
            'properties': {'changeset_id': -1, 'layer_id': self.layer_id, 'description': 'Import points.shp'},
            'type': 'Changeset'
        }
        changeset = self.tester.api_changeset_create(changeset)
        self.changeset_id = changeset["properties"]["changeset_id"]

    def tearDown(self):
        ##################################################
        # remove the layer
        ##################################################
        # CLOSE THE CHANGESET
        self.tester.api_changeset_close(changeset_id=self.changeset_id)

        # DELETE THE CHANGESET (the changeset is automatically removed when delete a layer)
        # self.tester.api_changeset_delete(changeset_id=changeset_id)

        # REMOVE THE layer AFTER THE TESTS
        self.tester.api_layer_delete(self.layer_id)

        # it is not possible to find the layer that just deleted
        self.tester.api_layer_error_404_not_found(layer_id=self.layer_id)

        # DO LOGOUT AFTER THE TESTS
        self.tester.auth_logout()

    # import - create

    def test_post_import_shp_error_400_bad_request_zip_without_shapefile(self):
        ##################################################
        # try to import the shapefile, but the zip doesn't have a shapefile
        ##################################################
        file_name = "folder_with_nothing.zip"
        with open(self.folder_name + file_name, mode='rb') as file:  # rb = read binary
            binary_file_content = file.read()

            self.tester.api_import_shp_create_error_400_bad_request(binary_file_content, f_table_name=self.f_table_name,
                                                                    file_name=file_name, changeset_id=self.changeset_id)

    def test_post_import_shp_error_400_bad_request_file_name_is_not_zip(self):
        ##################################################
        # try to import the shapefile, but the zip doesn't have a shapefile
        ##################################################
        file_name = "folder_with_nothing.zip"
        with open(self.folder_name + file_name, mode='rb') as file:  # rb = read binary
            binary_file_content = file.read()

            self.tester.api_import_shp_create_error_400_bad_request(binary_file_content, f_table_name=self.f_table_name,
                                                                    file_name="folder_with_nothing",
                                                                    changeset_id=self.changeset_id)

    def test_post_import_shp_error_400_bad_request_argument_is_missing(self):
        ##################################################
        # import the shapefile with the created layer (the feature table will be the shapefile)
        ##################################################
        file_name = "points.zip"
        with open(self.folder_name + file_name, mode='rb') as file:  # rb = read binary
            binary_file_content = file.read()

            # try to import without binary_file_content
            self.tester.api_import_shp_create_error_400_bad_request("", f_table_name=self.f_table_name,
                                                                    file_name=file_name, changeset_id=self.changeset_id)

            # try to import without f_table_name
            self.tester.api_import_shp_create_error_400_bad_request(binary_file_content,
                                                                    file_name=file_name, changeset_id=self.changeset_id)

            # try to import without file_name
            self.tester.api_import_shp_create_error_400_bad_request(binary_file_content, f_table_name=self.f_table_name,
                                                                    changeset_id=self.changeset_id)

            # try to import without changeset_id
            self.tester.api_import_shp_create_error_400_bad_request(binary_file_content, f_table_name=self.f_table_name,
                                                                    file_name=file_name)

# It is not necessary to pyt the main() of unittest here,
# because this file will be call by run_tests.py
