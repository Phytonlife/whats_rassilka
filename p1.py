import csv
import time
import random
import os
import re
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException, StaleElementReferenceException

# Путь к файлам
CSV_FILE_PATH = "contacts_data.csv"  # Путь к файлу с CSV данными
PDF_FILE_PATH = "document.pdf"  # Путь к PDF файлу
MESSAGE_TEMPLATE = "Здравствуйте! Отправляем Вам важную информацию. Пожалуйста, ознакомьтесь с приложенным документом."  # Шаблон сообщения
SESSION_FOLDER = "whatsapp_session"  # Папка для сохранения сессии

# Создаем папку для сессии, если она не существует
if not os.path.exists(SESSION_FOLDER):
    os.makedirs(SESSION_FOLDER)

# Файл для хранения номеров, которым уже отправлены сообщения
SENT_NUMBERS_FILE = "sent_numbers.txt"


def extract_phone_numbers_from_csv(csv_file_path):
    """Извлечение номеров телефонов и WhatsApp из CSV файла"""
    phone_numbers = []
    whatsapp_links = []

    try:
        with open(csv_file_path, 'r', encoding='utf-8') as file:
            # Читаем первую строку для определения разделителя
            first_line = file.readline()
            file.seek(0)

            # Определяем разделитель (запятая или точка с запятой)
            delimiter = ',' if first_line.count(',') > first_line.count(';') else ';'

            reader = csv.DictReader(file, delimiter=delimiter)

            # Получаем заголовки для поиска номеров телефонов и ссылок WhatsApp
            headers = reader.fieldnames
            phone_columns = [h for h in headers if h and ("телефон" in h.lower() or "phone" in h.lower())]
            whatsapp_columns = [h for h in headers if h and "whatsapp" in h.lower()]

            for row in reader:
                # Извлечение обычных номеров телефонов
                for column in phone_columns:
                    if column in row and row[column]:
                        # Очистка номера от нецифровых символов
                        phone = ''.join(filter(str.isdigit, row[column]))
                        if phone:
                            # Убираем первую цифру, если это 8 или 7 (код страны)
                            if phone.startswith('8') or phone.startswith('7'):
                                phone = '7' + phone[1:]  # Заменяем первую цифру на 7
                            elif not phone.startswith('7'):
                                phone = '7' + phone  # Добавляем 7 в начало, если её нет
                            phone_numbers.append(phone)

                # Извлечение ссылок WhatsApp
                for column in whatsapp_columns:
                    if column in row and row[column]:
                        whatsapp_link = row[column]
                        if whatsapp_link:
                            # Если это ссылка вида https://wa.me/77715221500, извлекаем номер
                            if "wa.me/" in whatsapp_link:
                                parts = whatsapp_link.split("wa.me/")
                                if len(parts) > 1:
                                    # Извлекаем только цифры
                                    phone = ''.join(filter(str.isdigit, parts[1].split('?')[0]))
                                    if phone:
                                        whatsapp_links.append(phone)

            # Объединяем все номера, отдавая приоритет WhatsApp ссылкам
            all_numbers = list(set(whatsapp_links + phone_numbers))

            print(f"Найдено номеров телефонов: {len(phone_numbers)}")
            print(f"Найдено ссылок WhatsApp: {len(whatsapp_links)}")
            print(f"Всего уникальных номеров: {len(all_numbers)}")

            return all_numbers

    except Exception as e:
        print(f"Ошибка при чтении CSV файла {csv_file_path}: {str(e)}")
        return []


def get_sent_numbers():
    """Получение номеров, которым уже были отправлены сообщения"""
    sent_numbers = set()
    if os.path.exists(SENT_NUMBERS_FILE):
        with open(SENT_NUMBERS_FILE, 'r') as file:
            sent_numbers = set(file.read().splitlines())
    return sent_numbers


def save_sent_number(phone):
    """Сохранение номера в список отправленных"""
    with open(SENT_NUMBERS_FILE, 'a') as file:
        file.write(f"{phone}\n")


def sanitize_text(text):
    """Очистка текста от символов, не входящих в BMP"""
    # Оставляем только символы BMP (Basic Multilingual Plane)
    return re.sub(r'[^\u0000-\uFFFF]', '', text)


def wait_for_chat_to_load(driver, wait):
    """Ожидание загрузки чата и поиск поля для ввода сообщения"""
    # Различные локаторы для поля ввода сообщения в чате
    input_selectors = [
        "//div[@contenteditable='true' and @data-tab='10']",
        "//div[@contenteditable='true' and @title='Type a message']",
        "//div[@contenteditable='true' and @data-testid='conversation-compose-box-input']",
        "//div[@contenteditable='true' and @spellcheck='true']",
        "//div[@role='textbox' and @contenteditable='true']",
        "//footer//div[@contenteditable='true']"
    ]

    # Проверяем наличие текста "Phone number shared via url is invalid"
    try:
        invalid_number = wait.until(
            EC.presence_of_element_located((
                By.XPATH,
                "//*[contains(text(), 'Phone number shared via url is invalid') or contains(text(), 'Номер телефона неверный')]"
            ))
        )
        return None  # Если номер неверный, возвращаем None
    except TimeoutException:
        pass  # Номер может быть верным, продолжаем поиск поля для ввода

    # Ожидаем появления хотя бы одного из указанных элементов
    for selector in input_selectors:
        try:
            input_field = wait.until(EC.presence_of_element_located((By.XPATH, selector)))
            # Проверка, что это поле ввода, а не поле поиска
            parent = driver.execute_script("return arguments[0].closest('footer');", input_field)
            if parent or "footer" in driver.execute_script("return arguments[0].outerHTML;", input_field):
                return input_field
        except (TimeoutException, StaleElementReferenceException):
            continue

    # Если не нашли поле ввода по селекторам, пробуем найти по местоположению
    try:
        # Ищем подвал страницы (footer), где обычно находится поле ввода сообщения
        footer = wait.until(EC.presence_of_element_located((By.XPATH, "//footer")))
        input_fields = footer.find_elements(By.XPATH, ".//div[@contenteditable='true']")
        if input_fields:
            return input_fields[0]
    except (TimeoutException, NoSuchElementException):
        pass

    # Последняя попытка - находим все поля ввода и берем последнее (обычно это поле для сообщения)
    try:
        all_inputs = driver.find_elements(By.XPATH, "//div[@contenteditable='true']")
        if all_inputs:
            return all_inputs[-1]  # Берем последний элемент
    except NoSuchElementException:
        pass

    return None  # Не нашли подходящее поле для ввода


