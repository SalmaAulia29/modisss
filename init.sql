CREATE TABLE IF NOT EXISTS volcanoes (
  id INT PRIMARY KEY, name VARCHAR(100) NOT NULL, lonmin DECIMAL(9,5), lonmax DECIMAL(9,5), latmin DECIMAL(9,5), latmax DECIMAL(9,5)
);
INSERT INTO volcanoes VALUES (1,'Gunung Ibu',127.50,127.75,1.35,1.60),(2,'Gunung Lewotolok',123.40,123.60,-8.40,-8.20)
ON DUPLICATE KEY UPDATE name=VALUES(name),lonmin=VALUES(lonmin),lonmax=VALUES(lonmax),latmin=VALUES(latmin),latmax=VALUES(latmax);
CREATE TABLE IF NOT EXISTS modis_data (
  id BIGINT AUTO_INCREMENT PRIMARY KEY, volcano_id INT NOT NULL, UNIX_Time BIGINT NOT NULL, Sat VARCHAR(20), datetime DATETIME NOT NULL,
  Longitude DOUBLE, Latitude DOUBLE, B21 DOUBLE, B22 DOUBLE, B6 DOUBLE, B31 DOUBLE, B32 DOUBLE, SatZen DOUBLE, SatAzi DOUBLE,
  SunZen DOUBLE, SunAzi DOUBLE, Line INT, Samp INT, Nti DOUBLE, Glint DOUBLE, Excess DOUBLE, Temp DOUBLE, Err DOUBLE,
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP, UNIQUE KEY uq_detection (volcano_id,UNIX_Time,Sat,Longitude,Latitude),
  INDEX idx_volcano_datetime (volcano_id,datetime), CONSTRAINT fk_data_volcano FOREIGN KEY (volcano_id) REFERENCES volcanoes(id)
);
CREATE TABLE IF NOT EXISTS collection_runs (
  id BIGINT AUTO_INCREMENT PRIMARY KEY, volcano_id INT NOT NULL, volcano_name VARCHAR(100) NOT NULL, target_date DATE NOT NULL,
  status ENUM('running','success','no_data','failed') NOT NULL, rows_received INT DEFAULT 0, rows_inserted INT DEFAULT 0,
  http_status SMALLINT NULL, message TEXT NULL, worker VARCHAR(100), started_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP, finished_at TIMESTAMP NULL,
  INDEX idx_runs_started (started_at), INDEX idx_runs_volcano (volcano_id,started_at), CONSTRAINT fk_runs_volcano FOREIGN KEY (volcano_id) REFERENCES volcanoes(id)
);
CREATE TABLE IF NOT EXISTS lava_volume_calculations (
  id BIGINT AUTO_INCREMENT PRIMARY KEY, volcano_id INT NOT NULL, observation_datetime DATETIME NOT NULL,
  pixel_count INT NOT NULL, sum_b21 DOUBLE NOT NULL, max_b21 DOUBLE NOT NULL, delta_seconds BIGINT NOT NULL DEFAULT 0,
  effusion_cold DOUBLE NOT NULL, effusion_hot DOUBLE NOT NULL, heat_flux_cold DOUBLE NOT NULL, heat_flux_hot DOUBLE NOT NULL,
  volume_cold DOUBLE NOT NULL, volume_hot DOUBLE NOT NULL, cumulative_cold DOUBLE NOT NULL, cumulative_hot DOUBLE NOT NULL,
  calculated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  UNIQUE KEY uq_lava_observation (volcano_id,observation_datetime),
  CONSTRAINT fk_lava_volcano FOREIGN KEY (volcano_id) REFERENCES volcanoes(id)
);
CREATE TABLE IF NOT EXISTS worker_state (
  id TINYINT PRIMARY KEY, status VARCHAR(20) NOT NULL DEFAULT 'idle', interval_minutes INT NOT NULL DEFAULT 60,
  last_started_at DATETIME NULL, last_completed_at DATETIME NULL, next_run_at DATETIME NULL,
  last_error TEXT NULL, worker VARCHAR(100) NULL,
  updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
);
INSERT IGNORE INTO worker_state (id,status,interval_minutes) VALUES (1,'idle',60);
