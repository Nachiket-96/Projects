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

-- Insert data into Project
INSERT INTO Project (ProjectID, ProjectName, Budget, StartDate, EndDate) VALUES
(1, 'Website Redesign', 50000.00, '2023-01-01', '2023-06-01'),
(2, 'Mobile App Development', 80000.00, '2023-02-01', '2023-08-01'),
(3, 'Marketing Campaign', 60000.00, '2023-03-01', '2023-09-01'),
(4, 'Customer Service Improvement', 40000.00, '2023-04-01', '2023-10-01'),
(5, 'Financial Audit', 30000.00, '2023-05-01', '2023-11-01');

-- Insert data into Supplier
INSERT INTO Supplier (SupplierID, SupplierName, ContactPerson, ContactNumber, Location) VALUES
(1, 'Tech Supplies Inc.', 'John Doe', '555-1234', 'City Center'),
(2, 'Office Essentials', 'Jane Smith', '555-5678', 'Downtown'),
(3, 'Marketing Solutions', 'Mike Johnson', '555-9012', 'Uptown'),
(4, 'Sales Pros', 'Sara White', '555-3456', 'East End'),
(5, 'Finance Partners', 'Linda Green', '555-7890', 'West End');


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


