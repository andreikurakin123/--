import asyncio
import asyncpg
import time
import random
from datetime import datetime
import config

# Настройки подключения к базе данных
DB_HOST = '127.0.0.1'
DB_USER = 'postgres'
DB_PASSWORD = '90338410Pp'
DB_NAME = 'postgres'

# Настройки для тестирования
TEST_TABLE_NAME = 'test_patients'
TEST_SIZES = [1000, 10000, 100000]

async def create_test_table(conn):
    """Создает тестовую таблицу."""
    await conn.execute(f"""
        CREATE TABLE IF NOT EXISTS {TEST_TABLE_NAME} (
            patient_id SERIAL PRIMARY KEY,
            first_name VARCHAR(50),
            last_name VARCHAR(50),
            admission_date DATE,
            status VARCHAR(20),
            is_ambulatory BOOLEAN,
            department_id INTEGER,
            doctor_id INTEGER
        );
    """)

async def clear_test_table(conn):
    """Очищает тестовую таблицу."""
    await conn.execute(f"TRUNCATE TABLE {TEST_TABLE_NAME} RESTART IDENTITY;")

async def insert_records(conn, count):
    """Добавляет заданное количество записей."""
    print(f"Добавляем {count} записей...")
    start_time = time.time()
    
    records = []
    for i in range(count):
        records.append((
            f"Имя_{i}",
            f"Фамилия_{i}",
            datetime.now().date(),
            random.choice(['болен', 'здоров', 'умер']),
            random.choice([True, False]),
            random.randint(1, 10),
            random.randint(1, 5)
        ))
    
    await conn.copy_records_to_table(
        TEST_TABLE_NAME,
        records=records,
        columns=('first_name', 'last_name', 'admission_date', 'status', 'is_ambulatory', 'department_id', 'doctor_id')
    )
    
    end_time = time.time()
    return end_time - start_time

async def measure_operation(conn, op_name, operation):
    """Измеряет время выполнения операции."""
    start_time = time.time()
    await operation(conn)
    end_time = time.time()
    return op_name, end_time - start_time

