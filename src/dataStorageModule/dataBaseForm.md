-- Włączenie wsparcia dla kluczy obcych (w SQLite jest domyślnie wyłączone)
PRAGMA foreign_keys = ON;

-- 1. Tabela serii (wiele powtórzeń należy do jednej serii)
CREATE TABLE IF NOT EXISTS serie (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    data_wykonania TEXT NOT NULL,         -- Format: 'YYYY-MM-DD HH:MM:SS'
    miejsce TEXT,                         -- Np. 'Dom', 'Siłownia'
    czas_trwania_sekundy INTEGER NOT NULL, -- Długość trwania serii w sekundach
    ilosc_powtórzen INTEGER NOT NULL,
    powtórzenia_poprawne INTEGER NOT NULL,
    powtórzenia_z_bledami INTEGER NOT NULL
);

-- 2. Tabela powtórzeń (relacja wiele-do-jednego z tabelą serii)
CREATE TABLE IF NOT EXISTS powtórzenia (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    seria_id INTEGER NOT NULL,
    szybkosc_wykonania_sekundy REAL NOT NULL, -- Czas trwania jednego powtórzenia (np. 2.5 sekundy)
    status_jakosci TEXT NOT NULL,              -- 'POPRAWNE' lub 'BŁĄD'
    
    -- Flagi konkretnych błędów (0 - brak błędu, 1 - wykryto błąd)
    blad_zbyt_plytko INTEGER DEFAULT 0,
    blad_za_daleko_od_krzesla INTEGER DEFAULT 0,
    blad_brak_kontroli_tempa INTEGER DEFAULT 0,
    
    FOREIGN KEY (seria_id) REFERENCES serie(id) ON DELETE CASCADE
);
