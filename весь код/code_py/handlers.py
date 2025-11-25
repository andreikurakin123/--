from aiogram import Router, F
from aiogram.types import Message
from aiogram.filters import Command 
from FSM import AddPatientStates, AddDoctorStates, UpdateStatusStates, TreatmentStates, ShowTableStates, ReportStates
from FSM import DismissDoctor
from aiogram.fsm.context import FSMContext
from db import execute, fetch, fetchrow, fetchval
from datetime import datetime
from datetime import date

router = Router()

@router.message(Command("start"))
async def cmd_start(message: Message):
    await message.answer(
        "Добро пожаловать! Я — бот для управления больницей.\n"
        "Для списка доступных команд введите /help."
    )

@router.message(Command("help"))
async def cmd_help(message: Message):
    await message.answer(
        "Доступные команды:\n"
        "/start — начать работу\n"
        "/help — показать справку\n"
        "/add_patient — добавить пациента\n"
        "/add_doctor — добавить врача\n"
        "/update_status — обновить статус пациента\n"
        "/assign_treatment - назначение лечения\n"
        "/show_table - вывод таблицы\n"
        "/dismiss_doctor - увольнение врача\n"
    )

#! добавление пациента

@router.message(Command("add_patient"))
async def cmd_add_patient(message: Message, state: FSMContext):
    await message.answer("Введите имя пациента:")
    await state.set_state(AddPatientStates.waiting_for_first_name)


@router.message(AddPatientStates.waiting_for_first_name)
async def process_first_name(message: Message, state: FSMContext):
    await state.update_data(first_name=message.text)
    await message.answer("Введите фамилию пациента:")
    await state.set_state(AddPatientStates.waiting_for_last_name)


@router.message(AddPatientStates.waiting_for_last_name)
async def process_last_name(message: Message, state: FSMContext):
    await state.update_data(last_name=message.text)

    departments = await fetch("SELECT department_id, department_name, bed_count_free FROM departments")
    if not departments:
        await message.answer("Отделения не найдены.")
        await state.clear()
        return

    text = "Выберите ID отделения для пациента:\n"
    for dep in departments:
        text += f"{dep['department_id']}: {dep['department_name']} (свободных коек: {dep['bed_count_free']})\n"
    await message.answer(text)

    await state.set_state(AddPatientStates.waiting_for_department_id)


@router.message(AddPatientStates.waiting_for_department_id)
async def process_patient_department(message: Message, state: FSMContext):
    try:
        department_id = int(message.text)
    except ValueError:
        await message.answer("Введите корректный числовой ID отделения.")
        return

    doctors = await fetch(
        "SELECT doctor_id, first_name, last_name FROM doctors WHERE department_id = $1 AND is_active = TRUE",
        department_id
    )

    if not doctors:
        await message.answer("В этом отделении нет активных врачей. Сначала добавьте врача.")
        await state.clear()
        return

    text = "Выберите ID врача для пациента:\n"
    for doc in doctors:
        text += f"{doc['doctor_id']}: {doc['first_name']} {doc['last_name']}\n"

    await state.update_data(department_id=department_id)
    await message.answer(text)
    await state.set_state(AddPatientStates.waiting_for_doctor_id)


@router.message(AddPatientStates.waiting_for_doctor_id)
async def process_patient_doctor(message: Message, state: FSMContext):
    try:
        doctor_id = int(message.text)
    except ValueError:
        await message.answer("Введите корректный числовой ID врача.")
        return

    doctor_exists = await fetchval(
        "SELECT 1 FROM doctors WHERE doctor_id = $1 AND is_active = TRUE",
        doctor_id
    )
    if not doctor_exists:
        await message.answer("Врач не найден или неактивен!")
        return

    await state.update_data(doctor_id=doctor_id)
    data = await state.get_data()

    # Получение доступных диагнозов в выбранном отделении
    diagnoses = await fetch("""
        SELECT diagnosis_name FROM diagnoses
        WHERE department_id = $1
    """, data['department_id'])

    if diagnoses:
        text = "Введите диагноз пациента или выберите из списка ниже:\n"
        for d in diagnoses:
            text += f"• {d['diagnosis_name'].capitalize()}\n"
    else:
        text = "Введите диагноз пациента (в этом отделении пока нет сохранённых диагнозов):"

    await message.answer(text)
    await state.set_state(AddPatientStates.waiting_for_diagnosis)


@router.message(AddPatientStates.waiting_for_diagnosis)
async def process_diagnosis(message: Message, state: FSMContext):
    diagnosis_name = message.text.strip().lower()
    data = await state.get_data()
    department_id = data['department_id']
    doctor_id = data['doctor_id']

    # Поиск или добавление диагноза
    existing = await fetch("""
        SELECT diagnosis_id FROM diagnoses 
        WHERE LOWER(diagnosis_name) = $1 AND department_id = $2
    """, diagnosis_name, department_id)

    if existing:
        diagnosis_id = existing[0]['diagnosis_id']
    else:
        await execute("""
            INSERT INTO diagnoses (diagnosis_name, department_id)
            VALUES ($1, $2)
        """, diagnosis_name, department_id, execute=True)

        new_diagnosis = await fetch("""
            SELECT diagnosis_id FROM diagnoses 
            WHERE LOWER(diagnosis_name) = $1 AND department_id = $2
        """, diagnosis_name, department_id)
        diagnosis_id = new_diagnosis[0]['diagnosis_id']

    first_name = data['first_name']
    last_name = data['last_name']

    # Добавление пациента
    await execute("""
        INSERT INTO patients 
        (first_name, last_name, admission_date, status, is_ambulatory, department_id, doctor_id)
        VALUES 
        ($1, $2, $3, $4, $5, $6, $7)
    """,
        first_name,
        last_name,
        datetime.now().date(),
        'болен',
        False,
        department_id,
        doctor_id,
        execute=True
    )

    # Получение ID пациента
    patient_row = await fetch("""
        SELECT patient_id FROM patients 
        WHERE first_name = $1 AND last_name = $2
        ORDER BY patient_id DESC LIMIT 1
    """, first_name, last_name)
    patient_id = patient_row[0]['patient_id']

    # Добавление диагноза пациенту
    await execute("""
        INSERT INTO patient_treatments (patient_id, diagnosis_id, treatment_date, doctor_id)
        VALUES ($1, $2, CURRENT_DATE, $3)
    """, patient_id, diagnosis_id, doctor_id, execute=True)

    # Обновление количества свободных коек
    await execute("""
        UPDATE departments
        SET bed_count_free = bed_count_free - 1
        WHERE department_id = $1
    """, department_id, execute=True)

    await message.answer(
        f"Пациент {first_name} {last_name} успешно добавлен в отделение {department_id} с диагнозом '{diagnosis_name}'.\n"
        "Теперь вы можете назначить лечение командой /assign_treatment"
    )
    await state.clear()