async def run_tests():
    pool = await asyncpg.create_pool(
        host=DB_HOST,
        user=DB_USER,
        password=DB_PASSWORD,
        database=DB_NAME
    )

    with open("performance_report.txt", "w") as f:
        f.write("Отчет о производительности операций с базой данных\n\n")

        async with pool.acquire() as conn:
            await create_test_table(conn)

            for size in TEST_SIZES:
                await clear_test_table(conn)
                insert_time = await insert_records(conn, size)
                f.write(f"--- Таблица с {size} записями ---\n")
                f.write(f"Время заполнения: {insert_time:.6f} сек\n")

                # 1. Поиск записи по ключевому полю
                patient_id_to_find = random.randint(1, size)
                op_name, op_time = await measure_operation(
                    conn,
                    "Поиск по ключу",
                    lambda c: c.fetchrow(f"SELECT * FROM {TEST_TABLE_NAME} WHERE patient_id = $1", patient_id_to_find)
                )
                f.write(f"{op_name}: {op_time:.6f} сек\n")

                # 2. Поиск записи по неключевому полю
                op_name, op_time = await measure_operation(
                    conn,
                    "Поиск по неключевому полю (last_name)",
                    lambda c: c.fetch(f"SELECT * FROM {TEST_TABLE_NAME} WHERE last_name = 'Фамилия_10'")
                )
                f.write(f"{op_name}: {op_time:.6f} сек\n")

                # 3. Поиск записи по маске
                op_name, op_time = await measure_operation(
                    conn,
                    "Поиск по маске (first_name LIKE)",
                    lambda c: c.fetch(f"SELECT * FROM {TEST_TABLE_NAME} WHERE first_name LIKE '%_1%'")
                )
                f.write(f"{op_name}: {op_time:.6f} сек\n")

                # 4. Добавление записи
                op_name, op_time = await measure_operation(
                    conn,
                    "Добавление 1 записи",
                    lambda c: c.execute(f"INSERT INTO {TEST_TABLE_NAME} (first_name, last_name, status) VALUES ('Новый', 'Пациент', 'болен')")
                )
                f.write(f"{op_name}: {op_time:.6f} сек\n")

                # 5. Добавление группы записей (100 записей)
                op_name, op_time = await measure_operation(
                    conn,
                    "Добавление 100 записей",
                    lambda c: c.executemany(
                        f"INSERT INTO {TEST_TABLE_NAME} (first_name, last_name, status) VALUES ($1, $2, $3)",
                        [("Группа_1", "Пациент", "болен")] * 100
                    )
                )
                f.write(f"{op_name}: {op_time:.6f} сек\n")
                
                # 6. Изменение записи по ключевому полю
                patient_id_to_update = random.randint(1, size)
                op_name, op_time = await measure_operation(
                    conn,
                    "Изменение по ключу",
                    lambda c: c.execute(f"UPDATE {TEST_TABLE_NAME} SET status = 'здоров' WHERE patient_id = $1", patient_id_to_update)
                )
                f.write(f"{op_name}: {op_time:.6f} сек\n")

                # 7. Изменение записи по неключевому полю
                op_name, op_time = await measure_operation(
                    conn,
                    "Изменение по неключевому полю",
                    lambda c: c.execute(f"UPDATE {TEST_TABLE_NAME} SET status = 'умер' WHERE first_name = 'Имя_10'")
                )
                f.write(f"{op_name}: {op_time:.6f} сек\n")

                # 8. Удаление записи по ключевому полю
                patient_id_to_delete = random.randint(1, size)
                op_name, op_time = await measure_operation(
                    conn,
                    "Удаление по ключу",
                    lambda c: c.execute(f"DELETE FROM {TEST_TABLE_NAME} WHERE patient_id = $1", patient_id_to_delete)
                )
                f.write(f"{op_name}: {op_time:.6f} сек\n")

                # 9. Удаление записи по неключевому полю
                op_name, op_time = await measure_operation(
                    conn,
                    "Удаление по неключевому полю",
                    lambda c: c.execute(f"DELETE FROM {TEST_TABLE_NAME} WHERE first_name = 'Имя_100'")
                )
                f.write(f"{op_name}: {op_time:.6f} сек\n")

                # 10. Удаление группы записей
                delete_count = 100
                await conn.execute(f"DELETE FROM {TEST_TABLE_NAME} WHERE patient_id > {size - delete_count}")
                op_name, op_time = await measure_operation(
                    conn,
                    "Удаление группы записей",
                    lambda c: c.execute(f"DELETE FROM {TEST_TABLE_NAME} WHERE patient_id > {size - 2*delete_count}")
                )
                f.write(f"{op_name}: {op_time:.6f} сек\n")
                
                # 11. Сжатие после удаления 200 строк
                delete_count_200 = 200
                await conn.execute(f"DELETE FROM {TEST_TABLE_NAME} WHERE patient_id > {size - delete_count_200}")
                op_name, op_time = await measure_operation(
                    conn,
                    "Сжатие после удаления 200 строк",
                    lambda c: c.execute(f"VACUUM FULL {TEST_TABLE_NAME}")
                )
                f.write(f"{op_name}: {op_time:.6f} сек\n")

                # 12. Сжатие, чтобы осталось 200 строк
                await conn.execute(f"DELETE FROM {TEST_TABLE_NAME} WHERE patient_id > 200")
                op_name, op_time = await measure_operation(
                    conn,
                    "Сжатие (осталось 200 строк)",
                    lambda c: c.execute(f"VACUUM FULL {TEST_TABLE_NAME}")
                )
                f.write(f"{op_name}: {op_time:.6f} сек\n")
                
                f.write("\n")

    await pool.close()

if __name__ == "__main__":
    asyncio.run(run_tests())