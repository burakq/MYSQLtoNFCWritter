const { app, BrowserWindow, ipcMain } = require('electron');
const path = require('path');
const mysql = require('mysql2');
const nfc = require('nfc-pcsc');

let mainWindow;
let connection;
let nfcReader = null;

function createWindow() {
    mainWindow = new BrowserWindow({
        width: 1200,
        height: 800,
        webPreferences: {
            nodeIntegration: true,
            contextIsolation: false,
            enableRemoteModule: true
        }
    });

    mainWindow.loadFile('index.html');

    // Veritabanı bağlantısını oluştur
    connection = mysql.createConnection({
        host: 'localhost',
        port: 8889,
        user: 'root',
        password: 'root',
        database: 'artwork_auth'
    });

    // Bağlantıyı test et
    connection.connect((err) => {
        if (err) {
            console.error('Veritabanı bağlantı hatası:', err);
            return;
        }
        console.log('Veritabanına başarıyla bağlanıldı');
    });

    // NFC okuyucuyu başlat
    initNFCReader();
}

function initNFCReader() {
    try {
        nfcReader = new nfc.NFC();
        console.log('NFC okuyucu başlatıldı');

        nfcReader.on('reader', (reader) => {
            console.log('NFC okuyucu bulundu:', reader.reader.name);

            reader.on('error', (err) => {
                console.error('Okuyucu hatası:', err);
            });

            reader.on('card', (card) => {
                console.log('Kart algılandı:', card);
            });

            reader.on('card.off', (card) => {
                console.log('Kart çıkarıldı:', card);
            });

            reader.on('end', () => {
                console.log('Okuyucu kapatıldı');
            });
        });

        nfcReader.on('error', (err) => {
            console.error('NFC okuyucu hatası:', err);
        });
    } catch (err) {
        console.error('NFC okuyucu başlatma hatası:', err);
    }
}

// Veritabanı işlemleri için IPC handler
ipcMain.handle('get-eserler', async () => {
    return new Promise((resolve, reject) => {
        const query = `
            SELECT 
                verification_code,
                CONCAT('http://localhost:8888/ArtworkAuthCompPHP/verify.php?code=', verification_code) as dogrulama_linki,
                title,
                image_path,
                artist_name,
                created_at
            FROM artworks 
            WHERE deleted_at IS NULL 
            ORDER BY created_at DESC 
            LIMIT 50
        `;
        
        connection.query(query, (err, results) => {
            if (err) {
                console.error('SQL sorgu hatası:', err);
                reject(err);
                return;
            }
            console.log('Bulunan eser sayısı:', results.length);
            resolve(results);
        });
    });
});

// NFC kartına veri yaz
async function writeToCard(data) {
    if (!nfcReader) {
        throw new Error('NFC okuyucu başlatılamadı');
    }

    return new Promise((resolve, reject) => {
        nfcReader.on('reader', (reader) => {
            reader.on('card', async (card) => {
                try {
                    // Ultralight C kartına yazma
                    const writeCommand = Buffer.from([
                        0xFF, 0xD6, 0x00, 0x04, 0x10, // WRITE BINARY
                        ...Buffer.from(data)
                    ]);

                    const response = await reader.transmit(writeCommand, 40);
                    console.log('Yazma yanıtı:', response);

                    resolve('Başarıyla yazdırıldı');
                } catch (err) {
                    reject(new Error('Yazma hatası: ' + err.message));
                }
            });
        });
    });
}

// NFC işlemleri için IPC handler
ipcMain.handle('write-to-nfc', async (event, data) => {
    try {
        return await writeToCard(data);
    } catch (err) {
        console.error('NFC yazma hatası:', err);
        throw new Error('NFC yazma hatası: ' + err.message);
    }
});

app.whenReady().then(() => {
    createWindow();

    app.on('activate', () => {
        if (BrowserWindow.getAllWindows().length === 0) {
            createWindow();
        }
    });
});

app.on('window-all-closed', () => {
    if (process.platform !== 'darwin') {
        app.quit();
    }
}); 