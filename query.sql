CREATE DATABASE IF NOT EXISTS gym_management;
USE gym_management;

CREATE TABLE IF NOT EXISTS members (
    id INT AUTO_INCREMENT PRIMARY KEY,
    ho_ten VARCHAR(100) NOT NULL,
    cccd VARCHAR(255) UNIQUE, 
    so_dien_thoai VARCHAR(15) NOT NULL UNIQUE,
    email VARCHAR(100) UNIQUE,
    goi_tap VARCHAR(50),
    gioi_tinh VARCHAR(10),
    ngay_sinh DATE,
    gia_tien DECIMAL(10, 2) DEFAULT 0,
    ngay_dang_ky DATE,
    ngay_het_han DATE,
    trang_thai ENUM('Active', 'Expired', 'Suspended') DEFAULT 'Active',
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
);