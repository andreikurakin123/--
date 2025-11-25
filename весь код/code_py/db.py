import asyncpg
from config import DB_HOST, DB_PORT, DB_USER, DB_PASSWORD, DB_NAME

pool = None

async def init_db():
    global pool
    pool = await asyncpg.create_pool(
        host= "127.0.0.1",
        port= 5432,
        user= "postgres",
        password= "90338410Pp",
        database= "postgres"
    )
    

async def smart_execute(query, *args):
    """
    Универсальная функция для выполнения запросов.
    Автоматически определяет, нужно ли использовать транзакцию.
    
    Args:
        query (str): SQL-запрос.
        *args: Параметры для запроса.
    
    Returns:
        Результат выполнения запроса.
    """
    conn = await pool.acquire()
    try:
        # Проверяем, начинается ли запрос с 'VACUUM'
        if query.strip().upper().startswith("VACUUM"):
            # Команда VACUUM должна выполняться вне транзакции
            return await conn.execute(query, *args)
        else:
            # Все остальные запросы выполняем в транзакции для безопасности
            async with conn.transaction():
                return await conn.execute(query, *args)
    finally:
        await pool.release(conn)

# Базовая универсальная функция
async def execute(query, *args, fetch=False, fetchrow=False, fetchval=False, execute=False):
    async with pool.acquire() as conn:
        async with conn.transaction():
            if fetch:
                return await conn.fetch(query, *args)
            elif fetchrow:
                return await conn.fetchrow(query, *args)
            elif fetchval:
                return await conn.fetchval(query, *args)
            elif execute:
                return await conn.execute(query, *args)

# Обёртки для удобного импорта
async def fetch(query, *args):
    return await execute(query, *args, fetch=True)

async def fetchrow(query, *args):
    return await execute(query, *args, fetchrow=True)

async def fetchval(query, *args):
    return await execute(query, *args, fetchval=True)

async def exec_only(query, *args):
    return await execute(query, *args, execute=True)