def send_whatsapp_messages():
    """Отправка сообщений WhatsApp с PDF"""
    # Очистка шаблона сообщения от проблемных символов
    clean_message = sanitize_text(MESSAGE_TEMPLATE)

    # Извлечение номеров телефонов
    print("Извлечение номеров телефонов из CSV...")
    all_phone_numbers = extract_phone_numbers_from_csv(CSV_FILE_PATH)
    print(f"Найдено {len(all_phone_numbers)} номеров телефонов.")

    # Получение уже отправленных номеров
    sent_numbers = get_sent_numbers()
    phone_numbers = [phone for phone in all_phone_numbers if phone not in sent_numbers]
    print(f"Осталось отправить {len(phone_numbers)} номеров.")

    if not phone_numbers:
        print("Нет новых номеров для отправки.")
        return

    # Инициализация браузера
    options = webdriver.ChromeOptions()
    options.add_argument(f"--user-data-dir={os.path.abspath(SESSION_FOLDER)}")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    # Добавляем опцию для решения проблемы с BMP символами
    options.add_argument('--disable-extensions')
    options.add_argument('--disable-gpu')

    driver = webdriver.Chrome(options=options)

    try:
        # Открытие WhatsApp Web
        driver.get("https://web.whatsapp.com/")

        # Проверка авторизации и ожидание сканирования QR-кода если необходимо
        print("Проверка авторизации в WhatsApp Web...")
        wait = WebDriverWait(driver, 120)

        # Проверка наличия QR-кода
        try:
            qr_code = WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.XPATH, '//div[contains(@class, "landing-wrapper")]'))
            )
            print("Требуется сканирование QR-кода. Отсканируйте код на экране.")

            # Ожидание входа в систему
            wait.until(EC.invisibility_of_element_located((By.XPATH, '//div[contains(@class, "landing-wrapper")]')))
            print("Авторизация прошла успешно!")
        except TimeoutException:
            print("Вы уже авторизованы или QR-код не найден.")

        # Ожидание полной загрузки WhatsApp
        wait.until(EC.presence_of_element_located((By.XPATH, '//div[@id="app"]')))
        time.sleep(5)  # Дополнительная задержка для полной загрузки

        # Обработка каждого номера телефона
        for i, phone in enumerate(phone_numbers):
            try:
                # Конструирование URL прямого чата
                direct_url = f"https://web.whatsapp.com/send?phone={phone}"
                driver.get(direct_url)

                # Ожидание загрузки чата
                print(f"Открытие чата с номером {phone} ({i + 1}/{len(phone_numbers)})...")

                # Ждем достаточно долго для загрузки страницы
                time.sleep(5)

                # Ищем поле для ввода сообщения с помощью улучшенной функции
                message_input = wait_for_chat_to_load(driver, wait)

                if message_input is None:
                    print(f"Не удалось найти поле для ввода сообщения или номер {phone} недействителен. Пропуск.")
                    save_sent_number(phone)
                    continue

                # Задержка для полной загрузки чата
                time.sleep(random.uniform(3, 5))

                # Сначала очищаем поле на случай, если там уже что-то есть
                driver.execute_script("arguments[0].innerHTML = '';", message_input)
                message_input.click()

                # Отправляем текст по частям с помощью send_keys вместо JavaScript
                # Это более надежный метод
                for word in clean_message.split():
                    message_input.send_keys(word + " ")
                    time.sleep(random.uniform(0.1, 0.3))

                # Добавляем небольшую задержку перед отправкой
                time.sleep(random.uniform(1, 2))

                # Отправка сообщения
                message_input.send_keys(Keys.ENTER)
                print(f"Сообщение отправлено {phone}")

                # Ожидание отправки сообщения
                time.sleep(random.uniform(2, 3))

                # Прикрепление PDF файла
                try:
                    # Используем несколько вариантов поиска кнопки прикрепления
                    attachment_selectors = [
                        '//div[@title="Attach" or @title="Прикрепить"]',
                        '//div[@aria-label="Attach" or @aria-label="Прикрепить"]',
                        '//span[@data-icon="attach" or @data-testid="clip"]',
                        '//span[@data-testid="clip"]',
                        '//*[name()="svg" and (@data-icon="attach" or @data-testid="clip")]/..',
                        '//button[contains(@class, "attach")]'
                    ]

                    attachment_btn = None
                    for selector in attachment_selectors:
                        try:
                            attachment_btn = driver.find_element(By.XPATH, selector)
                            break
                        except NoSuchElementException:
                            continue

                    if not attachment_btn:
                        print(f"Не удалось найти кноп
