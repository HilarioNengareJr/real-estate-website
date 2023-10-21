import os
import random
import json
from app import elastic
from flask import request

file_path = os.path.join('app', 'webspider', 'estate_data.json')


def load_estate_data() -> dict:
    '''Load estate data from a JSON file'''
    with open(file_path, 'r') as file:
        data = json.load(file)
    return data


def featuring_data(*args: list) -> list:
    '''Randomly select data from given arguments'''
    selected_data = []
    for arg in args:
        num_items_from_each = random.randint(1, min(5, len(arg)))
        selected_data.extend(random.sample(arg, num_items_from_each))
    return selected_data


index_mapping = {
    "mappings": {
        "properties": {
            "Cover Image": {"type": "text"},
            "Price": {"type": "text"},
            "Agent Name": {"type": "text"},
            "Agent Image Source": {"type": "text"},
            "Description": {"type": "text"},
            "Rooms": {"type": "text"},
            "Baths Count": {"type": "text"},
            "Building Age": {"type": "text"},
            "Gated Community": {"type": "text"},
            "Floors Count": {"type": "text"},
            "Floor Number": {"type": "text"},
            "Furnishes": {"type": "text"},
            "Ad No": {"type": "text"},
            "Location": {"type": "text"},
            "Property Type": {"type": "text"},
            "Status": {"type": "text"},
            "Title Type": {"type": "text"},
            "Area": {"type": "text"},
            "Swap": {"type": "text"},
            "Published On": {"type": "text"},
            "Last Updated": {"type": "text"},
            "Min. Rental Period": {"type": "text"},
            "Pay Interval": {"type": "text"},
            "Outside Features": {"type": "text"}
        }
    }
}


if not elastic.indices.exists(index='estate_data'):
    elastic.indices.create(index='estate_data', body=index_mapping)
else:
    print("Index 'estate_data' already exists. Skipping creation.")


data_set = load_estate_data()['featured_data'] + load_estate_data()['lefke_data'] + load_estate_data()['guzelyurt_data'] + load_estate_data()[
    'rent_data'] + load_estate_data()['iskele_data'] + load_estate_data()['cyprus_data'] + load_estate_data()['magusa_data'] + load_estate_data()['konut_data']

for item in data_set:
    elastic.index(index='estate_data', body=item)


def perform_search(query, page, per_page, last_hit=None):
    if page == 1:
        response = elastic.search(index='estate_data', body={
            'size': per_page,
            'query': {
                'multi_match': {
                    'query': query,
                    'fields': ['Location', 'Description', 'Property Type', 'Location Features', 'Outside Features', 'Price', 'status']
                }
            },
            'sort': ['_id']
        })
    else:
        if last_hit is None:
            return []

        response = elastic.search(index='estate_data', body={
            'size': per_page,
            'query': {
                'bool': {
                    'must': [
                        {
                            'multi_match': {
                                'query': query,
                                'fields': ['Location', 'Description', 'Property Type', 'Location Features', 'Outside Features', 'Price']
                            }
                        },
                        {
                            'range': {
                                '_id': {
                                    'lt': last_hit
                                }
                            }
                        }
                    ]
                }
            },
            'sort': ['_id']
        })

    return response


def get_form_data():
    city = request.form.get('city')
    status = request.form.get('status')
    min_price = request.form.get('min_price')
    max_price = request.form.get('max_price')
    property_type = request.form.get('property_type')

    return city, status, min_price, max_price, property_type


def perform_filtering(json_data, city, status, min_price, max_price, property_type):
    filtered_data = []

    for item in json_data:
        price_string = item.get('Price', '0').replace(
            '£', '').replace(',', '').split('\n')[0].strip()

        try:
            price = float(price_string)
        except ValueError:
            continue

        if (
            (not city or city in item.get('Location')) and
            (not status or status in item.get('Status')) and
            (not min_price or price >= float(min_price)) and
            (not max_price or price <= float(max_price)) and
            (not property_type or property_type in item.get('Property Type'))
        ):
            filtered_data.append(item)

    return filtered_data
