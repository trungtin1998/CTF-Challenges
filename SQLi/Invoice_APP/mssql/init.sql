CREATE DATABASE flaskdb;
GO
USE flaskdb;


CREATE TABLE invoices (
    id INT PRIMARY KEY IDENTITY(1,1),
    invoice_number NVARCHAR(52),
    customer_name NVARCHAR(100),
    total_amount DECIMAL(10,2),
    created_at DATETIME DEFAULT GETDATE()
)
INSERT INTO invoices (invoice_number, customer_name, total_amount)
VALUES
('INV-000000000001', 'Nguyen Van A', 100.00),
('INV-000000000002', 'Tran Duc B', 250.50),
('INV-000000000003', 'Nguyen Quoc T', 400.75);

GO


CREATE TABLE invoice_items (
    item_id INT PRIMARY KEY IDENTITY(1,1),
    invoice_id INT NOT NULL,
    description NVARCHAR(100),
    amount DECIMAL(10,2),
    FOREIGN KEY (invoice_id) REFERENCES invoices(id)
)
GO


SET QUOTED_IDENTIFIER ON;
SET ANSI_NULLS ON;
GO


CREATE TRIGGER [PreventDropInvoices]
ON DATABASE
FOR
DROP_TABLE
AS
DECLARE @eventData XML,
@uname NVARCHAR(50),
@oname NVARCHAR(100),
@otext VARCHAR(MAX),
@etype NVARCHAR(100),
@edate DATETIME
SET @eventData = eventdata()
SELECT
    @edate=GETDATE(),
    @uname=@eventData.value('data(/EVENT_INSTANCE/UserName)[1]', 'SYSNAME'),
    @oname=@eventData.value('data(/EVENT_INSTANCE/ObjectName)[1]', 'SYSNAME'),
    @otext=@eventData.value('data(/EVENT_INSTANCE/TSQLCommand/CommandText)[1]',
'VARCHAR(MAX)'),
    @etype=@eventData.value('data(/EVENT_INSTANCE/EventType)[1]', 'nvarchar(100)')
IF @oname IN ('invoices','invoice_items')
BEGIN
    DECLARE @err varchar(100)
    PRINT 'Dropping table ' + @oname + ' is not allowed.'
    ROLLBACK;
END
GO

ENABLE TRIGGER [PreventDropInvoices] ON DATABASE
GO