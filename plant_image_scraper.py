# importing the standard libraries
import pandas as pd
import time
import requests
import os
import re
from tqdm import tqdm
import warnings

warnings.filterwarnings("ignore")

# importing the selenium webdriver libraries
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.common.exceptions import NoSuchElementException


def initialize_driver():
    # Set up options for the WebDriver
    options = Options()
    options.add_argument("--headless")

    # Set up the service with the executable path
    service = Service("./chromedriver")

    # Intialising the web driver object
    driver = webdriver.Chrome(service=service, options=options)

    return driver


# helper function to create folders with each plant name
def create_folder_if_not_existed(directory, folder_name):
    folder_path = os.path.join(directory, folder_name)

    if not os.path.exists(folder_path):
        os.makedirs(folder_path)

    return folder_path


# define a function to scrape the data we need from the plant page
def plant_scraper(driver) -> pd.DataFrame():
    primary_name = driver.find_element(By.CSS_SELECTOR, "a.comname.display-name").text

    # Attempt to find the secondary name element
    try:
        secondary_name = driver.find_element(
            By.CSS_SELECTOR, "a.sciname.species.secondary-name"
        ).text
    except NoSuchElementException:
        # If the secondary name is not present, use the primary name as a fallback
        secondary_name = primary_name

    # Attempt to find the location element
    try:
        location = driver.find_element(By.CSS_SELECTOR, "span.place").text
    except NoSuchElementException:
        location = "Location not available"

    image_urls = []
    for image_element in driver.find_elements(
        By.CSS_SELECTOR, ".image-gallery-image img"
    ):
        image_url = image_element.get_attribute("src")

        # get the image source url
        image_urls.append(image_url)

        image_name = re.search("(?<=\/)\d+(?=\/)", image_url).group()

        # Create a folder for the plant using its name
        plant_folder = create_folder_if_not_existed("plant_image_data", primary_name)

        # download the image using requests
        response = requests.get(image_url)

        # Check if the request was successful (HTTP status code 200)
        if response.status_code == 200:
            # Specify the file path where you want to save the image
            image_file_path = os.path.join(plant_folder, f"{image_name}.jpg")

            with open(image_file_path, "wb") as image_file:
                image_file.write(response.content)
            print(f"Downloaded image for {primary_name} - {image_name}.jpg")
        else:
            print(f"Failed to download image for {primary_name}")

    return pd.DataFrame(
        {
            "Plant Name": primary_name,
            "Secondary Name": secondary_name,
            "Location": location,
            "Image URLs": image_urls,
        }
    )


def main():
    url = "https://www.inaturalist.org/observations?place_id=any&quality_grade=research&subview=table&taxon_id=47126&verifiable=any"
    number_of_pages = int(
        input("Please enter the number of pages you would like to scrape: ")
    )

    print(
        "Gathering all plant URLs across all the pages. Please wait, images should start downloading shortly."
    )

    driver = initialize_driver()

    # Navigating to website
    driver.get(url)

    # List to hold all the URLs
    plant_urls = []

    for _ in range(number_of_pages):
        # Scroll down to end of page using JavaScript
        for _ in range(10):
            scroll_distance = 1000  # Adjust this value to control the scroll distance
            script = f"window.scrollBy(0, {scroll_distance});"
            driver.execute_script(script)
            time.sleep(2)

        # Extract all plant URLs in current page
        pattern = '<a href="/(.+\d)" target="_self">'

        res = [
            f"https://www.inaturalist.org/{link}"
            for link in re.findall(pattern, driver.page_source)
        ]

        plant_urls.extend(res)

        # now to click to the next page
        driver.find_element(
            By.XPATH, '//*[@id="result-table"]/div[3]/ul/li[12]/a'
        ).click()

    # now to run the loop for each plant page
    res_list = []

    for plant_page in tqdm(plant_urls):
        try:
            driver.get(plant_page)

            time.sleep(5)

            data = plant_scraper(driver)
            if data is not None:
                res_list.append(data)

            time.sleep(5)

        except Exception as e:
            print(f"Error on page {plant_page}: {str(e)}")
            continue

    # ending this session
    driver.quit()

    if res_list:
        res_df = pd.concat(res_list, axis=0, ignore_index=True)
        # throwing out the output df as csv
        res_df.to_csv("plant_classifier_dataset.csv", index=False)
    else:
        print("No data collected.")


if __name__ == "__main__":
    main()
