# Student Management System

A web-based **Student Management System** developed using **Laravel, PHP, Tailwind CSS, Vite, and SQLite**. The project is designed to provide a structured platform for managing student-related information through a modern web application.

## 🚀 Project Overview

The Student Management System is a Laravel-based application that provides a foundation for managing student data and related administrative operations.

The project uses Laravel 12 as the backend framework with Vite and Tailwind CSS for the frontend development environment.

## ✨ Features

* Student management
* Student information management
* Admin-oriented management system
* Laravel-based backend
* Responsive frontend interface
* PDF generation support
* Excel export/import support
* SQLite database support
* Modern development setup using Vite
* Form and HTTP request handling with Axios

## 🛠️ Technologies Used

### Backend

* PHP 8.2+
* Laravel 12
* Laravel Tinker

### Frontend

* HTML
* Tailwind CSS
* JavaScript
* Vite
* Axios

### Database

* SQLite

### Additional Packages

* Laravel DomPDF
* Maatwebsite Excel
* PHPUnit

## 📂 Project Structure

```text
student-management/
│
├── app/
├── bootstrap/
├── config/
├── database/
├── public/
├── resources/
├── routes/
├── storage/
├── tests/
│
├── artisan
├── composer.json
├── package.json
├── vite.config.js
├── phpunit.xml
├── .env.example
└── README.md
```

## ⚙️ Requirements

Before running the project, make sure you have:

* PHP 8.2 or higher
* Composer
* Node.js
* NPM
* Git

## 🔧 Installation

Clone the repository:

```bash
git clone https://github.com/YOUR-USERNAME/student-management.git
```

Go to the project directory:

```bash
cd student-management
```

Install PHP dependencies:

```bash
composer install
```

Install frontend dependencies:

```bash
npm install
```

Create the environment file:

```bash
cp .env.example .env
```

Generate the Laravel application key:

```bash
php artisan key:generate
```

Create the SQLite database if required:

```bash
touch database/database.sqlite
```

Run migrations:

```bash
php artisan migrate
```

Build frontend assets:

```bash
npm run build
```

## ▶️ Run the Project

Start the Laravel development server:

```bash
php artisan serve
```

Then open:

```text
http://127.0.0.1:8000
```

For frontend development with Vite:

```bash
npm run dev
```

## 🗄️ Database

The project is configured to use **SQLite** by default.

Database configuration can be managed through the `.env` file.

**Do not upload your `.env` file to GitHub.** Use `.env.example` instead.

## 📸 Screenshots

Add project screenshots here:

```markdown
![Dashboard](screenshots/dashboard.png)

![Student Management](screenshots/students.png)
```

## 🎯 Purpose

This project was developed as a practical web application for understanding and implementing:

* Laravel application development
* CRUD-based management systems
* Database integration
* Frontend asset management
* PDF generation
* Excel functionality
* Modern PHP web development

## 🔮 Future Improvements

Possible future enhancements include:

* Authentication and role-based access
* Advanced student search and filtering
* Attendance management
* Course and subject management
* Student reports
* Dashboard analytics
* Notifications
* Online fee management
* Advanced admin dashboard

## 👨‍💻 Developer

**Mahesh**

B.Tech Cyber Security Engineer

## 📄 License

This project is intended for educational and development purposes.
