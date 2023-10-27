import json
import time
from selenium import webdriver
from bs4 import BeautifulSoup

def blog_scraper():
    with webdriver.Chrome() as driver:
        try:
            driver.get("https://www.studentrentalslacrosse.com/student-rental-blog/")
            
            collective_blog = []
            
            soup = BeautifulSoup(driver.page_source,"lxml")
            
            articles = soup.select("article.post")
            
            for article in articles:
                blog = {}
                
                image_cover = article.find("img")
                blog['Image Cover'] =  image_cover['src'] if image_cover else None
                
                entry_title = article.select_one("h1.entry-title")
                blog['Title'] = entry_title.a.text if entry_title else None
                link = entry_title.a['href']
                blog['Link'] = link
                
                entry_date = article.select_one("span.entry-date")
                blog['Date'] = entry_date.a.text if entry_date else None
                
                entry = article.select_one("div.entry-content")
                blog['Content'] = entry.get_text() if entry else None
                
                driver.get(link)
                author = article.select_one("span.author")
                blog['Author'] = author.a.text if author else None
                
                collective_blog.append(blog)
                
            return collective_blog
        
        except Exception as e:
            print(f'Error occured {e}')
            
            
def write_data_to_file(filename, data):
    with open(filename, 'w') as file:
        json.dump(data, file)
    
    
def run_background_task():
    write_data_to_file('./blog_data.json', blog_scraper())
    time.sleep(1800)