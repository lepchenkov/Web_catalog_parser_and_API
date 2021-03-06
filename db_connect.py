import sys
import os
import logging
from sqlalchemy import create_engine, update, text
from sqlalchemy import Column, String, Integer, MetaData, Table
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
import time
from datetime import datetime


class Postgres_db:

    def __init__(self, db_config):
        self._engine = create_engine(db_config)
        self._connect = self._engine.connect()
        self._meta = MetaData(self._engine)

    def _query(self, query):
        return self._connect.execute(query)

    def _reflect_table(self, table_name):
        table = Table(table_name,
                      self._meta, autoload=True,
                      autoload_with=self._engine)
        return table

    def create_tables(self):
        categories_query = """CREATE TABLE categories
                              (id SERIAL PRIMARY KEY,
                              name VARCHAR (255) NOT NULL);"""
        self._query(categories_query)
        subcategories_lvl1_query = """CREATE TABLE subcategories_lvl1
                                      (id SERIAL PRIMARY KEY,
                                      name VARCHAR (255),
                                      category_id INT REFERENCES
                                      categories ON DELETE RESTRICT);"""
        self._query(subcategories_lvl1_query)
        subcategories_lvl2_query = """CREATE TABLE subcategories_lvl2
                                      (id SERIAL PRIMARY KEY,
                                      name VARCHAR (255) NOT NULL,
                                      url VARCHAR (255) NOT NULL,
                                      parsed_at TIMESTAMP DEFAULT NULL,
                                      subcat_lvl1_id INT NOT NULL REFERENCES
                                      subcategories_lvl1 ON DELETE RESTRICT);"""
        self._query(subcategories_lvl2_query)
        product_table_query = """CREATE TABLE products
                                 (id SERIAL PRIMARY KEY,
                                 url VARCHAR (255) NULL,
                                 name VARCHAR (255) NULL,
                                 price NUMERIC(6,2) NULL,
                                 units VARCHAR NULL,
                                 description VARCHAR NULL,
                                 image_url VARCHAR NULL,
                                 is_trend BOOLEAN NULL,
                                 parsed_at TIMESTAMP DEFAULT NULL,
                                 subcat_lvl2_id INT NOT NULL REFERENCES
                                 subcategories_lvl2 ON DELETE RESTRICT);"""
        self._query(product_table_query)
        product_properties_query = """CREATE TABLE product_properties
                                      (id SERIAL PRIMARY KEY,
                                      name VARCHAR,
                                      value VARCHAR,
                                      product_id INT NOT NULL REFERENCES
                                      products ON DELETE RESTRICT);"""
        self._query(product_properties_query)
        return True

    def drop_existing_tables_from_db(self):
        statement = """DROP TABLE categories,subcategories_lvl1,
                       subcategories_lvl2, products, product_properties;"""
        return self._query(statement)

    def get_table_names_from_database(self):
        statement = """SELECT table_name FROM information_schema.tables
                       WHERE table_schema='public'"""
        result_set = self._query(statement)
        for tablename in result_set:
            yield tablename

    def select_product_by_id(self, prod_id):
        statement = text("SELECT * FROM products WHERE id=:product_id").\
                    bindparams(product_id=prod_id)
        return self._query(statement)

    def category_item_insert(self, category_name):
        statement = text("""INSERT INTO categories
                            VALUES (DEFAULT,
                            :category_name)
                            RETURNING id;""").\
                            bindparams(category_name=category_name)
        result = self._connect.execute(statement).fetchone()[0]
        return result

    def subcat_lvl1_insert(self, subcat_lvl1_name, parent_id):
        statement = text("""INSERT INTO subcategories_lvl1
                            VALUES (DEFAULT,
                            :name, :parent_id)
                            RETURNING id;""").\
                            bindparams(name=subcat_lvl1_name,
                                       parent_id=parent_id)
        result = self._connect.execute(statement).fetchone()[0]
        return result

    def subcat_lvl2_insert(self, subcat_lvl2_dict, subcat_lvl1_id):
        statement = text("""INSERT INTO subcategories_lvl2
                            VALUES (DEFAULT,
                            :name, :url, NULL,
                            :parent_id);""").\
                            bindparams(name=subcat_lvl2_dict['name'],
                                       url=subcat_lvl2_dict['url'],
                                       parent_id=subcat_lvl1_id
                                       )
        return self._connect.execute(statement)

    def get_unparsed_subcat_lvl2_entry(self):
        statement = """SELECT id, url, name from subcategories_lvl2
                       WHERE parsed_at IS NULL LIMIT 1;"""
        entry = self._query(statement).fetchone()
        logging.info('db.Get unparsed subcat_lvl2_entry1 {}'.format(str(entry)))
        dict_ = {
                 'id': entry[0],
                 'url': entry[1],
                 'name': entry[2]
                 }
        logging.info('db.Get unparsed subcat_lvl2_entry {}'.format(dict_['url']))
        return dict_

    def _current_timestamp(self):
        ts = time.time()
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        return timestamp

    def update_lvl2_entry_set_parsed_at(self, entry_id):
        statement = text("""UPDATE subcategories_lvl2 SET
                            parsed_at=:timestamp
                            WHERE id=:entry_id;""").\
                            bindparams(entry_id=entry_id,
                                       timestamp=self._current_timestamp())
        return self._query(statement)

    def product_initial_insert(self, product_dict):
        statement = text("""INSERT INTO products
                            VALUES (DEFAULT,
                            :url, NULL, NULL, NULL,
                            NULL, NULL, NULL, NULL,
                            (SELECT id from subcategories_lvl2
                            WHERE name=:parent_name LIMIT 1))
                            RETURNING id;""").\
                            bindparams(url=product_dict['url'],
                                       parent_name=product_dict['parent']
                                       )
        return self._query(statement).fetchone()[0]

    def get_unparsed_product_entry(self):
        statement = """SELECT id, url from products
                       WHERE parsed_at IS NULL LIMIT 1;"""
        entry = self._query(statement).fetchone()
        dict_ = {
                 'id': entry[0],
                 'url': entry[1],
                 }
        return dict_

    def product_update(self, product_id, product_dict):
        statement = text("""UPDATE products SET
                            name=:name,
                            price=:price,
                            units=:units,
                            description=:description,
                            image_url=:image_url,
                            is_trend=:is_trend,
                            parsed_at=:timestamp
                            WHERE id=:product_id;""").\
                            bindparams(product_id=product_id,
                                       name=product_dict['name'],
                                       price=product_dict['price'],
                                       units=product_dict['product_units'],
                                       description=product_dict['description'],
                                       image_url=product_dict['image_url'],
                                       is_trend=product_dict['is_trend'],
                                       timestamp=self._current_timestamp()
                                       )
        return self._query(statement)

    def product_update_uknown_error(self, product_id):
        unknown_failure_dict = {
                                'name': 'error',
                                'price': None,
                                'product_units': None,
                                'description': 'error',
                                'characteristics': None,
                                'similar_products': None,
                                'image_url': None,
                                'is_trend': None,
                                }
        self._db.product_update(entry_id, unknown_failure_dict)

    def product_features_insert(self, feature_name, feature_value, product_id):
        statement = text("""INSERT INTO product_properties
                            VALUES (DEFAULT, :name, :value, :product_id);""").\
                            bindparams(name=feature_name,
                                       value=feature_value,
                                       product_id=product_id)
        return self._query(statement)

    def check_if_subcats_lvl2_table_is_not_empty(self):
        try:
            response = self._query("SELECT COUNT(*) FROM subcategories_lvl2;")\
                           .fetchone()[0]
            return response >= 10
        except Exception as e:
            logging.exception(e)
            return False

    def check_if_all_lvl2_links_are_parsed(self):
        response = self._query("""SELECT COUNT(*) FROM
                                  subcategories_lvl2 WHERE parsed_at
                                  IS NULL;""").fetchone()[0]
        return response == 0

    def check_if_all_product_links_are_parsed(self):
        response = self._query("""SELECT COUNT(*) FROM
                                  products WHERE parsed_at
                                  IS NULL;""").fetchone()[0]
        return response == 0

    def remove_entry_from_product_table(self, id, hard=False):
        if hard is True:
            statement = text("""DELETE FROM products
                                WHERE id=:id;""").\
                                bindparams(id=id)
            return self._query(statement)
        statement1 = text("""UPDATE products SET
                             deleted_at=:timestamp
                             WHERE id=:id;""").\
                             bindparams(id=id,
                                        timestamp=self._current_timestamp()
                                        )
        self._query(statement1)
        statement2 = text("""UPDATE product_properties SET
                             deleted_at=:timestamp
                             WHERE product_id=:id;""").\
                             bindparams(id=id,
                                        timestamp=self._current_timestamp()
                                        )
        self._query(statement2)
        return True

    def get_product_by_id(self, prod_id):
        statement = text("""SELECT * FROM products
                            WHERE id=:product_id
                            AND deleted_at IS NULL""").\
                            bindparams(product_id=prod_id)
        proxy_obj = self._query(statement)
        return self._create_list_of_dictionaries(proxy_obj)

    def get_category(self, category_id):
        statement = text("""SELECT * FROM categories
                            WHERE id=:category_id
                            AND deleted_at IS NULL""").\
                    bindparams(category_id=category_id)
        proxy_obj = self._query(statement)
        return self._create_list_of_dictionaries(proxy_obj)

    def get_product_with_properties(self, product_id):
        statement = text("""SELECT * FROM products JOIN product_properties
                            ON (products.id = product_properties.product_id)
                            WHERE products.id=:product_id
                            AND product_properties.deleted_at IS NULL""").\
                    bindparams(product_id=product_id)
        proxy_obj = self._query(statement)
        return self._create_list_of_dictionaries(proxy_obj)

    def get_product_properties(self, product_id):
        statement = text("""SELECT * FROM product_properties
                            WHERE product_id=:product_id
                            AND product_properties.deleted_at IS NULL""").\
                    bindparams(product_id=product_id)
        proxy_obj = self._query(statement)
        return self._create_list_of_dictionaries(proxy_obj)

    def get_lvl1_subcategories(self, category_id):
        statement = text("""SELECT * FROM subcategories_lvl1
                            WHERE categorY_id=:category_id
                            AND deleted_at IS NULL""").\
                    bindparams(category_id=category_id)
        proxy_obj = self._query(statement)
        return self._create_list_of_dictionaries(proxy_obj)

    def _create_list_of_dictionaries(self, proxy_object):
        row_proxy_object = proxy_object.fetchall()
        if row_proxy_object is None:
            return None
        list_ = []
        for obj in row_proxy_object:
            list_.append({column_name: str(column_value) for column_name,
                          column_value in zip(proxy_object.keys(), obj)})
        return list_

    def remove_category(self, id, hard=False):
        if hard is True:
            statement = text("""DELETE FROM categories
                                WHERE id=:id;""").\
                                bindparams(id=id)
            return self._query(statement)
        statement1 = text("""UPDATE categories SET
                             deleted_at=:timestamp
                             WHERE id=:id;""").\
                             bindparams(id=id,
                                        timestamp=self._current_timestamp()
                                        )
        self._query(statement1)
        statement2 = text("""UPDATE subcategories_lvl1 SET
                             deleted_at=:timestamp
                             WHERE category_id=:id;""").\
                             bindparams(id=id,
                                        timestamp=self._current_timestamp()
                                        )
        self._query(statement2)
        return True

    def get_category_interval(self, category_id1, category_id2):
        if category_id2 < category_id1:
            return None
        statement = """SELECT * FROM categories
                           WHERE id
                           BETWEEN {} AND {}
                           AND deleted_at IS NULL;""".format(category_id1,
                                                             category_id2)
        proxy_obj = self._query(statement)
        return self._create_list_of_dictionaries(proxy_obj)

    def get_products_interval(self, product_id1, product_id2):
        statement = """SELECT * FROM products
                       WHERE id
                       BETWEEN {} AND {}
                       AND deleted_at IS NULL;""".format(product_id1,
                                                         product_id2)
        proxy_obj = self._query(statement)
        return self._create_list_of_dictionaries(proxy_obj)

    def get_subcategories_lvl1(self, category_id):
        statement = text("""SELECT * FROM subcategories_lvl1
                            WHERE category_id=:category_id
                            AND deleted_at IS NULL""").\
                            bindparams(category_id=category_id)
        proxy_obj = self._query(statement)
        return self._create_list_of_dictionaries(proxy_obj)

    def get_products_filtered_by_price(self, low, hight):
        statement = """SELECT * FROM products
                       WHERE price
                       BETWEEN {} AND {}
                       AND deleted_at IS NULL;""".format(low,
                                                         hight)
        proxy_obj = self._query(statement)
        return self._create_list_of_dictionaries(proxy_obj)

    def get_products_filtered_by_name(self, name):
        statement = text("""SELECT * FROM PRODUCTS
                            WHERE NAME::text
                            LIKE '%{}%';""".format(name))
        proxy_obj = self._query(statement)
        return self._create_list_of_dictionaries(proxy_obj)
