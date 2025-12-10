# 🏀 Voice Free Throw Basketball Game
### *Multimedia Voice-Controlled Basketball Mini Game*

**Nama Mahasiswa:** Reynaldi Cristian Simamora  
**NIM:** 122140116  
**Mata Kuliah:** Sistem Teknologi Multimedia
**Program Studi:** Teknik Informatika

---

## 🎮 Deskripsi Singkat
**Voice Free Throw Basketball Game** adalah game mini berbasis Python yang memanfaatkan **audio processing**, **video processing**, dan **pose detection** untuk menciptakan pengalaman bermain basket yang unik menggunakan suara sebagai kontrol utama.  
Pemain "menembak" bola menggunakan suara — seperti berteriak atau menghasilkan suara keras. Sistem mendeteksi intensitas audio dan menentukan apakah bola masuk atau tidak.

Game ini merupakan demonstrasi nyata penerapan teknologi multimedia:
- Audio signal processing
- Real-time video processing
- Pose estimation (MediaPipe)
- Interactive multimedia system

---

## 🚀 Fitur Utama

### 🔊 Kontrol Suara
- Deteksi intensitas suara real-time
- Filtering: noise reduction menggunakan deque rolling buffer
- Amplitude threshold sebagai pemicu tembakan

### 🎥 Video Processing & Overlay
- Webcam real-time (OpenCV)
- Render stickman, ring basket, trajectory, dan bola
- Accuracy bar yang responsif
- Efek Game Over dengan overlay transparent

### 🧍 Pose Tracking (MediaPipe)
- Deteksi landmark tubuh
- Skeleton tracking
- Penyesuaian animasi stickman berdasarkan pose

### 🔈 Sound Effects
- Sound effect **masuk**
- Sound effect **miss**
- Sound effect **best score**
- Background music in-game

---

## 🛠️ Cara Clone & Menjalankan Game

### 1️⃣ Clone Repository
```bash
git clone https://github.com/USERNAME/voice-freethrow-game.git
cd voice-freethrow-game
```

### 2️⃣ Install Dependencies

Pastikan Python 3.12+ telah terpasang.
```bash
pip install -r requirements.txt
```
3️⃣ Jalankan Game
```bash
python vft.py
```

## 📦 Dependency Utama
| Library    | Kegunaan                                   |
|------------|---------------------------------------------|
| OpenCV     | Video capture, overlay UI, drawing graphics |
| MediaPipe  | Pose estimation & landmark detection        |
| PyAudio    | Mengambil input mikrofon                    |
| NumPy      | Perhitungan numerik                         |
| Threading  | Audio stream paralel                        |

---

## 📘 Ringkasan Teknologi Multimedia

### 🎧 1. Audio Processing
Proyek ini menggunakan:
- Real-time microphone capture  
- RMS amplitude detection  
- Rolling average noise filtering  
- Event trigger berdasarkan suara  

Ini merupakan implementasi dasar **digital audio processing**.

---

### 🎥 2. Video Processing
OpenCV digunakan untuk:
- Rendering real-time  
- Overlay UI (score, accuracy bar)  
- Alpha blending (game over screen)  
- Custom sprite: ring basket & bola  

Termasuk dalam **video compositing** dan **frame-based graphics**.

---

### 🧍 3. Pose Estimation
Menggunakan MediaPipe Pose untuk:
- Deteksi skeleton tubuh  
- Landmark tracking  
- Mengubah pose stickman sesuai posisi pemain  

Ini termasuk konsep **computer vision** dan **multimodal interaction**.

---

### 🕹️ 4. Interactive Multimedia System
Game menggabungkan modalitas berikut:

| Modalitas     | Implementasi                        |
|---------------|--------------------------------------|
| Audio         | Voice input & sound effects          |
| Visual        | Webcam feed + overlay grafik         |
| Interactivity | Suara → tembakan bola                |

Ini membuktikan integrasi **audio + visual + interaksi** dalam satu sistem multimedia real-time.

---

## 📸 Screenshot Gameplay
### 1. Tampilan Menu Start
![Menu](screenshots/Menu.png)
### 2. Tampilan Menahan Shoot
![HoldShoot](screenshots/HoldingShoot.png)
### 3. Tampilan Shooting
![Shoot](screenshots/Shooting.png)
### 4. Tampilan Akurasi Setelah Shooting
![ShootAcc](screenshots/ShootingAccuracy.png)
### 5. Tampilan Menu Game Over
![GameOver](screenshots/GameOverMenu.png)


---

## 🤝 Kontribusi
Silakan fork dan buat pull request untuk pengembangan lebih lanjut.

---

### ⭐ Jika proyek ini bermanfaat, jangan lupa beri ⭐ di GitHub!