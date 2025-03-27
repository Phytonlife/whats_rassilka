import pandas as pd
import time
import os
import base64
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException
from webdriver_manager.chrome import ChromeDriverManager


class WhatsAppAutomation:
    def __init__(self, csv_path, pdf_path, message_text):
        self.csv_path = csv_path
        self.pdf_path = pdf_path
        self.message_text = message_text
        self.driver = None

    def setup_driver(self):
        """Настройка веб-драйвера Chrome"""
        chrome_options = Options()
        chrome_options.add_argument("--start-maximized")
        chrome_options.add_argument("--disable-extensions")
        chrome_options.add_argument("--disable-notifications")
        chrome_options.add_argument("--disable-infobars")
        chrome_options.add_argument("--disable-dev-shm-usage")
        chrome_options.add_argument("--no-sandbox")

        service = Service(ChromeDriverManager().install())
        self.driver = webdriver.Chrome(service=service, options=chrome_options)
        self.driver.get("https://web.whatsapp.com/")

        print("Отсканируйте QR-код для входа в WhatsApp Web")

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
            whatsapp_contacts = []
            whatsapp_columns = [col for col in df.columns if 'WhatsApp' in col]

            for _, row in df.iterrows():
                contact_info = {
                    'name': row.get('Наименование', 'Неизвестно'),
                    'numbers': []
                }

                for column in whatsapp_columns:
                    if pd.notna(row.get(column)) and str(row.get(column)).strip():
                        whatsapp_number = str(row.get(column))
                        if 'wa.me/' in whatsapp_number:
                            number = whatsapp_number.split('wa.me/')[1]
                        else:
                            number = whatsapp_number
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

    def upload_file_with_js(self, file_path):
        """Загрузка файла с использованием JavaScript"""
        try:
            with open(file_path, "rb") as pdf_file:
                base64_pdf = base64.b64encode(pdf_file.read()).decode('utf-8')

            js_code = f"""
            let input = document.createElement('input');
            input.type = 'file';
            fetch('data:application/pdf;base64,{base64_pdf}')
                .then(res => res.blob())
                .then(blob => {{
                    const file = new File([blob], "{os.path.basename(file_path)}", {{ type: 'application/pdf' }});
                    const dataTransfer = new DataTransfer();
                    dataTransfer.items.add(file);
                    input.files = dataTransfer.files;
                    const event = new Event('change', {{ bubbles: true }});
                    input.dispatchEvent(event);
                    return true;
                }});
            return input;
            """
            input_element = self.driver.execute_script(js_code)
            return input_element
        except Exception as e:
            print(f"Ошибка при подготовке файла через JavaScript: {e}")
            return None

    def manually_attach_file(self):
        """Альтернативный метод прикрепления файла через эмуляцию клавиатуры"""
        try:
            menu_buttons = [
                "//div[contains(@title, 'Меню')]",
                "//div[contains(@title, 'Menu')]",
                "//span[@data-icon='menu']",
                "//span[@data-icon='clip']",
                "//span[@data-testid='clip']",
                "//div[@role='button'][contains(@aria-label, 'Прикрепить')]",
                "//div[@data-tab='9']",
                "//div[@data-testid='compose-menu']",
                "//div[contains(@class, 'actions')]//div[@role='button']"
            ]

            for menu_xpath in menu_buttons:
                try:
                    menu_btn = WebDriverWait(self.driver, 2).until(
                        EC.element_to_be_clickable((By.XPATH, menu_xpath))
                    )
                    menu_btn.click()
                    print(f"Нажали на кнопку меню: {menu_xpath}")
                    time.sleep(1)
                    break
                except:
                    continue

            document_options = [
                "//div[contains(text(), 'Документ')]",
                "//div[contains(text(), 'Document')]",
                "//li[contains(@data-testid, 'document')]",
                "//input[@type='file']",
                "//input[@accept='*']"
            ]

            for doc_xpath in document_options:
                try:
                    doc_option = WebDriverWait(self.driver, 2).until(
                        EC.presence_of_element_located((By.XPATH, doc_xpath))
                    )
                    if "input" in doc_xpath:
                        doc_option.send_keys(os.path.abspath(self.pdf_path))
                    else:
                        doc_option.click()
                    print(f"Выбрали опцию документа: {doc_xpath}")
                    time.sleep(1)
                    return True
                except:
                    continue

            return False
        except Exception as e:
            print(f"Ошибка при ручном прикреплении: {e}")
            return False

    def send_message_to_number(self, number, name):
        """Отправка сообщения конкретному номеру"""
        try:
            chat_url = f"https://web.whatsapp.com/send?phone={number}"
            self.driver.get(chat_url)

            try:
                message_box = WebDriverWait(self.driver, 20).until(
                    EC.presence_of_element_located((By.XPATH,
                                                  "//div[@contenteditable='true'][@data-tab='10'] | //div[@contenteditable='true'][@data-tab='1'] | //div[@role='textbox']"))
                )

                personalized_message = self.message_text.replace("{name}", name)
                message_box.send_keys(personalized_message)
                time.sleep(1)

                send_button = WebDriverWait(self.driver, 5).until(
                    EC.element_to_be_clickable((By.XPATH, "//span[@data-icon='send'] | //button[@data-testid='send']"))
                )
                send_button.click()
                time.sleep(3)

                if self.pdf_path and os.path.exists(self.pdf_path):
                    print(f"Пытаемся прикрепить PDF для {name}")
                    attachment_found = False

                    try:
                        clip_button = WebDriverWait(self.driver, 5).until(
                            EC.element_to_be_clickable((By.XPATH,
                                                      "//div[@data-testid='attach-clip'] | //span[@data-testid='clip'] | //span[@data-icon='attach-menu-plus'] | //span[@data-icon='clip']"))
                        )
                        clip_button.click()
                        time.sleep(1)

                        document_option = WebDriverWait(self.driver, 5).until(
                            EC.element_to_be_clickable((By.XPATH,
                                                      "//div[@data-testid='mi-attach-document'] | //input[@accept='*'] | //li[contains(@data-testid, 'document')]"))
                        )

                        if document_option.tag_name.lower() == 'input':
                            document_option.send_keys(os.path.abspath(self.pdf_path))
                        else:
                            document_option.click()
                            file_input = WebDriverWait(self.driver, 5).until(
                                EC.presence_of_element_located((By.XPATH, "//input[@type='file']"))
                            )
                            file_input.send_keys(os.path.abspath(self.pdf_path))

                        attachment_found = True
                        print("Метод 1: Успешно прикрепили файл")
                    except Exception as e:
                        print(f"Метод 1 не сработал: {e}")

                    if not attachment_found:
                        try:
                            attachment_found = self.manually_attach_file()
                            if attachment_found:
                                print("Метод 2: Успешно прикрепили файл")
                        except Exception as e:
                            print(f"Метод 2 не сработал: {e}")

                    if not attachment_found:
                        try:
                            print("Пробуем прикрепить файл через JavaScript...")
                            chat_box = self.driver.find_element(By.XPATH,
                                                              "//div[@role='textbox'] | //div[@contenteditable='true']")
                            js_code = """
                            var input = document.createElement('input');
                            input.type = 'file';
                            input.style.display = 'none';
                            document.body.appendChild(input);
                            return input;
                            """
                            file_input = self.driver.execute_script(js_code)
                            file_input.send_keys(os.path.abspath(self.pdf_path))
                            print("Метод 3: Успешно прикрепили файл")
                            attachment_found = True
                        except Exception as e:
                            print(f"Метод 3 не сработал: {e}")

                    if attachment_found:
                        try:
                            time.sleep(3)
                            send_file_button = WebDriverWait(self.driver, 10).until(
                                EC.element_to_be_clickable((By.XPATH,
                                                          "//span[@data-icon='send'] | //div[@role='button'][contains(@aria-label, 'Send')] | //div[@role='button'][contains(@aria-label, 'Отправить')]"))
                            )
                            send_file_button.click()
                            print(f"PDF-файл отправлен для {name}, {number}")
                            time.sleep(5)
                        except Exception as e:
                            print(f"Ошибка при отправке файла: {e}")
                    else:
                        print(f"Не удалось прикрепить PDF-файл для {name}")

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
                time.sleep(10)

        print(f"\nИтоги отправки:")
        print(f"Успешно отправлено: {success_count}")
        print(f"Ошибок: {error_count}")

    def run(self):
        """Запуск процесса автоматизации"""
        if self.setup_driver():
            print("Начинаем отправку сообщений...")
            self.process_contacts()
            input("Нажмите Enter для завершения работы...")
            self.driver.quit()

if __name__ == "__main__":
    csv_file = "contacts_data.csv"
    pdf_file = "Создание сайтов.pdf"
    message = "Добрый день,\n Сайт — ваша цифровая точка продаж. Почему он еще не приносит деньги? Создайте качественный сайт недорого и начните получать заказы!"
    whatsapp_bot = WhatsAppAutomation(csv_file, pdf_file, message)
    whatsapp_bot.run()