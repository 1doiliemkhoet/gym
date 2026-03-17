USE gym_management;

CREATE TABLE IF NOT EXISTS email_logs (
    id INT AUTO_INCREMENT PRIMARY KEY,
    member_id INT, -- Phải để INT y hệt bảng members
    log_type VARCHAR(50), -- Ví dụ: 'expiry_7d'
    sent_date DATE,
    -- Thiết lập khóa ngoại với tên gợi nhớ
    CONSTRAINT fk_email_member FOREIGN KEY (member_id) 
    REFERENCES members(id) 
    ON DELETE CASCADE -- Nếu xóa hội viên, lịch sử mail cũng tự xóa theo
) ENGINE=InnoDB;