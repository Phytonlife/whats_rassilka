import pandas as pd
import pyautogui
import time
import webbrowser
import os
import logging
from datetime import datetime

# Настройка логирования
logging.basicConfig(
    filename=f'whatsapp_automation_{datetime.now().strftime("%Y-%m-%d_%H-%M-%S")}.log',
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)


class WhatsAppAutomation:
    def __init__(self, csv_path, pdf_path, message_text, delay_between_messages=30):
        """
        Инициализация класса автоматизации WhatsApp Web

        :param csv_path: путь к CSV файлу с контактами
        :param pdf_path: путь к PDF файлу для отправки
        :param message_text: текст сообщения
        :param delay_between_messages: задержка между отправкой сообщений в секундах
        """
        self.csv_path = csv_path
        self.pdf_path = os.path.abspath(pdf_path)
        self.message_text = message_text
        self.delay = delay_between_messages
        self.contacts_df = None
        self.load_contacts()

    def load_contacts(self):
        """Загрузка контактов из CSV файла"""
        try:
            self.contacts_df = pd.read_csv(self.csv_path, encoding='utf-8')
            logging.info(f"Загружено {len(self.contacts_df)} контактов из CSV")
        except Exception as e:
            logging.error(f"Ошибка при загрузке CSV файла: {e}")
            raise

    def prepare_phone_number(self, phone):
        """Подготовка номера телефона к формату WhatsApp"""
        # Удаление всех нецифровых символов
        phone = ''.join(filter(str.isdigit, str(phone)))

        # Если номер начинается с 8, заменяем на 7
        if phone.startswith('8') and len(phone) == 11:
            phone = '7' + phone[1:]

        # Добавляем '+' если его нет
        if not phone.startswith('+'):
            phone = '+' + phone

        return phone

    def open_whatsapp_web(self):
        """Открытие WhatsApp Web"""
        webbrowser.open('https://web.whatsapp.com/')
        logging.info("Открыт WhatsApp Web")

        # Ожидание загрузки и авторизации через QR-код
        print("Пожалуйста, отсканируйте QR-код на экране для входа в WhatsApp Web.")
        print("После успешного входа нажмите Enter для продолжения...")
        input()
        logging.info("Вход в WhatsApp Web выполнен")

        # Даем время для полной загрузки интерфейса
        time.sleep(5)

    def send_message_to_contact(self, phone_number):
        """Отправка сообщения и PDF файла контакту с использованием drag-and-drop"""
        try:
            # Формируем URL для открытия чата с контактом с закодированным сообщением
            import urllib.parse
            encoded_message = urllib.parse.quote(self.message_text)
            chat_url = f"https://web.whatsapp.com/send?phone={phone_number}&text={encoded_message}"

            # Открываем чат с контактом
            webbrowser.open(chat_url)
            logging.info(f"Открыт чат с номером {phone_number}")

            # Ожидаем загрузку чата (увеличенное время ожидания)
            time.sleep(15)

            # Отправляем текстовое сообщение с помощью Enter
            pyautogui.press('enter')
            logging.info(f"Отправлено текстовое сообщение для {phone_number}")
            time.sleep(3)

            # Отправляем PDF файл через drag-and-drop
            # Открываем проводник с файлом
            os.system(f'explorer /select,"{self.pdf_path}"')
            time.sleep(3)

            # Координаты начальной и конечной точки для перетаскивания
            start_x, start_y = self.coordinates.get('file_position', (400, 300))  # Файл в проводнике
            end_x, end_y = self.coordinates.get('chat_window', (500, 500))  # Окно чата

            # Перетаскиваем файл
            pyautogui.moveTo(start_x, start_y)
            time.sleep(0.5)
            pyautogui.mouseDown()
            time.sleep(0.5)
            pyautogui.moveTo(end_x, end_y, duration=1)
            pyautogui.mouseUp()
            time.sleep(2)

            # Нажимаем Enter для отправки
            pyautogui.press('enter')
            logging.info(f"Отправлен PDF файл для {phone_number} через drag-and-drop")
            time.sleep(5)

            # Закрываем окно проводника
            pyautogui.hotkey('alt', 'f4')
            time.sleep(1)

            # Закрываем вкладку с чатом
            pyautogui.hotkey('ctrl', 'w')

            return True
        except Exception as e:
            logging.error(f"Ошибка при отправке сообщения для {phone_number}: {e}")
            return False
    def run_automation(self):
        """Запуск автоматизации отправки сообщений"""
        # Открываем WhatsApp Web
        self.open_whatsapp_web()

        # Обрабатываем каждый контакт
        for index, row in self.contacts_df.iterrows():
            # Получаем номер телефона из столбцов WhatsApp 1, WhatsApp 2, WhatsApp 3
            phone_columns = ['WhatsApp 1', 'WhatsApp 2', 'WhatsApp 3']

            for col in phone_columns:
                if col in row and pd.notna(row[col]) and row[col] != '':
                    phone = row[col]

                    # Если номер в формате wa.me, извлекаем номер
                    if 'wa.me/' in phone:
                        phone = phone.split('wa.me/')[1]

                    # Подготавливаем номер телефона
                    phone = self.prepare_phone_number(phone)

                    # Отправляем сообщение и PDF
                    success = self.send_message_to_contact(phone)

                    if success:
                        logging.info(f"Обработка контакта {index + 1}/{len(self.contacts_df)} завершена: {phone}")
                    else:
                        logging.warning(f"Не удалось обработать контакт {index + 1}/{len(self.contacts_df)}: {phone}")

                    # Задержка перед следующим сообщением
                    time.sleep(self.delay)
                    break  # Используем только первый доступный WhatsApp номер

        logging.info("Автоматизация завершена")
        print("Автоматизация завершена. Проверьте лог-файл для подробностей.")


# Пример использования
if __name__ == "__main__":
    # Укажите путь к CSV файлу с контактами
    csv_file = "contacts_data.csv"

    # Укажите путь к PDF файлу для отправки
    pdf_file = "Создание сайтов.pdf"

    # Текст сообщения
    message = "Добрый день,\n Сайт — ваша цифровая точка продаж. Почему он еще не приносит деньги? Создайте качественный сайт недорого и начните получать заказы!"

    # Создаем экземпляр класса автоматизации
    automation = WhatsAppAutomation(csv_file, pdf_file, message, delay_between_messages=40)

    # Запускаем автоматизацию
    automation.run_automation()