#! добавление врача 

@router.message(Command("add_doctor"))
async def cmd_add_doctor(message: Message, state: FSMContext):
    await message.answer("Введите имя врача:")
    await state.set_state(AddDoctorStates.waiting_for_first_name)

@router.message(AddDoctorStates.waiting_for_first_name)
async def process_first_name(message: Message, state: FSMContext):
    await state.update_data(first_name=message.text)
    await message.answer("Введите фамилию врача:")
    await state.set_state(AddDoctorStates.waiting_for_last_name)

@router.message(AddDoctorStates.waiting_for_last_name)
async def process_last_name(message: Message, state: FSMContext):
    await state.update_data(last_name=message.text)

    try:

        departments = await fetch("SELECT department_id, department_name FROM departments")
        
        if not departments:
            await message.answer("Нет доступных отделений. Сначала создайте отделение.")
            await state.clear()
            return
            
        text = "Выберите ID отделения для врача:\n"
        for dep in departments:
            text += f"{dep['department_id']}: {dep['department_name']}\n"
        await message.answer(text)
        
        await state.set_state(AddDoctorStates.waiting_for_department_id)
        
    except Exception as e:
        await message.answer(f"Ошибка при получении списка отделений: {str(e)}")
        await state.clear()

@router.message(AddDoctorStates.waiting_for_department_id)
async def process_department(message: Message, state: FSMContext):
    await state.update_data(department_id=int(message.text))
    
    data = await state.get_data()
    query = """
    INSERT INTO doctors (first_name, last_name, department_id, employment_date, is_active)
    VALUES ($1, $2, $3, CURRENT_DATE, TRUE)
    """
    await execute(query, data['first_name'], data['last_name'], data['department_id'], execute=True)
    
    await message.answer(f"Доктор {data['first_name']} {data['last_name']} успешно оформлен.")
    await state.clear()

#! увольнение врача

@router.message(Command("dismiss_doctor"))
async def cmd_dismiss_doctor(message: Message, state: FSMContext):
    await message.answer("Вывод таблицы doctors:(да/нет)")
    await state.set_state(DismissDoctor.waiting_for_doctors_table)
    
@router.message(DismissDoctor.waiting_for_doctors_table)
async def print_table_patients(message: Message, state: FSMContext):
    
    try:
        doctors = await fetch("""
            SELECT doctor_id, first_name, last_name
            FROM doctors
        """)
            
        if not doctors:
            await message.answer("Врачь не найдены.")
        else:
            text = "🧾 Список врачей:\n"
            for p in doctors:
                text += (
                    f"🆔 {p['doctor_id']}\n"
                    f"👤 {p['first_name']} {p['last_name']}\n\n"
                )
            await message.answer(text)
            await message.answer("Введите ID врача для увольнения:")
            await state.set_state(DismissDoctor.waiting_for_id_doctor_dismiss)
            
    except Exception as e:
        await message.answer(f"Ошибка при выводе таблицы: {e}")

@router.message(DismissDoctor.waiting_for_id_doctor_dismiss)
async def process_dismiss_doctor(message: Message, state: FSMContext):

    try:
        doctor_id = int(message.text)
        
        # Получаем полную информацию о враче
        doctor = await fetchrow(
            "SELECT first_name, last_name, is_active FROM doctors WHERE doctor_id = $1",
            doctor_id
        )
        
        if not doctor:
            await message.answer("Врач с таким ID не найден!")
            await state.clear()
            return

        # Проверяем, не уволен ли врач уже
        if not doctor['is_active']:
            await message.answer(
                f"Врач {doctor['first_name']} {doctor['last_name']} уже уволен ранее!"
            )
            await state.clear()
            return

        # Проверяем, есть ли у врача активные пациенты
        active_patients_count = await fetchval(
            "SELECT COUNT(*) FROM patients WHERE doctor_id = $1 AND status = 'болен'",
            doctor_id
        )
        
        if active_patients_count > 0:
            # Сохраняем данные для перевода пациентов
            await state.update_data(doctor_id=doctor_id, active_patients_count=active_patients_count)
            
            # Запрашиваем ID нового врача
            await message.answer(
                f"У врача {doctor['first_name']} {doctor['last_name']} есть {active_patients_count} активных пациентов.\n"
                "Введите ID врача, к которому нужно перевести этих пациентов:"
            )
            await state.set_state(DismissDoctor.waiting_for_new_doctor)
        else:
            # Если активных пациентов нет, сразу увольняем врача
            await dismiss_doctor_and_notify(message, doctor_id, doctor)
            await state.clear()

    except ValueError:
        await message.answer("Ошибка: ID врача должен быть числом. Попробуйте снова:")

