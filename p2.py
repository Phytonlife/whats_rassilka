import random

import pandas as pd
import time
import os
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException


class WhatsAppAutomation:
    def __init__(self, csv_path, pdf_path, message_text):
        self.csv_path = csv_path
        self.pdf_path = pdf_path
        self.message_text = message_text
        self.driver = None

    def setup_driver(self):
        """Настройка веб-драйвера Chrome"""
        chrome_options = Options()
        chrome_options.add_argument("--start-maximized")  # Открыть браузер на полный экран
        chrome_options.add_argument("--disable-extensions")
        chrome_options.add_argument("--disable-notifications")

        self.driver = webdriver.Chrome(options=chrome_options)
        self.driver.get("https://web.whatsapp.com/")

        print("Отсканируйте QR-код для входа в WhatsApp Web")

        # Ожидание входа в WhatsApp (до 60 секунд)
        try:
            WebDriverWait(self.driver, 60).until(
                EC.presence_of_element_located((By.ID, "pane-side"))
            )
            print("Вход выполнен успешно!")
            return True
        except TimeoutException:
            print("Время ожидания входа истекло. Пожалуйста, отсканируйте QR-код быстрее.")
            self.driver.quit()
            return False

    def load_contacts(self):
        """Загрузка контактов из CSV-файла"""
        try:
            df = pd.read_csv(self.csv_path, encoding='utf-8')
            # Извлекаем номера WhatsApp (из столбцов WhatsApp 1, WhatsApp 2, WhatsApp 3)
            whatsapp_contacts = []

            # Проверяем наличие столбцов WhatsApp в файле
            whatsapp_columns = [col for col in df.columns if 'WhatsApp' in col]

            for _, row in df.iterrows():
                contact_info = {
                    'name': row.get('Наименование', 'Неизвестно'),
                    'numbers': []
                }

                for column in whatsapp_columns:
                    if pd.notna(row.get(column)) and str(row.get(column)).strip():
                        # Извлекаем номер из URL-формата (например, https://wa.me/77715221500)
                        whatsapp_number = str(row.get(column))
                        if 'wa.me/' in whatsapp_number:
                            number = whatsapp_number.split('wa.me/')[1]
                        else:
                            number = whatsapp_number

                        # Удаляем все нецифровые символы
                        number = ''.join(filter(str.isdigit, number))

                        if number:
                            contact_info['numbers'].append(number)

                if contact_info['numbers']:
                    whatsapp_contacts.append(contact_info)

            print(f"Загружено {len(whatsapp_contacts)} контактов с номерами WhatsApp")
            return whatsapp_contacts
        except Exception as e:
            print(f"Ошибка при загрузке контактов: {e}")
            return []

    def send_message_to_number(self, number, name):
        """Отправка сообщения конкретному номеру"""
        try:
            # Формируем URL для прямого перехода к чату
            chat_url = f"https://web.whatsapp.com/send?phone={number}"
            self.driver.get(chat_url)

            # Ожидаем загрузки чата
            try:
                message_box = WebDriverWait(self.driver, 20).until(
                    EC.presence_of_element_located((By.XPATH, '//div[@contenteditable="true"][@data-tab="10"]'))
                )

                # Персонализированное сообщение
                personalized_message = self.message_text.replace("{name}", name)

                # Вводим текст сообщения
                message_box.send_keys(personalized_message)
                time.sleep(random.uniform(1,2))

                # Отправляем текстовое сообщение
                send_button = self.driver.find_element(By.XPATH, '//span[@data-icon="send"]')
                send_button.click()
                time.sleep(random.uniform(2,3))

                # Прикрепляем PDF-файл
                if self.pdf_path and os.path.exists(self.pdf_path):
                    # Найдем кнопку прикрепления файлов
                    attach_button = self.driver.find_element(By.XPATH, '//span[@data-icon="attach-menu-plus"]')
                    attach_button.click()
                    time.sleep(random.uniform(1,2))

                    # Выбираем опцию "Документ"
                    document_button = self.driver.find_element(By.XPATH, '//input[@accept="*"]')
                    document_button.send_keys(os.path.abspath(self.pdf_path))
                    time.sleep(random.uniform(3,5))

                    # Ждем появления кнопки отправки файла и нажимаем на нее
                    send_file_button = WebDriverWait(self.driver, 10).until(
                        EC.element_to_be_clickable((By.XPATH, '//span[@data-icon="send"]'))
                    )
                    send_file_button.click()

                time.sleep(random.uniform(5,9))  # Ждем завершения отправки
                print(f"Сообщение отправлено: {name}, {number}")
                return True

            except TimeoutException:
                print(f"Не удалось загрузить чат для номера {number}")
                return False

        except Exception as e:
            print(f"Ошибка при отправке сообщения на номер {number}: {e}")
            return False

    def process_contacts(self):
        """Обработка всех контактов и отправка сообщений"""
        contacts = self.load_contacts()
        if not contacts:
            print("Нет контактов для отправки сообщений")
            return

        success_count = 0
        error_count = 0

        for contact in contacts:
            name = contact['name']

            for number in contact['numbers']:
                print(f"Отправка сообщения: {name}, {number}")

                if self.send_message_to_number(number, name):
                    success_count += 1
                else:
                    error_count += 1

                # Делаем паузу между отправками, чтобы избежать блокировки
                time.sleep(random.uniform(9,15))

        print(f"\nИтоги отправки:")
        print(f"Успешно отправлено: {success_count}")
        print(f"Ошибок: {error_count}")

    def run(self):
        """Запуск процесса автоматизации"""
        if self.setup_driver():
            print("Начинаем отправку сообщений...")
            self.process_contacts()

            # Закрываем браузер
            input("Нажмите Enter для завершения работы...")
            self.driver.quit()


# Пример использования
if __name__ == "__main__":
    csv_file = "contacts_data.csv"  # Путь к вашему CSV-файлу
    pdf_file = "Создание сайтов.pdf"  # Путь к PDF-файлу для отправки

    # Текст сообщения
    message = """Хотите больше клиентов, но не знаете, как их привлечь?
Недавно ко мне обратился владелец (Сборки мебели). Клиенты были, но мало. Мы сделали лендинг, добавили меню, отзывы, карту, кнопку WhatsApp – и поток заказов вырос!- Теперь я предлагаю это вам!
- Наша команда сделает сайт за 5 дней
- Подключу WhatsApp, Instagram, онлайн-запись
- Дешевле, чем реклама!

 Скидка 50% первым 3 клиентам!

 Напишите "Сайт" в WhatsApp, и получите бесплатную консультацию!"""

    # Создаем экземпляр класса автоматизации и запускаем
    whatsapp_bot = WhatsAppAutomation(csv_file, pdf_file, message)
    whatsapp_bot.run()