from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.common.desired_capabilities import DesiredCapabilities
import json
import os
import time
import requests
from bs4 import BeautifulSoup as BS
from collections import Counter
import csv
import datetime

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
    html = BS(elemento.get_attribute("innerHTML"), "lxml")
    if html.find("span", "date-viewed") is not None:
        if html.find("span", "date-viewed").contents[0] == "25 de agosto de 2022  às 08:58h":
            raise IndexError
    time.sleep(3)
    elemento.click()
    driver.implicitly_wait(3)
    elemento = driver.find_element(By.XPATH, '//*[@id="root"]/div[7]/div/div[2]/div/div/div/div[2]/div')
    driver.execute_script("arguments[0].click();", elemento)
    time.sleep(1)
    driver.execute_script("arguments[0].scrollIntoView();", driver.find_element(By.CLASS_NAME, "infinite-scroll-component ")\
                          .find_elements(By.TAG_NAME, "div")[tag_atual])
    
def get_urls(driver):
    browser_log = driver.get_log('performance')
    urls = [process_browser_log_entry(entry) for entry in browser_log]
    urls = list(set(urls))[1:]
    return urls

def get_senhas(caminho):
    with open(caminho, "r", encoding="utf-8") as f:
        return [x.replace("\n", "") for x in f]

def get_status(caminho):
    with open(caminho, "r", encoding="utf-8") as f:
        return json.load(f)
    
def get_nomes_manuais(dados_pedidos):
    with open("resources\\nomes_manuais.json", "r", encoding="utf-8") as f:
        nomes_manuais = json.load(f)
    for pedido in dados_pedidos:
        if pedido["code"] in nomes_manuais.keys():
            pedido["observation"] = nomes_manuais[pedido["code"]]
    return dados_pedidos

def resumo_malharia(relatorio_pedidos, valor_unidade, pedidos_extra=[]):
    counter = Counter([x["tamanho"] for x in relatorio_pedidos])
    total_extra = 0
    for key in pedidos_extra:
        total_extra += pedidos_extra[key]
        if key in counter.keys():
            counter[key] += pedidos_extra[key]
        else:
            counter[key] = pedidos_extra[key]
    total_pedidos = len(relatorio_pedidos) + total_extra
    str_relatorio = "RELATÓRIO PEDIDOS\n\n"
    str_relatorio += "Total camisetas: {}\nValor total: R$ {}\nValor entrada: R$ {}\n\n"\
        .format(total_pedidos, valor_unidade*total_pedidos, valor_unidade*total_pedidos/2)
    if pedidos_extra != []:
        str_relatorio += "Além dos pedidos da planilha, temos os seguintes extras (sem nome):\n"
        for key in pedidos_extra:
            str_relatorio += "{} - {} unidades\n".format(key, pedidos_extra[key])
    
    str_relatorio += "\nTotal por tamanho:\n"
    for key in counter:
        str_relatorio += "{} - {} unidades\n".format(key, counter[key])
    with open("resultados\\resumo_malharia.txt", "w", encoding="utf-8") as f:
        f.write(str_relatorio)
    print(str_relatorio)
    
