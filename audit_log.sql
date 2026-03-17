USE gym_management;

-- Bảng Nhật ký hệ thống (Audit Logs) [cite: 2026-01-25, 2026-01-28]
CREATE TABLE IF NOT EXISTS audit_logs (
    log_id INT AUTO_INCREMENT PRIMARY KEY,
    user_action VARCHAR(255),
    table_affected VARCHAR(50),
    record_id INT,
    action_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    ip_address VARCHAR(45)
);

-- Kích hoạt trình lập lịch và tạo sự kiện tự động khóa khách hết hạn [cite: 2026-01-28]
SET GLOBAL event_scheduler = ON;

DELIMITER $$
CREATE EVENT IF NOT EXISTS auto_expire_members
ON SCHEDULE EVERY 1 DAY
STARTS (TIMESTAMP(CURRENT_DATE) + INTERVAL 1 DAY)
DO
BEGIN
    UPDATE members 
    SET trang_thai = 'Expired' 
    WHERE ngay_het_han < CURDATE() AND trang_thai = 'Active';
END$$
DELIMITER ;