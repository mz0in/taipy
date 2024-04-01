# Copyright 2021-2024 Avaiga Private Limited
#
# Licensed under the Apache License, Version 2.0 (the "License"); you may not use this file except in compliance with
# the License. You may obtain a copy of the License at
#
#        http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software distributed under the License is distributed on
# an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the License for the
# specific language governing permissions and limitations under the License.

from importlib import util
from unittest.mock import patch

import numpy as np
import pandas as pd
import pytest

from taipy.config.common.scope import Scope
from taipy.core.data.sql_table import SQLTableDataNode


class MyCustomObject:
    def __init__(self, foo=None, bar=None, *args, **kwargs):
        self.foo = foo
        self.bar = bar
        self.args = args
        self.kwargs = kwargs


class TestReadSQLTableDataNode:
    __pandas_properties = [
        {
            "db_name": "taipy",
            "db_engine": "sqlite",
            "table_name": "example",
            "db_extra_args": {
                "TrustServerCertificate": "yes",
                "other": "value",
            },
        },
    ]

    if util.find_spec("pyodbc"):
        __pandas_properties.append(
            {
                "db_username": "sa",
                "db_password": "Passw0rd",
                "db_name": "taipy",
                "db_engine": "mssql",
                "table_name": "example",
                "db_extra_args": {
                    "TrustServerCertificate": "yes",
                },
            },
        )

    if util.find_spec("pymysql"):
        __pandas_properties.append(
            {
                "db_username": "sa",
                "db_password": "Passw0rd",
                "db_name": "taipy",
                "db_engine": "mysql",
                "table_name": "example",
                "db_extra_args": {
                    "TrustServerCertificate": "yes",
                },
            },
        )

    if util.find_spec("psycopg2"):
        __pandas_properties.append(
            {
                "db_username": "sa",
                "db_password": "Passw0rd",
                "db_name": "taipy",
                "db_engine": "postgresql",
                "table_name": "example",
                "db_extra_args": {
                    "TrustServerCertificate": "yes",
                },
            },
        )

    @staticmethod
    def mock_read_value():
        return {"foo": ["baz", "quux", "corge"], "bar": ["quux", "quuz", None]}

    @pytest.mark.parametrize("pandas_properties", __pandas_properties)
    def test_read_pandas(self, pandas_properties):
        custom_properties = pandas_properties.copy()

        sql_data_node_as_pandas = SQLTableDataNode(
            "foo",
            Scope.SCENARIO,
            properties=custom_properties,
        )

        with patch("sqlalchemy.engine.Engine.connect") as engine_mock:
            cursor_mock = engine_mock.return_value.__enter__.return_value
            cursor_mock.execute.return_value = self.mock_read_value()

            pandas_data = sql_data_node_as_pandas.read()
            assert isinstance(pandas_data, pd.DataFrame)
            assert pandas_data.equals(pd.DataFrame(self.mock_read_value()))

    @pytest.mark.parametrize("pandas_properties", __pandas_properties)
    def test_read_numpy(self, pandas_properties):
        custom_properties = pandas_properties.copy()
        custom_properties["exposed_type"] = "numpy"

        sql_data_node_as_pandas = SQLTableDataNode(
            "foo",
            Scope.SCENARIO,
            properties=custom_properties,
        )

        with patch("sqlalchemy.engine.Engine.connect") as engine_mock:
            cursor_mock = engine_mock.return_value.__enter__.return_value
            cursor_mock.execute.return_value = self.mock_read_value()

            numpy_data = sql_data_node_as_pandas.read()
            assert isinstance(numpy_data, np.ndarray)
            assert np.array_equal(numpy_data, pd.DataFrame(self.mock_read_value()).to_numpy())

    @pytest.mark.parametrize("pandas_properties", __pandas_properties)
    def test_read_custom_exposed_type(self, pandas_properties):
        custom_properties = pandas_properties.copy()

        custom_properties.pop("db_extra_args")
        custom_properties["exposed_type"] = MyCustomObject
        sql_data_node = SQLTableDataNode("foo", Scope.SCENARIO, properties=custom_properties)

        mock_return_data = [
            {"foo": "baz", "bar": "qux"},
            {"foo": "quux", "bar": "quuz"},
            {"foo": "corge"},
            {"bar": "grault"},
            {"KWARGS_KEY": "KWARGS_VALUE"},
            {},
        ]

        with patch("sqlalchemy.engine.Engine.connect") as engine_mock:
            cursor_mock = engine_mock.return_value.__enter__.return_value
            cursor_mock.execute.return_value = mock_return_data
            custom_data = sql_data_node.read()

        for row_mock_data, row_custom in zip(mock_return_data, custom_data):
            assert isinstance(row_custom, MyCustomObject)
            assert row_custom.foo == row_mock_data.pop("foo", None)
            assert row_custom.bar == row_mock_data.pop("bar", None)
            assert row_custom.kwargs == row_mock_data

    @pytest.mark.parametrize(
        "tmp_sqlite_path",
        [
            "tmp_sqlite_db_file_path",
            "tmp_sqlite_sqlite3_file_path",
        ],
    )
    def test_sqlite_read_file_with_different_extension(self, tmp_sqlite_path, request):
        tmp_sqlite_path = request.getfixturevalue(tmp_sqlite_path)
        folder_path, db_name, file_extension = tmp_sqlite_path
        properties = {
            "db_engine": "sqlite",
            "table_name": "example",
            "db_name": db_name,
            "sqlite_folder_path": folder_path,
            "sqlite_file_extension": file_extension,
        }

        dn = SQLTableDataNode("sqlite_dn", Scope.SCENARIO, properties=properties)
        data = dn.read()

        assert data.equals(pd.DataFrame([{"foo": 1, "bar": 2}, {"foo": 3, "bar": 4}]))
