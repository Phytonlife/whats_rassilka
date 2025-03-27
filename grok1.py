from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
import pandas as pd
import time
import os

# Путь к PDF-файлу (укажите свой путь)
PDF_PATH = "Создание сайтов.pdf"  # Замените на реальный путь к вашему PDF

# Чтение CSV-файла
df = pd.read_csv("atyrau.csv", delimiter=",")

# Извлекаем все номера телефонов из колонок "Телефон 1", "Телефон 2", "Телефон 3"
phone_columns = ["Телефон 1", "Телефон 2", "Телефон 3"]
phone_numbers = []
for col in phone_columns:
    if col in df.columns:
        # Преобразуем в строки, убираем NaN и добавляем в список
        phones = df[col].dropna().astype(str).tolist()
        phone_numbers.extend(phones)

# Убираем дубликаты номеров
phone_numbers = list(set(phone_numbers))

# Настройка браузера
options = webdriver.ChromeOptions()
options.add_argument("--user-data-dir=./chrome_profile")  # Сохраняем профиль для повторного использования
driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)

# Открываем WhatsApp Web
driver.get("https://web.whatsapp.com/")
print("Пожалуйста, отсканируйте QR-код в WhatsApp Web. У вас есть 20 секунд.")
time.sleep(20)  # Даем время для сканирования QR-кода вручную

# Функция отправки сообщения и PDF
def send_whatsapp_message(phone, message, pdf_path):
    # Формируем ссылку для открытия чата
    whatsapp_url = f"https://web.whatsapp.com/send?phone={phone}&text={message}"
    driver.get(whatsapp_url)
    time.sleep(5)  # Ждем загрузки страницы

    # Проверяем, загрузился ли чат
    try:
        input_box = driver.find_element(By.XPATH, '//*[@id="main"]/footer/div[1]/div/span[2]/div/div[2]/div[1]/div/div[1]')
        input_box.send_keys(Keys.ENTER)  # Отправляем текстовое сообщение
        time.sleep(2)

        # Нажимаем на кнопку прикрепления (скрепка)
        attach_button = driver.find_element(By.XPATH, '//*[@id="main"]/footer/div[1]/div/span[2]/div/div[1]/div[2]/div/div/span')
        attach_button.click()
        time.sleep(1)

        # Выбираем "Документ"
        document_option = driver.find_element(By.XPATH, '//input[@accept="*"]')
        document_option.send_keys(pdf_path)  # Загружаем PDF
        time.sleep(2)

        # Нажимаем кнопку отправки
        send_button = driver.find_element(By.XPATH, '//*[@id="app"]/div/div[2]/div[2]/div[2]/span/div/span/div/div/div[2]/div/div[2]/div[2]/div/div/span')
        send_button.click()
        time.sleep(3)  # Ждем отправки
        print(f"Сообщение отправлено на {phone}")
    except Exception as e:
        print(f"Ошибка при отправке на {phone}: {e}")

# Текст сообщения
message = "Здравствуйте! Вот ваш PDF-документ."

# Отправляем сообщения по списку номеров
for phone in phone_numbers:
    phone_str = phone.strip()  # Убираем лишние пробелы
    if not phone_str.startswith("+"):  # Добавляем код страны, если его нет
        phone_str = "+7" + phone_str  # Предполагаем Казахстан (+7)
    send_whatsapp_message(phone_str, message, PDF_PATH)
    time.sleep(5)  # Задержка между отправками для избежания блокировки

# Закрываем браузер после завершения
driver.quit()
print("Все сообщения отправлены!")