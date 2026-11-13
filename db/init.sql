-- =====================================================================
-- Схема базы данных системы «Santa Promo Predictor»
-- Основана на физическом проектировании (лабораторная работа № 7):
-- 5 таблиц в 3НФ, СУБД MySQL, ограничения целостности и индексы.
-- Расширения реализации (зафиксированы в ЛР9):
--   promo_campaign.status       – статус акции («Черновик»/«Утверждена», UC-2, UC-5);
--   product.pack_qty            – квант поставки (упаковка поставщика, BR-2);
--   forecast_result.status      – жизненный цикл объекта «Прогноз» (диаграмма состояний ЛР8);
--   forecast_result.correction_reason / is_corrected – ручная корректировка (UC-4).
-- =====================================================================

CREATE DATABASE IF NOT EXISTS santa_promo
    DEFAULT CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;

USE santa_promo;

CREATE TABLE IF NOT EXISTS promo_campaign (
    id_promo   INT AUTO_INCREMENT PRIMARY KEY,
    promo_name VARCHAR(150) NOT NULL,
    start_date DATE NOT NULL,
    end_date   DATE NOT NULL,
    status     VARCHAR(20) NOT NULL DEFAULT 'DRAFT',
    CONSTRAINT chk_promo_dates CHECK (end_date > start_date)
) ENGINE=InnoDB;

CREATE TABLE IF NOT EXISTS product (
    id_product  INT PRIMARY KEY,              -- SKU из ERP-системы
    name        VARCHAR(100) NOT NULL,
    category    VARCHAR(50)  NOT NULL,        -- например, «Фреш», «Бакалея»
    base_price  DECIMAL(10,2) NOT NULL,
    pack_qty    INT NOT NULL DEFAULT 1,       -- квант поставки (BR-2)
    CONSTRAINT chk_pack_qty CHECK (pack_qty >= 1)
) ENGINE=InnoDB;

CREATE TABLE IF NOT EXISTS store (
    id_store INT PRIMARY KEY,
    address  VARCHAR(200) NOT NULL,
    format   VARCHAR(50)  NOT NULL         -- «Супермаркет», «У дома» и т. п.
) ENGINE=InnoDB;

CREATE TABLE IF NOT EXISTS promo_product (
    id_promo_prod    INT AUTO_INCREMENT PRIMARY KEY,
    id_promo         INT NOT NULL,
    id_product       INT NOT NULL,
    discount_percent DECIMAL(5,2) NOT NULL,
    CONSTRAINT chk_discount CHECK (discount_percent > 0 AND discount_percent <= 50),
    FOREIGN KEY (id_promo) REFERENCES promo_campaign(id_promo) ON DELETE CASCADE,
    FOREIGN KEY (id_product) REFERENCES product(id_product)
) ENGINE=InnoDB;

CREATE TABLE IF NOT EXISTS forecast_result (
    id_forecast       INT AUTO_INCREMENT PRIMARY KEY,
    id_promo_prod     INT NOT NULL,
    id_store          INT NOT NULL,
    baseline_qty      SMALLINT NOT NULL DEFAULT 0,
    uplift_qty        SMALLINT NOT NULL,
    final_order_qty   INT NOT NULL,
    status            VARCHAR(20) NOT NULL DEFAULT 'CREATED',
    correction_reason VARCHAR(100) NULL,
    is_corrected      BOOLEAN NOT NULL DEFAULT FALSE,
    CONSTRAINT chk_baseline CHECK (baseline_qty >= 0),
    CONSTRAINT chk_final_order CHECK (final_order_qty >= 0),
    FOREIGN KEY (id_promo_prod) REFERENCES promo_product(id_promo_prod) ON DELETE CASCADE,
    FOREIGN KEY (id_store) REFERENCES store(id_store)
) ENGINE=InnoDB;

-- Индексы (ЛР7, физическое проектирование)
CREATE INDEX idx_forecast_store_id ON forecast_result(id_store);
CREATE INDEX idx_promo_product_promo ON promo_product(id_promo);
CREATE INDEX idx_forecast_promo_prod ON forecast_result(id_promo_prod);
