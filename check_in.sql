USE gym_management;

CREATE TABLE IF NOT EXISTS check_ins (
    check_in_id INT AUTO_INCREMENT PRIMARY KEY,
    member_id INT,
    check_in_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (member_id) REFERENCES members(id) ON DELETE CASCADE
);