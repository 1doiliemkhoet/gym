USE gym_management;

CREATE TABLE IF NOT EXISTS body_metrics (
    id INT AUTO_INCREMENT PRIMARY KEY,
    member_id INT NOT NULL,
    chieu_cao DECIMAL(5, 2), -- Đơn vị: cm 
    can_nang DECIMAL(5, 2),  -- Đơn vị: kg 
    bmi DECIMAL(4, 2),       -- Chỉ số BMI tự động tính 
    ngay_ghi_nhan DATE DEFAULT (CURDATE()), -- 
    ghi_chu TEXT,
    CONSTRAINT fk_metrics_member FOREIGN KEY (member_id) 
    REFERENCES members(id) ON DELETE CASCADE -- Tự động xóa nếu hội viên nghỉ tập [cite: 2026-01-28]
) ENGINE=InnoDB;