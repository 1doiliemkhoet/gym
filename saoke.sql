USE gym_management;

CREATE TABLE IF NOT EXISTS payments (
    payment_id INT AUTO_INCREMENT PRIMARY KEY,
    member_id INT,
    amount DECIMAL(10, 2) NOT NULL,
    payment_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    payment_method ENUM('Cash', 'Transfer', 'Card') DEFAULT 'Cash',
    content TEXT, -- Ví dụ: "Đăng ký mới gói 3 tháng" hoặc "Gia hạn gói 1 tháng"
    FOREIGN KEY (member_id) REFERENCES members(id) ON DELETE CASCADE
);