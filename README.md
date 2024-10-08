# Zoo Health Monitoring System

## Project Description
The **Zoo Health Monitoring System** is a web application designed to assist zookeepers in monitoring the health and behavior of animals within a zoo. This system leverages image processing techniques to allow staff to upload periodic images of the animals, enabling them to track changes in appearance and identify potential health issues. By comparing new images with previous records, the application can detect significant changes that may indicate health concerns, such as skin problems or weight fluctuations.

The application is built using Flask, a Python web framework, and features a PostgreSQL database for storing animal and image data. Additionally, the system sends alert notifications via email when significant changes are detected, ensuring that zookeepers can respond promptly to any potential health issues.

## Table of Contents
- [Features](#features)
- [Tools](#tools)
- [Photos](#photos)

## Features
- **Animal Health Tracking:** Allows zookeepers to monitor the health of animals over time.
- **Image Upload:** Enables the uploading of periodic images of animals for health assessment.
- **Image Comparison:** Compares new images with previous ones to detect changes in appearance.
- **Skin Issue Detection:** Utilizes image processing to identify potential skin issues based on uploaded images.
- **Health Alerts:** Sends notifications via email if significant changes in an animal's health are detected.
- **Database Integration:** Stores animal data and image records in a PostgreSQL database.

## Tools
- **Programming Languages:** Python, HTML, CSS, JavaScript
- **Frameworks:** Flask for backend, Bootstrap for frontend styling
- **Image Processing:** OpenCV for image comparison and analysis
- **Database:** PostgreSQL for data storage
- **Email Notifications:** smtplib for sending alerts
- **Virtual Environment:** venv for managing dependencies

## Photos
![Application Photo 1](Screenshot%202024-10-08%20113021.png)
![Application Photo 2](Screenshot%202024-10-08%20113100.png)
