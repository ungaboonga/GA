import sqlite3
import database as db

conn = sqlite3.connect(db.DB_NAME)
c = conn.cursor()

# Показать все переменные
c.execute("SELECT id, name, deleted FROM variables")
print("Все переменные в БД:")
rows = c.fetchall()
for row in rows:
    print(f"ID: {row[0]}, Имя: {row[1]}, deleted: {row[2]}")

# Спросить, какую переменную удалить
var_id = input("Введите ID переменной, которую хотите удалить (или нажмите Enter для выхода): ")
if var_id.strip():
    try:
        var_id = int(var_id)
        # Проверим, существует ли такая
        c.execute("SELECT id FROM variables WHERE id=?", (var_id,))
        if c.fetchone():
            # Удаляем физически
            c.execute("DELETE FROM variables WHERE id=?", (var_id,))
            # Также удаляем связанные значения
            c.execute("DELETE FROM steps WHERE variable_id=?", (var_id,))
            conn.commit()
            print(f"Переменная с ID {var_id} удалена.")
        else:
            print("Переменная с таким ID не найдена.")
    except:
        print("Неверный ввод.")

conn.close()