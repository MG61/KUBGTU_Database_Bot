import telebot
from telebot import types
from docx import Document
import re
import os

from settings import API_KEY

# ------------------ НАСТРОЙКИ ------------------
bot = telebot.TeleBot(API_KEY)

# Хранилище дисциплин по пользователям
user_disciplines = {}

# ------------------ ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ ------------------

def get_user_file(user_id):
    """Возвращает путь к файлу конкретного пользователя."""
    return f"competencies_{user_id}.docx"


def extract_disciplines_from_docx(file_path):
    """
    Извлекает дисциплины и связанные УК из .docx,
    даже если они перечислены в одной ячейке.
    """
    doc = Document(file_path)
    text = ""

    # Собираем текст всех ячеек таблиц
    print("📄 Всего таблиц в документе:", len(doc.tables))
    for table in doc.tables:
        for row in table.rows:
            for cell in row.cells:
                text += " " + cell.text.strip()

    # Ищем все строки вида "Б1Б 4 Безопасность жизнедеятельности (УК 7.3 УК 7.4)"
    pattern = r"(Б\d+[А-ЯA-Zа-яa-zЁё\s\d,–\-]+?\(УК\s*[\d.\s]+\))"
    matches = re.findall(pattern, text)

    disciplines = []
    for match in matches:
        clean = " ".join(match.split())
        disciplines.append(clean)

    print(f"📘 Найдено дисциплин: {len(disciplines)}")
    for d in disciplines[:5]:
        print("•", d)

    return disciplines


def main_keyboard():
    kb = types.ReplyKeyboardMarkup(resize_keyboard=True)
    kb.row("📂 Загрузить компетенции", "🗑 Удалить файл")
    return kb


# ------------------ /START ------------------
@bot.message_handler(commands=['start'])
def start(message):
    bot.send_message(
        message.chat.id,
        f"👋 Привет, {message.from_user.first_name or 'пользователь'}!\n\n"
        "Я бот для работы с таблицей компетенций 📄\n\n"
        "📂 Загрузите Word (.docx) файл с компетенциями,\n"
        "🔍 введите часть названия дисциплины — и я покажу связанные УК!\n\n"
        "🗑 Можно также удалить свой файл.\n\n"
        "Выбери действие 👇",
        reply_markup=main_keyboard()
    )


# ------------------ ОБРАБОТКА ТЕКСТА ------------------
@bot.message_handler(content_types=['text'])
def handle_text(message):
    text = message.text.strip().lower()
    user_id = message.from_user.id
    user_file = get_user_file(user_id)

    # --- ЗАГРУЗКА ФАЙЛА ---
    if text == "📂 загрузить компетенции":
        bot.send_message(message.chat.id, "📤 Отправь мне Word-файл (.docx) с таблицей компетенций.")
        return

    # --- УДАЛЕНИЕ ФАЙЛА ---
    if text == "🗑 удалить файл":
        if os.path.exists(user_file):
            os.remove(user_file)
            user_disciplines.pop(user_id, None)
            bot.send_message(message.chat.id, "✅ Ваш файл успешно удалён.", reply_markup=main_keyboard())
        else:
            bot.send_message(message.chat.id, "⚠️ У вас ещё нет загруженного файла.", reply_markup=main_keyboard())
        return

    # --- ПРОВЕРКА НАЛИЧИЯ ФАЙЛА ---
    if user_id not in user_disciplines:
        if not os.path.exists(user_file):
            bot.send_message(message.chat.id, "⚠️ Сначала загрузите файл (📂 Загрузить компетенции).", reply_markup=main_keyboard())
            return
        else:
            # Если файл есть, но не обработан — читаем
            user_disciplines[user_id] = extract_disciplines_from_docx(user_file)

    disciplines = user_disciplines[user_id]

    # --- ПОИСК ПО ТЕКСТУ ---
    found = [d for d in disciplines if text in d.lower()]

    if not found:
        bot.send_message(
            message.chat.id,
            "❌ Тема не найдена. Попробуйте ввести точнее.\n\n"
            "💡 Совет: попробуй ввести только часть названия, например «жизнедеятельность».",
            reply_markup=main_keyboard()
        )
        return

    # --- ФОРМИРУЕМ ОТВЕТ ---
    response = "📚 Найдено совпадений:\n\n" + "\n\n".join([f"📘 {d}" for d in found])
    bot.send_message(message.chat.id, response, reply_markup=main_keyboard())


# ------------------ ОБРАБОТКА ДОКУМЕНТА ------------------
@bot.message_handler(content_types=['document'])
def handle_document(message):
    user_id = message.from_user.id
    user_file = get_user_file(user_id)
    file_name = message.document.file_name

    if not file_name.endswith(".docx"):
        bot.send_message(message.chat.id, "⚠️ Пожалуйста, пришлите файл формата .docx")
        return

    # Сохраняем файл
    file_info = bot.get_file(message.document.file_id)
    downloaded = bot.download_file(file_info.file_path)
    with open(user_file, "wb") as new_file:
        new_file.write(downloaded)

    # Извлекаем дисциплины
    disciplines = extract_disciplines_from_docx(user_file)
    user_disciplines[user_id] = disciplines

    bot.send_message(message.chat.id, "✅ Файл успешно загружен и готов к работе!", reply_markup=main_keyboard())


# ------------------ ЗАПУСК ------------------
if __name__ == "__main__":
    print("🤖 Бот запущен...")
    bot.polling(none_stop=True)
