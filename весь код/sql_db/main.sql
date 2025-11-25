-- Active: 1744916845222@@127.0.0.1@5432@postgres
-- Создаём тип ENUM для статуса пациента
CREATE TYPE patient_status AS ENUM ('болен', 'здоров', 'умер');

-- 1. Отделения
CREATE TABLE departments (
    department_id INT NOT NULL GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    department_name TEXT NOT NULL,
    bed_count INTEGER NOT NULL,
);

-- 2. Врачи
CREATE TABLE doctors (
    doctor_id INT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    first_name TEXT NOT NULL,
    last_name TEXT NOT NULL,
    department_id INTEGER REFERENCES departments(department_id) ON DELETE SET NULL,
    employment_date DATE NOT NULL,
    is_active BOOLEAN DEFAULT TRUE
);

-- 3. Пациенты
CREATE TABLE patients (
    patient_id INT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    first_name TEXT NOT NULL,
    last_name TEXT NOT NULL,
    admission_date DATE,
    discharge_date DATE,
    status patient_status,
    is_ambulatory BOOLEAN,
    department_id INTEGER REFERENCES departments(department_id) ON DELETE SET NULL
);

-- 4. Болезни
CREATE TABLE diagnoses (
    diagnosis_id INT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    diagnosis_name TEXT NOT NULL
);

-- 5. Лекарства
CREATE TABLE medications (
    medication_id INT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    medication_name TEXT NOT NULL
);

-- 6. Процедуры
CREATE TABLE procedures (
    procedure_id INT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    procedure_name TEXT NOT NULL
);

-- 7. Назначения по диагнозам (модифицировано)
CREATE TABLE diagnosis_treatments (
    treatment_id INT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    diagnosis_id INTEGER NOT NULL REFERENCES diagnoses(diagnosis_id) ON DELETE CASCADE,
    medication_id INTEGER REFERENCES medications(medication_id) ON DELETE SET NULL,
    medication_dose_per_day INTEGER,
    procedure_id INTEGER REFERENCES procedures(procedure_id) ON DELETE SET NULL,
    procedure_times_per_day INTEGER
);

-- 8. Лечение пациентов
CREATE TABLE patient_treatments (
    treatment_id INT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    patient_id INTEGER NOT NULL REFERENCES patients(patient_id) ON DELETE CASCADE,
    doctor_id INTEGER REFERENCES doctors(doctor_id) ON DELETE SET NULL,
    diagnosis_id INTEGER REFERENCES diagnoses(diagnosis_id) ON DELETE SET NULL,
    treatment_date DATE NOT NULL,
    medication_id INTEGER REFERENCES medications(medication_id) ON DELETE SET NULL,
    procedure_id INTEGER REFERENCES procedures(procedure_id) ON DELETE SET NULL,
    dose INTEGER,
    procedure_times INTEGER
);

-- 9. История состояния пациента
CREATE TABLE patient_status_history (
    history_id INT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    patient_id INTEGER NOT NULL REFERENCES patients(patient_id) ON DELETE CASCADE,
    date DATE NOT NULL,
    status patient_status
);


-- Добавляем таблицу для контроля дозировок
CREATE TABLE medication_dosage (
    medication_id INT REFERENCES medications(medication_id),
    max_daily_dose INT NOT NULL,
    PRIMARY KEY (medication_id)
);

CREATE TABLE diagnosis_department (
    diagnosis_id INT REFERENCES diagnoses(diagnosis_id) ON DELETE CASCADE,
    department_id INT REFERENCES departments(department_id) ON DELETE CASCADE,
    PRIMARY KEY (diagnosis_id, department_id)
);

INSERT INTO departments (department_name, bed_count, bed_count_free) VALUES
('Санитарный пропускник (санпропускник)', 10, 10),
('Терапевтический корпус', 50, 50),
('Хирургический корпус', 40, 40),
('Гинекологическое отделение', 30, 30),
('Клиническое отделение', 25, 25),
('Травмпункт', 20, 20);

-- Добавляем ограничение на частоту изменения лечения
ALTER TABLE patient_treatments ADD CONSTRAINT check_treatment_frequency
CHECK (treatment_date >= CURRENT_DATE - INTERVAL '1 day');

-- Добавляем таблицу для контроля дозировок
CREATE TABLE medication_dosage (
    medication_id INT REFERENCES medications(medication_id),
    max_daily_dose INT NOT NULL,
    PRIMARY KEY (medication_id)
);

