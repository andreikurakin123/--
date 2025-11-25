from aiogram.fsm.state import StatesGroup, State

class AddPatientStates(StatesGroup): #добавление пациента
    waiting_for_first_name = State()
    waiting_for_last_name = State()
    waiting_for_department_id = State()
    waiting_for_diagnosis = State()
    waiting_for_doctor_id = State()


class AddDoctorStates(StatesGroup): #добавление доктора
    waiting_for_first_name = State()
    waiting_for_last_name = State()
    waiting_for_department_id = State()
    waiting_for_doctor_to_dismiss = State()


class UpdateStatusStates(StatesGroup):
    waiting_for_patient_id = State()
    waiting_for_status = State()
    waiting_for_new_diagnosis = State()  
    waiting_for_new_department = State()  
    waiting_for_next_diagnosis = State()
    asking_if_still_sick = State() 
    waiting_table_for_patients = State()
    waiting_for_new_diagnosis = State()
    waiting_for_new_doctor = State()

class TreatmentStates(StatesGroup):
    waiting_for_patient_id = State()
    waiting_for_diagnosis_id = State()
    waiting_for_medications = State()
    waiting_for_dosage = State()
    waiting_for_procedures = State()
    waiting_table_patients = State()
    waiting_for_diagnosis_table = State()
    waiting_for_table_medicine = State()

class ShowTableStates(StatesGroup):
    waiting_for_table_name = State()

class ReportStates(StatesGroup):
    waiting_for_start_date = State()
    waiting_for_end_date = State()
    waiting_for_history_period = State()
    waiting_for_history_start_date = State()
    waiting_for_history_end_date = State()

class DismissDoctor(StatesGroup):
    waiting_for_id_doctor_dismiss = State()
    waiting_for_new_doctor = State()
    waiting_for_doctors_table = State()

class StandardOperationsStates(StatesGroup):
    waiting_for_find_pk = State()
    waiting_for_find_non_pk = State()
    waiting_for_find_mask = State()
    waiting_for_insert_single = State()
    waiting_for_insert_multiple = State()
    waiting_for_update_pk = State()
    waiting_for_update_non_pk = State()
    waiting_for_delete_pk = State()
    waiting_for_delete_non_pk = State()
    waiting_for_delete_multiple = State()