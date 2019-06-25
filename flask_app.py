import sys
import os
from flask import Flask, request, jsonify, abort
from flask_sqlalchemy import SQLAlchemy
from db_connect import Postgres_db
from db_configurator import get_config_string
from marshmallow import Schema, fields, post_load


db_config = get_config_string()
db = Postgres_db(db_config)
app = Flask(__name__)
basedir = os.path.abspath(os.path.dirname(__file__))

class Product(object):
    def __init__(self, url, parent, name, price, product_units,
                 description, image_url, is_trend):
        self.url = url
        self.parent = parent
        self.name = name
        self.price = price
        self.product_units = product_units
        self.description = description
        self.image_ur = image_url
        self.is_trend = is_trend

class ProductSchema(Schema):
    url = fields.Url()
    parent = fields.String()
    name = fields.String()
    price = fields.Float()
    product_units = fields.String()
    description = fields.String()
    image_url = fields.Url()
    is_trend = fields.Boolean()

    @post_load
    def create_product(self, data):
        return Product(**data)

@app.route('/product', methods=['POST'])
def create_product():
    data = request.get_json()
    product_dict = {
                    'parent': data['parent'],
                    'url': data['url'],
                    'name': data['name'],
                    'price': data['price'],
                    'product_units': data['product_units'],
                    'description': data['description'],
                    'image_url': data['image_url'],
                    'is_trend': data['is_trend']
                    }
    schema = ProductSchema()
    product_instance = schema.load(product_dict)
    if len(product_instance.errors) != 0:
        return jsonify(product_instance.errors)
    product_id = db.product_insert(product_dict)
    return jsonify(db.get_product_by_id(product_id))

@app.route('/products/<product_id>', methods=['GET'])
def get_product(product_id):
    product = db.get_product_by_id(product_id)
    if len(product) == 0:
        return abort(404)
    return jsonify(product)

@app.route('/products/<product_id>', methods=['DELETE'])
def delete_product(product_id):
    db.remove_entry_from_product_table(product_id)
    return jsonify({'message': 'product removed'})

@app.route('/products/<product_id1>-<product_id2>', methods=['GET'])
def get_products_interval(product_id1, product_id2):
    limit = int(request.args.get('limit', None))
    offset = int(request.args.get('offset', None))
    products = db.get_products_interval(product_id1, product_id2)
    if len(products) == 0:
        return abort(404)
    if limit is None or offset is None:
        return jsonify(products)
    return jsonify(products[offset:offset+limit])

@app.route('/products/<product_id>/properties', methods=['GET'])
def get_product_properties(product_id):
    product = db.get_product_properties(product_id)
    if len(product) == 0:
        return abort(404)
    return jsonify(product)

@app.route('/products/property', methods=['GET'])
def get_product_by_name_or_price_range():
    if 'name' in request.args:
        name = request.args['name']
        product = db.get_products_filtered_by_name(name)
    elif 'low' in request.args and 'high' in request.args:
        low = float(request.args['low'])
        high = float(request.args['high'])
        product = db.get_products_filtered_by_price(low, high)
    else:
        return abort(404)
    if len(product) == 0:
        return abort(404)
    return jsonify(product)

@app.route('/categories/<category_id>', methods=['GET'])
def get_category(category_id):
    category = db.get_category(category_id)
    if len(category) == 0:
        return abort(404)
    return jsonify(category)

@app.route('/categories/<category_id>', methods=['DELETE'])
def delete_category(category_id):
    db.remove_category(category_id)
    return jsonify({'message': 'category removed'})

@app.route('/categories/<category_id1>-<category_id2>', methods=['GET'])
def get_category_interval(category_id1, category_id2):
    category = db.get_category_interval(category_id1, category_id2)
    if len(category) == 0:
        return abort(404)
    return jsonify(category)

@app.route('/categories/<category_id>/subcategories-level1', methods=['GET'])
def get_subcategories_lvl1(category_id):
    subcategories_level1 = db.get_subcategories_lvl1(category_id)
    if len(subcategories_level1) == 0:
        return abort(404)
    return jsonify(subcategories_level1)

if __name__ == '__main__':
    app.run(debug=True)
