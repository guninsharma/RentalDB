-- ============================================================
-- RUBRIC 2: Auto-update trigger
-- After a new Rental row is inserted, this trigger automatically
-- sets the corresponding Equipment's Status to 'Rented'.
-- Run this ONCE in MySQL before using the web app.
-- ============================================================

DELIMITER //

CREATE TRIGGER after_rental_insert
AFTER INSERT ON Rental
FOR EACH ROW
BEGIN
    UPDATE Equipment
    SET Status = 'Rented'
    WHERE Equip_ID = NEW.Equip_ID;
END //

DELIMITER ;

-- ============================================================
-- Verify trigger exists:
-- SHOW TRIGGERS FROM RentalDB;
-- ============================================================
