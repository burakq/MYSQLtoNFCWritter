const { ipcRenderer } = require('electron');

let selectedEser = null;

// Durum mesajı göster
function showStatus(message, type) {
    const statusDiv = document.getElementById('status');
    statusDiv.textContent = message;
    statusDiv.className = type;
    console.log(`${type}: ${message}`);
}

// Tarih formatla
function formatDate(dateString) {
    const date = new Date(dateString);
    return date.toLocaleDateString('tr-TR', {
        year: 'numeric',
        month: 'long',
        day: 'numeric'
    });
}

// Eser kartı oluştur
function createEserCard(eser) {
    const card = document.createElement('div');
    card.className = 'eser-card';
    card.innerHTML = `
        <img src="${eser.image_path}" class="eser-image" onerror="this.src='placeholder.jpg'">
        <div class="eser-title">${eser.title}</div>
        <div class="eser-artist">${eser.artist_name || 'Sanatçı belirtilmemiş'}</div>
        <div class="eser-code">${eser.verification_code}</div>
        <div class="eser-date">${formatDate(eser.created_at)}</div>
    `;

    card.addEventListener('click', () => {
        // Önceki seçili kartın seçimini kaldır
        const previousSelected = document.querySelector('.eser-card.selected');
        if (previousSelected) {
            previousSelected.classList.remove('selected');
        }

        // Yeni kartı seç
        card.classList.add('selected');
        selectedEser = eser;
        
        // Yazdır butonunu aktif et
        document.getElementById('yazdirBtn').disabled = false;
    });

    return card;
}

// Eser listesini yükle
async function loadEserler() {
    try {
        const results = await ipcRenderer.invoke('get-eserler');
        console.log('Bulunan eser sayısı:', results.length);
        
        const loadingDiv = document.getElementById('loading');
        const gridDiv = document.getElementById('eserGrid');
        
        if (results.length === 0) {
            loadingDiv.textContent = 'Hiç eser bulunamadı';
            return;
        }

        // Loading mesajını kaldır
        loadingDiv.style.display = 'none';

        // Eserleri grid'e ekle
        results.forEach(eser => {
            console.log('Eser:', eser.verification_code);
            const card = createEserCard(eser);
            gridDiv.appendChild(card);
        });
        
        showStatus(`${results.length} eser yüklendi`, 'success');
    } catch (err) {
        console.error('Eser yükleme hatası:', err);
        showStatus('Eser yükleme hatası: ' + err.message, 'error');
    }
}

// Sayfa yüklendiğinde
document.addEventListener('DOMContentLoaded', () => {
    console.log('Sayfa yüklendi');
    loadEserler();

    document.getElementById('yazdirBtn').addEventListener('click', async () => {
        if (selectedEser) {
            console.log('Seçilen eser:', selectedEser);
            showStatus('NFC kartını bekliyor...', 'success');
            
            try {
                const result = await ipcRenderer.invoke('write-to-nfc', selectedEser.dogrulama_linki);
                showStatus(result, 'success');
            } catch (err) {
                console.error('NFC yazdırma hatası:', err);
                showStatus('NFC yazdırma hatası: ' + err.message, 'error');
            }
        } else {
            showStatus('Lütfen bir eser seçin', 'error');
        }
    });
}); 