CREATE TABLE Customer (
    CustomerID INT,
    FirstName VARCHAR(50),
    LastName VARCHAR(50),
    Email VARCHAR(100)
);

INSERT INTO Customer (CustomerID, FirstName, LastName, Email) VALUES
(1, 'John', 'Doe', 'john.doe@example.com'),
(2, 'Jane', 'Smith', 'jane.smith@example.com'),
(3, 'Alex', 'Johnson', 'alex.johnson@example.com');

CREATE TABLE Product (
    ProductID INT,
    ProductName VARCHAR(100),
    Category VARCHAR(50),
    Price DECIMAL(10, 2)
);

INSERT INTO Product (ProductID, ProductName, Category, Price) VALUES
(1, 'Laptop', 'Electronics', 899.99),
(2, 'Headphones', 'Accessories', 199.99),
(3, 'Coffee Maker', 'Appliances', 79.99);


CREATE TABLE Order (
    OrderID INT,
    OrderDate DATE,
    CustomerID INT,
    ProductID INT,
    Quantity INT
);

INSERT INTO Order (OrderID, OrderDate, CustomerID, ProductID, Quantity) VALUES
(1, '2024-10-01', 1, 1, 1),
(2, '2024-10-02', 2, 2, 2),
(3, '2024-10-03', 3, 3, 1);


CREATE TABLE CustomerType1 (
    CustomerID INT,
    FirstName VARCHAR(50),
    LastName VARCHAR(50),
    Email VARCHAR(100)
);

-- Initial load
INSERT INTO CustomerType1 (CustomerID, FirstName, LastName, Email) VALUES
(1, 'John', 'Doe', 'john.doe@example.com');

-- Incremental load with SCD Type 1 (update)
-- John Doe's last name changed
UPDATE CustomerType1 
SET LastName = 'Smith-Doe'
WHERE CustomerID = 1;


CREATE TABLE CustomerType2 (
    CustomerID INT,
    FirstName VARCHAR(50),
    LastName VARCHAR(50),
    Email VARCHAR(100),
    StartDate DATE,
    EndDate DATE,
    IsCurrent CHAR(1)
);

-- Initial load
INSERT INTO CustomerType2 (CustomerID, FirstName, LastName, Email, StartDate, EndDate, IsCurrent) VALUES
(1, 'John', 'Doe', 'john.doe@example.com', '2024-01-01', NULL, 'Y');

-- Incremental load with SCD Type 2 (insert)
-- John Doe's last name changed, so we close the previous record and add a new one
UPDATE CustomerType2 
SET EndDate = '2024-10-25', IsCurrent = 'N'
WHERE CustomerID = 1 AND IsCurrent = 'Y';

INSERT INTO CustomerType2 (CustomerID, FirstName, LastName, Email, StartDate, EndDate, IsCurrent) VALUES
(1, 'John', 'Smith-Doe', 'john.doe@example.com', '2024-10-26', NULL, 'Y');