INSERT INTO medications (medication_name) VALUES
('Парацетамол'),
('Ибупрофен'),
('Анальгин'),
('Цитрамон'),
('Аспирин'),
('Но-шпа'),
('Амоксициллин'),
('Нимесулид'),
('Лоперамид'),
('Активированный уголь'),
('Смекта'),
('Энтеросгель'),
('Фурацилин'),
('Хлоргексидин'),
('Мирамистин'),
('Називин'),
('Пиносол'),
('Амбробене'),
('Лазолван'),
('АЦЦ'),
('Супрастин'),
('Кларитин'),
('Зиртек'),
('Фенистил'),
('Визин'),
('Офтан Катахром'),
('Корвалол'),
('Валокордин'),
('Валидол'),
('Нитроспрей'),
('Глицин'),
('Фенибут'),
('Афобазол'),
('Ново-Пассит'),
('Мезим'),
('Креон'),
('Фестал'),
('Эспумизан'),
('Дюфалак'),
('Регидрон'),
('Линекс'),
('Бифиформ'),
('Виферон'),
('Арбидол'),
('Кагоцел'),
('Оциллококцинум'),
('Анаферон'),
('Вольтарен'),
('Фастум гель'),
('Долгит'),
('Найз гель');


INSERT INTO medication_dosage (medication_id, max_daily_dose) VALUES
(1, 4000),   -- Парацетамол
(2, 1200),   -- Ибупрофен
(3, 3000),   -- Анальгин
(4, 4000),   -- Цитрамон
(5, 4000),   -- Аспирин
(6, 240),    -- Но-шпа (дротаверин)
(7, 1500),   -- Амоксициллин
(8, 400),    -- Нимесулид
(9, 16),     -- Лоперамид
(10, 10000), -- Активированный уголь (нет строгого лимита)
(11, 6),     -- Смекта
(12, 135),   -- Энтеросгель
(13, 500),   -- Фурацилин (для полосканий)
(14, 300),   -- Хлоргексидин (0.05% раствор)
(15, 50),    -- Мирамистин
(16, 3),     -- Називин (капли)
(17, 4),     -- Пиносол
(18, 90),    -- Амбробене
(19, 90),    -- Лазолван
(20, 600),   -- АЦЦ
(21, 100),   -- Супрастин
(22, 10),    -- Кларитин
(23, 10),    -- Зиртек
(24, 3),     -- Фенистил (капли)
(25, 4),     -- Визин
(26, 6),     -- Офтан Катахром
(27, 150),   -- Корвалол (капли)
(28, 150),   -- Валокордин
(29, 600),   -- Валидол
(30, 3),     -- Нитроспрей
(31, 700),   -- Глицин
(32, 750),   -- Фенибут
(33, 30),    -- Афобазол
(34, 6),     -- Ново-Пассит (таблетки)
(35, 15000), -- Мезим (в липазных единицах)
(36, 10000), -- Креон
(37, 6),     -- Фестал
(38, 500),   -- Эспумизан
(39, 60),    -- Дюфалак
(40, 4),     -- Регидрон (пакетика)
(41, 6),     -- Линекс
(42, 6),     -- Бифиформ
(43, 1000000), -- Виферон (в МЕ)
(44, 800),   -- Арбидол
(45, 36),    -- Кагоцел
(46, 8),     -- Оциллококцинум
(47, 8),     -- Анаферон
(48, 150),   -- Вольтарен (гель)
(49, 150),   -- Фастум гель
(50, 150);   -- Найз гель


DELETE FROM procedures;
DELETE FROM diagnoses;
DELETE FROM doctors;
DELETE FROM patients;
DELETE FROM departments;

DELETE FROM patient_status_history;
DELETE FROM patient_treatments;
DELETE FROM diagnosis_treatments;


INSERT INTO departments (department_name, bed_count, bed_count_free) VALUES
('Санитарный пропускник (санпропускник)', 10, 10),
('Терапевтический корпус', 50, 50),
('Хирургический корпус', 40, 40),
('Гинекологическое отделение', 30, 30),
('Клиническое отделение', 25, 25),
('Травмпункт', 20, 20);


ALTER TABLE patients
ADD COLUMN doctor_id INTEGER REFERENCES doctors(doctor_id) ON DELETE SET NULL;

INSERT INTO doctors (first_name, last_name, department_id, employment_date, is_active) VALUES
('Иван', 'Иванов', 17, '2020-05-12', TRUE),
('Мария', 'Петрова', 21, '2019-08-21', TRUE),
('Алексей', 'Сидоров', 19, '2021-03-10', TRUE),
('Елена', 'Кузнецова', 20, '2018-11-30', TRUE),
('Дмитрий', 'Смирнов', 18, '2022-01-15', TRUE),
('Анна', 'Морозова', 22, '2017-07-25', TRUE),
('Сергей', 'Васильев', 17, '2020-12-01', TRUE),
('Ольга', 'Федорова', 21, '2023-02-05', TRUE),
('Павел', 'Андреев', 18, '2016-04-18', TRUE),
('Татьяна', 'Крылова', 22, '2019-09-09', TRUE);