@router.message(DismissDoctor.waiting_for_new_doctor)
async def process_reassign_patients(message: Message, state: FSMContext):
    try:
        new_doctor_id = int(message.text)

        # Получаем данные из состояния
        data = await state.get_data()
        old_doctor_id = data['doctor_id']
        active_patients_count = data['active_patients_count']

        # Проверяем существование нового врача
        new_doctor = await fetchrow(
            "SELECT first_name, last_name, is_active FROM doctors WHERE doctor_id = $1 AND is_active = TRUE",
            new_doctor_id
        )

        if not new_doctor:
            # Проверяем, есть ли другие активные врачи в отделении
            department_id = await fetchval(
                "SELECT department_id FROM doctors WHERE doctor_id = $1",
                old_doctor_id
            )

            other_active_doctors = await fetch(
                "SELECT doctor_id FROM doctors WHERE department_id = $1 AND doctor_id != $2 AND is_active = TRUE",
                department_id, old_doctor_id
            )

            if not other_active_doctors:
                await message.answer(
                    "В отделении нет других активных врачей. Увольнение невозможно, пока у врача есть активные пациенты."
                )
                await state.clear()
                return

            await message.answer(
                "Новый врач не найден или он уже уволен! Введите корректный ID."
            )
            return

        # Переводим пациентов
        try:
            await execute(
                "UPDATE patients SET doctor_id = $1 WHERE doctor_id = $2 AND status = 'болен'",
                new_doctor_id, old_doctor_id
            )

            # Увольняем старого врача
            doctor = await fetchrow(
                "SELECT first_name, last_name FROM doctors WHERE doctor_id = $1",
                old_doctor_id
            )
            await dismiss_doctor_and_notify(message, old_doctor_id, doctor)

            await message.answer(
                f"✅ Все {active_patients_count} пациентов успешно переведены к врачу "
                f"{new_doctor['first_name']} {new_doctor['last_name']}.\n"
                f"Врач {doctor['first_name']} {doctor['last_name']} уволен."
            )
        except Exception as e:
            await message.answer(f"Ошибка при переводе пациентов: {str(e)}")
        finally:
            await state.clear()

    except ValueError:
        await message.answer("Ошибка: ID врача должен быть числом. Попробуйте снова:")

async def dismiss_doctor_and_notify(message: Message, doctor_id: int, doctor: dict):
    """Увольняет врача и уведомляет об этом."""
    try:
        await execute(
            "UPDATE doctors SET is_active = FALSE, dismissal_date = CURRENT_DATE WHERE doctor_id = $1",
            doctor_id
        )
        
        await message.answer(
            f"✅ Врач {doctor['first_name']} {doctor['last_name']} успешно уволен.\n"
            f"Дата увольнения: {datetime.now().strftime('%Y-%m-%d')}"
        )
    except Exception as e:
        await message.answer(
            f"Ошибка при увольнении врача: {str(e)}\n"
            "Попробуйте позже или обратитесь к администратору."
        )

#! обновление статуса

@router.message(Command("update_status"))
async def cmd_update_status(message: Message, state: FSMContext):
    await message.answer("Вывод таблицы patients:(да/нет)")
    await state.set_state(UpdateStatusStates.waiting_table_for_patients)
    
@router.message(UpdateStatusStates.waiting_table_for_patients)
async def print_table_patients(message: Message, state: FSMContext):
    try:
        patients = await fetch("""
            SELECT patient_id, first_name, last_name
            FROM patients
        """)
            
        if not patients:
            await message.answer("Пациенты не найдены.")
        else:
            text = "🧾 Список пациентов:\n"
            for p in patients:
                text += (
                    f"🆔 {p['patient_id']}\n"
                    f"👤 {p['first_name']} {p['last_name']}\n\n"
                )
            await message.answer(text)
            await message.answer("Введите ID пациента:")
            await state.set_state(UpdateStatusStates.waiting_for_patient_id)
            
    except Exception as e:
        await message.answer(f"Ошибка при выводе таблицы: {e}")
        

@router.message(UpdateStatusStates.waiting_for_patient_id)
async def process_patient_id(message: Message, state: FSMContext):
    
    try:
        patient_id = int(message.text)
        patient = await fetchrow("SELECT * FROM patients WHERE patient_id = $1", patient_id)
        if not patient:
            await message.answer("Пациент не найден!")
            return

        await state.update_data(patient_id=patient_id)
        await message.answer("Введите статус (болен/здоров/умер/еще болен):")
        await state.set_state(UpdateStatusStates.waiting_for_status)

    except ValueError:
        await message.answer("Введите корректный ID пациента!")
        await state.clear()

