import time
import mysql.connector
from smartcard.System import readers
from smartcard.util import toHexString

def get_mysql_connection():
    try:
        connection = mysql.connector.connect(
            host="localhost",
            port=8889,
            user="root",
            password="root",
            database="artwork_auth"
        )
        return connection
    except mysql.connector.Error as err:
        print(f"MySQL bağlantı hatası: {err}")
        return None

def read_verification_code(artwork_id):
    connection = get_mysql_connection()
    if connection:
        try:
            cursor = connection.cursor()
            cursor.execute("SELECT verification_code FROM artworks WHERE id = %s", (artwork_id,))
            result = cursor.fetchone()
            if result:
                return result[0]
            else:
                print(f"ID {artwork_id} için verification code bulunamadı!")
                return None
        except mysql.connector.Error as err:
            print(f"MySQL sorgu hatası: {err}")
            return None
        finally:
            if connection.is_connected():
                cursor.close()
                connection.close()
    return None

def create_ndef_message(verification_code):
    # URL'yi oluştur
    base_url = "https://erbilkare.com/artworks/verify.php?code="
    url = base_url + verification_code
    
    # URL verisi
    url_data = list(url.encode('ascii'))
    
    # Payload uzunluğu (URL identifier + URL verisi)
    payload_length = len(url_data) + 1  # +1 for URL identifier
    
    # NDEF başlık ve TLV yapısı
    ndef_header = [0x03, payload_length + 3]  # NDEF Mesaj başlangıcı + toplam uzunluk
    
    # URL için NDEF kayıt başlığı
    record_header = [0xD1,  # TNF=0x01 (Well Known) + MB=1 + ME=1
                    0x01,   # Type length
                    payload_length]  # Payload length
    
    # URL tipi ve identifier
    url_type = [0x55]  # 'U' for URL
    url_prefix = [0x00]  # No prefix - tam URL kullanacağız
    
    # NDEF sonlandırma
    terminator = [0xFE]
    
    # Tüm mesajı birleştir
    return ndef_header + record_header + url_type + url_prefix + url_data + terminator

def list_readers():
    try:
        reader_list = readers()
        if not reader_list:
            print("NFC okuyucu bulunamadı!")
            return None
        print("Bulunan okuyucular:")
        for i, reader in enumerate(reader_list):
            print(f"{i}: {reader}")
        return reader_list[0]
    except Exception as e:
        print(f"Okuyucu listesi alınamadı: {str(e)}")
        return None

def clear_tag(reader):
    try:
        connection = reader.createConnection()
        connection.connect()
        print("Kart okuyucuya bağlanıldı!")
        
        # Get UID
        get_uid = [0xFF, 0xCA, 0x00, 0x00, 0x00]
        response, sw1, sw2 = connection.transmit(get_uid)
        if (sw1, sw2) == (0x90, 0x00):
            print(f"Kart UID: {toHexString(response)}")
            
            # NTAG213'te NDEF verisi 4. sayfadan başlar
            print("\nKartı temizliyorum...")
            for page in range(4, 40):  # İlk 40 sayfayı temizle
                # Her sayfayı 0x00 ile doldur
                write_cmd = [0xFF, 0xD6, 0x00, page, 0x04, 0x00, 0x00, 0x00, 0x00]
                response, sw1, sw2 = connection.transmit(write_cmd)
                
                if (sw1, sw2) == (0x90, 0x00):
                    print(f"Sayfa {page} temizlendi")
                else:
                    print(f"Sayfa {page} temizleme hatası: SW1={hex(sw1)}, SW2={hex(sw2)}")
                    return False
            
            print("\nKart başarıyla temizlendi!")
            return True
        else:
            print("UID okunamadı")
            return False
            
    except Exception as e:
        print(f"Hata oluştu: {str(e)}")
        return False
    finally:
        try:
            connection.disconnect()
        except:
            pass

