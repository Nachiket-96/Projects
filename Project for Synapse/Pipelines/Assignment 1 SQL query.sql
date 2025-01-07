CREATE TABLE customers (
    custID INT PRIMARY KEY NOT NULL,
    customername VARCHAR(100),
    custphone BIGINT,
    country VARCHAR(50)
);


INSERT INTO customers VALUES (1, 'nachiket', 6399971996, 'Canada');
INSERT INTO customers VALUES (2, 'dhruti', 6399971998, 'Canada');
INSERT INTO customers VALUES (3, 'nik', 6399971796, 'Canada');
INSERT INTO customers VALUES (4, 'jamani', 6391856232, 'India');


CREATE TABLE orders (
    orderID INT PRIMARY KEY NOT NULL,
    ordername VARCHAR(50),
    orderdate VARCHAR(50),
    custID INT,
    FOREIGN KEY (custID) REFERENCES customers(custID)
);

INSERT INTO orders VALUES (1, 'laptop', 'september 25', 1);
INSERT INTO orders VALUES (2, 'mobile', 'september 21', 2);
INSERT INTO orders VALUES (3, 'tv', 'september 22', 3);
INSERT INTO orders VALUES (4, 'ipad', 'september 20', 4);

CREATE TABLE datetable (
    datekey INT PRIMARY KEY NOT NULL,
    months INT,
    years INT,
    daynumbers INT,
    daynames VARCHAR(100)
);

INSERT INTO datetable VALUES (2, 4, 2022, 20, 'Monday');
INSERT INTO datetable VALUES (5, 9, 2023, 7, 'Friday');
INSERT INTO datetable VALUES (7, 6, 2021, 11, 'Thursday');
INSERT INTO datetable VALUES (9, 8, 2020, 1, 'Wednesday');

CREATE TABLE sales (
    salesnumber INT PRIMARY KEY NOT NULL,
    productname VARCHAR(50),
    productID INT,
    custID INT,
    orderID INT,
    datekey INT,
    FOREIGN KEY (custID) REFERENCES customers(custID),
    FOREIGN KEY (orderID) REFERENCES orders(orderID),
    FOREIGN KEY (datekey) REFERENCES datetable(datekey)
);

INSERT INTO sales VALUES (100, 'Apple', 15, 1, 1, 2);
INSERT INTO sales VALUES (85, 'Microsoft', 25, 2, 2, 5);
INSERT INTO sales VALUES (45, 'Motorola', 34, 3, 3, 7);
INSERT INTO sales VALUES (79, 'Apple', 23, 4, 4, 9);

SELECT * FROM customers;
SELECT * FROM orders;
SELECT * FROM datetable;
SELECT * FROM sales;
