CREATE TABLE ClaimsDetails (
    ClaimID UNIQUEIDENTIFIER , 
    Items NVARCHAR(10),           
    Diagnosis NVARCHAR(100),          
    ServiceDate DATE,               
    Provider NVARCHAR(255),           
    Country NVARCHAR(50)             
);


CREATE TABLE ClaimsMaster (
    ClaimID UNIQUEIDENTIFIER ,         
    PolicyID UNIQUEIDENTIFIER ,       
    CustomerID UNIQUEIDENTIFIER ,      
    ClaimDate DATE ,                   
    ClaimAmount DECIMAL(18, 2) ,     
    ClaimType NVARCHAR(50),                    
    Region NVARCHAR(100),                    
    CustomerAge INT,                          
    CustomerGender NVARCHAR(10),               
    PolicyStartDate DATE,                   
    PolicyEndDate DATE                     
);



CREATE TABLE ClaimsPayment (
    PaymentID UNIQUEIDENTIFIER ,       
    ClaimID UNIQUEIDENTIFIER ,         
    PaymentDate DATE,                       
    PaymentAmount DECIMAL(18, 2) ,    
    PaymentStatus NVARCHAR(50)        
);



CREATE TABLE PolicyPremium (
    PolicyID UNIQUEIDENTIFIER ,        
    CustomerID UNIQUEIDENTIFIER ,    
    PremiumAmount DECIMAL(18, 2) ,    
    PaymentFrequency NVARCHAR(20) ,  
    LastPaymentDate DATE                   
);

---truncate table ClaimsDetails

--------------------------------------------

select * from PolicyPremium

select * from ClaimsPayment

select * from ClaimsMaster

select * from ClaimsDetails

---drop table ClaimsDetails, ClaimsMaster, ClaimsPayment, PolicyPremium
---------------------

