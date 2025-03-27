import pyautogui
import time
import webbrowser
import keyboard


def get_mouse_coordinates():
    print("Запуск программы определения координат мыши...")
    print("1. Сейчас откроется WhatsApp Web")
    print("2. Наведите курсор на нужный элемент и нажмите клавишу 'c' для фиксации координат")
    print("3. Для выхода из программы нажмите клавишу 'q'")
    print("\nЗапуск через 3 секунды...")
    time.sleep(3)

    # Открываем WhatsApp Web
    webbrowser.open('https://web.whatsapp.com/')
    print("\nДождитесь загрузки WhatsApp Web и авторизуйтесь через QR-код если необходимо.")
    print("После этого вы можете начать определять координаты элементов.")

    saved_coordinates = []

    # Функция которая будет выполняться при нажатии клавиши 'c'
    def on_c_press(e):
        if e.name == 'c':
            x, y = pyautogui.position()
            saved_coordinates.append((x, y))
            print(f"Сохранены координаты: X = {x}, Y = {y}")

    # Функция для выхода из программы при нажатии 'q'
    def on_q_press(e):
        if e.name == 'q':
            print("\nВыход из программы...")
            print("\nСохраненные координаты:")
            for i, (x, y) in enumerate(saved_coordinates, 1):
                print(f"{i}. X = {x}, Y = {y}")
            print("\nИспользуйте эти координаты в основном скрипте для автоматизации WhatsApp.")

            # Записываем координаты в файл для удобства
            with open('whatsapp_coordinates.txt', 'w') as f:
                f.write("Сохраненные координаты для WhatsApp Web:\n")
                for i, (x, y) in enumerate(saved_coordinates, 1):
                    f.write(f"{i}. X = {x}, Y = {y}\n")

                f.write("\nПример использования в скрипте:\n")
                elements = ["кнопка прикрепления файлов (скрепка)",
                            "опция 'Документ'",
                            "кнопка отправки файла"]

                for i, ((x, y), element) in enumerate(zip(saved_coordinates, elements)):
                    if i < len(elements):
                        f.write(f"# Координаты для элемента '{element}'\n")
                        f.write(f"pyautogui.click(x={x}, y={y})\n\n")

            print(f"Координаты также сохранены в файл 'whatsapp_coordinates.txt'")
            keyboard.unhook_all()
            return False

    # Регистрируем обработчики событий клавиатуры
    keyboard.on_press(on_c_press)
    keyboard.on_press(on_q_press)

    # Показываем текущие координаты в реальном времени
    try:
        while True:
            x, y = pyautogui.position()
            position_str = f"Текущие координаты: X = {x}, Y = {y}"
            print(position_str, end='\r')
            time.sleep(0.1)
    except KeyboardInterrupt:
        print("\nПрограмма остановлена")


if __name__ == "__main__":
    # Проверяем наличие необходимых библиотек
    try:
        import pyautogui
        import keyboard
    except ImportError:
        print("Необходимо установить библиотеки:")
        print("pip install pyautogui keyboard")
        exit(1)

    get_mouse_coordinates()