from smartcard.System import readers
from smartcard.util import toHexString
import mysql.connector
from PyQt6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, 
                            QHBoxLayout, QPushButton, QLabel, QTableWidget, 
                            QTableWidgetItem, QMessageBox)
import sys

class NFCWriter(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("NFC Kart Yazıcı (Yeni)")
        self.setGeometry(100, 100, 800, 600)
        
        # Ana widget ve layout
        main_widget = QWidget()
        self.setCentralWidget(main_widget)
        layout = QVBoxLayout(main_widget)
        
        # Üst bilgi alanı
        info_layout = QHBoxLayout()
        self.reader_label = QLabel("NFC Okuyucu: Aranıyor...")
        info_layout.addWidget(self.reader_label)
        layout.addLayout(info_layout)
        
        # Tablo
        self.table = QTableWidget()
        self.table.setColumnCount(4)
        self.table.setHorizontalHeaderLabels(["ID", "Eser Adı", "Sanatçı", "Doğrulama Kodu"])
        layout.addWidget(self.table)
        
        # Butonlar
        button_layout = QHBoxLayout()
        self.refresh_button = QPushButton("Yenile")
        self.write_button = QPushButton("Karta Yaz")
        self.read_button = QPushButton("Kartı Oku")
        self.clear_button = QPushButton("Kartı Temizle")
        button_layout.addWidget(self.refresh_button)
        button_layout.addWidget(self.write_button)
        button_layout.addWidget(self.read_button)
        button_layout.addWidget(self.clear_button)
        layout.addLayout(button_layout)
        
        # Buton bağlantıları
        self.refresh_button.clicked.connect(self.load_artworks)
        self.write_button.clicked.connect(self.write_to_card)
        self.read_button.clicked.connect(self.read_card)
        self.clear_button.clicked.connect(self.clear_card)
        
        # NFC okuyucuyu kontrol et
        self.check_reader()
        
        # Verileri yükle
        self.load_artworks()
    
    def check_reader(self):
        try:
            reader_list = readers()
            if reader_list:
                self.reader = reader_list[0]
                self.reader_label.setText(f"NFC Okuyucu: {self.reader}")
                return True
            else:
                self.reader_label.setText("NFC Okuyucu: Bulunamadı!")
                return False
        except Exception as e:
            self.reader_label.setText(f"NFC Okuyucu Hatası: {str(e)}")
            return False
    
    def get_mysql_connection(self):
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
            QMessageBox.critical(self, "Hata", f"MySQL bağlantı hatası: {err}")
            return None
    
    def load_artworks(self):
        connection = self.get_mysql_connection()
        if connection:
            try:
                cursor = connection.cursor()
                cursor.execute("""
                    SELECT a.id, a.title, a.artist_name, a.verification_code 
                    FROM artworks a 
                    ORDER BY a.id DESC 
                    LIMIT 50
                """)
                results = cursor.fetchall()
                
                self.table.setRowCount(len(results))
                for i, row in enumerate(results):
                    for j, value in enumerate(row):
                        self.table.setItem(i, j, QTableWidgetItem(str(value)))
                
                self.table.resizeColumnsToContents()
                
            except mysql.connector.Error as err:
                QMessageBox.critical(self, "Hata", f"MySQL sorgu hatası: {err}")
            finally:
                if connection.is_connected():
                    cursor.close()
                    connection.close()
    
    def create_ndef_message(self, verification_code):
        # URL'yi oluştur
        url = f"erbilkare.com/artworks/verify.php?code={verification_code}"
        url_bytes = url.encode('ascii')
        
        # NDEF Message TLV
        tlv_type = 0x03  # NDEF Message
        tlv_length = len(url_bytes) + 5  # header + type length + payload length + type + prefix
        
        # NDEF Record Header
        header = 0xD1  # TNF=0x01 (Well Known) + MB=1 + ME=1 + SR=1
        type_length = 0x01  # 'U' için 1 byte
        payload_length = len(url_bytes) + 1  # URL + prefix byte
        
        message = []
        # TLV
        message.extend([tlv_type, tlv_length])
        
        # NDEF Header
        message.extend([
            header,          # TNF + flags
            type_length,     # Type length
            payload_length   # Payload length
        ])
        
        # Record Type
        message.extend(b'U')  # URI record
        
        # URI Identifier (https://www.)
        message.append(0x02)
        
        # URL
        message.extend(url_bytes)
        
        # TLV Terminator
        message.append(0xFE)
        
        return message
    
    def write_to_card(self):
        if not self.check_reader():
            QMessageBox.warning(self, "Uyarı", "NFC okuyucu bulunamadı!")
            return
            
        current_row = self.table.currentRow()
        if current_row < 0:
            QMessageBox.warning(self, "Uyarı", "Lütfen bir eser seçin!")
            return
            
        verification_code = self.table.item(current_row, 3).text()
        
        try:
            connection = self.reader.createConnection()
            connection.connect()
            
            # Get UID
            get_uid = [0xFF, 0xCA, 0x00, 0x00, 0x00]
            response, sw1, sw2 = connection.transmit(get_uid)
            if (sw1, sw2) != (0x90, 0x00):
                QMessageBox.critical(self, "Hata", "Kart UID okunamadı!")
                return
            
            # Önce kartı temizle
            for page in range(4, 40):
                clear_cmd = [0xFF, 0xD6, 0x00, page, 0x04, 0x00, 0x00, 0x00, 0x00]
                response, sw1, sw2 = connection.transmit(clear_cmd)
                if (sw1, sw2) != (0x90, 0x00):
                    QMessageBox.critical(self, "Hata", f"Sayfa {page} temizleme hatası!")
                    return
            
            # NDEF mesajını oluştur
            ndef_data = self.create_ndef_message(verification_code)
            
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
                
                if (sw1, sw2) != (0x90, 0x00):
                    QMessageBox.critical(self, "Hata", f"Sayfa {page} yazma hatası!")
                    return
                
                page += 1
            
            QMessageBox.information(self, "Başarılı", "Kart başarıyla yazıldı!")
            
        except Exception as e:
            QMessageBox.critical(self, "Hata", f"Kart yazma hatası: {str(e)}")
        finally:
            try:
                connection.disconnect()
            except:
                pass
    
    def read_card(self):
        if not self.check_reader():
            QMessageBox.warning(self, "Uyarı", "NFC okuyucu bulunamadı!")
            return
            
        try:
            connection = self.reader.createConnection()
            connection.connect()
            
            # Get UID
            get_uid = [0xFF, 0xCA, 0x00, 0x00, 0x00]
            response, sw1, sw2 = connection.transmit(get_uid)
            if (sw1, sw2) != (0x90, 0x00):
                QMessageBox.critical(self, "Hata", "Kart UID okunamadı!")
                return
            
            # NTAG213'te NDEF verisi 4. sayfadan başlar
            data = []
            for page in range(4, 40):
                read_cmd = [0xFF, 0xB0, 0x00, page, 0x04]
                response, sw1, sw2 = connection.transmit(read_cmd)
                
                if (sw1, sw2) != (0x90, 0x00):
                    break
                
                data.extend(response)
            
            # NDEF mesajını parse et
            if len(data) > 0:
                # TLV Type
                tlv_type = data[0]
                if tlv_type != 0x03:  # NDEF Message
                    QMessageBox.warning(self, "Uyarı", "Kartta NDEF mesajı bulunamadı!")
                    return
                
                # TLV Length
                tlv_length = data[1]
                
                # NDEF Record Header
                header = data[2]
                type_length = data[3]
                payload_length = data[4]
                
                # Record Type
                record_type = bytes(data[5:5+type_length])
                
                # Payload
                payload_start = 5 + type_length
                payload = data[payload_start:payload_start+payload_length]
                
                if record_type == b'U':
                    uri_prefix = payload[0]
                    uri_content = bytes(payload[1:]).decode('ascii')
                    
                    result = f"""
NDEF Mesaj İçeriği:
==================
Record Type: URI
URI Prefix: {uri_prefix:02X} (https://www.)
Content: {uri_content}
Full URL: https://www.{uri_content}
=================="""
                    QMessageBox.information(self, "Kart İçeriği", result)
                else:
                    QMessageBox.information(self, "Kart İçeriği", 
                        f"Record Type: {record_type.decode('ascii')}\n"
                        f"Payload: {bytes(payload).decode('ascii')}")
            else:
                QMessageBox.warning(self, "Uyarı", "Kart boş veya okunamadı!")
            
        except Exception as e:
            QMessageBox.critical(self, "Hata", f"Kart okuma hatası: {str(e)}")
        finally:
            try:
                connection.disconnect()
            except:
                pass

    def clear_card(self):
        if not self.check_reader():
            QMessageBox.warning(self, "Uyarı", "NFC okuyucu bulunamadı!")
            return
            
        try:
            connection = self.reader.createConnection()
            connection.connect()
            
            # Get UID
            get_uid = [0xFF, 0xCA, 0x00, 0x00, 0x00]
            response, sw1, sw2 = connection.transmit(get_uid)
            if (sw1, sw2) != (0x90, 0x00):
                QMessageBox.critical(self, "Hata", "Kart UID okunamadı!")
                return
            
            # Kartı temizle
            for page in range(4, 40):
                clear_cmd = [0xFF, 0xD6, 0x00, page, 0x04, 0x00, 0x00, 0x00, 0x00]
                response, sw1, sw2 = connection.transmit(clear_cmd)
                if (sw1, sw2) != (0x90, 0x00):
                    QMessageBox.critical(self, "Hata", f"Sayfa {page} temizleme hatası!")
                    return
            
            QMessageBox.information(self, "Başarılı", "Kart başarıyla temizlendi!")
            
        except Exception as e:
            QMessageBox.critical(self, "Hata", f"Kart temizleme hatası: {str(e)}")
        finally:
            try:
                connection.disconnect()
            except:
                pass

if __name__ == '__main__':
    app = QApplication(sys.argv)
    window = NFCWriter()
    window.show()
    sys.exit(app.exec()) 