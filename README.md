# RentalDB - Equipment Rental Management System

A full-stack web application designed to streamline the management of equipment inventory, customer records, and rental transactions.

## Project Overview

RentalDB provides a centralized platform for businesses to track their equipment inventory across multiple branches, manage customer registrations, and process rental bookings and payments. The system includes built-in analytics for business intelligence.

## Core Functionality

### Inventory Management
- Real-time tracking of equipment status (Available, Rented, Maintenance).
- Categorized inventory with support for parent-child equipment relationships.
- Branch-wise stock management.

### Customer & Rental Operations
- Secure customer registration with PBKDF2 password hashing.
- Complete rental lifecycle: Booking -> Status Tracking -> Returns.
- Integrated payment recording with status tracking (Pending, Completed, Failed).

### Business Intelligence
- Revenue analysis by branch.
- Customer loyalty tracking (repeat rental statistics).
- Inventory utilization reports.

## Technical Stack

- Backend: Python / Flask
- Database: MySQL (Relational)
- Security: Werkzeug (Password Hashing)
- Frontend: HTML5, CSS3, Jinja2

## Technical Implementation Details

### Relational Database Design
The project implements a relational schema with normalized tables for Customers, Equipment, Rentals, Payments, Staff, and Branches. Complex queries utilize:
- JOINs for cross-table data retrieval.
- GROUP BY and AVG for financial reporting.
- HAVING clauses for conditional analytics on aggregated data.

### Security
Sensitive user information is protected using industry-standard hashing. All database interactions are parameterized to prevent SQL injection.

## Setup and Installation

### 1. Requirements
- Python 3.x
- MySQL Server

### 2. Installation
Install the required Python packages:
pip install flask mysql-connector-python werkzeug

### 3. Database Configuration
1. Create a database named 'RentalDB' in your MySQL instance.
2. Update the connection parameters in the get_db() function in app.py:
   - host: Database server address
   - user: MySQL username
   - password: MySQL password

### 4. Running the Application
python app.py
The application will be available at http://localhost:5000

## Docker Deployment

You can run the entire stack (Flask + MySQL) using Docker:

1. Build and start the containers:
   docker-compose up --build

2. The application will be available at http://localhost:5000 and the database on port 3306.

## Directory Structure

- app.py: Entry point containing core application logic and routing.
- templates/: Jinja2 HTML templates for the frontend.
- static/: Static assets including CSS for custom styling.
- README.md: Documentation.
