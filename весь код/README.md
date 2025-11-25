#-hospital_bot/
│
├── bot.py              # Точка входа
├── db.py               # Работа с базой (заменяет database.py)
├── config.py           # Токен бота и настройки БД
├── FSM.py              # Машины состояний (можно разбить на patient_states.py и др.)
├── handlers.py         # Обработка команд (можно разбить на handlers/patients.py и др.)
├── buttons.py          # Клавиатуры (соответствует keyboards/inline.py)
├── tests.py            # Тесты (не указан в плане, но логично добавить)
│
├── sql_db/
│   └── main.sql        # SQL-скрипт создания базы
│
├── requirements.txt    # Список библиотек
├── plan.txt            # План проекта
└── README.md           # Описание проекта


       
