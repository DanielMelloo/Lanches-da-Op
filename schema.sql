-- Database Schema for Lanches da Operação

-- CREATE DATABASE IF NOT EXISTS lanches_db;
-- USE lanches_db;

-- Subsites
CREATE TABLE IF NOT EXISTS subsites (
    id INT AUTO_INCREMENT PRIMARY KEY,
    name VARCHAR(50) NOT NULL UNIQUE,
    active BOOLEAN DEFAULT TRUE,
    require_payment BOOLEAN DEFAULT FALSE
);

-- Users
CREATE TABLE IF NOT EXISTS users (
    id INT AUTO_INCREMENT PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    phone VARCHAR(20),
    petro_key VARCHAR(4) NOT NULL UNIQUE,
    password_hash VARCHAR(256),
    role ENUM('user', 'admin', 'admin_master') DEFAULT 'user',
    subsite_id INT,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    active BOOLEAN DEFAULT TRUE,
    FOREIGN KEY (subsite_id) REFERENCES subsites(id)
);

-- Stores
CREATE TABLE IF NOT EXISTS stores (
    id INT AUTO_INCREMENT PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    active BOOLEAN DEFAULT TRUE,
    subsite_id INT NOT NULL,
    FOREIGN KEY (subsite_id) REFERENCES subsites(id) ON DELETE CASCADE
);

-- Items
CREATE TABLE IF NOT EXISTS items (
    id INT AUTO_INCREMENT PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    price FLOAT NOT NULL,
    active BOOLEAN DEFAULT TRUE,
    image_url VARCHAR(500),
    subitems_json JSON,
    store_id INT NOT NULL,
    FOREIGN KEY (store_id) REFERENCES stores(id) ON DELETE CASCADE
);

-- Sectors
CREATE TABLE IF NOT EXISTS sectors (
    id INT AUTO_INCREMENT PRIMARY KEY,
    name VARCHAR(50) NOT NULL,
    subsite_id INT,
    FOREIGN KEY (subsite_id) REFERENCES subsites(id)
);

-- Statuses
CREATE TABLE IF NOT EXISTS statuses (
    id INT AUTO_INCREMENT PRIMARY KEY,
    name VARCHAR(50) NOT NULL,
    type VARCHAR(20),
    sort_order INT DEFAULT 0,
    subsite_id INT
);

-- Orders
CREATE TABLE IF NOT EXISTS orders (
    id INT AUTO_INCREMENT PRIMARY KEY,
    user_id INT NOT NULL,
    subsite_id INT NOT NULL,
    sector_id INT,
    status_id INT NOT NULL,
    section VARCHAR(50),
    total_items FLOAT DEFAULT 0.0,
    tax_fixed FLOAT DEFAULT 0.0,
    service_fee FLOAT DEFAULT 0.0,
    total_general FLOAT DEFAULT 0.0,
    payment_required BOOLEAN DEFAULT FALSE,
    payment_status VARCHAR(20) DEFAULT 'pending',
    pix_charge_id VARCHAR(100),
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id),
    FOREIGN KEY (subsite_id) REFERENCES subsites(id),
    FOREIGN KEY (sector_id) REFERENCES sectors(id),
    FOREIGN KEY (status_id) REFERENCES statuses(id)
);

-- Order Items
CREATE TABLE IF NOT EXISTS order_items (
    id INT AUTO_INCREMENT PRIMARY KEY,
    order_id INT NOT NULL,
    item_id INT NOT NULL,
    quantity INT DEFAULT 1,
    price_at_moment FLOAT NOT NULL,
    subtotal FLOAT NOT NULL,
    FOREIGN KEY (order_id) REFERENCES orders(id) ON DELETE CASCADE,
    FOREIGN KEY (item_id) REFERENCES items(id)
);
