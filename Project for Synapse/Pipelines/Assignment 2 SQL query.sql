CREATE TABLE students
(studentID int primary key,
name varchar(50),
age int,
phone_number bigint,
address varchar(50)
)

INSERT into students values (1,'Nachiket',25,6399971996,'Gandhinagar')
INSERT into students values (2,'Dhruti',24,3063514488,'Junagarh')
INSERT into students values (3,'Tirth',23,3063005000,'Ahmedabad')
INSERT into students values (4,'Mansi',26,6395554123,'Kalol')
INSERT into students values (5,'Neel',27,6396667585,'Kadi')


CREATE TABLE Courses (
    course_name VARCHAR(50),
    courseID INT,
    course_credit INT,
    studentID INT,
    FOREIGN KEY (studentID) REFERENCES students(studentID)
);

INSERT into Courses values ('Data analytics',600,3,5);
INSERT into Courses values ('Business Management',354,1,4);
INSERT into Courses values ('Maths',211,3,2);
INSERT into Courses values ('CDBM',752,5,1);

select * from students
select * from Courses

drop table Courses

--JOINS

SELECT students.studentID, students.name, Courses.studentID
From students 
Join Courses ON students.studentID=Courses.studentID

SELECT students.studentID, students.name, Courses.studentID
From students 
Left Join Courses ON students.studentID=Courses.studentID

SELECT students.studentID, students.name, Courses.studentID
From students 
Right Join Courses ON students.studentID=Courses.studentID

SELECT students.studentID, students.name, Courses.studentID
From students 
Cross Join Courses 



-- Count enrollments for each student
SELECT students.studentID, students.name, COUNT(Courses.course_name) AS enrollment_count
FROM students
LEFT JOIN Courses ON students.studentID = Courses.studentID
GROUP BY students.studentID, students.name;


-- Identify students with zero enrollments
SELECT students.studentID, students.name
FROM students
LEFT JOIN Courses ON students.studentID = Courses.studentID
WHERE Courses.course_name IS NULL;


-- The students table already has a primary key.
-- The Courses table has a foreign key constraint.

-- Attempt to insert a duplicate studentID into students
INSERT INTO students (studentID, name, age, phone_number, address) VALUES (1, 'Arjun', 28, 1234567890, 'Pune');  -- This will fail

-- Attempt to insert a course with a non-existent studentID
INSERT INTO Courses (course_name, courseID, course_credit, studentID) VALUES ('Physics', 800, 3, 10);  -- This will fail


