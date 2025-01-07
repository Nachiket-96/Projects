create table tabl_customer
(
Id int,
name varchar(100),
city varchar(100)

)


insert into tabl_customer values (1, 'Rajesh Kumar', 'Mumbai'),
(2, 'Priya Sharma', 'Delhi'),
(3, 'Amit Verma', 'Bangalore'),
(4, 'Sneha Gupta', 'Kolkata'),
(5, 'Rahul Mehta', 'Ahmedabad'),
(6, 'Anjali Singh', 'Pune'),
(7, 'Vikram Patel', 'Surat'),
(8, 'Pooja Desai', 'Jaipur'),
(9, 'Arjun Nair', 'Chennai'),
(10, 'Neha Joshi', 'Hyderabad');

select * from tabl_customer

create table tabl_orders
(
    OrderId int,
    CustomerId int,
    OrderDate date,
    TotalAmount decimal(10,2)
);

insert into tabl_orders values
(101, 1, '2024-12-01', 1500.50),
(102, 3, '2024-12-02', 3500.00),
(103, 5, '2024-12-03', 750.25),
(104, 7, '2024-12-04', 2100.00),
(105, 9, '2024-12-05', 500.75);


create table tabl_products
(
    ProductId int,
    ProductName varchar(100),
    Price decimal(10,2)
);

insert into tabl_products values
(201, 'Mobile Phone', 15000.00),
(202, 'Laptop', 55000.00),
(203, 'Tablet', 25000.00),
(204, 'Smartwatch', 5000.00),
(205, 'Headphones', 2000.00);


create table tabl_metadata
(
    TableName varchar(100),
    ColumnName varchar(100),
    DataType varchar(50),
    Description varchar(255)
);

insert into tabl_metadata values
('tabl_customer', 'Id', 'int', 'Unique identifier for customers'),
('tabl_customer', 'name', 'varchar(100)', 'Customer name'),
('tabl_customer', 'city', 'varchar(100)', 'City of the customer'),

('tabl_orders', 'OrderId', 'int', 'Unique identifier for orders'),
('tabl_orders', 'CustomerId', 'int', 'Reference to the customer who placed the order'),
('tabl_orders', 'OrderDate', 'date', 'Date of the order'),
('tabl_orders', 'TotalAmount', 'decimal(10,2)', 'Total amount of the order'),

('tabl_products', 'ProductId', 'int', 'Unique identifier for products'),
('tabl_products', 'ProductName', 'varchar(100)', 'Name of the product'),
('tabl_products', 'Price', 'decimal(10,2)', 'Price of the product');


select * from tabl_metadata