#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
    Responsible module to create base handlers.
"""
from json import loads
from abc import abstractmethod, ABCMeta

from psycopg2 import Error, ProgrammingError
from requests import exceptions

from psycopg2._psycopg import DataError
from tornado.web import RequestHandler, HTTPError
from tornado.escape import json_encode, json_decode

from modules.user import get_new_user_struct_cookie
# from settings import HOSTS_ALLOWED


def catch_generic_exception(method):

    def wrapper(self, *args, **kwargs):

        try:
            # try to execute the method
            return method(self, *args, **kwargs)

        # all methods can raise a psycopg exception, so catch it
        except ProgrammingError as error:
            # print(">>>> ", error)
            self.PGSQLConn.rollback()  # do a rollback to comeback in a safe state of DB
            raise HTTPError(500, "Psycopg2 error (psycopg2.ProgrammingError). Please, contact the administrator. " +
                                 "\nInformation: " + str(error) + "\npgcode: " + str(error.pgcode))

        except Error as error:
            # print(">>>> ", dir(error))
            self.PGSQLConn.rollback()  # do a rollback to comeback in a safe state of DB
            raise HTTPError(500, "Psycopg2 error (psycopg2.Error). Please, contact the administrator. " +
                                 "\n Information: " + str(error) + "\npgcode: " + str(error.pgcode))

    return wrapper


def auth_non_browser_based(method):
    """
    Authentication to non browser based service
    :param method: the method decorated
    :return: the method wrapped
    """
    def wrapper(self, *args, **kwargs):

        # if user is not logged in, so return a 403 Forbidden
        if not self.current_user:
            raise HTTPError(403, "It is necessary a user logged in to access this URL.")

        # if the user is logged in, so execute the method
        return method(self, *args, **kwargs)

    return wrapper


def just_run_on_debug_mode(method):
    """
    Just run the method on Debug Mode
    :param method: the method decorated
    :return: the method wrapped
    """
    def wrapper(self, *args, **kwargs):

        # if is not in debug mode, so return a 404 Not Found
        if not self.DEBUG_MODE:
            raise HTTPError(404, "Invalid URL.")

        # if is in debug mode, so execute the method
        return method(self, *args, **kwargs)

    return wrapper


# BASE CLASS

class BaseHandler(RequestHandler):
    """
        Responsible class to be a base handler for the others classes.
        It extends of the RequestHandler class.
    """

    # Static list to be added the all valid urls to one handler
    urls = []

    __AFTER_LOGGED_IN_REDIRECT_TO__ = ",/"
    __AFTER_LOGGED_OUT_REDIRECT_TO__ = "/auth/logout/success/"

    # __init__ for Tornado subclasses
    def initialize(self):
        # get the database instances
        self.PGSQLConn = self.application.PGSQLConn
        # self.Neo4JConn = self.application.Neo4JConn

        self.DEBUG_MODE = self.application.DEBUG_MODE

    # headers

    def set_default_headers(self):
        # self.set_header('Content-Type', 'application/json; charset="utf-8"')
        self.set_header('Content-Type', 'application/json')

        # concat the hosts allowed in a string separated by comma
        # hosts_allowed = ",".join(HOSTS_ALLOWED)

        # self.set_header("Access-Control-Allow-Origin", hosts_allowed)
        # self.set_header("Access-Control-Allow-Origin", "*")
        # self.set_header("Access-Control-Allow-Headers", "x-requested-with")

        # how solve the CORS problem: https://stackoverflow.com/questions/32500073/request-header-field-access-control-allow-headers-is-not-allowed-by-itself-in-pr
        self.set_header("Access-Control-Allow-Origin", "http://localhost:8080")
        self.set_header("Access-Control-Allow-Headers", "Origin, X-Requested-With, Content-Type, Accept, Authorization")
        self.set_header('Access-Control-Allow-Methods', ' POST, GET, PUT, DELETE, OPTIONS')
        self.set_header("Access-Control-Allow-Credentials", "true")

        # self.set_header("Access-Control-Allow-Headers", "Origin, Content-Type, X-Auth-Token, x-requested-with")
        # self.set_header("Access-Control-Allow-Headers", "Origin, Content-Type, X-Auth-Token")

    def options(self, *args, **kwargs):
        """
        This method is necessary to do the CORS works.
        """
        # no body
        self.set_status(204)
        self.finish()

    def get_the_json_validated(self):
        """
            Responsible method to validate the JSON received in the POST method.

            Args:
                Nothing until the moment.

            Returns:
                The JSON validated.

            Raises:
                - HTTPError (400 - Bad request): if don't receive a JSON.
                - HTTPError (400 - Bad request): if the JSON received is empty or is None.
        """

        # Verify if the type of the content is JSON
        if self.request.headers["Content-Type"].startswith("application/json"):
            # Convert string to unicode in Python 2 or convert bytes to string in Python 3
            # How string in Python 3 is unicode, so independent of version, both are converted in unicode
            foo = self.request.body.decode("utf-8")

            # Transform the string/unicode received to JSON (dictionary in Python)
            search = loads(foo)
        else:
            raise HTTPError(400, "It is not a JSON...")  # 400 - Bad request

        if search == {} or search is None:
            raise HTTPError(400, "The search given is empty...")  # 400 - Bad request

        return search

    # LOGIN AND LOGOUT

    @catch_generic_exception
    def auth_login(self, email, password):

        user_in_db = self.PGSQLConn.get_users(email=email, password=password)

        # get the only one user in list returned
        user_in_db = user_in_db["features"][0]

        # insert the user in cookie
        self.set_current_user(user=user_in_db, new_user=True)

    @catch_generic_exception
    def login(self, user_json):
        # looking for a user in db, if not exist user, so create a new one
        # user_in_db = self.PGSQLConn.get_user_in_db(user["email"])

        try:
            user_in_db = self.PGSQLConn.get_users(email=user_json["properties"]["email"])
        except HTTPError as error:
            # if the error is different of 404, raise a exception...
            if error.status_code != 404:
                raise HTTPError(500, str(error))
            # ... because I expected a 404 to create a new user
            id_in_json = self.PGSQLConn.create_user(user_json)
            user_in_db = self.PGSQLConn.get_users(user_id=str(id_in_json["id"]))

        # get the only one user in list returned
        user_in_db = user_in_db["features"][0]

        # insert the user in cookie
        self.set_current_user(user=user_in_db, new_user=True)

    def logout(self):
        # if there is no user logged, so raise a exception
        if not self.get_current_user():
            raise HTTPError(404, "Not found any user to logout.")

        # if there is a user logged, so remove it from cookie
        self.clear_cookie("user")

        # self.redirect(self.__AFTER_LOGGED_OUT_REDIRECT_TO__)

    # COOKIES

    def set_current_user(self, user={}, new_user=True):
        if new_user:
            # if new user, so create a new cookie
            user_cookie = get_new_user_struct_cookie()
        else:
            # if already exist, so get the cookie
            user_cookie = json_decode(self.get_secure_cookie("user"))

        # insert the information
        user_cookie["user"] = user

        # set the cookie (it needs to be separated)
        # transform dictionary in JSON and add in cookie
        encode = json_encode(user_cookie)
        self.set_secure_cookie("user", encode)

    def get_current_user(self):
        user_cookie = self.get_secure_cookie("user")

        if user_cookie:
            return json_decode(user_cookie)
        else:
            return None

    def get_current_user_id(self):
        user_cookie = self.get_secure_cookie("user")

        if user_cookie:
            user = json_decode(user_cookie)
            return user["user"]["properties"]["id"]
        else:
            return None

    # URLS

    def get_aguments(self):
        """
        Create the 'arguments' dictionary.
        :return: the 'arguments' dictionary contained the arguments and parameters of URL,
                in a easier way to work with them.
        """
        arguments = {k: self.get_argument(k) for k in self.request.arguments}

        # "q" is the query argument, that have the fields of query
        # if "q" in arguments:
        #     arguments["q"] = self.get_q_param_as_dict_from_str(arguments["q"])
        # else:
        #     # if "q" is not in arguments, so put None value
        #     arguments["q"] = None

        # if key "format" not in arguments, put a default value, the "geojson"
        # if "format" not in arguments:
        #     arguments["format"] = "geojson"

        return arguments

    # AUXILIAR FUNCTION

    def is_element_type_valid(self, element, element_json):
        multi_element = element_json["features"][0]["geometry"]["type"]

        return ((element == "point" and multi_element == "MultiPoint") or
                (element == "line" and multi_element == "MultiLineString") or
                (element == "polygon" and multi_element == "MultiPolygon"))

    def get_q_param_as_dict_from_str(self, str_query):
        str_query = str_query.strip()

        # normal case: I have a query
        prequery = str_query.replace(r"[", "").replace(r"]", "").split(",")

        # with each part of the string, create a dictionary
        query = {}
        for condiction in prequery:
            parts = condiction.split("=")
            query[parts[0]] = parts[1]

        return query


# TEMPLATE METHOD

class BaseHandlerTemplateMethod(BaseHandler, metaclass=ABCMeta):
    # GET METHOD

    def _get_feature(self, *args, **kwargs):
        raise NotImplementedError

    @catch_generic_exception
    def get_method_api_feature(self, *args):
        arguments = self.get_aguments()

        try:
            # break the arguments dict in each parameter of method
            result = self._get_feature(*args, **arguments)
        except DataError as error:
            # print("Error: ", error)
            raise HTTPError(500, "Problem when get a resource. Please, contact the administrator.")

        # Default: self.set_header('Content-Type', 'application/json')
        self.write(json_encode(result))

    # PUT METHOD

    def _create_feature(self, feature_json, current_user_id):
        raise NotImplementedError

    def put_method_api_feature_create(self, *args):
        # get the JSON sent, to add in DB
        feature_json = self.get_the_json_validated()
        current_user_id = self.get_current_user_id()

        try:
            json_with_id = self._create_feature(feature_json, current_user_id)

            # do commit after create a feature
            self.PGSQLConn.commit()
        except DataError as error:
            # print("Error: ", error)
            raise HTTPError(500, "Problem when create a resource. Please, contact the administrator.")

        # Default: self.set_header('Content-Type', 'application/json')
        self.write(json_encode(json_with_id))

    def _update_feature(self, *args, **kwargs):
        raise NotImplementedError

    def put_method_api_feature_update(self, *args):
        # get the JSON sent, to add in DB
        feature_json = self.get_the_json_validated()
        # current_user_id = self.get_current_user_id()

        try:
            # json_with_id = self._create_feature(feature_json, current_user_id)
            self._update_feature(feature_json)

            # do commit after create a feature
            self.PGSQLConn.commit()
        except DataError as error:
            # print("Error: ", error)
            raise HTTPError(500, "Problem when update a feature. Please, contact the administrator.")

    def _close_feature(self, *args, **kwargs):
        raise NotImplementedError

    def _request_feature(self, *args, **kwargs):
        raise NotImplementedError

    def _accept_feature(self, *args, **kwargs):
        raise NotImplementedError

    @catch_generic_exception
    def put_method_api_feature(self, *args):
        param = args[0]

        # remove the first argument ('param'), because it is not necessary anymore
        args = args[1:]  # get the second argument and so on

        if param == "create":
            # self._create_feature(*args)
            self.put_method_api_feature_create(*args)
        # elif param == "update":
        #     # self._update_feature(*args)
        #     self.put_method_api_feature_update(*args)
        elif param == "close":
            self._close_feature(*args)
        elif param == "request":
            self._request_feature(*args)
        elif param == "accept":
            self._accept_feature(*args)
        else:
            raise HTTPError(404, "Invalid URL.")

    # DELETE METHOD

    def _delete_feature(self, *args, **kwargs):
        raise NotImplementedError

    @catch_generic_exception
    def delete_method_api_feature(self, *args):
        try:
            self._delete_feature(*args)

            # do commit after delete the feature
            self.PGSQLConn.commit()
        except DataError as error:
            # print("Error: ", error)
            raise HTTPError(500, "Problem when delete a resource. Please, contact the administrator.")


# SUBCLASSES


class BaseHandlerUser(BaseHandlerTemplateMethod):

    def _get_feature(self, *args, **kwargs):
        return self.PGSQLConn.get_users(**kwargs)

    def _create_feature(self, feature_json, current_user_id):
        return self.PGSQLConn.create_user(feature_json)

    def _update_feature(self, *args, **kwargs):
        raise NotImplementedError

    def _delete_feature(self, *args, **kwargs):
        # TODO: one user just can delete itself or if the user is a admin
        user_id = args[0]

        self.PGSQLConn.delete_user(user_id)

        current_user_id = self.get_current_user_id()

        # If the user delete itself (the owner of account), so logout it
        if current_user_id == int(user_id):
            self.logout()


# class BaseHandlerUserGroup(BaseHandlerTemplateMethod):
#
#     def _get_feature(self, *args, **kwargs):
#         return self.PGSQLConn.get_user_group(**kwargs)
#
#     def _create_feature(self, feature_json, current_user_id):
#         return self.PGSQLConn.create_user_group(feature_json, current_user_id)
#
#     def _update_feature(self, *args, **kwargs):
#         raise NotImplementedError
#
#     def _request_feature(self, *args, **kwargs):
#         raise NotImplementedError
#
#     def _accept_feature(self, *args, **kwargs):
#         raise NotImplementedError
#
#     def _delete_feature(self, *args, **kwargs):
#         # receive user_id and group_id as argument
#         arguments = self.get_aguments()
#
#         self.PGSQLConn.delete_user_group(**arguments)


# class BaseHandlerGroup(BaseHandlerTemplateMethod):
#
#     def _get_feature(self, *args, **kwargs):
#         return self.PGSQLConn.get_group(**kwargs)
#
#     def _create_feature(self, feature_json, current_user_id):
#         return self.PGSQLConn.create_group(feature_json, current_user_id)
#
#     def _update_feature(self, feature_json):
#         return self.PGSQLConn.update_group(feature_json)
#
#     def _delete_feature(self, *args, **kwargs):
#         self.PGSQLConn.delete_group_in_db(*args)


# class BaseHandlerProject(BaseHandlerTemplateMethod):
#
#     def _get_feature(self, *args, **kwargs):
#         return self.PGSQLConn.get_projects(**kwargs)
#
#     def _create_feature(self, feature_json, current_user_id):
#         return self.PGSQLConn.create_project(feature_json, current_user_id)
#
#     def _update_feature(self, *args, **kwargs):
#         raise NotImplementedError
#
#     def _delete_feature(self, *args, **kwargs):
#         self.PGSQLConn.delete_project_in_db(*args)


class BaseHandlerLayer(BaseHandlerTemplateMethod):

    def _get_feature(self, *args, **kwargs):
        return self.PGSQLConn.get_layers(**kwargs)

    def _create_feature(self, feature_json, current_user_id):
        return self.PGSQLConn.create_layer(feature_json, current_user_id)

    def _update_feature(self, *args, **kwargs):
        raise NotImplementedError

    def _delete_feature(self, *args, **kwargs):
        self.delete_validation(*args)

        self.PGSQLConn.delete_layer_in_db(*args)

    def delete_validation(self, resource_id):
        """
        Verify if the user has permition to delete a layer
        :param resource_id: layer id
        :return:
        """
        current_user_id = self.get_current_user_id()

        layer = self.PGSQLConn.get_layers(layer_id=resource_id)
        fk_user_id_author = layer["features"][0]["properties"]["fk_user_id_author"]

        if current_user_id != fk_user_id_author:
            raise HTTPError(403, "The owner of the layer is the unique who can delete the layer.")








# class BaseHandlerFeatureTable(BaseHandlerTemplateMethod):
#
#     def _get_feature(self, *args, **kwargs):
#         raise NotImplementedError
#
#     @catch_generic_exception
#     def _create_feature(self):
#         # get the JSON sent, to add in DB
#         feature_json = self.get_the_json_validated()
#         current_user_id = self.get_current_user_id()
#
#         try:
#             self.PGSQLConn.create_feature_table(feature_json, current_user_id)
#
#             # do commit after create a feature
#             self.PGSQLConn.commit()
#         except DataError as error:
#             # print("Error: ", error)
#             raise HTTPError(500, "Problem when create a resource. Please, contact the administrator.")
#         except ProgrammingError as error:
#             if error.pgcode == "42P07":
#                 self.PGSQLConn.rollback()  # do a rollback to comeback in a safe state of DB
#                 raise HTTPError(400, "Feature table already exist.")
#             else:
#                 raise error
#
#     def _update_feature(self, *args, **kwargs):
#         raise NotImplementedError
#
#     def _delete_feature(self, *args, **kwargs):
#         raise NotImplementedError


# class BaseHandlerChangeset(BaseHandlerTemplateMethod):
#
#     def _get_feature(self, *args, **kwargs):
#         return self.PGSQLConn.get_changesets(**kwargs)
#
#     def _create_feature(self, feature_json, current_user_id):
#         return self.PGSQLConn.create_changeset(feature_json, current_user_id)
#
#     def _update_feature(self, *args, **kwargs):
#         raise NotImplementedError
#
#     def _close_feature(self, *args, **kwargs):
#         try:
#             self.PGSQLConn.close_changeset(args[0])
#         except DataError as error:
#             # print("Error: ", error)
#             raise HTTPError(500, "Problem when close a feature. Please, contact the administrator.")
#
#     def _delete_feature(self, *args, **kwargs):
#         self.PGSQLConn.delete_changeset_in_db(*args)


# class BaseHandlerNotification(BaseHandlerTemplateMethod):
#
#     def _get_feature(self, *args, **kwargs):
#         return self.PGSQLConn.get_notification(**kwargs)
#
#     def _create_feature(self, feature_json, current_user_id):
#         return self.PGSQLConn.create_notification(feature_json, current_user_id)
#
#     def _update_feature(self, *args, **kwargs):
#         raise NotImplementedError
#
#     def _delete_feature(self, *args, **kwargs):
#         self.PGSQLConn.delete_notification_in_db(*args)


# class BaseHandlerElement(BaseHandlerTemplateMethod):
#
#     def _get_feature(self, *args, **kwargs):
#         return self.PGSQLConn.get_elements(args[0], **kwargs)
#
#     def _create_feature(self, feature_json, current_user_id):
#         raise NotImplementedError
#
#     @catch_generic_exception
#     def put_method_api_feature_create(self, *args):
#         element = args[0]
#         feature_json = self.get_the_json_validated()
#
#         if not self.is_element_type_valid(element, feature_json):
#             raise HTTPError(404, "Invalid URL.")
#
#         # current_user_id = self.get_current_user_id()
#
#         list_of_id_of_features_created = []
#
#         try:
#             for feature in feature_json["features"]:
#                 # the CRS is necessary inside the geometry, because the DB needs to know the EPSG
#                 feature["geometry"]["crs"] = feature_json["crs"]
#
#                 list_of_id_of_features_created.append(
#                     # create_element returns the id of the element created
#                     self.PGSQLConn.create_element(element, feature)
#                 )
#
#             # send the elements created to DB
#             self.PGSQLConn.commit()
#
#         except psycopg2.Error as error:
#             # print(">>>> ", error)
#             self.PGSQLConn.rollback()  # do a rollback to comeback in a safe state of DB
#
#             if error.pgcode == "VW001":
#                 # VW001 - The changeset with id=#ID was closed at #CLOSED_AT, so it is not possible to use it
#                 raise HTTPError(409, str(error))
#
#             # if the db error is undefined so raise it again...
#             raise error
#             # raise HTTPError(500, "Psycopg2 error. Please, contact the administrator.")
#             # raise HTTPError(500, "Psycopg2 error. Please, contact the administrator. Information: " + str(error))
#
#         except DataError as error:
#             # print("Error: ", error)
#             raise HTTPError(500, "Problem when create a feature. Please, contact the administrator.")
#
#         # Default: self.set_header('Content-Type', 'application/json')
#         self.write(json_encode(list_of_id_of_features_created))
#
#     def _update_feature(self, *args, **kwargs):
#         raise NotImplementedError
#
#     def _delete_feature(self, *args, **kwargs):
#         self.PGSQLConn.delete_element_in_db(*args)


# class BaseHandlerThemeTree(BaseHandlerTemplateMethod):
#
#     def _get_feature(self, *args, **kwargs):
#         return self.Neo4JConn.get_theme_tree()
#
#     def _create_feature(self, feature_json, current_user_id):
#         raise NotImplementedError
#
#     def _update_feature(self, *args, **kwargs):
#         raise NotImplementedError
#
#     def _delete_feature(self, *args, **kwargs):
#         raise NotImplementedError
#
#     # def get_method_api_theme(self, param):
#     #     if param == "tree":
#     #         self.get_method_api_theme_tree()
#     #     # else:
#     #     #     self.get_method_api_theme_other()
#
#     # def get_method_api_theme_tree(self):
#     #     try:
#     #         result = self.Neo4JConn.get_theme_tree()
#     #     except DataError as error:
#     #         # print("Error: ", error)
#     #         raise HTTPError(500, "Problem when get the theme tree. Please, contact the administrator.")
#     #     except exceptions.ConnectionError as error:
#     #         # print("Error: ", error)
#     #         raise HTTPError(503, "Connection refused. Please, contact the administrator.")
#     #
#     #     # Default: self.set_header('Content-Type', 'application/json')
#     #     self.write(json_encode(result))
#
#     # def put_method_api_layer_create(self):
#     #     # get the JSON sent, to add in DB
#     #     layer_json = self.get_the_json_validated()
#     #
#     #     current_user_id = self.get_current_user_id()
#     #
#     #     try:
#     #         json_with_id = self.PGSQLConn.create_layer(layer_json, current_user_id)
#     #     except DataError as error:
#     #         # print("Error: ", error)
#     #         raise HTTPError(500, "Problem when create a layer. Please, contact the administrator.")
#     #
#     #     # Default: self.set_header('Content-Type', 'application/json')
#     #     self.write(json_encode(json_with_id))
#     #
#     # def put_method_api_layer(self, param):
#     #     # param on this case is "create" or "update"
#     #     if param == "create":
#     #         self.put_method_api_layer_create()
#     #     elif param == "update":
#     #         self.write(json_encode({"ok", 1}))
#     #     else:
#     #         raise HTTPError(404, "Invalid URL")
#     #
#     # def delete_method_api_layer(self, param):
#     #     # param on this case is the id of element
#     #     try:
#     #         self.PGSQLConn.delete_layer_in_db(param)
#     #     except DataError as error:
#     #         # print("Error: ", error)
#     #         raise HTTPError(500, "Problem when delete a layer. Please, contact the administrator.")

