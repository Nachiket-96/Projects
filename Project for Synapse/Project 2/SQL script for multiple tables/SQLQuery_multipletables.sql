-- Table: Department (Regular Table)
CREATE TABLE Department (
    DepartmentID INT,
    DepartmentName VARCHAR(50),
    Location VARCHAR(50),
    ManagerName VARCHAR(50),
    EstablishedDate DATE
);

-- Table: Employee (SCD Type 1 - Basic details can be overwritten)
CREATE TABLE Employee (
    EmployeeID INT,
    FirstName VARCHAR(50),
    LastName VARCHAR(50),
    Email VARCHAR(50),
    DepartmentID INT
);

-- Table: Product (SCD Type 2 - Historical changes tracked)
CREATE TABLE Product (
    ProductID INT,
    ProductName VARCHAR(50),
    Price DECIMAL(10, 2),
    StartDate DATE,
    EndDate DATE
);


CREATE TABLE Cust_scdtype1
(
Id int,
name varchar(50),
city varchar(50),
phonenumber BigInt,
created_by varchar(100),
created_date datetime,
Updated_by varchar(100),
updated_date datetime,
HashKey Bigint
)



CREATE TABLE CUST_TYPE2
(
CustId int,
CustName varchar(100),
CustCity Varchar(100),
CustPhonenumber BigInt,
CustEffective_StartDate datetime,
CustEffective_EndDate datetime,
Created_by varchar(100),
Created_on datetime,
Updated_by varchar(100),
Updated_on datetime,
HashKey BigInt,
Is_Active Int
)




-- Insert data into Department
INSERT INTO Department (DepartmentID, DepartmentName, Location, ManagerName, EstablishedDate) VALUES
(1, 'Human Resources', 'Building A', 'Alice Smith', '2015-01-01'),
(2, 'IT', 'Building B', 'Bob Johnson', '2016-05-10'),
(3, 'Marketing', 'Building C', 'Carol Williams', '2017-03-15'),
(4, 'Sales', 'Building D', 'David Brown', '2018-07-20'),
(5, 'Finance', 'Building E', 'Eve Davis', '2019-09-25');

-- Insert data into Employee (SCD Type 1 - Data can be overwritten)
INSERT INTO Employee (EmployeeID, FirstName, LastName, Email, DepartmentID) VALUES
(1, 'Alice', 'Smith', 'alice.smith@company.com', 1),
(2, 'Bob', 'Johnson', 'bob.johnson@company.com', 2),
(3, 'Carol', 'Williams', 'carol.williams@company.com', 3),
(4, 'David', 'Brown', 'david.brown@company.com', 4),
(5, 'Eve', 'Davis', 'eve.davis@company.com', 5);

-- Insert data into Product (SCD Type 2 - Historical changes tracked)
INSERT INTO Product (ProductID, ProductName, Price, StartDate, EndDate) VALUES
(1, 'Laptop', 1500.00, '2023-01-01', '2023-06-30'),
(1, 'Laptop', 1400.00, '2023-07-01', NULL),
(2, 'Mouse', 25.00, '2023-01-01', '2023-03-31'),
(2, 'Mouse', 20.00, '2023-04-01', NULL),
(3, 'Keyboard', 50.00, '2023-01-01', NULL);


----drop table Product,Employee, Department, Cust_scdtype1, CUST_TYPE2

------

INSERT INTO Cust_scdtype1 (Id, name, city, phonenumber, created_by)
VALUES (1, 'Alice Smith', 'Toronto', 6471234567, 'admin');

INSERT INTO Cust_scdtype1 (Id, name, city, phonenumber, created_by)
VALUES (2, 'Bob Johnson', 'Vancouver', 7789876543, 'admin');

INSERT INTO Cust_scdtype1 (Id, name, city, phonenumber, created_by)
VALUES (3, 'Charlie Brown', 'Montreal', 5146543210, 'manager');

INSERT INTO Cust_scdtype1 (Id, name, city, phonenumber, created_by)
VALUES (4, 'Diana Prince', 'Ottawa', 6137891234, 'supervisor');

INSERT INTO Cust_scdtype1 (Id, name, city, phonenumber, created_by)
VALUES (5, 'Eve Adams', 'Calgary', 4033219876, 'admin');


INSERT INTO CUST_TYPE2 (CustId, CustName, CustCity, CustPhonenumber, CustEffective_StartDate, CustEffective_EndDate, Created_by, Created_on, Updated_by, Updated_on, HashKey, Is_Active)
VALUES (1, 'Alice Smith', 'Toronto', 6471234567, '2024-01-01', '2024-12-31', 'admin', '2024-01-01', 'admin', '2024-10-25', 1001, 1);

INSERT INTO CUST_TYPE2 (CustId, CustName, CustCity, CustPhonenumber, CustEffective_StartDate, CustEffective_EndDate, Created_by, Created_on, Updated_by, Updated_on, HashKey, Is_Active)
VALUES (2, 'Bob Johnson', 'Vancouver', 7789876543, '2023-05-10', '2024-05-10', 'admin', '2023-05-10', 'manager', '2024-05-10', 1002, 0);

INSERT INTO CUST_TYPE2 (CustId, CustName, CustCity, CustPhonenumber, CustEffective_StartDate, CustEffective_EndDate, Created_by, Created_on, Updated_by, Updated_on, HashKey, Is_Active)
VALUES (3, 'Charlie Brown', 'Montreal', 5146543210, '2024-03-15', '2025-03-15', 'manager', '2024-03-15', 'admin', '2024-10-25', 1003, 1);

INSERT INTO CUST_TYPE2 (CustId, CustName, CustCity, CustPhonenumber, CustEffective_StartDate, CustEffective_EndDate, Created_by, Created_on, Updated_by, Updated_on, HashKey, Is_Active)
VALUES (4, 'Diana Prince', 'Ottawa', 6137891234, '2022-11-20', '2023-11-20', 'supervisor', '2022-11-20', 'supervisor', '2023-11-20', 1004, 0);

INSERT INTO CUST_TYPE2 (CustId, CustName, CustCity, CustPhonenumber, CustEffective_StartDate, CustEffective_EndDate, Created_by, Created_on, Updated_by, Updated_on, HashKey, Is_Active)
VALUES (5, 'Eve Adams', 'Calgary', 4033219876, '2024-07-01', '2025-07-01', 'admin', '2024-07-01', 'admin', '2024-10-25', 1005, 1);

drop table tbl_watermark
CREATE TABLE tbl_watermark
(
    TableName varchar(50),
    WatermarkValue datetime
);
alter table tbl_watermark add delta_col varchar(100)
-----select * from tbl_watermark
-----truncate table tbl_watermark
-- Inserting values for the specified tables

INSERT INTO tbl_watermark (TableName, WatermarkValue, delta_col)
VALUES ('Product', '2024-10-01', 'EndDate');

INSERT INTO tbl_watermark (TableName, WatermarkValue, delta_col)
VALUES ('Department', '2024-10-03', 'EstablishedDate');

INSERT INTO tbl_watermark (TableName, WatermarkValue, delta_col)
VALUES ('CUST_TYPE2', '2024-10-05', 'CustEffective_StartDate');

select max(Id) as Maxvalue from Cust_scdtype1
select * from Product where '1'>'2024-10-01 00:00:00'





CREATE proc usp_Watermark
    @TableName varchar(50),
    @WatermarkValue datetime
 as
INSERT INTO tbl_watermark (TableName, WatermarkValue)
    VALUES (@TableName, @WatermarkValue);

