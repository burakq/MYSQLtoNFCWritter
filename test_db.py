import mysql.connector

try:
    connection = mysql.connector.connect(
        host='185.244.146.135',
        port=3306,
        user='erbilkareverify',
        password='234!1Extl',
        database='erbilkareverify'
    )
    
    if connection.is_connected():
        print("Veritabanına başarıyla bağlandı!")
        cursor = connection.cursor()
        cursor.execute("SELECT 1")
        result = cursor.fetchone()
        print("Test sorgusu sonucu:", result)
        
except mysql.connector.Error as err:
    print(f"Veritabanına bağlanılamadı: {err}")
    
finally:
    if 'connection' in locals() and connection.is_connected():
        connection.close()
        print("Veritabanı bağlantısı kapatıldı.") 