@router.message(UpdateStatusStates.waiting_for_status)
async def process_status(message: Message, state: FSMContext):
    new_status = message.text.lower()
    if new_status not in ("болен", "здоров", "умер", "еще болен"): 
        await message.answer("Неверный статус. Допустимые значения: болен, здоров, умер, еще болен")
        return

    data = await state.get_data()
    patient_id = data['patient_id']

    await execute("""
        UPDATE patients SET status = $1 WHERE patient_id = $2
    """, new_status, patient_id, execute=True)

    await execute("""
        INSERT INTO patient_status_history (patient_id, date, status)
        VALUES ($1, CURRENT_DATE, $2)
    """, patient_id, new_status, execute=True)

    if new_status == "здоров":
        await message.answer("Болен ли пациент чем-то ещё? (да/нет)")
        await state.set_state(UpdateStatusStates.asking_if_still_sick)
        return

    elif new_status == "умер":
        await execute("""
            UPDATE patients SET discharge_date = CURRENT_DATE
            WHERE patient_id = $1
        """, patient_id, execute=True)

        await execute("""
            UPDATE departments SET bed_count_free = bed_count_free + 1
            WHERE department_id = (
                SELECT department_id FROM patients WHERE patient_id = $1
            )
        """, patient_id, execute=True)

        await message.answer(f"Пациент {patient_id} выписан со статусом 'умер'")
        
    
    elif new_status == "еще болен":
        await message.answer("Введите дополнительный диагноз пациента:")
        await state.set_state(UpdateStatusStates.waiting_for_next_diagnosis)
        return

    elif new_status == "болен":
        await message.answer("Введите диагноз пациента:")
        await state.set_state(UpdateStatusStates.waiting_for_new_diagnosis)
        return

    await state.clear()

@router.message(UpdateStatusStates.waiting_for_next_diagnosis)
async def next_diagnosis(message: Message, state: FSMContext):
    additional_diagnosis = message.text.strip().lower()
    data = await state.get_data()
    patient_id = data['patient_id']
    
    try:
        patient = await fetchrow("""
        SELECT * FROM patients 
        WHERE patient_id = $1
        """, patient_id)
        
        if not patient:
            await message.answer("Пациент не найден!")
            await state.clear()
            return
        
        # Проверяем существование диагноза в базе
        existing_diagnosis = await fetchrow("""
            SELECT diagnosis_id FROM diagnoses 
            WHERE LOWER(diagnosis_name) = $1 AND department_id = $2
        """, additional_diagnosis, patient['department_id'])
        
        if existing_diagnosis:
            diagnosis_id = existing_diagnosis['diagnosis_id']
        else:
            # Добавляем новый диагноз в базу
            await execute("""
                INSERT INTO diagnoses (diagnosis_name, department_id)
                VALUES ($1, $2)
            """, additional_diagnosis, patient['department_id'], execute=True)
            
            # Получаем ID нового диагноза
            new_diagnosis = await fetchrow("""
                SELECT diagnosis_id FROM diagnoses 
                WHERE LOWER(diagnosis_name) = $1 AND department_id = $2
            """, additional_diagnosis, patient['department_id'])
            diagnosis_id = new_diagnosis['diagnosis_id']
        
        # Добавляем связь пациента с новым диагнозом
        await execute("""
            INSERT INTO patient_treatments 
            (patient_id, diagnosis_id, treatment_date, doctor_id)
            VALUES ($1, $2, CURRENT_DATE, $3)
        """, patient_id, diagnosis_id, patient['doctor_id'], execute=True)
        
        # Получаем список всех диагнозов пациента для отчета
        patient_diagnoses = await fetch("""
            SELECT d.diagnosis_name 
            FROM patient_treatments pt
            JOIN diagnoses d ON pt.diagnosis_id = d.diagnosis_id
            WHERE pt.patient_id = $1
            ORDER BY pt.treatment_date
        """, patient_id)
        
        diagnoses_list = [d['diagnosis_name'] for d in patient_diagnoses]
        
        await message.answer(
            f"✅ Дополнительный диагноз успешно добавлен.\n"
            f"Текущие диагнозы пациента:\n"
            f"{', '.join(diagnoses_list)}"
        )
        
    except Exception as e:
        await message.answer(f"⚠️ Произошла ошибка при добавлении диагноза: {str(e)}")
    
    await state.clear()


@router.message(UpdateStatusStates.asking_if_still_sick)
async def process_still_sick_answer(message: Message, state: FSMContext):
    answer = message.text.strip().lower()
    data = await state.get_data()
    patient_id = data['patient_id']

    if answer == "нет":
        await execute("""
            UPDATE patients SET discharge_date = CURRENT_DATE
            WHERE patient_id = $1
        """, patient_id, execute=True)

        await execute("""
            UPDATE departments SET bed_count_free = bed_count_free + 1
            WHERE department_id = (
                SELECT department_id FROM patients WHERE patient_id = $1
            )
        """, patient_id, execute=True)

        await message.answer(f"Пациент {patient_id} выписан со статусом 'здоров'")
        await state.clear()

    elif answer == "да":
        await message.answer("Укажите диагноз пациента:")
        await state.set_state(UpdateStatusStates.waiting_for_new_diagnosis)
    else:
        await message.answer("Ответ должен быть 'да' или 'нет'. Пожалуйста, повторите.")

@router.message(UpdateStatusStates.waiting_for_new_diagnosis)
async def process_new_diagnosis(message: Message, state: FSMContext):
    diagnosis_name = message.text.strip().lower()
    data = await state.get_data()
    patient_id = data['patient_id']

    admission_diagnosis = await fetchval("""
        SELECT d.diagnosis_name FROM patient_treatments pt
        JOIN diagnoses d ON pt.diagnosis_id = d.diagnosis_id
        WHERE pt.patient_id = $1
        ORDER BY pt.treatment_date ASC
        LIMIT 1
    """, patient_id)

    existing = await fetch("SELECT diagnosis_id FROM diagnoses WHERE LOWER(diagnosis_name) = $1", diagnosis_name)
    if existing:
        diagnosis_id = existing[0]['diagnosis_id']
    else:
        await execute("INSERT INTO diagnoses (diagnosis_name) VALUES ($1)", diagnosis_name, execute=True)
        new_diagnosis = await fetch("SELECT diagnosis_id FROM diagnoses WHERE LOWER(diagnosis_name) = $1", diagnosis_name)
        diagnosis_id = new_diagnosis[0]['diagnosis_id']

    await execute("""
        INSERT INTO patient_treatments (patient_id, diagnosis_id, treatment_date)
        VALUES ($1, $2, CURRENT_DATE)
    """, patient_id, diagnosis_id, execute=True)

    if diagnosis_name != admission_diagnosis:
        departments = await fetch("SELECT department_id, department_name FROM departments")
        text = "Диагноз изменился. Выберите новое отделение:\n"
        for dep in departments:
            text += f"{dep['department_id']}: {dep['department_name']}\n"

        await state.update_data(new_diagnosis_id=diagnosis_id)
        await message.answer(text)
        await state.set_state(UpdateStatusStates.waiting_for_new_department)
        await state.clear()
        