INSERT INTO procedures (procedure_name) VALUES
-- Диагностические процедуры
('Рентгенография грудной клетки'),
('УЗИ брюшной полости'),
('ЭКГ (электрокардиография)'),
('Эндоскопия желудка'),
('Колоноскопия'),
('МРТ головного мозга'),
('КТ легких'),
('Анализ крови (общий)'),
('Анализ мочи (общий)'),
('Биохимический анализ крови'),
-- Лечебные процедуры
('Физиотерапия (электрофорез)'),
('Ингаляционная терапия'),
('Массаж лечебный'),
('ЛФК (лечебная физкультура)'),
('Иглорефлексотерапия'),
('Переливание крови'),
('Гемодиализ'),
('Плазмаферез'),
('Химиотерапия'),
('Лучевая терапия'),
-- Хирургические процедуры
('Аппендэктомия'),
('Лапароскопия'),
('Артроскопия коленного сустава'),
('Катетеризация вены'),
('Наложение гипса'),
('Снятие швов'),
('Пункция сустава'),
('Биопсия тканей'),
('Дренирование раны'),
('Иссечение геморроидальных узлов');

ALTER TABLE doctors
ADD COLUMN dismissal_date DATE 

ALTER TYPE patient_status ADD VALUE 'еще болен';

-- Гинекологическое отделение (id = 20)
INSERT INTO diagnoses (diagnosis_name) VALUES 
('эндометриоз'), ('миома матки'), ('аднексит'), ('внематочная беременность'), ('полип эндометрия');

-- Хирургический корпус (id = 19)
INSERT INTO diagnoses (diagnosis_name) VALUES 
('аппендицит'), ('холецистит'), ('панкреатит'), ('грыжа паховая'), ('острый перитонит');

-- Клиническое отделение (id = 21)
INSERT INTO diagnoses (diagnosis_name) VALUES 
('гипертония'), ('сахарный диабет'), ('ишемическая болезнь сердца'), ('анемия'), ('гастрит');

-- Травмпункт (id = 22)
INSERT INTO diagnoses (diagnosis_name) VALUES 
('перелом руки'), ('перелом ноги'), ('ушиб мягких тканей'), ('растяжение связок'), ('вывих плеча');

-- Терапевтический корпус (id = 18)
INSERT INTO diagnoses (diagnosis_name) VALUES 
('ОРВИ'), ('пневмония'), ('бронхит'), ('ангина'), ('астма');

-- Санитарный пропускник (id = 17)
INSERT INTO diagnoses (diagnosis_name) VALUES 
('вшивость'), ('чесотка'), ('грибок кожи'), ('корь'), ('ветрянка');

-- Связываем диагнозы с отделениями
INSERT INTO diagnosis_department (diagnosis_id, department_id)
SELECT d.diagnosis_id, 20 FROM diagnoses d WHERE LOWER(d.diagnosis_name) IN (
    'эндометриоз', 'миома матки', 'аднексит', 'внематочная беременность', 'полип эндометрия'
);

INSERT INTO diagnosis_department (diagnosis_id, department_id)
SELECT d.diagnosis_id, 19 FROM diagnoses d WHERE LOWER(d.diagnosis_name) IN (
    'аппендицит', 'холецистит', 'панкреатит', 'грыжа паховая', 'острый перитонит'
);

INSERT INTO diagnosis_department (diagnosis_id, department_id)
SELECT d.diagnosis_id, 21 FROM diagnoses d WHERE LOWER(d.diagnosis_name) IN (
    'гипертония', 'сахарный диабет', 'ишемическая болезнь сердца', 'анемия', 'гастрит'
);

INSERT INTO diagnosis_department (diagnosis_id, department_id)
SELECT d.diagnosis_id, 22 FROM diagnoses d WHERE LOWER(d.diagnosis_name) IN (
    'перелом руки', 'перелом ноги', 'ушиб мягких тканей', 'растяжение связок', 'вывих плеча'
);

INSERT INTO diagnosis_department (diagnosis_id, department_id)
SELECT d.diagnosis_id, 18 FROM diagnoses d WHERE LOWER(d.diagnosis_name) IN (
    'орви', 'пневмония', 'бронхит', 'ангина', 'астма'
);

INSERT INTO diagnosis_department (diagnosis_id, department_id)
SELECT d.diagnosis_id, 17 FROM diagnoses d WHERE LOWER(d.diagnosis_name) IN (
    'вшивость', 'чесотка', 'грибок кожи', 'корь', 'ветрянка'
);


ALTER TABLE diagnoses
ADD COLUMN department_id INTEGER REFERENCES departments(department_id);

INSERT INTO diagnoses (diagnosis_name, department_id) VALUES
('Миома матки', 20),
('Эндометриоз', 20),
('Поликистоз яичников', 20),
('Цистит', 20),
('Вагинит', 20),
('Апендицит', 19),
('Желчнокаменная болезнь', 19),
('Грыжа', 19),
('Панкреатит', 19),
('Ожоги', 19),
('Пневмония', 21),
('Бронхит', 21),
('Астма', 21),
('COVID-19', 21),
('Грипп', 21),
('Перелом руки', 22),
('Перелом ноги', 22),
('Ушиб головы', 22),
('Растяжение связок', 22),
('Вывих', 22),
('Гастрит', 18),
('Язва желудка', 18),
('Гипертония', 18),
('Диабет', 18),
('Мигрень', 18),
('Чесотка', 17),
('Педикулёз', 17),
('ОКИ', 17),
('ОРВИ', 17),
('Конъюнктивит', 17);

