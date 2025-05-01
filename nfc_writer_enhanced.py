from smartcard.System import readers
from smartcard.util import toHexString
import pymysql
from PyQt6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, 
                            QHBoxLayout, QPushButton, QLabel, QTableWidget, 
                            QTableWidgetItem, QMessageBox, QStatusBar, QFrame,
                            QDialog, QLineEdit, QFormLayout, QDialogButtonBox,
                            QCheckBox)
from PyQt6.QtCore import Qt, QTimer, QSettings
from PyQt6.QtGui import QColor, QPalette, QIcon, QFont, QPixmap
import sys
import datetime
import json
import os
import logging
import time
import bcrypt
import urllib.request

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
        self.setFixedSize(400, 250)  # Pencere boyutunu büyüttük
        
        # Ana layout
        main_layout = QVBoxLayout(self)
        main_layout.setSpacing(20)  # Elemanlar arası boşluk
        main_layout.setContentsMargins(30, 30, 30, 30)  # Kenar boşlukları
        
        # Form layout
        form_layout = QFormLayout()
        form_layout.setSpacing(15)  # Form elemanları arası boşluk
        
        # E-posta alanı
        self.email = QLineEdit()
        self.email.setMinimumHeight(35)  # Yükseklik
        self.email.setStyleSheet("""
            QLineEdit {
                padding: 8px;
                border: 1px solid #ccc;
                border-radius: 4px;
                font-size: 14px;
            }
        """)
        
        # Şifre alanı
        self.password = QLineEdit()
        self.password.setEchoMode(QLineEdit.EchoMode.Password)
        self.password.setMinimumHeight(35)
        self.password.setStyleSheet("""
            QLineEdit {
                padding: 8px;
                border: 1px solid #ccc;
                border-radius: 4px;
                font-size: 14px;
            }
        """)
        
        # Beni hatırla checkbox'ı
        self.remember_me = QCheckBox("Beni hatırla")
        self.remember_me.setStyleSheet("""
            QCheckBox {
                font-size: 14px;
                spacing: 8px;
            }
        """)
        
        # Form elemanlarını ekle
        form_layout.addRow("E-posta:", self.email)
        form_layout.addRow("Şifre:", self.password)
        form_layout.addRow("", self.remember_me)
        
        # Butonlar
        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.setStyleSheet("""
            QPushButton {
                min-width: 100px;
                min-height: 35px;
                font-size: 14px;
                padding: 8px 16px;
                border-radius: 4px;
            }
            QPushButton[text="OK"] {
                background-color: #4CAF50;
                color: white;
                border: none;
            }
            QPushButton[text="OK"]:hover {
                background-color: #45a049;
            }
            QPushButton[text="Cancel"] {
                background-color: #f44336;
                color: white;
                border: none;
            }
            QPushButton[text="Cancel"]:hover {
                background-color: #d32f2f;
            }
        """)
        
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        
        # Layout'ları ana layout'a ekle
        main_layout.addLayout(form_layout)
        main_layout.addWidget(buttons)
        
        # Ayarları yükle
        self.settings = QSettings("NFCWriter", "Settings")
        self.load_remembered_credentials()
    
    def load_remembered_credentials(self):
        # Son giriş zamanını kontrol et
        last_login = self.settings.value("last_login")
        if last_login:
            last_login = datetime.datetime.fromisoformat(last_login)
            if (datetime.datetime.now() - last_login).days <= 30:  # 1 ay
                self.email.setText(self.settings.value("remembered_email", ""))
                self.password.setText(self.settings.value("remembered_password", ""))
                self.remember_me.setChecked(True)
    
    def get_credentials(self):
        email = self.email.text()
        password = self.password.text()
        
        if self.remember_me.isChecked():
            # Kullanıcı bilgilerini kaydet
            self.settings.setValue("remembered_email", email)
            self.settings.setValue("remembered_password", password)
            self.settings.setValue("last_login", datetime.datetime.now().isoformat())
        else:
            # Kullanıcı bilgilerini temizle
            self.settings.remove("remembered_email")
            self.settings.remove("remembered_password")
            self.settings.remove("last_login")
        
        return email, password

class SettingsDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Ayarlar")
        self.settings = QSettings("NFCWriter", "Settings")
        
        layout = QFormLayout(self)
        
        # Veritabanı Ayarları
        self.db_host = QLineEdit(self.settings.value("db_host", "185.244.146.135"))
        self.db_port = QLineEdit(self.settings.value("db_port", "3306"))
        self.db_user = QLineEdit(self.settings.value("db_user", "erbilkareverify"))
        self.db_password = QLineEdit(self.settings.value("db_password", "234!1Extl"))
        self.db_password.setEchoMode(QLineEdit.EchoMode.Password)  # Şifreyi gizle
        self.db_name = QLineEdit(self.settings.value("db_name", "erbilkareverify"))
        
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
            
            # Sayfalama için değişkenler
            self.current_page = 1
            self.page_size = 20
            
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
            self.table.setColumnCount(5)
            self.table.setHorizontalHeaderLabels(["Sıra", "Eser Adı", "Sanatçı", "Doğrulama Kodu", "Durum"])
            self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
            self.table.setSelectionMode(QTableWidget.SelectionMode.SingleSelection)
            self.table.verticalHeader().setVisible(False)  # Sol taraftaki sıra numaralarını gizle
            self.table.setStyleSheet("""
                QTableWidget {
                    background-color: white;
                    border: 1px solid #ddd;
                    border-radius: 4px;
                    color: #333;
                    gridline-color: #ddd;
                }
                QTableWidget::item {
                    padding: 8px;
                    border-bottom: 1px solid #eee;
                }
                QTableWidget::item:selected {
                    background-color: #f5f5f5;
                    color: #333;
                }
                QHeaderView::section {
                    background-color: #f8f8f8;
                    color: #333;
                    padding: 8px;
                    border: none;
                    border-bottom: 2px solid #ddd;
                    font-weight: bold;
                }
                QTableWidget::item:hover {
                    background-color: #f9f9f9;
                }
            """)
            layout.addWidget(self.table)
            
            # Butonlar
            button_frame = QFrame()
            button_frame.setFrameStyle(QFrame.Shape.StyledPanel)
            button_layout = QHBoxLayout(button_frame)
            
            # Sayfalama butonları
            self.prev_button = QPushButton("Önceki")
            self.prev_button.setEnabled(False)
            self.prev_button.clicked.connect(self.prev_page)
            
            self.next_button = QPushButton("Sonraki")
            self.next_button.clicked.connect(self.next_page)
            
            self.refresh_button = QPushButton("Yenile")
            self.write_button = QPushButton("Karta Yaz")
            self.read_button = QPushButton("Kartı Oku")
            self.clear_button = QPushButton("Kartı Temizle")
            self.settings_button = QPushButton("Ayarlar")
            
            button_layout.addWidget(self.prev_button)
            button_layout.addWidget(self.next_button)
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
            host = "185.244.146.135"  # Sabit IP adresi
            port = 3306
            user = "erbilkareverify"
            password = "234!1Extl"
            database = "erbilkareverify"
            
            logging.info(f"Bağlantı parametreleri: host={host}, port={port}, user={user}, db={database}")
            
            connection = pymysql.connect(
                host=host,
                port=port,
                user=user,
                password=password,
                database=database
            )
            logging.info("Veritabanı bağlantısı başarılı")
            return connection
        except pymysql.Error as err:
            error_msg = f"Veritabanı bağlantı hatası: {err}\n"
            error_msg += f"Host: {host}\n"
            error_msg += f"Port: {port}\n"
            error_msg += f"Kullanıcı: {user}\n"
            error_msg += f"Veritabanı: {database}"
            logging.error(error_msg)
            QMessageBox.critical(self, "Hata", error_msg)
            return None
    
    def load_artworks(self, page=1, page_size=20):
        # Yenileme butonunu devre dışı bırak
        self.refresh_button.setEnabled(False)
        
        # Dönen efekt ekle
        self.refresh_button.setStyleSheet("""
            QPushButton {
                background-color: #4CAF50;
                color: white;
                border: none;
                padding: 8px 16px;
                border-radius: 4px;
                font-weight: bold;
            }
            QPushButton:disabled {
                background-color: #cccccc;
                color: #666666;
            }
        """)
        
        # Animasyon efekti
        self.refresh_button.setText("Yenileniyor...")
        QApplication.processEvents()
        
        # Dönen animasyon için timer
        self.rotation_angle = 0
        self.rotation_timer = QTimer()
        self.rotation_timer.timeout.connect(self.rotate_button)
        self.rotation_timer.start(50)  # 50ms aralıklarla döndür
        
        # Sayfa ve sayfa boyutu kontrolü
        if page < 1:
            page = 1
        if page_size < 1:
            page_size = 20
            
        connection = self.get_mysql_connection()
        if connection:
            try:
                cursor = connection.cursor()
                
                # Site URL'sini ayarlardan al
                site_url = self.settings.value("site_url", "https://erbilkare.com/artworks/")
                
                # Toplam kayıt sayısını al
                cursor.execute("""
                    SELECT COUNT(*) 
                    FROM artworks a
                    LEFT JOIN nfc_written_logs nwl ON a.verification_code = nwl.verification_code
                """)
                total_records = cursor.fetchone()[0]
                total_pages = (total_records + page_size - 1) // page_size
                
                # Sayfa numarasını kontrol et
                if page > total_pages:
                    page = total_pages
                
                # Sayfalama ile verileri çek
                offset = (page - 1) * page_size
                cursor.execute("""
                    SELECT 
                        a.id, 
                        a.title, 
                        a.artist_name, 
                        a.verification_code,
                        CASE 
                            WHEN nwl.verification_code IS NOT NULL THEN 'Yazıldı'
                            ELSE 'Yazılmadı'
                        END as status
                    FROM artworks a
                    LEFT JOIN nfc_written_logs nwl ON a.verification_code = nwl.verification_code
                    ORDER BY a.id DESC 
                    LIMIT %s OFFSET %s
                """, (page_size, offset))
                results = cursor.fetchall()
                
                # Tablo sütunlarını ayarla
                self.table.setRowCount(len(results))
                for i, row in enumerate(results):
                    # Sıra numarası (sayfa numarasına göre)
                    row_number = (page - 1) * page_size + i + 1
                    self.table.setItem(i, 0, QTableWidgetItem(str(row_number)))
                    
                    # Eser Adı
                    self.table.setItem(i, 1, QTableWidgetItem(str(row[1])))
                    
                    # Sanatçı
                    self.table.setItem(i, 2, QTableWidgetItem(str(row[2])))
                    
                    # Doğrulama Kodu
                    self.table.setItem(i, 3, QTableWidgetItem(str(row[3])))
                    
                    # Durum
                    status_item = QTableWidgetItem(str(row[4]))
                    if row[4] == "Yazıldı":
                        status_item.setForeground(QColor("green"))
                    else:
                        status_item.setForeground(QColor("red"))
                    self.table.setItem(i, 4, status_item)
                
                # Sütun genişliklerini ayarla
                self.table.setColumnWidth(0, 50)   # Sıra
                self.table.setColumnWidth(1, 250)  # Eser Adı - genişliği artırıldı
                self.table.setColumnWidth(2, 200)  # Sanatçı - genişliği artırıldı
                self.table.setColumnWidth(3, 150)  # Doğrulama Kodu
                self.table.setColumnWidth(4, 100)  # Durum
                
                # Sayfalama bilgilerini göster
                self.statusBar.showMessage(f"Sayfa {page}/{total_pages} - Toplam {total_records} eser")
                
                # Sayfalama butonlarını güncelle
                self.prev_button.setEnabled(page > 1)
                self.next_button.setEnabled(page < total_pages)
                
            except pymysql.Error as err:
                self.show_error("MySQL Sorgu Hatası", f"Eserler yüklenemedi: {err}")
            finally:
                cursor.close()
                connection.close()
                
                # Animasyonu durdur
                self.rotation_timer.stop()
                
                # Yenileme butonunu tekrar aktif et
                self.refresh_button.setEnabled(True)
                self.refresh_button.setText("Yenile")
                self.refresh_button.setStyleSheet("""
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
                """)
    
    def rotate_button(self):
        # Dönen animasyon için açıyı güncelle
        self.rotation_angle = (self.rotation_angle + 10) % 360
        
        # Dönen efekt için CSS
        self.refresh_button.setStyleSheet(f"""
            QPushButton {{
                background-color: #cccccc;
                color: #666666;
                border: none;
                padding: 8px 16px;
                border-radius: 4px;
                font-weight: bold;
                background-image: url('refresh_icon.png');
                background-repeat: no-repeat;
                background-position: center;
                background-size: 20px;
                transform: rotate({self.rotation_angle}deg);
            }}
            QPushButton:disabled {{
                background-color: #cccccc;
                color: #666666;
            }}
        """)
    
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
        
        # SQL sorgusundan artwork_id'yi al
        connection = self.get_mysql_connection()
        if connection:
            try:
                cursor = connection.cursor()
                cursor.execute("""
                    SELECT id FROM artworks 
                    WHERE verification_code = %s
                """, (verification_code,))
                result = cursor.fetchone()
                if result:
                    artwork_id = result[0]  # integer olarak artwork_id
                else:
                    self.show_error("Hata", "Eser bulunamadı!")
                    return
            except pymysql.Error as err:
                self.show_error("Veritabanı Hatası", f"Eser ID'si alınamadı: {err}")
                return
            finally:
                cursor.close()
                connection.close()
        
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

    def download_image(self, url):
        try:
            with urllib.request.urlopen(url) as response:
                return response.read()
        except Exception as e:
            logging.error(f"Görsel indirme hatası: {str(e)}")
            return None

    def prev_page(self):
        if self.current_page > 1:
            self.current_page -= 1
            self.load_artworks(self.current_page, self.page_size)
            self.next_button.setEnabled(True)
            if self.current_page == 1:
                self.prev_button.setEnabled(False)

    def next_page(self):
        self.current_page += 1
        self.load_artworks(self.current_page, self.page_size)
        self.prev_button.setEnabled(True)

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