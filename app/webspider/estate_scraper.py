import os
import time
import json
from bs4 import BeautifulSoup
from selenium import webdriver
from concurrent.futures import ThreadPoolExecutor
from typing import List, Dict, Union
from selenium.webdriver.common.by import By

def estate_scraper(url: str) -> List[Dict[str, Union[str, None]]]:
    file_path = os.path.join('app', 'webspider', 'estate_data.json')
    if os.path.exists(file_path):
        with open(file_path, 'r') as file:
            return json.load(file)

    with webdriver.Chrome() as driver:
        try:
            driver.get(url)
            soup = BeautifulSoup(driver.page_source, "lxml")

            divs = soup.select('div.ilanitembasic')

            collective_data = []

            for div in divs:
                retrieved_data = {}
                image_urls_list = [] 

                cover_image = div.select_one('img.coverimagefulwidthheight')
                retrieved_data['Cover Image'] = cover_image.get('src') if cover_image else None

                local_currency_element = div.select_one('div.basicpriceconv')
                retrieved_data['Price'] = local_currency_element.text if local_currency_element else None

                agent_name_element = div.select_one('div.div-block-334')
                retrieved_data['Agent Name'] = agent_name_element.text if agent_name_element else None

                agent_image_element = div.select_one('img.image-46')
                retrieved_data['Agent Image Source'] = agent_image_element.get('src', "/static/profile_pics/default.jpg") if agent_image_element else "/static/profile_pics/default.jpg"

                description_element = div.select_one('h4.text-block-129')
                retrieved_data['Description'] = description_element.text if description_element else None

                a_tag = div.find('a', class_='hover-black')
                link_ = 'https://www.101evler.com/' + a_tag['href'] + '#st'
                driver.get(link_)
                link_soup = BeautifulSoup(driver.page_source, "lxml")
                property_details_div = link_soup.find('div', id='konut-detaylari')
                property_details = property_details_div.find_all('div', class_='text-block-141')
                for detail in property_details:
                    label = detail.find('div', class_='col-5').text.strip()
                    value = detail.find('div', class_='col-7').strong.text.strip()
                    retrieved_data[label] = value

                quick_overview_div = link_soup.find('div', id='hizli-bakis')
                quick_overview = quick_overview_div.find_all('div', class_='text-block-141')
                for detail in quick_overview:
                    label = detail.find('div', class_='col-5').text.strip()
                    value = detail.find('div', class_='col-7').strong.text.strip()
                    retrieved_data[label] = value
                    
                phone_number_div = link_soup.find('div', id='danismankartilan')
                whatsapp_btn = phone_number_div.find('div', class_='div-block-383-green')
                if whatsapp_btn:
                    whatsapp_link = whatsapp_btn.find('a')['href']
                    retrieved_data['Whatsapp Number'] = whatsapp_link
                else:
                    retrieved_data['Whatsapp Number'] = None

                    
                sections = link_soup.find_all(class_='ilandetayaccordion')
                for section in sections:
                    feature_name = section.find(class_='text-block-142').text
                    checkboxes = section.find_all(class_='div-block-365')
                    checkbox_labels = [checkbox.find(class_='checktext').text for checkbox in checkboxes]
                    retrieved_data[feature_name] = checkbox_labels
                    
                collective_data.append(retrieved_data)
                
                component = driver.find_element(By.CLASS_NAME, 'tumfotothumb')
                component.click()
                time.sleep(2)
                div_blocks = link_soup.find_all(class_='div-block-482')
                for div in div_blocks:
                    image_tag = div.find('img')
                    image_urls_list.append(image_tag['src'])
                    
                retrieved_data['Images'] = image_urls_list
                
        except Exception as e:
            print(f"An error occurred: {e}")
            
    return collective_data

def write_data_to_file(filename: str, data: Dict) -> None:
    with open(filename, 'w') as file:
        json.dump(data, file)

def background_task():
    while True:
        with ThreadPoolExecutor() as executor:
            rent_data = executor.submit(estate_scraper, 'https://www.101evler.com/north-cyprus/houses-to-rent').result()
            cyprus_data = executor.submit(estate_scraper, 'https://www.101evler.com/north-cyprus/houses-for-sale').result()
            iskele_data = executor.submit(estate_scraper, 'https://www.101evler.com/north-cyprus/houses-for-sale/iskele').result()
            magusa_data = executor.submit(estate_scraper, 'https://www.101evler.com/north-cyprus/houses-to-rent/famagusta').result()
            konut_data = executor.submit(estate_scraper, 'https://www.101evler.com/north-cyprus/houses-for-sale').result()
            featured_data = executor.submit(estate_scraper, 'https://www.101evler.com/north-cyprus/property-to-rent?s-r=R&property_type=1&property_subtype%5B0%5D=2&min_price=&max_price=&currency=1&min_m2=&max_m2=&search_keyword=&publish_date=').result()
            lefke_data = executor.submit(estate_scraper, 'https://www.101evler.com/north-cyprus/property-to-rent/lefke').result()
            guzelyurt_data = executor.submit(estate_scraper, 'https://www.101evler.com/north-cyprus/property-to-rent/guzelyurt').result()

        all_data = {
            'featured_data': featured_data,
            'lefke_data': lefke_data,
            'guzelyurt_data': guzelyurt_data,
            'rent_data': rent_data,
            'cyprus_data': cyprus_data,
            'iskele_data': iskele_data,
            'magusa_data': magusa_data,
            'konut_data': konut_data
        }

        write_data_to_file('./estate_data.json', all_data)

        time.sleep(1800)

