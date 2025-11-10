# import telebot
# from telebot import types
# import os
# import re
# import random
# import docx2txt
# from settings import API_KEY
#
# bot = telebot.TeleBot(API_KEY)
# user_files = {}
#
#
# def main_keyboard():
#     kb = types.ReplyKeyboardMarkup(resize_keyboard=True)
#     kb.row("📂 Загрузить файл", "🗑 Удалить файл")
#     kb.row("🎯 Сгенерировать 15 вопросов")
#     return kb
#
#
# @bot.message_handler(commands=['start'])
# def start(message):
#     bot.send_message(
#         message.chat.id,
#         f"👋 Привет, {message.from_user.first_name or 'пользователь'}!\n\n"
#         "Я бот для генерации тестов из Word-документа 🧩\n\n"
#         "📂 Загрузите .docx файл с вопросами,\n"
#         "🎯 Нажмите кнопку — и я соберу 15 вопросов по типам (ЕВ, МВ, ЧВ и т.д.)",
#         reply_markup=main_keyboard()
#     )
#
#
# @bot.message_handler(content_types=['text'])
# def handle_text(message):
#     user_id = message.from_user.id
#     text = message.text.strip().lower()
#     user_file = f"questions_{user_id}.docx"
#
#     if text == "📂 загрузить файл":
#         bot.send_message(message.chat.id, "📤 Отправьте Word-файл (.docx) с вопросами.")
#         return
#
#     if text == "🗑 удалить файл":
#         if os.path.exists(user_file):
#             os.remove(user_file)
#             user_files.pop(user_id, None)
#             bot.send_message(message.chat.id, "✅ Файл удалён.", reply_markup=main_keyboard())
#         else:
#             bot.send_message(message.chat.id, "⚠️ У вас ещё нет загруженного файла.", reply_markup=main_keyboard())
#         return
#
#     if text == "🎯 сгенерировать 15 вопросов":
#         if not os.path.exists(user_file):
#             bot.send_message(message.chat.id, "⚠️ Сначала загрузите файл (.docx).", reply_markup=main_keyboard())
#             return
#
#         bot.send_message(message.chat.id, "⏳ Извлекаю вопросы, подождите...")
#         questions, debug = extract_questions(user_file)
#
#         if not questions:
#             send_long_message(message.chat.id, f"❌ Не удалось извлечь вопросы.\n\n📋 Отчёт диагностики:\n{debug}")
#             return
#
#         send_long_message(
#             message.chat.id,
#             "📚 *Сгенерированные вопросы:*\n\n" + "\n".join(questions),
#             parse_mode="Markdown"
#         )
#         return
#
#     bot.send_message(message.chat.id, "Выберите действие из меню 👇", reply_markup=main_keyboard())
#
#
# @bot.message_handler(content_types=['document'])
# def handle_document(message):
#     user_id = message.from_user.id
#     user_file = f"questions_{user_id}.docx"
#
#     file_name = message.document.file_name
#     if not file_name.endswith(".docx"):
#         bot.send_message(message.chat.id, "⚠️ Пожалуйста, пришлите файл формата .docx")
#         return
#
#     file_info = bot.get_file(message.document.file_id)
#     downloaded = bot.download_file(file_info.file_path)
#     with open(user_file, "wb") as new_file:
#         new_file.write(downloaded)
#
#     user_files[user_id] = user_file
#     bot.send_message(message.chat.id, "✅ Файл загружен! Теперь нажмите «🎯 Сгенерировать 15 вопросов».", reply_markup=main_keyboard())
#
#
# def extract_questions(file_path):
#     import docx2txt, re, random
#     debug = []
#
#     try:
#         text = docx2txt.process(file_path)
#     except Exception as e:
#         return None, f"Ошибка чтения файла: {e}"
#
#     # Очистка лишнего
#     text = re.sub(r'[ \t]+', ' ', text)
#     text = re.sub(r'\n{2,}', '\n\n', text)
#     debug.append(f"📄 Длина текста: {len(text)} символов")
#
#     sections = [
#         "ЕВ", "МВ", "ЧВ", "Соответствие",
#         "Одно пропущенное слово", "Два пропущенных слова", "Вложенные вопросы"
#     ]
#
#     categorized, current = {}, None
#     for line in text.splitlines():
#         stripped = line.strip()
#         if stripped in sections:
#             current = stripped
#             categorized[current] = ""
#         elif current:
#             categorized[current] += line + "\n"
#
#     debug.append(f"📚 Найдено разделов: {list(categorized.keys())}")
#
#     # ---------- ВСПОМОГАТЕЛЬНЫЕ ----------
#     def normalize_options(options):
#         opts = [o.strip() for o in options.splitlines() if o.strip()]
#         return "\n".join(opts[:4])
#
#     # ---------- ЕВ / МВ ----------
#     def find_ev(text):
#         matches = re.findall(r"([^\n]+?\?)\s*\n((?:[^\n]*\n){2,8})", text, re.DOTALL)
#         return [(q.strip(), normalize_options(o)) for q, o in matches]
#
#     def find_mv(text):
#         matches = re.findall(r"([^\n]+?\?)\s*\n((?:[^\n]*\n){2,8})", text, re.DOTALL)
#         return [(q.strip(), normalize_options(o)) for q, o in matches]
#
#     # ---------- ЧВ ----------
#     def find_chv(text):
#         return re.findall(r"([^\n]+?\(Введите[^\n]+?\))\s*\n\s*=\s*([^\n]+)", text, re.DOTALL)
#
#     # ---------- Соответствие ----------
#     def find_matching(text):
#         blocks = re.findall(r"(Установите соответствие.+?(?=(?:\nУстановите соответствие|$)))", text, re.DOTALL)
#         return [re.sub(r'\n{2,}', '\n', b).strip() for b in blocks]
#
#     # ---------- Одно пропущенное слово ----------
#     def find_one_gap(text):
#         return re.findall(r"([^\n]+?\(Введите[^\n]+?\))", text)
#
#     # ---------- Два пропущенных слова ----------
#     def find_two_gap(text):
#         """
#         Извлекает каждый блок 'Два пропущенных слова':
#         шаблон с [[1]] и [[2]] + все варианты 1= и 2=.
#         """
#         # Разбиваем на отдельные куски по началу каждого блока
#         blocks = re.split(r'(?=\n?.*?\[\[1\]\].*?\[\[2\]\])', text)
#         results = []
#
#         for block in blocks:
#             block = block.strip()
#             if not block or '[[1]]' not in block:
#                 continue
#
#             # Находим сам шаблон (строку с [[1]] и [[2]])
#             main_part_match = re.search(r'([^\n]*\[\[1\]\].+?\[\[2\]\][^\n]*)', block)
#             if not main_part_match:
#                 continue
#             main_part = main_part_match.group(1).strip()
#
#             # Ищем блок вариантов — теперь до конца второго списка
#             opt_match = re.search(
#                 r'(1\s*=\s*[^\n]+(?:\n\s*(?!\d=)[^\n]+)*\n\s*2\s*=\s*[^\n]+(?:\n\s*(?!\[\[)[^\n]+)*)',
#                 block,
#                 re.DOTALL
#             )
#             options = ""
#             if opt_match:
#                 options = "\n" + re.sub(r'\n{2,}', '\n', opt_match.group(1)).strip()
#
#             # Формируем итог
#             full = f"{main_part}\n{options}".strip()
#             results.append(full)
#
#         return list(dict.fromkeys(results))
#
#     # ---------- Вложенные ----------
#     def find_nested(text):
#         blocks = re.findall(r"(?:\s*\d+\s*\n)?(.+?(?=\n\s*\d+\s*\n|$))", text, re.DOTALL)
#         return [re.sub(r'\n{2,}', '\n', b).strip() for b in blocks if b.strip()]
#
#     extractors = {
#         "ЕВ": find_ev, "МВ": find_mv, "ЧВ": find_chv,
#         "Соответствие": find_matching,
#         "Одно пропущенное слово": find_one_gap,
#         "Два пропущенных слова": find_two_gap,
#         "Вложенные вопросы": find_nested
#     }
#
#     questions = {}
#     for key, func in extractors.items():
#         sec = categorized.get(key, "")
#         if not sec.strip():
#             debug.append(f"⚠️ Раздел {key} пуст.")
#             questions[key] = []
#             continue
#         found = func(sec)
#         debug.append(f"🔍 {key}: найдено {len(found)} вопросов")
#         questions[key] = found
#
#     selection = {
#         "ЕВ": 4, "МВ": 4, "ЧВ": 2,
#         "Соответствие": 1, "Одно пропущенное слово": 2,
#         "Два пропущенных слова": 1, "Вложенные вопросы": 1
#     }
#
#     result = []
#     for key, count in selection.items():
#         pool = questions.get(key, [])
#         if not pool:
#             continue
#         sample = random.sample(pool, min(count, len(pool)))
#         for q in sample:
#             if key in ("ЕВ", "МВ") and isinstance(q, tuple):
#                 full = f"{q[0].strip()}\n" + "\n".join([l for l in q[1].splitlines() if l.strip()][:4])
#             elif key == "ЧВ" and isinstance(q, tuple):
#                 full = f"{q[0]}\nОтвет: {q[1]}"
#             else:
#                 full = q.strip()
#             result.append(f"🟩 *{key}:*\n{full}\n")
#
#     if not result:
#         return None, "\n".join(debug)
#
#     random.shuffle(result)
#     debug.append(f"✅ Всего собрано вопросов: {len(result)}")
#     return result[:15], "\n".join(debug)
#
#
#
#
#
#
#
#
#
#
#
# def send_long_message(chat_id, text, parse_mode=None):
#     """Отправляет длинное сообщение частями (до 4096 символов каждая)."""
#     max_len = 4000
#     parts = [text[i:i + max_len] for i in range(0, len(text), max_len)]
#     for part in parts:
#         bot.send_message(chat_id, part, parse_mode=parse_mode)
#
#
#
# if __name__ == "__main__":
#     print("🤖 Бот запущен (улучшенный парсер)...")
#     bot.polling(none_stop=True)
