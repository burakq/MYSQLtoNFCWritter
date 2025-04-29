from smartcard.System import readers
from smartcard.util import toHexString
import pymysql
from PyQt6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, 
                            QHBoxLayout, QPushButton, QLabel, QTableWidget, 
                            QTableWidgetItem, QMessageBox, QStatusBar, QFrame,
                            QDialog, QLineEdit, QFormLayout, QDialogButtonBox)
from PyQt6.QtCore import Qt, QTimer, QSettings
from PyQt6.QtGui import QColor, QPalette, QIcon, QFont
import sys
import datetime
import json
import os
import logging
import time
import bcrypt

# Log dosyası ayarları
log_dir = os.path.expanduser("~/Library/Logs")
if not os.path.exists(log_dir):
    os.makedirs(log_dir)
    
log_file = os.path.join(log_dir, "nfc_writer_enhanced.log")
logging.basicConfig(
    filename=log_file,
    level=logging.DEBUG,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

class LoginDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Giriş")
        self.setFixedSize(300, 150)
        
        layout = QFormLayout(self)
        
        self.email = QLineEdit()
        self.password = QLineEdit()
        self.password.setEchoMode(QLineEdit.EchoMode.Password)
        
        layout.addRow("E-posta:", self.email)
        layout.addRow("Şifre:", self.password)
        
        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addRow(buttons)
    
    def get_credentials(self):
        return self.email.text(), self.password.text()

class SettingsDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Ayarlar")
        self.settings = QSettings("NFCWriter", "Settings")
        
        layout = QFormLayout(self)
        
        # Veritabanı Ayarları
        self.db_host = QLineEdit(self.settings.value("db_host", "localhost"))
        self.db_port = QLineEdit(self.settings.value("db_port", "8889"))
        self.db_user = QLineEdit(self.settings.value("db_user", "root"))
        self.db_password = QLineEdit(self.settings.value("db_password", "root"))
        self.db_name = QLineEdit(self.settings.value("db_name", "artwork_auth"))
        
        # URL Ayarları
        self.base_url = QLineEdit(self.settings.value("base_url", "erbilkare.com"))
        
        # Form Alanları
        layout.addRow("Veritabanı Sunucu:", self.db_host)
        layout.addRow("Veritabanı Port:", self.db_port)
        layout.addRow("Veritabanı Kullanıcı:", self.db_user)
        layout.addRow("Veritabanı Şifre:", self.db_password)
        layout.addRow("Veritabanı Adı:", self.db_name)
        layout.addRow("Temel URL:", self.base_url)
        
        # Butonlar
        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addRow(buttons)
    
    def save_settings(self):
        self.settings.setValue("db_host", self.db_host.text())
        self.settings.setValue("db_port", self.db_port.text())
        self.settings.setValue("db_user", self.db_user.text())
        self.settings.setValue("db_password", self.db_password.text())
        self.settings.setValue("db_name", self.db_name.text())
        self.settings.setValue("base_url", self.base_url.text())

class NFCWriterEnhanced(QMainWindow):
    def __init__(self):
        try:
            logging.info("NFCWriterEnhanced sınıfı başlatılıyor...")
            super().__init__()
            self.setWindowTitle("NFC Kart Yazıcı (Gelişmiş)")
            self.setGeometry(100, 100, 1000, 700)
            
            # Icon ayarla - resource_path kullanarak
            icon_path = resource_path("logo.icns")
            if os.path.exists(icon_path):
                self.setWindowIcon(QIcon(icon_path))
                logging.info("İkon başarıyla yüklendi")
            else:
                logging.warning("İkon dosyası bulunamadı: " + icon_path)
            
            # Ayarları yükle
            self.settings = QSettings("NFCWriter", "Settings")
            
            # Stil ayarları
            self.setStyleSheet("""
                QMainWindow {
                    background-color: #f0f0f0;
                }
                QPushButton {
                    background-color: #4CAF50;
                    color: white;
                    border: none;
                    padding: 8px 16px;
                    border-radius: 4px;
                    font-weight: bold;
                }
                QPushButton:hover {
                    background-color: #45a049;
                }
                QPushButton:disabled {
                    background-color: #cccccc;
                }
                QTableWidget {
                    background-color: white;
                    border: 1px solid #ddd;
                    border-radius: 4px;
                    color: #333;
                    gridline-color: #ddd;
                }
                QTableWidget::item {
                    color: #333;
                    padding: 5px;
                }
                QTableWidget::item:selected {
                    background-color: #e0e0e0;
                    color: #000;
                }
                QHeaderView::section {
                    background-color: #f8f8f8;
                    color: #333;
                    padding: 5px;
                    border: 1px solid #ddd;
                    font-weight: bold;
                }
                QLabel {
                    font-size: 12px;
                    color: #333;
                }
                QStatusBar {
                    background-color: #333;
                    color: white;
                }
                QLineEdit {
                    padding: 5px;
                    border: 1px solid #ddd;
                    border-radius: 4px;
                    background-color: white;
                    color: #333;
                }
                QFrame {
                    background-color: white;
                    border: 1px solid #ddd;
                    border-radius: 4px;
                }
            """)
            
            # Ana widget ve layout
            main_widget = QWidget()
            self.setCentralWidget(main_widget)
            layout = QVBoxLayout(main_widget)
            layout.setSpacing(10)
            layout.setContentsMargins(20, 20, 20, 20)
            
            # Üst bilgi alanı
            info_frame = QFrame()
            info_frame.setFrameStyle(QFrame.Shape.StyledPanel)
            info_layout = QHBoxLayout(info_frame)
            
            self.reader_label = QLabel("NFC Okuyucu: Aranıyor...")
            self.reader_label.setFont(QFont("Arial", 12, QFont.Weight.Bold))
            info_layout.addWidget(self.reader_label)
            
            self.stats_label = QLabel("İstatistikler: 0 kart yazıldı")
            self.stats_label.setFont(QFont("Arial", 12))
            info_layout.addWidget(self.stats_label)
            
            layout.addWidget(info_frame)
            
            # Tablo
            self.table = QTableWidget()
            self.table.setColumnCount(5)  # Yeni sütun: Durum
            self.table.setHorizontalHeaderLabels(["ID", "Eser Adı", "Sanatçı", "Doğrulama Kodu", "Durum"])
            self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
            self.table.setSelectionMode(QTableWidget.SelectionMode.SingleSelection)
            layout.addWidget(self.table)
            
            # Butonlar
            button_frame = QFrame()
            button_frame.setFrameStyle(QFrame.Shape.StyledPanel)
            button_layout = QHBoxLayout(button_frame)
            
            self.refresh_button = QPushButton("Yenile")
            self.write_button = QPushButton("Karta Yaz")
            self.read_button = QPushButton("Kartı Oku")
            self.clear_button = QPushButton("Kartı Temizle")
            self.settings_button = QPushButton("Ayarlar")
            
            button_layout.addWidget(self.refresh_button)
            button_layout.addWidget(self.write_button)
            button_layout.addWidget(self.read_button)
            button_layout.addWidget(self.clear_button)
            button_layout.addWidget(self.settings_button)
            
            layout.addWidget(button_frame)
            
            # Durum çubuğu
            self.statusBar = QStatusBar()
            self.setStatusBar(self.statusBar)
            self.statusBar.showMessage("Hazır")
            
            # Buton bağlantıları
            self.refresh_button.clicked.connect(self.load_artworks)
            self.write_button.clicked.connect(self.write_to_card)
            self.read_button.clicked.connect(self.read_card)
            self.clear_button.clicked.connect(self.clear_card)
            self.settings_button.clicked.connect(self.show_settings)
            
            # İstatistikler için değişkenler
            self.written_cards = 0
            self.written_artworks = set()
            
            # NFC okuyucuyu kontrol et
            self.check_reader()
            
            # Verileri yükle
            self.load_artworks()
            
            # Otomatik yenileme zamanlayıcısı
            self.refresh_timer = QTimer()
            self.refresh_timer.timeout.connect(self.check_reader)
            self.refresh_timer.start(5000)  # 5 saniyede bir
            
            logging.info("NFCWriterEnhanced sınıfı başlatıldı")
        except Exception as e:
            logging.error(f"Başlatma hatası: {str(e)}")
            raise
    
    def check_login(self):
        dialog = LoginDialog(self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            email, password = dialog.get_credentials()
            connection = self.get_mysql_connection()
            if connection:
                try:
                    cursor = connection.cursor()
                    cursor.execute("""
                        SELECT password FROM users 
                        WHERE email = %s AND is_admin = 1
                    """, (email,))
                    result = cursor.fetchone()
                    if result:
                        hashed_password = result[0].encode('utf-8')
                        if bcrypt.checkpw(password.encode('utf-8'), hashed_password):
                            return True
                        else:
                            QMessageBox.critical(self, "Hata", "Geçersiz şifre!")
                            return False
                    else:
                        QMessageBox.critical(self, "Hata", "Geçersiz e-posta veya yetkiniz yok!")
                        return False
                except pymysql.Error as err:
                    self.show_error("MySQL Sorgu Hatası", f"Giriş kontrolü başarısız: {err}")
                    return False
                finally:
                    cursor.close()
                    connection.close()
            return False
        return False
    
    def show_settings(self):
        dialog = SettingsDialog(self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            dialog.save_settings()
            self.load_artworks()  # Ayarlar değiştiğinde verileri yeniden yükle
    
    def check_reader(self):
        try:
            reader_list = readers()
            if reader_list:
                self.reader = reader_list[0]
                self.reader_label.setText(f"✅ NFC Okuyucu: {self.reader}")
                self.reader_label.setStyleSheet("color: green;")
                return True
            else:
                self.reader_label.setText("❌ NFC Okuyucu: Bulunamadı!")
                self.reader_label.setStyleSheet("color: red;")
                return False
        except Exception as e:
            self.reader_label.setText(f"❌ NFC Okuyucu Hatası: {str(e)}")
            self.reader_label.setStyleSheet("color: red;")
            return False
    
    def get_mysql_connection(self):
        try:
            logging.info("Veritabanı bağlantısı deneniyor...")
            connection = pymysql.connect(
                host='185.244.146.135',
                port=3306,
                user='erbilkareverify',
                password='234!1Extl',
                database='erbilkareverify'
            )
            logging.info("Veritabanı bağlantısı başarılı")
            return connection
        except pymysql.Error as err:
            logging.error(f"Veritabanı bağlantı hatası: {err}")
            QMessageBox.critical(self, "Hata", f"Veritabanına bağlanılamadı: {err}")
            return None
    
    def load_artworks(self):
        connection = self.get_mysql_connection()
        if connection:
            try:
                cursor = connection.cursor()
                cursor.execute("""
                    SELECT a.id, a.title, a.artist_name, a.verification_code 
                    FROM artworks a 
                    WHERE a.verification_code NOT IN (
                        SELECT verification_code 
                        FROM nfc_written_logs 
                        WHERE DATE(written_at) = CURDATE()
                    )
                    ORDER BY a.id DESC 
                    LIMIT 50
                """)
                results = cursor.fetchall()
                
                self.table.setRowCount(len(results))
                for i, row in enumerate(results):
                    for j, value in enumerate(row):
                        self.table.setItem(i, j, QTableWidgetItem(str(value)))
                    # Durum sütunu
                    self.table.setItem(i, 4, QTableWidgetItem("Yazılmadı"))
                    self.table.item(i, 4).setForeground(QColor("red"))
                
                self.table.resizeColumnsToContents()
                self.statusBar.showMessage(f"{len(results)} eser yüklendi")
                
            except pymysql.Error as err:
                self.show_error("MySQL Sorgu Hatası", f"Eserler yüklenemedi: {err}")
            finally:
                cursor.close()
                connection.close()
    
    def show_error(self, title, message):
        QMessageBox.critical(self, title, message)
        self.statusBar.showMessage(f"Hata: {message}", 5000)
    
    def show_success(self, title, message):
        QMessageBox.information(self, title, message)
        self.statusBar.showMessage(f"Başarılı: {message}", 5000)
    
    def write_to_card(self):
        if not self.check_reader():
            self.show_error("NFC Okuyucu Hatası", "NFC okuyucu bulunamadı!")
            return
        
        current_row = self.table.currentRow()
        if current_row < 0:
            self.show_error("Seçim Hatası", "Lütfen bir eser seçin!")
            return
        
        verification_code = self.table.item(current_row, 3).text()
        artwork_id = self.table.item(current_row, 0).text()
        
        try:
            connection = self.reader.createConnection()
            connection.connect()
            
            # Get UID
            get_uid = [0xFF, 0xCA, 0x00, 0x00, 0x00]
            response, sw1, sw2 = connection.transmit(get_uid)
            if (sw1, sw2) != (0x90, 0x00):
                self.show_error("Kart Okuma Hatası", "Kart UID okunamadı!")
                return
            
            # Önce kartı temizle
            for page in range(4, 40):
                clear_cmd = [0xFF, 0xD6, 0x00, page, 0x04, 0x00, 0x00, 0x00, 0x00]
                response, sw1, sw2 = connection.transmit(clear_cmd)
                if (sw1, sw2) != (0x90, 0x00):
                    self.show_error("Kart Temizleme Hatası", f"Sayfa {page} temizleme hatası!")
                    return
            
            # NDEF mesajını oluştur
            ndef_data = self.create_ndef_message(verification_code)
            
            # NTAG213'te NDEF verisi 4. sayfadan başlar
            page = 4
            
            # NDEF mesajını 4'er byte'lık sayfalara böl ve yaz
            for i in range(0, len(ndef_data), 4):
                chunk = ndef_data[i:i+4]
                while len(chunk) < 4:
                    chunk.append(0x00)
                
                write_cmd = [0xFF, 0xD6, 0x00, page] + [0x04] + chunk
                response, sw1, sw2 = connection.transmit(write_cmd)
                
                if (sw1, sw2) != (0x90, 0x00):
                    self.show_error("Kart Yazma Hatası", f"Sayfa {page} yazma hatası!")
                    return
                
                page += 1
            
            # Yazma işlemi başarılı, log kaydı oluştur
            self.log_written_card(artwork_id, verification_code)
            
            # İstatistikleri güncelle
            self.written_cards += 1
            self.written_artworks.add(artwork_id)
            self.update_stats()
            
            # Tablodaki durumu güncelle
            self.table.item(current_row, 4).setText("Yazıldı")
            self.table.item(current_row, 4).setForeground(QColor("green"))
            
            self.show_success("Başarılı", "Kart başarıyla yazıldı!")
            
        except Exception as e:
            self.show_error("Kart Yazma Hatası", f"Kart yazma işlemi başarısız: {str(e)}")
        finally:
            try:
                connection.disconnect()
            except:
                pass
    
    def log_written_card(self, artwork_id, verification_code):
        connection = self.get_mysql_connection()
        if connection:
            try:
                cursor = connection.cursor()
                cursor.execute("""
                    INSERT INTO nfc_written_logs (artwork_id, verification_code, written_at)
                    VALUES (%s, %s, NOW())
                """, (artwork_id, verification_code))
                connection.commit()
            except pymysql.Error as err:
                self.show_error("Log Kaydı Hatası", f"Yazma logu kaydedilemedi: {err}")
            finally:
                cursor.close()
                connection.close()
    
    def update_stats(self):
        self.stats_label.setText(f"İstatistikler: {self.written_cards} kart yazıldı, {len(self.written_artworks)} farklı eser")
    
    def create_ndef_message(self, verification_code):
        base_url = self.settings.value("base_url", "erbilkare.com")
        url = f"{base_url}/artworks/verify.php?code={verification_code}"
        url_bytes = url.encode('ascii')
        
        tlv_type = 0x03
        tlv_length = len(url_bytes) + 5
        
        header = 0xD1
        type_length = 0x01
        payload_length = len(url_bytes) + 1
        
        message = []
        message.extend([tlv_type, tlv_length])
        message.extend([header, type_length, payload_length])
        message.extend(b'U')
        message.append(0x02)
        message.extend(url_bytes)
        message.append(0xFE)
        
        return message
    
    def read_card(self):
        if not self.check_reader():
            self.show_error("NFC Okuyucu Hatası", "NFC okuyucu bulunamadı!")
            return
        
        try:
            connection = self.reader.createConnection()
            connection.connect()
            
            get_uid = [0xFF, 0xCA, 0x00, 0x00, 0x00]
            response, sw1, sw2 = connection.transmit(get_uid)
            if (sw1, sw2) != (0x90, 0x00):
                self.show_error("Kart Okuma Hatası", "Kart UID okunamadı!")
                return
            
            data = []
            for page in range(4, 40):
                read_cmd = [0xFF, 0xB0, 0x00, page, 0x04]
                response, sw1, sw2 = connection.transmit(read_cmd)
                
                if (sw1, sw2) != (0x90, 0x00):
                    break
                
                data.extend(response)
            
            if len(data) > 0:
                tlv_type = data[0]
                if tlv_type != 0x03:
                    self.show_error("Kart Okuma Hatası", "Kartta NDEF mesajı bulunamadı!")
                    return
                
                tlv_length = data[1]
                ndef_data = data[2:2+tlv_length]
                
                # URL'yi çıkar
                url_start = 7  # Header + type + prefix
                url_bytes = bytes(ndef_data[url_start:])
                url = url_bytes.decode('ascii')
                
                # URL'yi düzelt
                if not url.startswith('http'):
                    url = 'https://' + url
                
                self.show_success("Kart Okuma", f"Kartta bulunan URL: {url}")
            else:
                self.show_error("Kart Okuma Hatası", "Kart boş veya okunamadı!")
            
        except Exception as e:
            self.show_error("Kart Okuma Hatası", f"Kart okuma işlemi başarısız: {str(e)}")
        finally:
            try:
                connection.disconnect()
            except:
                pass
    
    def clear_card(self):
        if not self.check_reader():
            self.show_error("NFC Okuyucu Hatası", "NFC okuyucu bulunamadı!")
            return
        
        try:
            connection = self.reader.createConnection()
            connection.connect()
            
            for page in range(4, 40):
                clear_cmd = [0xFF, 0xD6, 0x00, page, 0x04, 0x00, 0x00, 0x00, 0x00]
                response, sw1, sw2 = connection.transmit(clear_cmd)
                if (sw1, sw2) != (0x90, 0x00):
                    self.show_error("Kart Temizleme Hatası", f"Sayfa {page} temizleme hatası!")
                    return
            
            self.show_success("Başarılı", "Kart başarıyla temizlendi!")
            
        except Exception as e:
            self.show_error("Kart Temizleme Hatası", f"Kart temizleme işlemi başarısız: {str(e)}")
        finally:
            try:
                connection.disconnect()
            except:
                pass

def resource_path(relative_path):
    """ Get absolute path to resource, works for dev and for PyInstaller """
    try:
        # PyInstaller creates a temp folder and stores path in _MEIPASS
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.abspath(".")

    return os.path.join(base_path, relative_path)

if __name__ == "__main__":
    app = QApplication(sys.argv)
    
    # Uygulama başlatma süresini ölç
    start_time = time.time()
    
    window = NFCWriterEnhanced()
    
    # Login kontrolü
    if window.check_login():
        window.show()
        end_time = time.time()
        logging.info(f"Uygulama başlatma süresi: {end_time - start_time:.2f} saniye")
        sys.exit(app.exec())
    else:
        sys.exit(1) 