
drop table if exists detecciones;
drop table if exists españa;
CREATE TABLE IF NOT EXISTS detecciones (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  latitude REAL DEFAULT NULL,
  longitude REAL DEFAULT NULL,
  brightness REAL DEFAULT NULL,
  scan REAL DEFAULT NULL,
  track REAL DEFAULT NULL,
  acq_date TEXT DEFAULT NULL,
  acq_time INTEGER DEFAULT NULL,
  satellite TEXT DEFAULT NULL,
  instrument TEXT DEFAULT 'MODIS',
  confidence INTEGER DEFAULT NULL,
  version TEXT DEFAULT NULL,
  bright_t31 REAL DEFAULT NULL,
  frp REAL DEFAULT NULL,
  daynight TEXT DEFAULT NULL,
  type INT
);

CREATE TABLE IF NOT EXISTS detecciones_tiemporeal (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  latitude REAL DEFAULT NULL,
  longitude REAL DEFAULT NULL,
  bright_ti4 REAL DEFAULT NULL,
  scan REAL DEFAULT NULL,
  track REAL DEFAULT NULL,
  acq_date TEXT DEFAULT NULL,
  acq_time INTEGER DEFAULT NULL,
  satellite TEXT DEFAULT NULL,
  instrument TEXT DEFAULT 'MODIS',
  confidence INTEGER DEFAULT NULL,
  version TEXT DEFAULT NULL,
  bright_ti5 REAL DEFAULT NULL,
  frp REAL DEFAULT NULL,
  daynight TEXT DEFAULT NULL
);