@router.message(UpdateStatusStates.waiting_for_new_department)
async def process_new_department(message: Message, state: FSMContext):
    try:
        department_id = int(message.text)
        data = await state.get_data()
        patient_id = data['patient_id']

        department_exists = await fetchval("SELECT 1 FROM departments WHERE department_id = $1", department_id)
        if not department_exists:
            await message.answer("Отделение с таким ID не существует!")
            await state.clear()
            return

        await execute("""
            UPDATE patients SET department_id = $1
            WHERE patient_id = $2
        """, department_id, patient_id, execute=True)

        await execute("""
            UPDATE departments 
            SET bed_count_free = bed_count_free + 1
            WHERE department_id = (
                SELECT department_id FROM patients WHERE patient_id = $1
            )
        """, patient_id, execute=True)

        await execute("""
            UPDATE departments
            SET bed_count_free = bed_count_free - 1
            WHERE department_id = $1
        """, department_id, execute=True)

        department_name = await fetchval("SELECT department_name FROM departments WHERE department_id = $1", department_id)
        await message.answer(f"Пациент успешно переведен в отделение: {department_name}")
        await state.set_state(UpdateStatusStates.waiting_for_new_doctor)

    except ValueError:
        await message.answer("Пожалуйста, введите числовой ID отделения!")
        
@router.message(UpdateStatusStates.waiting_for_new_doctor)
async def process_doctor_selection(message: Message, state: FSMContext):
    try:
        doctor_id = int(message.text)
        data = await state.get_data()
        department_id = data['new_department_id']
        patient_id = data['patient_id']
        diagnosis_id = data['new_diagnosis_id']

        # Проверяем, есть ли врач с таким ID в нужном отделении
        doctor_exists = await fetchval("""
            SELECT 1 FROM doctors 
            WHERE doctor_id = $1 AND department_id = $2
        """, doctor_id, department_id)

        if not doctor_exists:
            await message.answer("Врач не найден в выбранном отделении. Повторите выбор.")
            return

        # Записываем связь пациента и врача (зависит от структуры БД)
        await execute("""
            UPDATE patient_treatments 
            SET doctor_id = $1
            WHERE patient_id = $2 AND diagnosis_id = $3
        """, doctor_id, patient_id, diagnosis_id, execute=True)

        doctor_name = await fetchval("""
            SELECT first_name || ' ' || last_name FROM doctors WHERE doctor_id = $1
        """, doctor_id)

        await message.answer(f"Вторая болезнь успешно добавлена. Назначен врач: {doctor_name}")
        await state.clear()

    except ValueError:
        await message.answer("Введите корректный числовой ID врача.")

#! назначение лечения

@router.message(Command("assign_treatment"))
async def cmd_assign_treatment(message: Message, state: FSMContext):
    await message.answer("Вывод таблицы patients:(да/нет)")
    await state.set_state(TreatmentStates.waiting_table_patients)
    
@router.message(TreatmentStates.waiting_table_patients)
async def print_table_patients(message: Message, state: FSMContext):
    try:
        patients = await fetch("""
            SELECT patient_id, first_name, last_name
            FROM patients
        """)
            
        if not patients:
            await message.answer("Пациенты не найдены.")
        else:
            text = "🧾 Список пациентов:\n"
            for p in patients:
                text += (
                    f"🆔 {p['patient_id']}\n"
                    f"👤 {p['first_name']} {p['last_name']}\n\n"
                )
            await message.answer(text)
            await message.answer("Введите ID пациента:")
            await state.set_state(TreatmentStates.waiting_for_patient_id)
            
    except Exception as e:
        await message.answer(f"Ошибка при выводе таблицы: {e}")


@router.message(TreatmentStates.waiting_for_patient_id)
async def process_patient_for_treatment(message: Message, state: FSMContext):

    try:
        patient_id = int(message.text)
        # Проверяем существование пациента
        patient = await fetchrow("SELECT * FROM patients WHERE patient_id = $1", patient_id)
        if not patient:
            await message.answer("Введите существующий id: ")
            return
            
        await state.update_data(patient_id=patient_id)
        
        await message.answer("Введите таблицу диагнозов(да/нет):")
        await state.set_state(TreatmentStates.waiting_for_diagnosis_table)
        
    except ValueError:
        await message.answer("Введите корректный ID пациента!")
        
@router.message(TreatmentStates.waiting_for_diagnosis_table)
async def print_table_diagmosis(message: Message, state: FSMContext):
    try:
        diagnosis = await fetch("""
        SELECT diagnosis_id, diagnosis_name FROM  diagnoses
        """)
        
        if not diagnosis:
            await message.answer("Диагноза не найдено")
        else:
            text = "Список диагнозов:\n"
            for i in diagnosis:
                text += (
                    f"🆔 {i['diagnosis_id']}\n"
                    f" {i['diagnosis_name']}\n"
                )
            await message.answer(text)
            await message.answer("Введите ID диагноза")
            await state.set_state(TreatmentStates.waiting_for_diagnosis_id)
    except Exception as e:
        await message.answer(f"Ошибка при выводе таблицы {e}")

