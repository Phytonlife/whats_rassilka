import csv
import time
import random
import os
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException

# Путь к файлам
CSV_FILE_PATH = "contacts_data.csv"  # Путь к файлу с CSV данными
PDF_FILE_PATH = "Создание сайтов.pdf"  # Путь к PDF файлу
MESSAGE_TEMPLATE = "Добрый день,\n Сайт — ваша цифровая точка продаж. Почему он еще не приносит деньги?  Создайте качественный сайт недорого и начните получать заказы!"
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
            # Проверяем, использует ли файл разделители запятой или точки с запятой
            dialect = csv.Sniffer().sniff(file.read(1024))
            file.seek(0)

            reader = csv.DictReader(file, dialect=dialect)

            # Получаем заголовки для поиска номеров телефонов и ссылок WhatsApp
            headers = reader.fieldnames
            phone_columns = [h for h in headers if "телефон" in h.lower() or "phone" in h.lower()]
            whatsapp_columns = [h for h in headers if "whatsapp" in h.lower()]

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


def send_whatsapp_messages():
    """Отправка сообщений WhatsApp с PDF"""
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

                # Ожидание поля ввода сообщения или индикатора неверного номера
                try:
                    message_input = wait.until(
                        EC.presence_of_element_located((By.XPATH, '//div[@contenteditable="true"]'))
                    )

                    # Задержка для полной загрузки чата
                    time.sleep(random.uniform(3, 5))

                    # Ввод сообщения
                    message_input.click()
                    # Отправка сообщения по частям с задержкой для имитации печати
                    words = MESSAGE_TEMPLATE.split()
                    for word in words:
                        message_input.send_keys(word + " ")
                        time.sleep(random.uniform(0.1, 0.3))

                    # Отправка сообщения
                    message_input.send_keys(Keys.ENTER)
                    print(f"Сообщение отправлено {phone}")

                    # Ожидание отправки сообщения
                    time.sleep(random.uniform(2, 3))

                    # Прикрепление PDF файла
                    try:
                        attachment_btn = driver.find_element(By.XPATH, '//div[@title="Attach" or @title="Прикрепить"]')
                        attachment_btn.click()
                        time.sleep(1)

                        # Найти поле для загрузки документа
                        document_btn = driver.find_element(By.XPATH, '//input[@accept="*"]')
                        document_btn.send_keys(os.path.abspath(PDF_FILE_PATH))
                        time.sleep(5)  # Ожидание загрузки файла

                        # Отправка файла
                        send_file_btn = wait.until(
                            EC.element_to_be_clickable((By.XPATH, '//span[@data-icon="send"]'))
                        )
                        send_file_btn.click()
                        print(f"PDF отправлен {phone}")

                        # Сохранение номера в список отправленных
                        save_sent_number(phone)

                        # Случайная задержка между сообщениями
                        delay = random.uniform(45, 90)  # 45-90 секунд задержки
                        print(f"Ожидание {delay:.1f} секунд перед следующим сообщением...")
                        time.sleep(delay)

                    except NoSuchElementException:
                        print(f"Не удалось найти кнопку прикрепления для {phone}")
                        continue
                    except Exception as e:
                        print(f"Ошибка при прикреплении файла для {phone}: {str(e)}")
                        continue

                except TimeoutException:
                    print(f"Номер {phone} недействителен или не принимает сообщения. Пропуск.")
                    # Сохраняем номер как отправленный, чтобы избежать повторных попыток
                    save_sent_number(phone)
                    continue

            except Exception as e:
                print(f"Ошибка при отправке сообщения для {phone}: {str(e)}")
                continue

        print("Все сообщения отправлены!")

    except Exception as e:
        print(f"Произошла ошибка: {str(e)}")

    finally:
        # Закрытие браузера
        driver.quit()


if __name__ == "__main__":
    send_whatsapp_messages()