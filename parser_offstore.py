from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.common.desired_capabilities import DesiredCapabilities
import json
import os
import time
import requests

def get_driver():
    caps = DesiredCapabilities.CHROME
    caps['goog:loggingPrefs'] = {'performance': 'ALL'}
    
    options = webdriver.ChromeOptions()
    options.add_argument('--headless')
    if os.path.exists("chromedriver.exe"):
        service = Service(executable_path="chromedriver.exe")
        return webdriver.Chrome(options=options, service=service, desired_capabilities=caps)
    else:
        return webdriver.Chrome(options=options, desired_capabilities=caps)

def endless_scroll(driver):
    #https://stackoverflow.com/questions/20986631/how-can-i-scroll-a-web-page-using-selenium-webdriver-in-python
    # Get scroll height
    last_height = driver.execute_script("return document.body.scrollHeight")
    while True:
        # Scroll down to bottom
        driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
    
        # Wait to load page
        time.sleep(1)
    
        # Calculate new scroll height and compare with last scroll height
        new_height = driver.execute_script("return document.body.scrollHeight")
        if new_height == last_height:
            break
        last_height = new_height

def process_browser_log_entry(entry):
    entry = json.loads(entry["message"])["message"]
    if "request" not in (entry["params"].keys()): return ""
    if "url" not in (entry["params"]["request"].keys()): return ""
    if "orderrequestbyid/" not in (entry["params"]["request"]["url"]): return ""
    return(entry["params"]["request"]["url"])

def get_dados_pedido(url, senha):
    if url == "": return
    headers = {"Authorization":senha}
    return(json.loads(requests.post(url, headers=headers).text))

def acessa_pedidos(driver, senha):
    driver.get("https://app.offstore.me/dashboard")
    driver.implicitly_wait(1)
    driver.find_element(By.ID, "user_email").send_keys("contato@abracm.org.br")
    driver.find_element(By.ID, "password").send_keys(senha)
    driver.find_element(By.CSS_SELECTOR, "#root > div.sc-bdVaJa.jZAhhm > div > form > button").click()
    driver.implicitly_wait(2)
    driver.find_element(By.CSS_SELECTOR, "#root > div.sc-dOkuiw.gJWaVB > header > div.sc-hMjcWo.jelPwy > div").click()
    time.sleep(2)

def clica_pedido_individual(driver, tag_atual):
    compras = driver.find_element(By.CLASS_NAME, "infinite-scroll-component ")
    elemento = compras.find_elements(By.TAG_NAME, "div")[tag_atual]
    if elemento.get_attribute("class") not in ["sc-fyjhYU KSoWN", "sc-fyjhYU bWlhg"]:
        return
    print(elemento.get_attribute("innerHTML"))
    time.sleep(1.5)
    elemento.click()
    driver.implicitly_wait(3)
    elemento = driver.find_element(By.XPATH, '//*[@id="root"]/div[7]/div/div[2]/div/div/div/div[2]/div')
    driver.execute_script("arguments[0].click();", elemento)
    time.sleep(0.2)
    driver.execute_script("arguments[0].scrollIntoView();", driver.find_element(By.CLASS_NAME, "infinite-scroll-component ")\
                          .find_elements(By.TAG_NAME, "div")[tag_atual])
    
def get_urls(driver):
    browser_log = driver.get_log('performance')
    urls = [process_browser_log_entry(entry) for entry in browser_log]
    urls = list(set(urls))[1:]
    return urls

def get_senhas():
    with open("senhas.txt", "r", encoding="utf-8") as f:
        return [x.replace("\n", "") for x in f]
    
senhas = get_senhas()
driver = get_driver()
acessa_pedidos(driver, senhas[0])

for tag in range(0,10000):
    
    tag_atual = (tag)
    
    try: 
        clica_pedido_individual(driver, tag_atual)
    except IndexError:
        break

urls = get_urls(driver)
driver.quit()
dados_pedidos = [get_dados_pedido(url, senhas[1]) for url in urls]
print(dados_pedidos)
with open("dados_pedidos.json", "w", encoding="utf-8") as f:
    json.dump(dados_pedidos, f)