@router.message(TreatmentStates.waiting_for_diagnosis_id)
async def process_diagnosis_for_treatment(message: Message, state: FSMContext):
    try:
        diagnosis_id = int(message.text)
        await state.update_data(diagnosis_id=diagnosis_id)
        await message.answer("Вывести таблицу лекарств(да/нет):")
        await state.set_state(TreatmentStates.waiting_for_table_medicine)
    except ValueError:
        await message.answer("Введите корректный ID диагноза!")

@router.message(TreatmentStates.waiting_for_table_medicine)
async def print_medicine_table(message: Message, state: FSMContext):
    try:
        medications = await fetch("""
            SELECT medication_id, medication_name
            FROM medications
        """)
            
        if not medications:
            await message.answer("Лекарство не найдено")
        else:
            text = "🧾 Список лекарств:\n"
            for p in medications:
                text += (
                    f"🆔 {p['medication_id']}\n"
                    f" {p['medication_name']}\n"
                )
            await message.answer(text)
            await message.answer("Введите ID лекарства(например 1,2,3):")
            await state.set_state(TreatmentStates.waiting_for_medications)
    except Exception as e:
        await message.answer(f"Ошибка при выводе таблицы: {e}")

        
@router.message(TreatmentStates.waiting_for_medications)
async def process_medications(message: Message, state: FSMContext):
    data = await state.get_data()
    patient_id = data['patient_id']
    
    try:
        # Сохраняем список ID лекарств
        med_ids = [int(m.strip()) for m in message.text.split(",")]
        await state.update_data(med_ids=med_ids, current_med_index=0)
        
        # Запрашиваем дозу для первого лекарства
        med_name = await fetchval(
            "SELECT medication_name FROM medications WHERE medication_id = $1", 
            med_ids[0]
        )
        max_dose = await fetchval(
            "SELECT max_daily_dose FROM medication_dosage WHERE medication_id = $1",
            med_ids[0]
        )
        
        await message.answer(
            f"Введите дозу для {med_name} (максимальная суточная доза: {max_dose} мг):"
        )
        await state.set_state(TreatmentStates.waiting_for_dosage)
        
    except ValueError:
        await message.answer("Введите корректные ID лекарств!")
        await state.clear()

@router.message(TreatmentStates.waiting_for_dosage)
async def process_dosage(message: Message, state: FSMContext):
    data = await state.get_data()
    patient_id = data['patient_id']
    med_ids = data['med_ids']
    current_index = data['current_med_index']
    med_id = med_ids[current_index]
    
    try:
        dose = int(message.text)
        
        # Проверяем максимальную дозу
        max_dose = await fetchval(
            "SELECT max_daily_dose FROM medication_dosage WHERE medication_id = $1",
            med_id
        )
        
        if dose > max_dose:
            med_name = await fetchval(
                "SELECT medication_name FROM medications WHERE medication_id = $1",
                med_id
            )
            await message.answer(
                f"Ошибка: доза {dose} мг превышает максимальную суточную дозу ({max_dose} мг) для {med_name}!\n"
                "Пожалуйста, введите корректную дозу:"
            )
            return
            
        # Проверяем общую дозу за сегодня
        total_dose = await fetchval("""
            SELECT SUM(dose) FROM patient_treatments
            WHERE patient_id = $1 AND medication_id = $2
            AND treatment_date = CURRENT_DATE
        """, patient_id, med_id) or 0
        
        if (total_dose + dose) > max_dose:
            med_name = await fetchval(
                "SELECT medication_name FROM medications WHERE medication_id = $1",
                med_id
            )
            await message.answer(
                f"Ошибка: общая доза за сегодня ({total_dose + dose} мг) превысит максимальную ({max_dose} мг) для {med_name}!\n"
                f"Уже назначено: {total_dose} мг\n"
                "Пожалуйста, введите меньшую дозу:"
            )
            return
            
        # Сохраняем дозу для текущего лекарства
        if 'med_doses' not in data:
            data['med_doses'] = []
        data['med_doses'].append(dose)
        await state.update_data(med_doses=data['med_doses'])
        
        # Если есть еще лекарства - запрашиваем дозу для следующего
        if current_index + 1 < len(med_ids):
            next_med_id = med_ids[current_index + 1]
            med_name = await fetchval(
                "SELECT medication_name FROM medications WHERE medication_id = $1",
                next_med_id
            )
            max_dose = await fetchval(
                "SELECT max_daily_dose FROM medication_dosage WHERE medication_id = $1",
                next_med_id
            )
            
            await state.update_data(current_med_index=current_index + 1)
            await message.answer(
                f"Введите дозу для {med_name} (максимальная суточная доза: {max_dose} мг):"
            )
        else:
            # Все дозы получены - назначаем лечение
            for i, med_id in enumerate(med_ids):
                await execute("""
                    INSERT INTO patient_treatments
                    (patient_id, diagnosis_id, medication_id, treatment_date, dose)
                    VALUES ($1, $2, $3, CURRENT_DATE, $4)
                """, patient_id, data['diagnosis_id'], med_id, data['med_doses'][i], execute=True)
            
            await message.answer("✅ Лечение успешно назначено!")
            await state.clear()
            
    except ValueError:
        await message.answer("Пожалуйста, введите числовое значение дозы:")
        await state.clear()


@router.message(Command("show_table"))
async def cmd_show_table(message: Message, state: FSMContext):
    await message.answer("""Выберите таблицу для отображения: 
    (patients, doctors, departments, diagnoses, patient_treatments, patient_status_history, medications, medication_dosage)""")
    await state.set_state(ShowTableStates.waiting_for_table_name)

