import telebot
from telebot import types
import re
import os
import docx2txt
from settings import API_KEY

bot = telebot.TeleBot(API_KEY)

# Храним дисциплины для каждого пользователя
user_disciplines = {}

# Обработка команды /start
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



# Обработка входящего текста
@bot.message_handler(content_types=['text'])
def handle_text(message):
    text = message.text.strip().lower()
    user_id = message.from_user.id
    user_file = f"competencies_{user_id}.docx"

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
    if not os.path.exists(user_file):
        bot.send_message(message.chat.id, "⚠️ Сначала загрузите файл (📂 Загрузить компетенции).", reply_markup=main_keyboard())
        return

    # --- ЕСЛИ ЕЩЁ НЕ ИЗВЛЕЧЕНО ---
    if user_id not in user_disciplines:
        disciplines = extract_disciplines(user_file)
        if not disciplines:
            bot.send_message(message.chat.id, "❌ Не удалось извлечь дисциплины из файла.", reply_markup=main_keyboard())
            return
        user_disciplines[user_id] = disciplines

    # --- ПОИСК ---
    disciplines = user_disciplines[user_id]
    found = [d for d in disciplines if text in d.lower()]

    if not found:
        bot.send_message(
            message.chat.id,
            "❌ Тема не найдена. Попробуйте ввести точнее.\n\n💡 Совет: введи часть названия, например 'жизнедеятельность'.",
            reply_markup=main_keyboard()
        )
        return

    # --- РЕЗУЛЬТАТ ---
    result_text = "📚 Найдено совпадений:\n\n" + "\n\n".join([f"📘 {f}" for f in found])
    bot.send_message(message.chat.id, result_text, reply_markup=main_keyboard())


# Обработка входящих документов
@bot.message_handler(content_types=['document'])
def handle_document(message):
    user_id = message.from_user.id
    user_file = f"competencies_{user_id}.docx"

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
    disciplines = extract_disciplines(user_file)
    user_disciplines[user_id] = disciplines

    bot.send_message(message.chat.id, f"✅ Файл успешно загружен! Найдено {len(disciplines)} дисциплин.", reply_markup=main_keyboard())

def extract_disciplines(file_path):
    """Извлекает дисциплины из всего .docx файла (анализирует весь текст полностью)."""
    full_text = docx2txt.process(file_path)

    # Показываем только краткую статистику, без вывода текста
    print("📘 Текст успешно считан. Общая длина:", len(full_text), "символов")

    # Универсальная регулярка под любые варианты:
    # Б1Б / Б2ВЭ / Б3ГИА / и т.д. + любые пробелы и УК
    pattern = r"(Б\d{1,2}[А-ЯA-Za-zа-яёЁ]*\s*\d*\s*[А-ЯA-Za-zа-яёЁ0-9,\-–\s]+?\(УК\s*[\d.\sА-Яа-яA-Za-z]*\))"

    matches = re.findall(pattern, full_text)

    print("🔍 Найдено дисциплин:", len(matches))
    for i, m in enumerate(matches[:10]):
        print(f"{i+1}: {m}")

    disciplines = [" ".join(m.split()) for m in matches]
    return disciplines

def main_keyboard():
    kb = types.ReplyKeyboardMarkup(resize_keyboard=True)
    kb.row("📂 Загрузить компетенции", "🗑 Удалить файл")
    return kb

if __name__ == "__main__":
    print("🤖 Бот запущен...")
    bot.polling(none_stop=True)
