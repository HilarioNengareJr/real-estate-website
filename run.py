from app import app
from app.webspider.estate_scraper import background_task
import threading

if __name__ == '__main__':
    background_task_thread = threading.Thread(target=background_task)
    background_task_thread.start()
    app.run(debug=True)