@router.message(ShowTableStates.waiting_for_table_name)
async def process_table_name(message: Message, state: FSMContext):
    table_name = message.text.lower()
    allowed_tables = {
        "patients", "doctors", "departments", "diagnoses",
        "patient_treatments", "patient_status_history", "medications", "medication_dosage"
    }

    if table_name not in allowed_tables:
        await message.answer("Некорректное имя таблицы. Попробуйте снова.")
        return

    try:
        rows = await fetch(f"SELECT * FROM {table_name}")
        if not rows:
            await message.answer("Таблица пуста.")
        else:
            preview = ""
            for row in rows:  # Показываем только первые 10 строк
                preview += ", ".join(f"{k}: {v}" for k, v in row.items()) + "\n\n"
            await message.answer(f"Содержимое таблицы '{table_name}':\n\n{preview}")
    except Exception as e:
        await message.answer(f"Ошибка при получении данных: {e}")

    await state.clear()

#! отчет по умершим пациентам у врачей

@router.message(Command("report_dead_patients"))
async def report_dead_patients(message: Message):
    rows = await fetch("""
        SELECT d.doctor_id, d.first_name, d.last_name, COUNT(p.patient_id) AS dead_count
        FROM doctors d
        JOIN patients p ON p.doctor_id = d.doctor_id
        WHERE p.status = 'умер'
        GROUP BY d.doctor_id, d.first_name, d.last_name
        ORDER BY dead_count DESC
    """)
    if not rows:
        await message.answer("Нет данных о смертности пациентов.")
        return

    text = "👨‍⚕️ Врачи, пациенты которых умирали:\n\n"
    for row in rows:
        text += f"{row['first_name']} {row['last_name']} — {row['dead_count']} умерших\n"
    await message.answer(text)


@router.message(Command("report_best_doctors"))
async def report_best_doctors(message: Message):
    rows = await fetch("""
        SELECT d.department_id, dep.department_name, d.first_name, d.last_name, 
               COUNT(CASE WHEN p.status = 'умер' THEN 1 END) AS dead_count
        FROM doctors d
        LEFT JOIN patients p ON d.doctor_id = p.doctor_id
        JOIN departments dep ON d.department_id = dep.department_id
        GROUP BY d.doctor_id, d.first_name, d.last_name, d.department_id, dep.department_name
        ORDER BY d.department_id, dead_count ASC
    """)
    if not rows:
        await message.answer("Нет данных для отчёта по врачам.")
        return

    text = "🏆 Лучшие врачи по отделениям:\n\n"
    current_dep = None
    for row in rows:
        if current_dep != row['department_id']:
            current_dep = row['department_id']
            text += f"\n📍 Отделение: {row['department_name']}\n"
        text += f"{row['first_name']} {row['last_name']} — смертей: {row['dead_count']}\n"
    await message.answer(text)


#! болезни часто


@router.message(Command("report_disease_frequency"))
async def report_disease_start(message: Message, state: FSMContext):
    await message.answer("Введите начальную дату (ГГГГ-ММ-ДД):")
    await state.set_state(ReportStates.waiting_for_start_date)

@router.message(ReportStates.waiting_for_start_date)
async def report_disease_get_start(message: Message, state: FSMContext):
    try:
        start_date = datetime.strptime(message.text, '%Y-%m-%d').date()
        await state.update_data(start_date=start_date)
        await message.answer("Введите конечную дату (ГГГГ-ММ-ДД):")
        await state.set_state(ReportStates.waiting_for_end_date)
    except ValueError:
        await message.answer("Неверный формат даты. Введите дату в формате ГГГГ-ММ-ДД:")
        return

@router.message(ReportStates.waiting_for_end_date)
async def report_disease_get_end(message: Message, state: FSMContext):
    try:
        end_date = datetime.strptime(message.text, '%Y-%m-%d').date()
        data = await state.get_data()
        start_date = data['start_date']
        
        # Получаем общее количество диагнозов за период
        total = await fetchval("""
            SELECT COUNT(*) 
            FROM patient_treatments 
            WHERE treatment_date BETWEEN $1 AND $2
        """, start_date, end_date) or 1  # Чтобы избежать деления на 0
        
        # Получаем диагнозы с количеством и процентом
        rows = await fetch("""
            SELECT 
                d.diagnosis_name, 
                COUNT(*) as frequency,
                ROUND(COUNT(*) * 100.0 / $3, 2) as percentage
            FROM patient_treatments pt
            JOIN diagnoses d ON pt.diagnosis_id = d.diagnosis_id
            WHERE pt.treatment_date BETWEEN $1 AND $2
            GROUP BY d.diagnosis_name
            ORDER BY frequency DESC
        """, start_date, end_date, total)

        if not rows:
            await message.answer(f"За период с {start_date} по {end_date} диагнозы не найдены.")
        else:
            text = f"📊 Частота диагнозов с {start_date} по {end_date} (всего {total} случаев):\n\n"
            for row in rows:
                text += (
                    f"{row['diagnosis_name']}: "
                    f"{row['frequency']} случаев "
                    f"({row['percentage']}%)\n"
                )
            await message.answer(text)
    except ValueError:
        await message.answer("Неверный формат даты. Введите дату в формате ГГГГ-ММ-ДД:")
    finally:
        await state.clear()


@router.message(Command("report_hospital_history"))
async def cmd_hospital_history(message: Message, state: FSMContext):
    await message.answer(
        "Выберите период для отчета по истории больницы:\n"
        "1 - За последний год\n"
        "2 - За весь период работы\n"
        "3 - За произвольный период"
    )
    await state.set_state(ReportStates.waiting_for_history_period)

