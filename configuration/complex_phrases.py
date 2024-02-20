from configuration.service.compex_phrase import ComplexPhrase

ALGOLIA_ANSWER_TEMPLATE = ComplexPhrase(
    "❓ Похоже, у нас есть подходящий ответ на твой вопрос:\n\n{algolia_answer}"
)

PAGINATION_TICKET_TEMPLATE = ComplexPhrase("❓ №{ticket_id}")
PAGINATION_REQUEST_TEMPLATE = ComplexPhrase("№{request_id}")

TICKET_PHRASE_CONSTRUCTOR = ComplexPhrase(
    "❓ Вопрос №{ticket_id}\n"
    "Статус: {status}\n"
    "Вопрос задан: {created_on}\n\n"
    "«{ticket_message}»"
)
TICKET_WITH_DIALOG_CONSTRUCTOR = ComplexPhrase(
    "❓ Вопрос №{ticket_id}\n"
    "Статус: {status}\n"
    "Вопрос задан: {created_on}\n\n"
    "{dialog}"
)
TICKET_MESSAGE_ADMIN_AUTHOR = "👮‍♂️"
TICKET_MESSAGE_USER_AUTHOR = "👽"
TICKET_MESSAGE_CONSTRUCTOR = ComplexPhrase("{author} {time_dmy} в {time_hm}: {text}")
TICKET_LOG_STATUS_UPDATE = ComplexPhrase(
    "❓ Вопрос №{id}\nУ вопроса обновился статус: {status}"
)
TICKET_LOG_MESSAGE_NEW = ComplexPhrase(
    "❓ Вопрос №{id}\nАдминистратор добавил ответ к вопросу:\n{message}"
)
TICKET_SUCCESS = ComplexPhrase(
    "☑️ Твой вопрос №{id} был принят\nМы рассмотрим его в ближайшее время и обязательно дадим ответ\nСпасибо ❤️"
)

ONE_ATTACHED_FILE = ComplexPhrase("📁 {count} прикреплённый файл")
SOME_ATTACHED_FILES = ComplexPhrase("📁 {count} прикреплённых файла")
MANY_ATTACHED_FILES = ComplexPhrase("📁 {count} прикреплённых файлов")

EDITOR_COMPLAIN_CONFIRM = ComplexPhrase(
    "‼️ Этап 3: Отправка жалобы 📩\n"
    "Проверь ещё раз всю информацию, которую ты указал. Если всё правильно, то отправляй запрос.\n"
    "В случае, если что-то не сходится, начни процесс с начала.\n\n"
    "✍️ Комментарий: {comment}\n💬 Примечание: {message}",
)
EDITOR_SUCCESS = ComplexPhrase(
    "🎉 Готово! 🎉\nМы выдали тебе редактора в группе @{group_screen_name}"
)
EDITOR_JOIN_GROUP = ComplexPhrase(
    "Круто! Мы подобрали тебе группу. Теперь вступи в неё: @{group_screen_name}"
)
EDITOR_FAIL = ComplexPhrase("💣 Не удалось выдать редактора: {reason}")
EDITOR_FAIL_LEFT_GROUP = ComplexPhrase(
    "Упс. Похоже во время выдачи редактора ты вышел из группы 👁👄👁\nДавай попробуем ещё раз 🧠"
)

SUPPORT_UNBLOCK_CONFIRM = ComplexPhrase(
    "👁️ Этап 3: Отправка запроса 📩\n"
    "Проверь ещё раз всю информацию, которую ты указал. Если всё правильно, то отправляй запрос.\n"
    "В случае, если что-то не сходится, начни процесс с начала.\n\n"
    "💬 Примечание: {message}"
)

INVITE_CONFIRM = ComplexPhrase(
    "Ты хочешь принять приглашение от пользователя [id{user_id}|{user_name}]? 😏"
)
USER_SCREEN_NAME_ALREADY_INVITED = ComplexPhrase(
    "Ты уже приглашен пользователем [id{user_id}|{user_name}] 😿"
)
USER_ID_ALREADY_INVITED = ComplexPhrase(
    "Ты уже приглашен пользователем @id{user_id} 😿"
)
INVITE_SUCCESS = ComplexPhrase("Ты принял приглашение от [id{user_id}|{user_name}] 🧣️️️️️️")

FAILED_TO_OPEN_REQUEST = ComplexPhrase("💣 Не удалось создать запрос: {response}")
COMPLAINT_SUCCESS = ComplexPhrase(
    "☑️ Твоя жалоба №{id} была принята\nМы рассмотрим её в ближайшее время и обязательно дадим ответ. Если что, ты всегда можешь посмотреть статус жалобы в архиве.\nСпасибо ❤️"
)

PROFILE_STRING = ComplexPhrase(
    "👽 Твой профиль\n👤 Имя: [id{user_id}|{user_name}]\n🤝 Траст-фактор: {trust}\n✈️ Привязка Telegram: {telegram}\n"
)
PROFILE_GROUPS = ComplexPhrase("✏ Группы ({limit}): {group_list}")
PROFILE_VIOLATION_PRIORITY = ComplexPhrase("✏️ Приоритет: {priority}\n")
PROFILE_VIOLATION_GROUP = ComplexPhrase("👥 Группа: @{group_screen_name}\n")
PROFILE_VIOLATION_DATE = ComplexPhrase("⏰ Дата нарушения: {date}\n")
PROFILE_VIOLATION_COMPLAINT = ComplexPhrase("😶‍🌫️ По жалобе от @id{user_id}")
PROFILE_INVITE_HEADING = ComplexPhrase(
    "🔗 Приглашения\nТы можешь поделиться своей специальной командой со своим другом. В зависимости от твоего траст-фактора, твой друг может получить больше доступных групп в начале.\n\n🖇 Твоя команда: /hi {invite}\n\n"
)
PROFILE_INVITED_BY = ComplexPhrase("🧣 Тебя пригласил: [id{user_id}|{user_name}]\n")
PROFILE_INVITED_BY_ID = ComplexPhrase("🧣 Тебя пригласил: @id{user_id}\n")
PROFILE_USER_INVITED = ComplexPhrase("✉️ Ты пригласил: {user_list}")

WATCHDOG_NEW_WARNING = ComplexPhrase(
    "⚠️ Новое предупреждение\nПричина: {priority}\nДействие совершено в @{group_screen_name}"
)

WATCHDOG_NEW_BAN = ComplexPhrase(
    "❗ Ты был заблокирован\nПричина: {priority}\nДействие совершено в @{group_screen_name}"
)