def write_to_ntag213(reader):
    try:
        # Kullanıcıdan artwork ID'sini al
        artwork_id = input("Artwork ID'sini girin: ")
        try:
            artwork_id = int(artwork_id)
        except ValueError:
            print("Geçersiz ID! Lütfen sayısal bir değer girin.")
            return False
            
        # MySQL'den verification code'u oku
        verification_code = read_verification_code(artwork_id)
        if not verification_code:
            return False
            
        connection = reader.createConnection()
        connection.connect()
        print("Kart okuyucuya bağlanıldı!")
        
        # Get UID
        get_uid = [0xFF, 0xCA, 0x00, 0x00, 0x00]
        response, sw1, sw2 = connection.transmit(get_uid)
        if (sw1, sw2) == (0x90, 0x00):
            print(f"Kart UID: {toHexString(response)}")
            
            # NDEF mesajını oluştur
            ndef_data = create_ndef_message(verification_code)
            
            print("\nNDEF mesajı:")
            print(f"Verification Code: {verification_code}")
            print(f"URL: https://erbilkare.com/artworks/verify.php?code={verification_code}")
            print(f"Başlık: {toHexString(ndef_data[:4])}")
            print(f"URL tipi: {toHexString(ndef_data[4:5])}")
            print(f"URL prefix: {toHexString(ndef_data[5:6])}")
            print(f"URL verisi: {toHexString(ndef_data[6:])}")
            
            # NTAG213'te NDEF verisi 4. sayfadan başlar
            page = 4
            
            # NDEF mesajını 4'er byte'lık sayfalara böl ve yaz
            for i in range(0, len(ndef_data), 4):
                chunk = ndef_data[i:i+4]
                # 4 byte'dan küçük chunk'ları 0 ile doldur
                while len(chunk) < 4:
                    chunk.append(0x00)
                
                # Sayfaya yaz
                write_cmd = [0xFF, 0xD6, 0x00, page] + [0x04] + chunk
                response, sw1, sw2 = connection.transmit(write_cmd)
                
                if (sw1, sw2) == (0x90, 0x00):
                    print(f"Sayfa {page} yazıldı: {toHexString(chunk)}")
                else:
                    print(f"Sayfa {page} yazma hatası: SW1={hex(sw1)}, SW2={hex(sw2)}")
                    return False
                
                page += 1
            
            print("\nNDEF mesajı başarıyla yazıldı!")
            return True
        else:
            print("UID okunamadı")
            return False
            
    except Exception as e:
        print(f"Hata oluştu: {str(e)}")
        return False
    finally:
        try:
            connection.disconnect()
        except:
            pass

def read_ntag213(reader):
    try:
        connection = reader.createConnection()
        connection.connect()
        print("Kart okuyucuya bağlanıldı!")
        
        # Get UID
        get_uid = [0xFF, 0xCA, 0x00, 0x00, 0x00]
        response, sw1, sw2 = connection.transmit(get_uid)
        if (sw1, sw2) == (0x90, 0x00):
            print(f"Kart UID: {toHexString(response)}")
            
            # NTAG213'te NDEF verisi 4. sayfadan başlar
            print("\nKart içeriğini okuyorum...")
            for page in range(4, 20):  # İlk 20 sayfayı oku
                read_cmd = [0xFF, 0xB0, 0x00, page, 0x04]
                response, sw1, sw2 = connection.transmit(read_cmd)
                if (sw1, sw2) == (0x90, 0x00):
                    print(f"Sayfa {page}: {toHexString(response)}")
                    try:
                        ascii_data = bytes(response).decode('ascii')
                        print(f"  ASCII: {ascii_data}")
                    except:
                        pass
                else:
                    print(f"Sayfa {page} okuma hatası: SW1={hex(sw1)}, SW2={hex(sw2)}")
        else:
            print("UID okunamadı")
            
    except Exception as e:
        print(f"Hata oluştu: {str(e)}")
    finally:
        try:
            connection.disconnect()
        except:
            pass

def main():
    while True:
        reader = list_readers()
        if reader:
            print("\n1. Kartı temizle")
            print("2. Karta yaz")
            print("3. Kartı oku")
            print("4. Çıkış")
            choice = input("Seçiminiz (1-4): ")
            
            if choice == "1":
                clear_tag(reader)
            elif choice == "2":
                write_to_ntag213(reader)
            elif choice == "3":
                read_ntag213(reader)
            elif choice == "4":
                break
            else:
                print("Geçersiz seçim!")
        
        time.sleep(1)

if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        print("\nProgram sonlandırıldı.") 