@router.message(ReportStates.waiting_for_history_period)
async def process_history_period(message: Message, state: FSMContext):
    choice = message.text.strip()
    if choice == "1":  # За последний год
        end_date = datetime.now().date()
        start_date = datetime(end_date.year - 1, end_date.month, end_date.day).date()
        await generate_hospital_history(message, start_date, end_date)
        await state.clear()
    elif choice == "2":  # За весь период
        start_date = await fetchval("SELECT MIN(admission_date) FROM patients") or datetime.now().date()
        end_date = datetime.now().date()
        await generate_hospital_history(message, start_date, end_date)
        await state.clear()
    elif choice == "3":  # За произвольный период
        await message.answer("Введите начальную дату (ГГГГ-ММ-ДД):")
        await state.set_state(ReportStates.waiting_for_history_start_date)
    else:
        await message.answer("Неверный выбор. Пожалуйста, введите 1, 2 или 3.")

@router.message(ReportStates.waiting_for_history_start_date)
async def process_history_start_date(message: Message, state: FSMContext):
    try:
        start_date = datetime.strptime(message.text, '%Y-%m-%d').date()
        await state.update_data(start_date=start_date)
        await message.answer("Введите конечную дату (ГГГГ-ММ-ДД):")
        await state.set_state(ReportStates.waiting_for_history_end_date)
    except ValueError:
        await message.answer("Неверный формат даты. Введите дату в формате ГГГГ-ММ-ДД:")

@router.message(ReportStates.waiting_for_history_end_date)
async def process_history_end_date(message: Message, state: FSMContext):
    try:
        end_date = datetime.strptime(message.text, '%Y-%m-%d').date()
        data = await state.get_data()
        start_date = data['start_date']
        
        if start_date > end_date:
            await message.answer("Начальная дата не может быть позже конечной. Попробуйте снова.")
            return
            
        await generate_hospital_history(message, start_date, end_date)
    except ValueError:
        await message.answer("Неверный формат даты. Введите дату в формате ГГГГ-ММ-ДД:")
    finally:
        await state.clear()

async def generate_hospital_history(message: Message, start_date: date, end_date: date):
    """Генерирует отчет по истории больницы за указанный период."""
    try:
        # Получаем статистику по пациентам
        patients_stats = await fetchrow("""
            SELECT 
                COUNT(*) AS total_patients,
                COUNT(CASE WHEN status = 'здоров' THEN 1 END) AS cured,
                COUNT(CASE WHEN status = 'умер' THEN 1 END) AS died,
                COUNT(CASE WHEN status = 'болен' THEN 1 END) AS still_sick
            FROM patients
            WHERE admission_date BETWEEN $1 AND $2
        """, start_date, end_date)

        # Получаем статистику по врачам
        doctors_stats = await fetchrow("""
            SELECT 
                COUNT(*) AS total_doctors,
                COUNT(CASE WHEN is_active THEN 1 END) AS active,
                COUNT(CASE WHEN NOT is_active THEN 1 END) AS dismissed
            FROM doctors
            WHERE employment_date BETWEEN $1 AND $2
               OR (dismissal_date BETWEEN $1 AND $2)
        """, start_date, end_date)

        # Получаем самые частые диагнозы
        common_diagnoses = await fetch("""
            SELECT d.diagnosis_name, COUNT(*) as frequency
            FROM patient_treatments pt
            JOIN diagnoses d ON pt.diagnosis_id = d.diagnosis_id
            WHERE pt.treatment_date BETWEEN $1 AND $2
            GROUP BY d.diagnosis_name
            ORDER BY frequency DESC
            LIMIT 5
        """, start_date, end_date)

        # Получаем статистику по отделениям
        departments_stats = await fetch("""
            SELECT department_name, 
                   COUNT(p.patient_id) AS patients_count,
                   COUNT(CASE WHEN p.status = 'здоров' THEN 1 END) AS cured,
                   COUNT(CASE WHEN p.status = 'умер' THEN 1 END) AS died
            FROM departments d
            LEFT JOIN patients p ON d.department_id = p.department_id
                                  AND p.admission_date BETWEEN $1 AND $2
            GROUP BY d.department_name
            ORDER BY patients_count DESC
        """, start_date, end_date)

        # Формируем отчет
        report = (
            f"📜 История больницы за период с {start_date} по {end_date}\n\n"
            f"👥 Пациенты:\n"
            f"- Всего пациентов: {patients_stats['total_patients']}\n"
            f"- Вылечено: {patients_stats['cured']}\n"
            f"- Умерло: {patients_stats['died']}\n"
            f"- На лечении: {patients_stats['still_sick']}\n\n"
            
            f"👨‍⚕️ Врачи:\n"
            f"- Всего врачей: {doctors_stats['total_doctors']}\n"
            f"- Активных: {doctors_stats['active']}\n"
            f"- Уволено: {doctors_stats['dismissed']}\n\n"
            
            f"🏥 Отделения и пациенты:\n"
        )
        
        for dep in departments_stats:
            report += (
                f"- {dep['department_name']}: "
                f"всего {dep['patients_count']}, "
                f"вылечено {dep['cured']}, "
                f"умерло {dep['died']}\n"
            )
            
        report += "\n🏆 Топ-5 диагнозов:\n"
        for i, diag in enumerate(common_diagnoses, 1):
            report += f"{i}. {diag['diagnosis_name']} - {diag['frequency']} случаев\n"

        await message.answer(report)
        
    except Exception as e:
        await message.answer(f"Произошла ошибка при формировании отчета: {str(e)}")
