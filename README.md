# NFC Kart Yazıcı Uygulaması

Bu uygulama, ACR122U NFC okuyucu/yazıcı kullanarak NTAG213 kartlara veri yazmak için geliştirilmiş bir masaüstü uygulamasıdır.

## Özellikler

- MySQL veritabanından sanat eseri bilgilerini okuma
- NFC kartlara NDEF formatında veri yazma
- NFC kartları temizleme
- Kullanıcı dostu arayüz
- Detaylı hata raporlama
- İşlem istatistikleri

## Gereksinimler

- Python 3.x
- PyQt6
- pyscard
- PyMySQL
- bcrypt
- cryptography

## Kurulum

1. Projeyi klonlayın:
```bash
git clone https://github.com/burakq/mysqltonfcwritter.git
cd mysqltonfcwritter
```

2. Gerekli paketleri yükleyin:
```bash
pip install -r requirements.txt
```

3. Uygulamayı çalıştırın:
```bash
python nfc_writer_enhanced.py
```

## Derleme

Uygulamayı tek bir çalıştırılabilir dosya haline getirmek için:

```bash
pyinstaller --clean --noconfirm --onedir --windowed --icon=logo.icns --add-data "venv/lib/python3.13/site-packages/smartcard:smartcard" --add-data "venv/lib/python3.13/site-packages/bcrypt:bcrypt" --add-data "venv/lib/python3.13/site-packages/PyMySQL:PyMySQL" --add-data "venv/lib/python3.13/site-packages/cryptography:cryptography" --add-data "venv/lib/python3.13/site-packages/cffi:cffi" --add-data "venv/lib/python3.13/site-packages/pycparser:pycparser" nfc_writer_enhanced.py
```

## Kullanım

1. Uygulamayı başlatın
2. NFC okuyucunun bağlı olduğunu kontrol edin
3. Veritabanından sanat eserlerini yükleyin
4. Yazmak istediğiniz sanat eserini seçin
5. NFC kartı okuyucuya yerleştirin
6. "Karta Yaz" butonuna tıklayın

## Lisans

Bu proje MIT lisansı altında lisanslanmıştır. 