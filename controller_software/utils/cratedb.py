# Description: Class to connect to a CrateDB and query data from it
# Author: Martin Altenburger

import crate.client
import pandas as pd


class CrateDBConnection:
    """
    Class for a connection to a CrateDB

    Args:
        - crate_db_url: URL of the CrateDB
        - crate_db_user: Name of the User of CrateDB
        - crate_db_pw: Password of the User of CrateDB
        - crate_db_ssl: Verify the SSL-Cert?
    """

    def __init__(
        self,
        crate_db_url: str,
        crate_db_user: str = None,
        crate_db_pw: str = None,
        crate_db_ssl: bool = False,
    ) -> None:
        self.crate_db_url = crate_db_url
        self.crate_db_user = crate_db_user
        self.crate_db_pw = crate_db_pw
        self.crate_db_ssl = crate_db_ssl

    def get_data(
        self,
        service: str,
        entity: str,
        entity_type: str,
        attributes: list,
        from_date: str,
        to_date: str,
        limit: int = 100000,
    ):
        """
        Function to query data from cratedb

        Args:
            - service: Name of the Fiware Service
            - entity: ID of the entity
            - entity_type: type of the entity
            - attributes: list of attribute names
            - from_date: timestamp from which data is to be retrieved (Milliseconds or Datetime (%Y-%m-%dT%H:%M:%S%z))
            - to_date: timestamp up to which data is to be retrieved (Milliseconds or Datetime (%Y-%m-%dT%H:%M:%S%z))
            - limit: maximal number of datapoints

        Return:
            - dataframe with time index in utc and attributes as columns
        """
        if self.crate_db_user is None:
            connection = crate.client.connect(self.crate_db_url)
        else:
            connection = crate.client.connect(
                self.crate_db_url,
                username=self.crate_db_user,
                password=self.crate_db_pw,
                verify_ssl_cert=self.crate_db_ssl,
            )

        attrs = "'time_index'"
        for attribute in list(attributes):
            attrs += ", '" + str(attribute) + "'"

        cursor = connection.cursor()

        # check which column exists
        sql_query = f"""SELECT column_name FROM information_schema.columns WHERE table_name = 'et{entity_type}' and table_schema = 'mt{service}'  AND column_name IN ({attrs})"""
        cursor.execute(sql_query)
        attributes_db = list(set([column[0] for column in cursor.fetchall()]))

        # query existing columns
        attrs = ""
        for attribute in attributes_db:
            if attribute == attributes_db[-1]:
                attrs += '"' + str(attribute) + '"'
            else:
                attrs += '"' + str(attribute) + '", '

        sql_query = f"""SELECT {attrs} FROM mt{service}.et{entity_type} WHERE entity_id = '{entity}' AND time_index > '{from_date}' AND time_index < '{to_date}' limit {limit}"""
        cursor.execute(sql_query)
        results = cursor.fetchall()

        if len(results) > 0:
            df = pd.DataFrame(results)

            columns = [desc[0] for desc in cursor.description]
            df.columns = columns

            df.time_index = pd.to_datetime(df.time_index, unit="ms").dt.tz_localize(
                "UTC"
            )
            df.rename(columns={"time_index": "datetime"}, inplace=True)
            df.set_index(keys="datetime", drop=True, inplace=True)

        else:
            df = pd.DataFrame()

        cursor.close()
        connection.close()

        return df
