import pymysql

def test_connection():
    try:
        # Veritabanı bağlantı bilgilerini güvenli bir şekilde al
        db_config = {
            'host': 'YOUR_DB_HOST',
            'port': 3306,
            'user': 'YOUR_DB_USER',
            'password': 'YOUR_DB_PASSWORD',
            'database': 'YOUR_DB_NAME'
        }
        
        connection = pymysql.connect(**db_config)
        print("Veritabanı bağlantısı başarılı!")
        connection.close()
    except pymysql.Error as err:
        print(f"Veritabanı bağlantı hatası: {err}")

if __name__ == "__main__":
    test_connection() 