def relatorio_malharia(dados_pedidos, data_inicio, produto, valor_unidade, pedidos_extra=[], ignorados=[]):
    relatorio_pedidos = []
    for pedido in dados_pedidos:
        if pedido["code"] in ignorados: continue
        if datetime.datetime.strptime(pedido["createdAt"].split("T")[0], "%Y-%m-%d").date()\
            > data_inicio:
            for product in pedido["products"]:
                if produto not in product["name"]: continue
                for unidade in range(product["amount"]):
                    relatorio_pedidos.append({"nome":pedido["name"],
                                              "data":pedido["createdAt"],
                                              "tamanho":product["name"].split("(")[1].replace(")", ""),
                                              "nome_costas":pedido["observation"],
                                              "codigo":pedido["code"]})
    
    with open("resultados\\relatorio_malharia.csv", "w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=list(relatorio_pedidos[0]))
        writer.writeheader()
        writer.writerows(relatorio_pedidos)
    
    resumo_malharia(relatorio_pedidos, valor_unidade, pedidos_extra)

def relatorio_pedidos(dados_pedidos, data_inicio, pedidos_ignorados=[]):
    relatorio_pedidos = []
    for pedido in dados_pedidos:
        if pedido["code"] in pedidos_ignorados: continue
        for product in pedido["products"]:
            relatorio_pedidos.append({"nome":pedido["name"],
                                      "data":pedido["createdAt"],
                                      "produto":product["name"],
                                      "quantidade":product["amount"],
                                      "codigo":pedido["code"]})
    relatorio_pedidos = sorted(relatorio_pedidos, key = lambda x: x["data"])
    with open("resultados\\relatorio_pedidos.csv", "w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=list(relatorio_pedidos[0]))
        writer.writeheader()
        writer.writerows(relatorio_pedidos)

def relatorio_retiradas(dados_pedidos, data_inicio, pedidos_ignorados=[]):
    relatorio_retiradas = []
    for pedido in dados_pedidos:
        if pedido["code"] in pedidos_ignorados: continue
        if datetime.datetime.strptime(pedido["createdAt"].split("T")[0], "%Y-%m-%d").date()\
            < data_inicio: continue
        if pedido["receivement"] == 1: entr_retirada = "R"
        elif pedido["receivement"] == 0: entr_retirada = "E"
        for product in pedido["products"]:
                relatorio_retiradas.append({"nome":pedido["name"],
                                          "produto":product["name"],
                                          "quantidade":product["amount"],
                                          "entrega_retirada":entr_retirada,
                                          "nome_costas":pedido["observation"]})
    relatorio_retiradas = sorted(relatorio_retiradas, key = lambda x: x["nome"])
    with open("resultados\\relatorio_retiradas.csv", "w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=list(relatorio_retiradas[0]))
        writer.writeheader()
        writer.writerows(relatorio_retiradas)

def relatorio_melhor_envio(dados_pedidos, data_inicio, pedidos_ignorados=[], pedidos_entregues=[]):
    relatorio_melhor_envio = {}
    relatorio_todos_dados = []
    for pedido in dados_pedidos:
        if pedido["code"] in pedidos_ignorados: continue
        if pedido["code"] in pedidos_entregues: continue
        if datetime.datetime.strptime(pedido["createdAt"].split("T")[0], "%Y-%m-%d").date()\
        < data_inicio: continue
        if pedido["receivement"] == 1: continue
    
        #TODO melhorar lógica de cálculo de peso, dimensões
        dimensoes = (24, 16, 4)
        peso = 0
        for produto in pedido["products"]:
            for unidade in range(produto["amount"]):
                if "Uniforme Oficial 2023" in produto["name"]: peso += 0.2
                if "Tapete" in produto["name"]: peso += 0.1
                
        if pedido["cep"] in relatorio_melhor_envio.keys():
            peso_original = relatorio_melhor_envio[pedido["cep"]]["PESO (KG)"]
            peso_original = float(peso_original.replace(",", "."))
            peso_total = peso_original + peso
            relatorio_melhor_envio[pedido["cep"]]["PESO (KG)"] = str(peso_total).replace(".", ",")
            
            valor_original = relatorio_melhor_envio[pedido["cep"]]["VALOR SEGURADO"]
            valor_original = float(valor_original.replace("R$\xa0", "").replace(",", "."))
            valor_total = valor_original + float(pedido["subtotal"].replace("R$\xa0", "").replace(",", "."))
            relatorio_melhor_envio[pedido["cep"]]["VALOR SEGURADO"] = "R$ " + str(valor_total).replace(".", ",")
            continue 
        
        dados_envio = {"CEP DESTINO":pedido["cep"],
                        "PESO (KG)": str(peso).replace(".", ","),
                        "ALTURA (CM)": dimensoes[2],
                        "LARGURA (CM)": dimensoes[1],
                        "COMPRIMENTO (CM)": dimensoes[0],
                        "AVISO DE RECEBIMENTO (AR)": "NÃO",
                        "MÃO PRÓPRIA (MP)": "NÃO",
                        "VALOR SEGURADO": pedido["subtotal"]}
        relatorio_melhor_envio[pedido["cep"]] = dados_envio
        relatorio_todos_dados.append({**dados_envio,
                                      "Valor Frete":pedido["rate"],
                                      "Nome":pedido["name"],
                                      "Telefone":pedido["whatsapp"],
                                      "Email":pedido["email"],
                                      "Endereço":pedido["address"],
                                      "Número":pedido["number"],
                                      "Complemento":pedido["complement"],
                                      "Bairro":pedido["neighborhood"],
                                      "CPF":pedido["cpf"]})
    relatorio_melhor_envio = [relatorio_melhor_envio[key] for key in relatorio_melhor_envio]
    with open("resultados\\relatorio_melhor_envio.csv", "w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=list(relatorio_melhor_envio[0]))
        writer.writeheader()
        writer.writerows(relatorio_melhor_envio)
    with open("resultados\\relatorio_melhor_envio_completo.csv", "w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=list(relatorio_todos_dados[0]))
        writer.writeheader()
        writer.writerows(relatorio_todos_dados)
        
senhas = get_senhas(r"resources\\senhas.txt")
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
with open("resources\\dados_pedidos.json", "w", encoding="utf-8") as f:
    json.dump(dados_pedidos, f)

data_inicio = datetime.date(2023, 1, 1)
status_pedidos = get_status("resources\\status_pedidos.json")
pedidos_ignorados = status_pedidos["ignorados"]
pedidos_entregues = status_pedidos["entregues"]
dados_pedidos = get_nomes_manuais(dados_pedidos)

relatorio_malharia(dados_pedidos, data_inicio, "Uniforme Oficial 2023",
                   40, {"M":3, "P":2, "PP": 2}, pedidos_ignorados)
relatorio_pedidos(dados_pedidos,data_inicio,pedidos_ignorados)
relatorio_retiradas(dados_pedidos, data_inicio, pedidos_ignorados)
relatorio_melhor_envio(dados_pedidos, data_inicio, pedidos_ignorados, pedidos_entregues)